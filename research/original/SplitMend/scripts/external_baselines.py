"""Run pinned external packages with an explicit locked-group adapter.

Run this script in the baseline environment. DataSAIL's published I1 solver is
called directly to supply per-group class count vectors without inventing a
single class for a mixed-label person. Its native ratio tolerances differ from
SplitMend's absolute bounds; the same row-level audit judges every output.
"""

import argparse
import gzip
import importlib.metadata as metadata
import inspect
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from datasail.solver.id_1d import solve_i1
from dataset_splitter import split

from splitmend import Policy, Sample, audit

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    with gzip.open(path, "rt") as f:
        obj = json.load(f)
    samples = [
        Sample(
            **{
                **r,
                "groups": tuple(r["groups"]),
                "allowed": None if r["allowed"] is None else tuple(r["allowed"]),
            }
        )
        for r in obj["samples"]
    ]
    return samples, Policy(**obj["policy"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["datasail_i1", "datasail_i1_tight", "datasail_i1_aligned", "dataset_splitter"],
    )
    args = parser.parse_args()
    (ROOT / "results/external").mkdir(exist_ok=True)
    result_path = ROOT / "results/external.json"
    rows = (
        [r for r in json.loads(result_path.read_text()) if r["method"] not in args.methods]
        if result_path.exists()
        else []
    )
    env = {
        p: metadata.version(p)
        for p in ["datasail", "dataset-splitter", "numpy", "scipy", "cvxpy", "pyscipopt"]
    }
    (ROOT / "results/external_environment.json").write_text(json.dumps(env, indent=2) + "\n")
    for dataset in ["har", "oulad"]:
        for seed in range(5):
            samples, policy = load(ROOT / "data/derived" / f"{dataset}_{seed}.json.gz")
            grouped = defaultdict(list)
            for s in samples:
                grouped[s.groups[0]].append(s)
            fixed = {}
            free = {}
            for g, u in grouped.items():
                locked = {s.original for s in u if s.locked}
                if locked:
                    fixed.update({s.id: next(iter(locked)) for s in u})
                else:
                    free[g] = u
            entities = sorted(free)
            labels = sorted({s.label for s in samples})
            weights = [len(free[g]) for g in entities]
            counts = np.array(
                [[sum(s.label == c for s in free[g]) for c in labels] for g in entities]
            )
            val = sum(s.original == "validation" for s in samples) / sum(weights)
            for method in args.methods:
                started = time.perf_counter()
                assignment = None
                error = None
                try:
                    if method.startswith("datasail_i1"):
                        kwargs = dict(
                            entities=entities,
                            weights=weights,
                            stratification=counts,
                            delta=0.2,
                            epsilon=0.1,
                            splits=[1 - val, val],
                            names=["train", "validation"],
                            max_sec=60,
                            solver="SCIP",
                            log_file=ROOT / "results/external" / f"{dataset}_{seed}_scip.log",
                        )
                        if method.endswith("_tight"):
                            kwargs.update(delta=0.05, epsilon=0.02)
                        if method.endswith("_aligned"):
                            # Native I1 supplies only relative lower bounds. With two free
                            # partitions, the complementary lower bound also enforces upper
                            # bounds. Derive conservative tolerances from the common policy.
                            def tolerance(total, bounds, ceiling):
                                values = []
                                for j, p in enumerate(["train", "validation"]):
                                    other = ["train", "validation"][1 - j]
                                    required = max(bounds[p][0], total - bounds[other][1])
                                    target = total * ([1 - val, val][j])
                                    values.append(1 - (required + 1) / target if target else 0)
                                return max(0, min(ceiling, *values))

                            eps = tolerance(sum(weights), policy.size_bounds, 0.1)
                            deltas = [
                                tolerance(int(counts[:, j].sum()), policy.label_bounds[label], 0.2)
                                for j, label in enumerate(labels)
                            ]
                            kwargs.update(epsilon=eps, delta=min(deltas))
                        kwargs["log_file"] = (
                            ROOT / "results/external" / f"{dataset}_{seed}_{method}_scip.log"
                        )
                        if "interaction_strat" in inspect.signature(solve_i1).parameters:
                            kwargs["interaction_strat"] = None
                        group_assignment = solve_i1(**kwargs)
                        if group_assignment is not None:
                            assignment = dict(fixed)
                            assignment.update(
                                {s.id: group_assignment[g] for g, u in free.items() for s in u}
                            )
                    else:
                        f = pd.DataFrame(
                            [
                                {"id": s.id, "group": g, "label": s.label}
                                for g, u in free.items()
                                for s in u
                            ]
                        )
                        result = split(
                            f,
                            target="label",
                            group="group",
                            test_size=val,
                            val_size=0,
                            random_state=seed,
                            dedupe=False,
                        )
                        assignment = dict(fixed)
                        assignment.update({str(sid): "train" for sid in result.train["id"]})
                        assignment.update({str(sid): "validation" for sid in result.test["id"]})
                except Exception as e:
                    error = type(e).__name__ + ": " + str(e)
                elapsed = time.perf_counter() - started
                audit_started = time.perf_counter()
                verified = audit(samples, policy, assignment) if assignment is not None else None
                audit_seconds = time.perf_counter() - audit_started
                row = {
                    "dataset": dataset,
                    "seed": seed,
                    "method": method,
                    "n": len(samples),
                    "valid": bool(verified and verified["valid"]),
                    "changed": verified["changed"] if verified else None,
                    "quarantined": verified["quarantined"] if verified else None,
                    "objective": verified["objective"] if verified else None,
                    "seconds": elapsed,
                    "error": error,
                    "audit_seconds": audit_seconds,
                    "verified_seconds": elapsed + audit_seconds,
                    "violations": verified["violation_counts"]
                    if verified
                    else {"no_assignment": 1},
                }
                rows.append(row)
                print(json.dumps(row), flush=True)
                with gzip.open(
                    ROOT / "results/assignments" / f"{dataset}_{seed}_{method}.json.gz", "wt"
                ) as f:
                    json.dump(
                        {"assignments": assignment, "audit": verified, "summary": row},
                        f,
                        sort_keys=True,
                    )
                (ROOT / "results/external.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
