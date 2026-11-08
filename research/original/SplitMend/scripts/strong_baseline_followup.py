"""Apply the frozen clinical cost-aware heuristic to both earlier person workflows.

Follow-up motivated after the clinical comparison, with no parameter retuning.
Groups touching locked test records are necessarily assigned to test. Remaining
groups use the train/validation adapter, as in the original split constructors.
The full original policy and original movement costs are audited afterwards.
"""

import gzip
import json
import time
from dataclasses import replace

from clinical_baselines import greedy_repair
from clinical_data import ROOT
from run_experiments import emit

from splitmend import Policy, Sample


def main():
    rows = []
    for dataset in ["har", "oulad"]:
        for seed in range(5):
            with gzip.open(ROOT / "data/derived" / f"{dataset}_{seed}.json.gz", "rt") as stream:
                obj = json.load(stream)
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
            started = time.perf_counter()
            locked_groups = {g for s in samples if s.locked for g in s.groups}
            adapted = [
                replace(s, original="test", locked=True, allowed=("test",))
                if locked_groups.intersection(s.groups)
                else replace(s, allowed=("train", "validation"))
                for s in samples
            ]
            assignments, stats = greedy_repair(adapted, policy, cost_aware=True, budget=60)
            row = emit(
                samples,
                policy,
                dataset,
                seed,
                "cost_greedy_local",
                assignments,
                time.perf_counter() - started,
                stats,
            )
            rows.append(row)
            print(json.dumps(row), flush=True)
    (ROOT / "results/strong_baseline_followup.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
