"""Transparent heuristic comparators; all outputs are independently audited."""

from collections import Counter, defaultdict

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

from splitmend import QUARANTINE as Q


def units(samples):
    # Benchmarks use one person group per record, or no group. Multi-group problems
    # are handled by SplitMend and the exhaustive tests, not this comparator adapter.
    d = defaultdict(list)
    for s in samples:
        if len(s.groups) > 1:
            raise ValueError("baseline adapter supports one group per row")
        d[s.groups[0] if s.groups else "row:" + s.id].append(s)
    return list(d.values())


def majority(samples, policy):
    assignment = {}
    for members in units(samples):
        locks = {s.original for s in members if s.locked}
        if len(locks) > 1:
            return None
        allowed = set(policy.partitions)
        for s in members:
            if s.allowed is not None:
                allowed.intersection_update(s.allowed)
        if policy.allow_quarantine:
            allowed.add(Q)
        if locks:
            allowed.intersection_update(locks)
        if not allowed:
            return None

        def cost(p):
            return sum(
                0 if s.original == p else s.weight * (policy.quarantine_cost if p == Q else 1)
                for s in members
            )

        best = min(allowed, key=lambda p: (cost(p), p))
        assignment.update({s.id: best for s in members})
    return assignment


def resplit(samples, policy, seed):
    all_units = units(samples)
    fixed = {}
    free = []
    for members in all_units:
        locks = {s.original for s in members if s.locked}
        if len(locks) > 1:
            return None
        if locks:
            fixed.update({s.id: next(iter(locks)) for s in members})
        else:
            free.extend(members)
    if not free:
        return fixed
    if any(s.allowed is not None for s in samples):
        # Deterministic time eligibility is the appropriate non-optimization baseline.
        return {
            s.id: s.original
            if s.allowed is None or s.original in s.allowed
            else s.allowed[0]
            if s.allowed
            else Q
            for s in samples
        }
    len(samples)
    desired_val = sum(s.original == "validation" for s in samples)
    fraction = min(0.95, max(0.05, desired_val / len(free)))
    groups = [s.groups[0] if s.groups else s.id for s in free]
    train, val = next(
        GroupShuffleSplit(n_splits=1, test_size=fraction, random_state=seed).split(
            np.arange(len(free)), groups=groups
        )
    )
    fixed.update({free[i].id: "train" for i in train})
    fixed.update({free[i].id: "validation" for i in val})
    return fixed


def greedy(samples, policy):
    a = majority(samples, policy)
    if a is None:
        return None
    all_units = units(samples)
    bounds = []
    for p, (lo, hi) in policy.size_bounds.items():
        bounds.append((None, p, lo, hi))
    for label, parts in policy.label_bounds.items():
        for p, (lo, hi) in parts.items():
            bounds.append((label, p, lo, hi))
    low = np.array([b[2] for b in bounds])
    high = np.array([b[3] for b in bounds])

    def contribution(members, p):
        labels = Counter(s.label for s in members)
        return np.array(
            [
                0 if dest != p else len(members) if label is None else labels[label]
                for label, dest, _, _ in bounds
            ]
        )

    state = sum((contribution(u, a[u[0].id]) for u in all_units), start=np.zeros(len(bounds)))

    def violation(state):
        return float(np.maximum(low - state, 0).sum() + np.maximum(state - high, 0).sum())

    def cost(u, p):
        return sum(
            0 if s.original == p else s.weight * (policy.quarantine_cost if p == Q else 1)
            for s in u
        )

    candidates = []
    for u in all_units:
        if any(s.locked for s in u):
            continue
        allowed = set(policy.partitions)
        for s in u:
            if s.allowed is not None:
                allowed.intersection_update(s.allowed)
        if policy.allow_quarantine:
            allowed.add(Q)
        candidates.append(
            (u, sorted(allowed), {p: contribution(u, p) for p in (*policy.partitions, Q)})
        )
    for _ in range(min(1000, len(all_units) * 3)):
        current = violation(state)
        if current == 0:
            break
        best = None
        for u, choices, vectors in candidates:
            old = a[u[0].id]
            for p in choices:
                if p == old:
                    continue
                next_state = state - vectors[old] + vectors[p]
                score = (violation(next_state), cost(u, p) - cost(u, old), u[0].id, p)
                if score[0] < current and (best is None or score < best[0]):
                    best = (score, u, p, next_state)
        if best is None:
            break
        _, u, p, state = best
        a.update({s.id: p for s in u})
    return a
