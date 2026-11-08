"""Check source bytes and recompute every saved assignment's declared policy verdict."""

import gzip
import hashlib
import json
from pathlib import Path

from splitmend import Policy, Sample, audit

ROOT = Path(__file__).resolve().parents[1]


def main():
    for source in json.loads((ROOT / "data/sources.json").read_text())["sources"]:
        with (ROOT / source["archive"]).open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        assert digest == source["sha256"], source["dataset"]
    checked = 0
    valid_count = 0
    for problem in sorted((ROOT / "data/derived").glob("*.json.gz")):
        with gzip.open(problem, "rt") as f:
            obj = json.load(f)
        samples = [
            Sample(
                **{
                    **s,
                    "groups": tuple(s["groups"]),
                    "allowed": None if s["allowed"] is None else tuple(s["allowed"]),
                }
            )
            for s in obj["samples"]
        ]
        policy = Policy(**obj["policy"])
        prefix = problem.name.removesuffix(".json.gz")
        for path in sorted((ROOT / "results/assignments").glob(prefix + "_*.json.gz")):
            with gzip.open(path, "rt") as f:
                result = json.load(f)
            if result["assignments"] is None:
                assert not result["summary"]["valid"]
                continue
            a = audit(samples, policy, result["assignments"])
            for key in ["valid", "changed", "objective", "quarantined"]:
                assert a[key] == result["audit"][key], (path.name, key)
            checked += 1
            valid_count += a["valid"]
    report = {
        "archive_hashes_verified": 3,
        "saved_assignments_reaudited": checked,
        "valid_assignments": valid_count,
        "note": "Invalid baseline outputs are retained and must match their recorded invalid verdict.",
    }
    (ROOT / "results/verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
