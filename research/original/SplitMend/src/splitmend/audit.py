"""Independent row-level verifier. This module does not import the optimization model."""

from collections import Counter, defaultdict

from .model import QUARANTINE, Policy, Sample, validate


def objective(samples: list[Sample], assignments: dict[str, str], policy: Policy) -> int:
    """Reassignment costs weight; new quarantine costs weight * quarantine_cost."""
    return sum(
        0
        if assignments[s.id] == s.original
        else s.weight * (policy.quarantine_cost if assignments[s.id] == QUARANTINE else 1)
        for s in samples
    )


def audit(samples: list[Sample], policy: Policy, assignments: dict[str, str] | None = None) -> dict:
    validate(samples, policy)
    if assignments is None:
        assignments = {s.id: s.original for s in samples}
    if set(assignments) != {s.id for s in samples}:
        raise ValueError("assignment IDs must match the input exactly")
    violations = []
    counts = Counter()
    labels = defaultdict(Counter)
    groups = defaultdict(lambda: defaultdict(list))
    for s in samples:
        p = assignments[s.id]
        if p not in policy.partitions and p != QUARANTINE:
            raise ValueError(f"unknown assigned partition {p!r}")
        counts[p] += 1
        if p == QUARANTINE:
            if not policy.allow_quarantine:
                violations.append({"kind": "quarantine_disabled", "sample": s.id})
        else:
            labels[s.label][p] += 1
            for g in s.groups:
                groups[g][p].append(s.id)
            if s.allowed is not None and p not in s.allowed:
                violations.append({"kind": "eligibility", "sample": s.id, "partition": p})
        if s.locked and p != s.original:
            violations.append({"kind": "lock", "sample": s.id})
    for g, by_part in sorted(groups.items()):
        if len(by_part) > 1:
            violations.append(
                {
                    "kind": "group_overlap",
                    "group": g,
                    "witness": {p: ids[:2] for p, ids in by_part.items()},
                }
            )
    for p, (lo, hi) in policy.size_bounds.items():
        if not lo <= counts[p] <= hi:
            violations.append(
                {"kind": "size", "partition": p, "count": counts[p], "bounds": [lo, hi]}
            )
    for label, bounds in policy.label_bounds.items():
        for p, (lo, hi) in bounds.items():
            if not lo <= labels[label][p] <= hi:
                violations.append(
                    {
                        "kind": "label",
                        "label": label,
                        "partition": p,
                        "count": labels[label][p],
                        "bounds": [lo, hi],
                    }
                )
    return {
        "valid": not violations,
        "counts": {p: counts[p] for p in (*policy.partitions, QUARANTINE)},
        "violation_counts": dict(Counter(v["kind"] for v in violations)),
        "violations": violations,
        "changed": sum(assignments[s.id] != s.original for s in samples),
        "quarantined": counts[QUARANTINE],
        "objective": objective(samples, assignments, policy),
    }
