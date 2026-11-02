"""All frozen clinical cases; keeps the original datasets and negative outcomes."""

import argparse
import gzip
import hashlib
import json
import platform
import time
from dataclasses import replace
from importlib.metadata import version

from baselines import majority, resplit
from clinical_baselines import greedy_repair
from clinical_data import ROOT, clinical_problem, load_clinical

from splitmend import audit, repair
from splitmend.model import problem_dict


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        json.dump(obj, stream, sort_keys=True, allow_nan=False, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(5)))
    parser.add_argument("--tolerances", nargs="+", type=float, default=[0.01, 0.025, 0.05])
    args = parser.parse_args()
    frame = load_clinical()
    destination = ROOT / "results/clinical"
    destination.mkdir(parents=True, exist_ok=True)
    env = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": {p: version(p) for p in ["numpy", "scipy", "pandas", "scikit-learn"]},
        "protocol_sha256": hashlib.sha256(
            (ROOT / "docs/CLINICAL_PROTOCOL.md").read_bytes()
        ).hexdigest(),
        "dataset": {
            "rows": len(frame),
            "patients": frame.patient_nbr.nunique(),
            "joint_strata": frame.stratum.nunique(),
            "schema": list(frame.columns),
            "outcomes": frame.readmitted.value_counts().to_dict(),
            "gender": frame.gender.value_counts().to_dict(),
        },
    }
    (destination / "environment.json").write_text(json.dumps(env, indent=2) + "\n")
    rows = []
    for seed in args.seeds:
        for tolerance in args.tolerances:
            samples, policy, context = clinical_problem(frame, seed, tolerance)
            case = f"diabetes_{seed}_tol{round(tolerance * 1000):03d}"
            save(ROOT / "data/clinical_derived" / f"{case}.json.gz", problem_dict(samples, policy))
            before = audit(samples, policy)
            for method in [
                "majority",
                "group_resplit",
                "violation_greedy",
                "cost_greedy_local",
                "splitmend",
            ]:
                started = time.perf_counter()
                extra = {}
                if method == "majority":
                    assignment = majority(samples, policy)
                elif method == "group_resplit":
                    # This adapter splits only the unlocked train/validation patients;
                    # the row audit below still enforces the original eligibility.
                    assignment = resplit([replace(s, allowed=None) for s in samples], policy, seed)
                elif method in {"violation_greedy", "cost_greedy_local"}:
                    assignment, extra = greedy_repair(
                        samples, policy, cost_aware=method == "cost_greedy_local", budget=60
                    )
                else:
                    result = repair(samples, policy, time_limit=60, explain=False)
                    assignment = result["assignments"]
                    extra = {k: result.get(k) for k in ["status", "lower_bound", "gap", "model"]}
                    save(destination / "solver" / f"{case}.json.gz", result)
                elapsed = time.perf_counter() - started
                audit_start = time.perf_counter()
                after = audit(samples, policy, assignment) if assignment is not None else None
                audit_seconds = time.perf_counter() - audit_start
                row = {
                    "case": case,
                    "dataset": "diabetes",
                    "seed": seed,
                    "tolerance": tolerance,
                    "method": method,
                    **context,
                    "valid": bool(after and after["valid"]),
                    "changed": after["changed"] if after else None,
                    "objective": after["objective"] if after else None,
                    "quarantined": after["quarantined"] if after else None,
                    "violations": after["violation_counts"] if after else {"no_assignment": 1},
                    "initial_violations": before["violation_counts"],
                    "seconds": elapsed,
                    "audit_seconds": audit_seconds,
                    "verified_seconds": elapsed + audit_seconds,
                    **extra,
                }
                save(
                    destination / "assignments" / f"{case}_{method}.json.gz",
                    {"assignments": assignment, "audit": after, "summary": row},
                )
                rows.append(row)
                (destination / "runs.json").write_text(json.dumps(rows, indent=2) + "\n")
                print(json.dumps(row), flush=True)
    print("CLINICAL RUN COMPLETE", len(rows), flush=True)


if __name__ == "__main__":
    main()
