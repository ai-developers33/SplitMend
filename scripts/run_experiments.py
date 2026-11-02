"""All prespecified workflow simulations. Results are observations, never constants."""

import argparse
import csv
import importlib.metadata as metadata
import json
import platform
import time
from dataclasses import replace

from artifact_io import save_gzip_json as save_json
from baselines import greedy, majority, resplit
from datasets import (
    ROOT,
    classification_problem,
    load_beijing,
    load_har,
    load_oulad,
    temporal_problem,
)

from splitmend import audit, repair
from splitmend.model import problem_dict


def emit(samples, policy, name, seed, method, assignments, elapsed, extra=None):
    audit_started = time.perf_counter()
    report = audit(samples, policy, assignments) if assignments is not None else None
    audit_seconds = time.perf_counter() - audit_started
    row = {
        "dataset": name,
        "seed": seed,
        "method": method,
        "n": len(samples),
        "valid": bool(report and report["valid"]),
        "changed": report["changed"] if report else None,
        "quarantined": report["quarantined"] if report else None,
        "objective": report["objective"] if report else None,
        "seconds": elapsed,
        "audit_seconds": audit_seconds,
        "verified_seconds": elapsed + audit_seconds,
        "violations": report["violation_counts"] if report else {"no_assignment": 1},
    }
    row.update(extra or {})
    save_json(
        ROOT / "results/assignments" / f"{name}_{seed}_{method}.json.gz",
        {"assignments": assignments, "audit": report, "summary": row},
    )
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["har", "oulad", "beijing"])
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(5)))
    parser.add_argument("--time-limit", type=float, default=60)
    args = parser.parse_args()
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            p: metadata.version(p)
            for p in ["numpy", "scipy", "pandas", "scikit-learn", "splitmend"]
        },
    }
    (ROOT / "results/environment.json").write_text(json.dumps(env, indent=2) + "\n")
    rows = []
    controls = []
    ablation = []
    for name in args.datasets:
        frame = (
            load_har()[0] if name == "har" else load_oulad() if name == "oulad" else load_beijing()
        )
        for seed in args.seeds:
            context = {}
            if name == "beijing":
                samples, policy, context = temporal_problem(frame, seed)
            else:
                samples, policy = classification_problem(frame, name, seed)
            save_json(
                ROOT / "data/derived" / f"{name}_{seed}.json.gz", problem_dict(samples, policy)
            )
            started = time.perf_counter()
            result = repair(samples, policy, time_limit=args.time_limit)
            elapsed = time.perf_counter() - started
            save_json(ROOT / "results/solver" / f"{name}_{seed}.json.gz", result)
            row = emit(
                samples,
                policy,
                name,
                seed,
                "splitmend",
                result["assignments"],
                elapsed,
                {k: result.get(k) for k in ["status", "lower_bound", "gap", "model"]},
            )
            row.update(context)
            rows.append(row)
            print(json.dumps(row), flush=True)
            # Clean output must be a zero-cost fixed point under the identical policy.
            if result["assignments"] is not None:
                clean = [replace(s, original=result["assignments"][s.id]) for s in samples]
                fixed = repair(clean, policy)
                controls.append(
                    {
                        "dataset": name,
                        "seed": seed,
                        "test": "clean_fixed_point",
                        "status": fixed["status"],
                        "objective": fixed["objective"],
                        "pass": fixed["objective"] == 0,
                    }
                )
            methods = {
                "majority": lambda: majority(samples, policy),
                "group_resplit": lambda: resplit(samples, policy, seed),
            }
            if name != "beijing":
                methods["greedy"] = lambda: greedy(samples, policy)
            for method, fn in methods.items():
                started = time.perf_counter()
                assignment = fn()
                elapsed = time.perf_counter() - started
                row = emit(samples, policy, name, seed, method, assignment, elapsed)
                rows.append(row)
                print(json.dumps(row), flush=True)
            if seed == 0:
                # A row-level formulation tests the exact aggregation independently of benchmarks.
                subset = samples[:2000]
                p = replace(policy, size_bounds={}, label_bounds={})
                compressed = repair(subset, p, time_limit=60)
                expanded = repair(subset, p, time_limit=60, compress=False)
                ablation.append(
                    {
                        "dataset": name,
                        "n": len(subset),
                        "compressed": {
                            k: compressed.get(k)
                            for k in ["status", "objective", "seconds", "model"]
                        },
                        "expanded": {
                            k: expanded.get(k) for k in ["status", "objective", "seconds", "model"]
                        },
                        "equal_optimum": compressed["status"] == expanded["status"] == "optimal"
                        and compressed["objective"] == expanded["objective"],
                    }
                )
        (ROOT / "results/main.json").write_text(json.dumps(rows, indent=2) + "\n")
        (ROOT / "results/controls.json").write_text(json.dumps(controls, indent=2) + "\n")
        (ROOT / "results/aggregation.json").write_text(json.dumps(ablation, indent=2) + "\n")
    with (ROOT / "results/main.csv").open("w", newline="") as f:
        fields = [
            "dataset",
            "seed",
            "method",
            "n",
            "valid",
            "changed",
            "quarantined",
            "objective",
            "seconds",
            "status",
            "lower_bound",
            "gap",
        ]
        writer = csv.DictWriter(f, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
