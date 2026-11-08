"""Independently re-audit all clinical assignments and original archive bytes."""

import gzip
import hashlib
import json
from pathlib import Path

from splitmend import Policy, Sample, audit

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = json.loads((ROOT / "data/clinical_sources.json").read_text())["sources"][0]
    with (ROOT / source["archive"]).open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == source["sha256"]
    checked, valid = 0, 0
    cases = list((ROOT / "data/clinical_derived").glob("*.json.gz"))
    assert len(cases) == 15
    for problem in sorted(cases):
        with gzip.open(problem, "rt") as stream:
            obj = json.load(stream)
        samples = [
            Sample(**{**s, "groups": tuple(s["groups"]), "allowed": tuple(s["allowed"])})
            for s in obj["samples"]
        ]
        policy = Policy(**obj["policy"])
        paths = list(
            (ROOT / "results/clinical/assignments").glob(
                problem.name.removesuffix(".json.gz") + "_*.json.gz"
            )
        )
        assert len(paths) == 5
        for path in paths:
            with gzip.open(path, "rt") as stream:
                saved = json.load(stream)
            assignments = saved["assignments"]
            if assignments is not None:
                report = audit(samples, policy, assignments)
                for key in ["valid", "changed", "objective", "quarantined", "violation_counts"]:
                    assert report[key] == saved["audit"][key], (path.name, key)
                assert all(assignments[s.id] == "test" for s in samples if s.locked)
                assert report["quarantined"] == 0
                valid += int(report["valid"])
            else:
                assert not saved["summary"]["valid"]
            checked += 1
    assert checked == 75
    report = {
        "source_archives_verified": 1,
        "cases": len(cases),
        "saved_runs_checked": checked,
        "valid_assignments": valid,
        "no_rows_dropped": True,
        "locked_test_memberships_preserved": True,
        "independent_host_reproduction": False,
    }
    (ROOT / "results/clinical/verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
