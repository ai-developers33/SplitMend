"""Exhaustive oracle, conflict cases, aggregation and non-improvement controls."""

import gzip
import itertools
import json
import random
from collections import defaultdict
from dataclasses import replace

from datasets import ROOT

from splitmend import QUARANTINE as Q
from splitmend import Policy, Sample, audit, repair


def load(name):
    with gzip.open(ROOT / "data/derived" / f"{name}_0.json.gz", "rt") as f:
        obj = json.load(f)
    return [
        Sample(
            **{
                **s,
                "groups": tuple(s["groups"]),
                "allowed": None if s["allowed"] is None else tuple(s["allowed"]),
            }
        )
        for s in obj["samples"]
    ], Policy(**obj["policy"])


def main():
    oracle = []
    for seed in range(100):
        rng = random.Random(seed + 1000)
        n = rng.randint(2, 6)
        parts = ("train", "validation", "test")
        s = [
            Sample(
                str(i),
                rng.choice(parts),
                groups=tuple(sorted({f"g:{rng.randrange(3)}" for _ in range(rng.randint(0, 2))})),
                label=str(i % 2),
                locked=rng.random() < 0.1,
                weight=rng.randint(1, 4),
                allowed=rng.choice([None, None, ("train", "test"), ()]),
            )
            for i in range(n)
        ]
        p = Policy(
            partitions=parts,
            allow_quarantine=seed % 2 == 0,
            size_bounds={"train": (1, n)},
            label_bounds={"0": {"test": (0, n)}},
        )
        best = None
        valid = 0
        for values in itertools.product((*parts, Q) if p.allow_quarantine else parts, repeat=n):
            report = audit(s, p, dict(zip([x.id for x in s], values)))
            if report["valid"]:
                valid += 1
                best = report["objective"] if best is None else min(best, report["objective"])
        r = repair(s, p, explain=False)
        passed = (
            r["status"] == "infeasible"
            if best is None
            else r["status"] == "optimal" and r["objective"] == best
        )
        oracle.append(
            {
                "seed": seed + 1000,
                "rows": n,
                "feasible_assignments": valid,
                "oracle_objective": best,
                "solver_status": r["status"],
                "solver_objective": r["objective"],
                "pass": passed,
            }
        )
        assert passed, oracle[-1]
    (ROOT / "results/oracle.json").write_text(json.dumps(oracle, indent=2) + "\n")
    ablations = []
    conflicts = []
    for name in ["har", "oulad", "beijing"]:
        samples, policy = load(name)
        if name == "beijing":
            bad = [s for s in samples if s.allowed == ()]
            selected = bad[:1000] + [s for s in samples if s.allowed][:1000]
            conflict = [replace(bad[0], locked=True)]
        else:
            groups = defaultdict(list)
            for s in samples:
                groups[s.groups[0]].append(s)
            badgroups = [u for u in groups.values() if len({s.original for s in u}) > 1]
            selected = []
            for u in badgroups:
                if len(selected) + len(u) > 2000:
                    break
                selected.extend(u)
            first = badgroups[0][0]
            second = next(s for s in badgroups[0] if s.original != first.original)
            conflict = [replace(first, locked=True), replace(second, locked=True)]
        p = replace(policy, size_bounds={}, label_bounds={})
        c = repair(selected, p, time_limit=60)
        u = repair(selected, p, time_limit=60, compress=False)
        same = c["status"] == u["status"] == "optimal" and c["objective"] == u["objective"]
        ablations.append(
            {
                "dataset": name,
                "n": len(selected),
                "compressed": {k: c.get(k) for k in ["status", "objective", "seconds", "model"]},
                "expanded": {k: u.get(k) for k in ["status", "objective", "seconds", "model"]},
                "equal_optimum": same,
            }
        )
        assert same
        result = repair(conflict, p)
        conflicts.append(
            {
                "dataset": name,
                "control": "deliberately_conflicting_lock",
                "status": result["status"],
                "conflict": result["conflict"],
                "pass": result["status"] == "infeasible",
            }
        )
        assert result["status"] == "infeasible"
    (ROOT / "results/aggregation.json").write_text(json.dumps(ablations, indent=2) + "\n")
    (ROOT / "results/conflict_controls.json").write_text(json.dumps(conflicts, indent=2) + "\n")
    print("100 exhaustive cases, 3 aggregation comparisons, 3 conflict controls passed")


if __name__ == "__main__":
    main()
