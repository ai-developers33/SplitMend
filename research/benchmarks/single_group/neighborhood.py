"""Unmodified helper function reused from the previous published-to-user pilot."""
import time
from collections import Counter, defaultdict
import numpy as np

def all_pair_greedy(samples, policy, budget=60):
    start = time.perf_counter()
    members = defaultdict(list)
    fixed = {}
    for row in samples:
        if row.locked:
            assert row.original == "test"
            fixed[row.id] = "test"
        else:
            assert len(row.groups) == 1 and row.weight == 1
            assert set(row.allowed) == {"train", "validation"}
            members[row.groups[0]].append(row)
    names = sorted(members)
    labels = sorted(policy.label_bounds)
    vectors, costs = [], []
    for name in names:
        rows = members[name]
        counts = Counter(r.label for r in rows)
        vectors.append([len(rows), *(counts[x] for x in labels)])
        costs.append([sum(r.original != p for r in rows) for p in ["train", "validation"]])
    vectors, costs = np.asarray(vectors), np.asarray(costs)
    total = vectors.sum(axis=0)
    limits = [policy.size_bounds, *(policy.label_bounds[x] for x in labels)]
    low = np.array([max(b["validation"][0], int(t)-b["train"][1]) for b,t in zip(limits,total)])
    high = np.array([min(b["validation"][1], int(t)-b["train"][0]) for b,t in zip(limits,total)])
    sides = (costs[:,1] < costs[:,0]).astype(int)
    n = len(names)
    pairs = [(i,) for i in range(n)] + [(i,j) for i in range(n) for j in range(i+1,n)]
    toggles = np.zeros((len(pairs),n),dtype=int)
    for i,pair in enumerate(pairs):
        toggles[i,list(pair)] = 1
    preprocessing = time.perf_counter()-start
    search_start = time.perf_counter()
    feasible_steps = cost_steps = evaluations = 0
    reason = "budget"
    def violation(state):
        return np.maximum(low-state,0).sum(axis=-1) + np.maximum(state-high,0).sum(axis=-1)
    while time.perf_counter()-search_start < budget:
        state = sides @ vectors
        current = int(violation(state))
        directions = 1-2*sides
        changes = (toggles*directions) @ vectors
        proposed = state+changes
        violations = violation(proposed)
        increments = (toggles*directions) @ (costs[:,1]-costs[:,0])
        evaluations += len(pairs)
        if current:
            improvement = current-violations
            eligible = np.flatnonzero(improvement>0)
            if not len(eligible):
                reason = "no_improving_one_or_two_person_violation_move"
                break
            order = np.lexsort((eligible,increments[eligible],-improvement[eligible],
                                increments[eligible]/improvement[eligible]))
            pick = int(eligible[order[0]])
            feasible_steps += 1
        else:
            eligible = np.flatnonzero((violations==0)&(increments<0))
            if not len(eligible):
                reason = "feasible_one_and_two_person_local_minimum"
                break
            order = np.lexsort((eligible,increments[eligible]))
            pick = int(eligible[order[0]])
            cost_steps += 1
        sides[list(pairs[pick])] = 1-sides[list(pairs[pick])]
    assignment = dict(fixed)
    for i,name in enumerate(names):
        assignment.update({r.id:("train","validation")[sides[i]] for r in members[name]})
    return assignment,{"preprocessing_seconds":preprocessing,"search_seconds":time.perf_counter()-search_start,
                       "feasibility_steps":feasible_steps,"cost_steps":cost_steps,
                       "candidates_evaluated":evaluations,"stop_reason":reason,
                       "remaining_violation":int(violation(sides @ vectors))}
