"""Two-partition patient repair comparators, with an explicit search budget.

The local method is a heuristic, not a globally optimal solver. Every result is
checked by the separate row-level verifier in the experiment driver.
"""

import time
from collections import Counter, defaultdict

import numpy as np


class PatientProfiles:
    def __init__(self, samples, policy):
        grouped = defaultdict(list)
        for row in samples:
            if len(row.groups) != 1 or row.weight != 1:
                raise ValueError("clinical comparator requires one patient token and unit costs")
            grouped[row.groups[0]].append(row)
        self.fixed = {}
        self.members = {}
        labels = sorted(policy.label_bounds)
        free = []
        for group, members in sorted(grouped.items()):
            locks = {s.original for s in members if s.locked}
            if locks:
                if locks != {"test"} or not all(s.locked for s in members):
                    raise ValueError("clinical adapter requires a completely locked test cohort")
                self.fixed.update({s.id: "test" for s in members})
            else:
                if any(set(s.allowed or ()) != {"train", "validation"} for s in members):
                    raise ValueError("free clinical patients must allow train and validation")
                if any(s.original not in {"train", "validation"} for s in members):
                    raise ValueError("unexpected original partition")
                self.members[group] = members
                free.append((group, members))
        profiles = {}
        self.bins = []
        vectors, deltas = [], []
        for group, members in free:
            counts = Counter(s.label for s in members)
            vector = (len(members), *(counts[label] for label in labels))
            train_cost = sum(s.original == "validation" for s in members)
            val_cost = len(members) - train_cost
            key = (vector, train_cost, val_cost)
            if key not in profiles:
                profiles[key] = len(vectors)
                vectors.append(vector)
                deltas.append(val_cost - train_cost)
                self.bins.append([[], []])
            # Match majority's deterministic tie in favor of training.
            side = int(val_cost < train_cost)
            self.bins[profiles[key]][side].append(group)
        self.vectors = np.array(vectors, dtype=np.int64)
        self.delta = np.array(deltas, dtype=np.int64)
        self.counts = np.array([[len(b[0]), len(b[1])] for b in self.bins], dtype=np.int64)
        total = self.counts.sum(axis=1) @ self.vectors
        self.state = self.counts[:, 1] @ self.vectors
        pairs = [policy.size_bounds, *(policy.label_bounds[label] for label in labels)]
        self.low = np.array(
            [max(b["validation"][0], int(t) - b["train"][1]) for t, b in zip(total, pairs)]
        )
        self.high = np.array(
            [min(b["validation"][1], int(t) - b["train"][0]) for t, b in zip(total, pairs)]
        )

    def violation(self, state):
        return np.maximum(self.low - state, 0).sum(axis=-1) + np.maximum(state - self.high, 0).sum(
            axis=-1
        )

    def move(self, profile, old):
        group = self.bins[profile][old].pop()
        self.bins[profile][1 - old].append(group)
        self.counts[profile, old] -= 1
        self.counts[profile, 1 - old] += 1
        self.state += (1 - 2 * old) * self.vectors[profile]

    def assignment(self):
        result = dict(self.fixed)
        for pair in self.bins:
            for side, groups in enumerate(pair):
                dest = ("train", "validation")[side]
                for group in groups:
                    result.update({s.id: dest for s in self.members[group]})
        return result


def greedy_repair(samples, policy, *, cost_aware=False, budget=60, pool_size=256):
    setup_start = time.perf_counter()
    model = PatientProfiles(samples, policy)
    preprocessing = time.perf_counter() - setup_start
    start = time.perf_counter()
    stop = start + budget
    steps, exchange_steps = 0, 0
    reason = "no_improving_violation_move"
    for _ in range(10000):
        current = int(model.violation(model.state))
        if current == 0:
            reason = "feasible"
            break
        if time.perf_counter() >= stop:
            reason = "budget"
            break
        profile, old = np.where(model.counts > 0)
        direction = 1 - 2 * old
        changes = direction[:, None] * model.vectors[profile]
        candidate_violation = model.violation(model.state + changes)
        improve = current - candidate_violation
        costs = direction * model.delta[profile]
        eligible = np.flatnonzero(improve > 0)
        if not len(eligible):
            break
        if cost_aware:
            ordered = np.lexsort(
                (
                    old[eligible],
                    profile[eligible],
                    costs[eligible],
                    -improve[eligible],
                    costs[eligible] / improve[eligible],
                )
            )
        else:
            ordered = np.lexsort(
                (old[eligible], profile[eligible], costs[eligible], candidate_violation[eligible])
            )
        best = eligible[ordered[0]]
        model.move(int(profile[best]), int(old[best]))
        steps += 1
    else:
        reason = "iteration_limit"

    if cost_aware and model.violation(model.state) == 0:
        reason = "local_neighborhood_exhausted"
        for _ in range(10000 - steps):
            if time.perf_counter() >= stop:
                reason = "budget_with_feasible_incumbent"
                break
            profile, old = np.where(model.counts > 0)
            direction = 1 - 2 * old
            costs = direction * model.delta[profile]
            eligible = np.flatnonzero(costs < 0)
            if len(eligible):
                next_states = (
                    model.state + direction[eligible, None] * model.vectors[profile[eligible]]
                )
                valid = model.violation(next_states) == 0
                eligible = eligible[valid]
            if len(eligible):
                ordered = np.lexsort((old[eligible], profile[eligible], costs[eligible]))
                best = eligible[ordered[0]]
                model.move(int(profile[best]), int(old[best]))
                exchange_steps += 1
                continue
            a = np.flatnonzero(model.counts[:, 0] > 0)
            b = np.flatnonzero(model.counts[:, 1] > 0)
            a = a[np.lexsort((a, model.delta[a]))[:pool_size]]
            b = b[np.lexsort((b, -model.delta[b]))[:pool_size]]
            best_pair = None
            for offset in range(0, len(a), 32):
                left = a[offset : offset + 32]
                if time.perf_counter() >= stop:
                    reason = "budget_with_feasible_incumbent"
                    break
                costs = model.delta[left, None] - model.delta[b]
                next_states = model.state + model.vectors[left, None, :] - model.vectors[b]
                valid = (costs < 0) & (model.violation(next_states) == 0)
                for i, j in zip(*np.where(valid)):
                    candidate = (int(costs[i, j]), int(left[i]), int(b[j]))
                    if best_pair is None or candidate < best_pair:
                        best_pair = candidate
            if best_pair is None:
                break
            _, i, j = best_pair
            model.move(i, 0)
            model.move(j, 1)
            exchange_steps += 1
        else:
            reason = "iteration_limit_with_feasible_incumbent"
    return model.assignment(), {
        "search_seconds": time.perf_counter() - start,
        "preprocessing_seconds": preprocessing,
        "greedy_steps": steps,
        "local_steps": exchange_steps,
        "stop_reason": reason,
        "profiles": len(model.vectors),
        "remaining_count_violation": int(model.violation(model.state)),
    }
