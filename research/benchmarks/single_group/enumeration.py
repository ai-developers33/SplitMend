"""Unmodified helper function reused from the previous published-to-user pilot."""
import time
from collections import Counter, defaultdict
import numpy as np

def exhaustive(samples, policy):
    """Enumerate every feasible subject allocation without calling SplitMend."""
    started = time.perf_counter()
    groups = defaultdict(list)
    for s in samples:
        if not s.locked:
            groups[s.groups[0]].append(s)
        else:
            assert s.original == "test" and s.allowed == ("test",)
    labels = sorted(policy.label_bounds)
    vectors, train_costs, val_costs = [], [], []
    for name, rows in sorted(groups.items()):
        assert all(set(s.allowed) == {"train", "validation"} for s in rows)
        counts = Counter(s.label for s in rows)
        vectors.append([len(rows), *(counts[x] for x in labels)])
        train_costs.append(sum(s.original != "train" for s in rows))
        val_costs.append(sum(s.original != "validation" for s in rows))
    vectors = np.asarray(vectors, dtype=np.int64)
    totals = vectors.sum(axis=0)
    limits = [policy.size_bounds, *(policy.label_bounds[x] for x in labels)]
    low = np.asarray([max(b["validation"][0], int(t)-b["train"][1])
                      for b, t in zip(limits, totals)])
    high = np.asarray([min(b["validation"][1], int(t)-b["train"][0])
                       for b, t in zip(limits, totals)])
    n = len(groups)
    assert n <= 18
    optimum, best_mask, valid_count, minimizers = None, None, 0, 0
    delta = np.array(val_costs) - np.array(train_costs)
    base_cost = sum(train_costs)
    for first in range(0, 1 << n, 16384):
        masks = np.arange(first, min(first+16384, 1 << n), dtype=np.int64)
        allocations = (masks[:, None] >> np.arange(n)) & 1
        counts = allocations @ vectors
        valid = ((counts >= low) & (counts <= high)).all(axis=1)
        valid_count += int(valid.sum())
        if not valid.any():
            continue
        costs = base_cost + allocations[valid] @ delta
        value = int(costs.min())
        number = int((costs == value).sum())
        if optimum is None or value < optimum:
            optimum, minimizers = value, number
            best_mask = int(masks[valid][np.flatnonzero(costs == value)[0]])
        elif value == optimum:
            minimizers += number
    return {"free_participants":n,"allocations_checked":1 << n,"valid_allocations":valid_count,
            "optimal_movement":optimum,"number_of_minimizers":minimizers,
            "best_mask":best_mask,"participant_order":sorted(groups),
            "seconds":time.perf_counter()-started}
