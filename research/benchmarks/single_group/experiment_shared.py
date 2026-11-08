"""Reproduce the pre-specified ExtraSensory split-repair pilot.

Uses original public labels, not sensor values or trained predictions. All
source rows are retained; unreported main activity is a separate stratum.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import platform
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "vendor"))
import numpy as np
import pandas as pd
from baselines import majority
from clinical_baselines import greedy_repair
from splitmend import Policy, Sample, audit, repair
from splitmend.model import fingerprint


def write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_sources():
    for item in json.loads((ROOT / "data/source/download_manifest.json").read_text()):
        path = ROOT / "data/source" / item["name"]
        if not path.exists():
            with urllib.request.urlopen(item["url"], timeout=90) as response:
                path.write_bytes(response.read())
        assert sha(path) == item["sha256"], f"Source hash mismatch: {path}"
    for name, expected in json.loads((ROOT / "vendor_manifest.json").read_text())["files"].items():
        assert sha(ROOT / name) == expected, f"Vendor hash mismatch: {name}"


def cohort(protocol):
    chunks = []
    labels = protocol["labels"]
    with zipfile.ZipFile(ROOT / "data/source/original_labels.zip") as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".csv.gz"):
                continue
            columns = ["original_label:" + x for x in labels]
            frame = pd.read_csv(io.BytesIO(gzip.decompress(archive.read(name))),
                                usecols=["timestamp", *columns])
            matrix = frame[columns].to_numpy()
            assert np.isin(matrix, [0, 1]).all()
            selected = np.array(labels, dtype=object)[matrix.argmax(axis=1)]
            selected[matrix.sum(axis=1) == 0] = "UNREPORTED_MAIN_ACTIVITY"
            selected[matrix.sum(axis=1) > 1] = "MULTIPLE_MAIN_ACTIVITIES"
            chunks.append(pd.DataFrame({"participant": name.split(".")[0],
                                        "timestamp": frame.timestamp, "label": selected}))
    frame = pd.concat(chunks, ignore_index=True)
    assert not frame.duplicated(["participant", "timestamp"]).any()
    assert len(frame) == 377346 and frame.participant.nunique() == 60
    return frame


def folds(frame):
    all_people = set(frame.participant)
    tests = []
    with zipfile.ZipFile(ROOT / "data/source/cv5Folds.zip") as archive:
        for fold in range(5):
            parts = {}
            for part in ["train", "test"]:
                parts[part] = set()
                for device in ["android", "iphone"]:
                    name = f"cv_5_folds/fold_{fold}_{part}_{device}_uuids.txt"
                    parts[part].update(archive.read(name).decode().split())
            assert not parts["train"] & parts["test"]
            assert parts["train"] | parts["test"] == all_people
            tests.append(parts["test"])
    assert sum(map(len, tests)) == len(set.union(*tests)) == 60
    return tests


def make_problem(frame, test_people, seed, protocol):
    rng = np.random.default_rng(seed)
    is_test = frame.participant.isin(test_people).to_numpy()
    original = np.full(len(frame), "train", dtype=object)
    original[is_test] = "test"
    for label in sorted(frame.label.unique()):
        indices = np.flatnonzero((frame.label == label).to_numpy() & ~is_test)
        indices = rng.permutation(indices)
        original[indices[:round(protocol["initial_validation_fraction_of_non_test"] * len(indices))]] = "validation"
    samples = [Sample(id=f"{r.participant}:{r.timestamp}", original=original[i],
                      groups=("participant:" + r.participant,), label=r.label,
                      allowed=("test",) if is_test[i] else ("train", "validation"),
                      locked=bool(is_test[i])) for i, r in enumerate(frame.itertuples(index=False))]
    def bounds(n, test_n, tol):
        result = {}
        for p, target in [("train", 0.75), ("validation", 0.25)]:
            result[p] = (max(0, math.floor((target-tol)*n)),
                         min(n, math.ceil((target+tol)*n)))
        result["test"] = (test_n, test_n)
        return result
    free = Counter(s.label for s in samples if not s.locked)
    fixed = Counter(s.label for s in samples if s.locked)
    policy = Policy(size_bounds=bounds(sum(free.values()), sum(fixed.values()),
                                      protocol["size_tolerance_pp"]/100),
                    label_bounds={label: bounds(free[label], fixed[label],
                                                 protocol["label_tolerance_pp"]/100)
                                  for label in sorted(set(free) | set(fixed))})
    return samples, policy


def independent_check(samples, policy, assignment):
    if assignment is None:
        return {"valid": False, "changed": None, "violations": {"missing_assignment": 1}}
    expected = {s.id for s in samples}
    errors = Counter(missing_ids=len(expected - set(assignment)),
                     extra_ids=len(set(assignment) - expected))
    sizes, label_counts = Counter(), defaultdict(Counter)
    group_parts, changed = defaultdict(set), 0
    for row in samples:
        assert len(row.groups) == 1 and row.weight == 1 and not policy.allow_quarantine
        part = assignment.get(row.id)
        errors["eligibility"] += int(part not in row.allowed)
        errors["locks"] += int(row.locked and part != row.original)
        sizes[part] += 1
        label_counts[row.label][part] += 1
        group_parts[row.groups[0]].add(part)
        changed += int(part != row.original)
    errors["participant_separation"] = sum(len(v) != 1 for v in group_parts.values())
    for part, (low, high) in policy.size_bounds.items():
        errors["size_bounds"] += int(not low <= sizes[part] <= high)
    for label, limits in policy.label_bounds.items():
        for part, (low, high) in limits.items():
            errors["label_bounds"] += int(not low <= label_counts[label][part] <= high)
    errors = {k: int(v) for k, v in errors.items() if v}
    return {"valid": not errors, "changed": changed, "violations": errors,
            "sizes": dict(sizes), "labels": dict(label_counts)}


def group_lower_bound(samples):
    counts = defaultdict(Counter)
    for s in samples:
        if not s.locked:
            counts[s.groups[0]][s.original] += 1
    return sum(min(c["train"], c["validation"]) for c in counts.values())


def run_method(samples, policy, method, protocol):
    start = time.perf_counter()
    raw = {}
    if method == "splitmend":
        raw = repair(samples, policy, time_limit=protocol["solver_seconds"], explain=False)
        assignment = raw.pop("assignments")
    elif method in ["violation_greedy", "cost_greedy_local"]:
        assignment, raw = greedy_repair(samples, policy,
                                        cost_aware=method == "cost_greedy_local",
                                        budget=protocol["greedy_search_seconds"],
                                        pool_size=protocol["greedy_pair_candidate_pool"])
    elif method == "majority":
        assignment = majority(samples, policy)
    else:
        raise ValueError(method)
    seconds = time.perf_counter() - start
    start = time.perf_counter()
    library_check = audit(samples, policy, assignment) if assignment is not None else None
    audit_seconds = time.perf_counter() - start
    independent = independent_check(samples, policy, assignment)
    assert independent["valid"] == bool(library_check and library_check["valid"])
    if library_check:
        assert independent["changed"] == library_check["changed"] == library_check["objective"]
    group_assignment = {}
    if assignment is not None:
        for row in samples:
            group = row.groups[0]
            part = assignment[row.id]
            assert group_assignment.setdefault(group, part) == part
    summary = {"method": method, "valid": independent["valid"],
               "changed": independent["changed"], "seconds": seconds,
               "external_audit_seconds": audit_seconds,
               "status": raw.get("status"), "lower_bound": raw.get("lower_bound"),
               "gap": raw.get("gap"), "violations": independent["violations"]}
    return summary, {"group_assignments": group_assignment, "raw": raw,
                     "library_audit": library_check, "independent_audit": independent}


def summarize(rows, output):
    summary = {"cases": len({r["case"] for r in rows}), "methods": {}}
    for method in sorted({r["method"] for r in rows}):
        selected = [r for r in rows if r["method"] == method]
        valid = [r for r in selected if r["valid"]]
        summary["methods"][method] = {"valid": len(valid), "attempted": len(selected),
            "mean_changed_valid_only": float(np.mean([r["changed"] for r in valid])) if valid else None,
            "median_seconds_all_attempts": float(np.median([r["seconds"] for r in selected]))}
    pairs = []
    for case in sorted({r["case"] for r in rows}):
        by_method = {r["method"]: r for r in rows if r["case"] == case}
        if not {"splitmend", "cost_greedy_local"} <= set(by_method):
            continue
        a, b = by_method["splitmend"], by_method["cost_greedy_local"]
        pair = {"case": case, "splitmend_valid": a["valid"], "strong_valid": b["valid"],
                "splitmend_changed": a["changed"], "strong_changed": b["changed"]}
        if a["valid"] and b["valid"]:
            pair["saved"] = b["changed"]-a["changed"]
            pair["saved_percent"] = 100*pair["saved"]/b["changed"]
        pairs.append(pair)
    valid_pairs = [p for p in pairs if "saved" in p]
    summary["strong_comparison"] = {"paired_valid_cases": len(valid_pairs),
        "wins": sum(p["saved"] > 0 for p in valid_pairs),
        "ties": sum(p["saved"] == 0 for p in valid_pairs),
        "losses": sum(p["saved"] < 0 for p in valid_pairs),
        "total_saved_across_paired_cases": sum(p["saved"] for p in valid_pairs),
        "aggregate_reduction_percent": 100*sum(p["saved"] for p in valid_pairs)/sum(p["strong_changed"] for p in valid_pairs) if valid_pairs else None,
        "note": "Case totals repeatedly count the same cohort; not unique records saved in a deployment."}
    write(output / "summary.json", summary)
    pd.DataFrame(rows).to_csv(output / "all_results.csv", index=False)
    pd.DataFrame(pairs).to_csv(output / "paired_results.csv", index=False)


def run(output):
    check_sources()
    protocol = json.loads((ROOT / "protocol.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    write(output / "run_environment.json", {"python": sys.version, "platform": platform.platform(),
          "versions": {n: version(n) for n in ["numpy", "scipy", "pandas", "scikit-learn"]},
          "protocol_sha256": sha(ROOT / "protocol.json"), "runner_sha256": sha(__file__)})
    frame = cohort(protocol)
    test_folds = folds(frame)
    rows = []
    index = 0
    for fold in protocol["folds"]:
        for seed in protocol["seeds"]:
            case = f"fold{fold}_seed{seed}"
            samples, policy = make_problem(frame, test_folds[fold], seed, protocol)
            case_path = output / "cases" / case
            case_path.mkdir(parents=True, exist_ok=True)
            metadata = {"case": case, "fold": fold, "seed": seed,
                        "problem_sha256": fingerprint(samples, policy),
                        "group_only_lower_bound": group_lower_bound(samples),
                        "size_bounds": policy.size_bounds, "label_bounds": policy.label_bounds}
            write(case_path / "problem_metadata.json", metadata)
            methods = protocol["methods"]
            offset = index % len(methods)
            for method in methods[offset:] + methods[:offset]:
                path = case_path / f"{method}.json"
                if path.exists():
                    result = json.loads(path.read_text())
                    assert result["problem_sha256"] == metadata["problem_sha256"]
                    row = result["summary"]
                else:
                    row, detail = run_method(samples, policy, method, protocol)
                    row.update(case=case, fold=fold, seed=seed)
                    write(path, {"problem_sha256": metadata["problem_sha256"],
                                 "summary": row, **detail})
                rows.append(row)
                print(json.dumps(row), flush=True)
                summarize(rows, output)
            index += 1
    print(json.dumps(json.loads((output/"summary.json").read_text()), indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "results/primary")
    args = parser.parse_args()
    run(args.output)
