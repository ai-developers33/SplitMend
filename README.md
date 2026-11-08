# SplitMend

SplitMend repairs **existing** machine-learning dataset partitions under explicit constraints.
It minimizes a weighted assignment-change objective, keeps locked records fixed, supports
group/duplicate separation and time-window eligibility, and independently verifies every
returned assignment. It uses the HiGHS integer optimizer through SciPy.

Version 0.1.1 is available on [PyPI](https://pypi.org/project/splitmend/0.1.1/).
Source code is maintained at [ai-developers33/SplitMend](https://github.com/ai-developers33/SplitMend).

## Install from PyPI

Python 3.11 or newer is required.

```sh
python -m pip install "splitmend==0.1.1"
splitmend --version
```

## Install from source

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: .venv\Scripts\activate
python -m pip install -e '.[test,experiments]'
python -m pytest
splitmend repair examples/problem.json --output repaired.json
```

## Python API

```python
from splitmend import Sample, Policy, repair

samples = [
    Sample('a', 'train', groups=('person:7',)),
    Sample('b', 'test', groups=('person:7',), locked=True),
    Sample('c', 'train', groups=('person:8',)),
]
result = repair(samples, Policy(partitions=('train', 'test')))
assert result['after']['valid']
assert result['assignments']['a'] == 'test'
```

Each group token is namespaced by the caller (for example `patient:7`, `duplicate:abc`).
Retained members of a group may appear in at most one partition. Exact duplicate hashes
can be supplied as group tokens. Unknown dependencies and approximate duplicates are not
inferred. Temporal eligibility uses the full source/target interval, not only the target
timestamp: see `interval_allowed` and `docs/API.md`.

## Result contract

* `optimal`: zero-cost unchanged output or optimizer-certified optimum at numerical tolerances.
* `feasible`: verified incumbent, but optimality was not proved before the budget ended.
* `infeasible`: a direct contradiction or a solver proof. An explanation may be included.
* `unknown`: no verified incumbent or infeasibility proof within the budget.

Quarantine is opt-in. A moved record costs its positive integer `weight`; newly quarantining
it costs `weight * quarantine_cost`. This is a weighted trade-off, not a lexicographic
minimum of exclusions and moves. Conflicts are not claimed to be minimum-cardinality.
Only completed deletion checks justify an irreducible explanation.

## Reproduce the results and run the experiments (Tables 1–5)

Follow the [step-by-step reviewer guide](docs/REPRODUCING.md) for prerequisites,
fixed-version checkout, expected outputs, individual suites and troubleshooting.
The evaluation contains **1,140 method outputs across 270 policy scenarios**:
180 original, 800 single-group and 160 coupled OULAD outputs. The package remains
version 0.1.1.

### Step 1: Obtain the fixed research release

```sh
git clone --depth 1 --branch research-2026-11-07 https://github.com/ai-developers33/SplitMend.git SplitMend-review
cd SplitMend-review
git rev-parse HEAD
```

Expected commit: `f35a470b03bcc1729ce4d702a224f9ff9a01f58f`. Run the following
commands from that repository root.

### Step 2: Check integrity and regenerate the saved tables

With Python 3.11 or newer, without installing research dependencies:

```sh
python3 research/scripts/verify_archive.py
python3 research/scripts/check_core_equivalence.py
python3 research/scripts/reproduce_all.py --mode tables
git diff --exit-code -- research/tables
```

Both verification commands must report `all_match: true`. The table command
reports `raw_method_outputs: 1140` and `generated_from_saved_results: true`.
Tables are written to `research/tables/` as CSV and JSON. A successful final
`git diff` produces no output. This regenerates tables from saved records;
it does not rerun optimization.

### Step 3: Execute fresh numerical experiments

Use **Python 3.12 on Linux** and a new output directory:

```sh
python3.12 research/scripts/reproduce_all.py --mode rerun --bootstrap --output ../splitmend-rerun-001
```

The command installs pinned dependencies into separate environments, runs all
three suites, checks assignments and compares results. Missing original source
archives are downloaded; the extension suites use their included derived
cohorts. Internet access is needed for installation and missing source data.

### Step 4: Inspect completion and fresh results

```sh
python3 -m json.tool ../splitmend-rerun-001/unified_reproduction.json
```

Require a successful exit and `mode: rerun`, `complete: true`, with all three
suites present. Fresh Tables 1–5 are in `../splitmend-rerun-001/fresh_tables/`;
stage logs and comparison reports are in the same run directory. See the
[expected reports](docs/REPRODUCING.md#5-check-that-the-numerical-run-completed)
for the exact checks, including bridge movement/quarantine differences.

Reference runs used Python 3.12.14 on x86-64 Linux. Full pinned numerical
reproduction has not been independently validated on macOS or Windows.
Timings and equally optimal assignments may differ; retain failed cases and
unresolved statuses. Existing evidence records development-host checks.

The [expanded repository snapshot](https://doi.org/10.5281/zenodo.24046217) and
[complete research archive](https://doi.org/10.5281/zenodo.24046268) are public.
The complete archive includes the original source ZIPs and additional provenance
omitted from Git. Its commands start with `scripts/`, not `research/scripts/`;
see the [archive instructions](docs/REPRODUCING.md#alternative-start-from-the-complete-zenodo-archive).
The [research README](research/README.md) describes the benchmark scope and
validity denominators.

## Original study only (Tables 1–3)

The original 180-comparison workflow remains available, including external tools
in their separate environment. Use the unified command above for all five tables:

```sh
python scripts/reproduce.py --bootstrap
```

Use Python 3.12 on Linux for the supplied full reference lock files. This installs dependencies and downloads
the original archives if they are not already included. Alternatively, if both environments
are installed, run `python scripts/reproduce.py --baseline-python /path/to/baseline/python`.
The following individual commands run the main study; the full entry point also runs
external comparisons, the clinical extension, stronger repair baselines, exhaustive checks,
fixed classifiers and result verification (180 method runs across 30 repair cases).
Successful completion writes `results/reproduction.json`; a missing completion file means
the full command has not finished. The included rerun is on the development host, not an
independent reproduction.

```sh
python scripts/download_data.py
python scripts/run_experiments.py
python scripts/summarize.py
```

Original datasets are credited in `data/sources.json`, `data/clinical_sources.json` and
`data/README.md`. Experimental
partitions are workflow simulations on real observations, not reports of defects in the
datasets' original published partitions. See `docs/EXPERIMENT_PROTOCOL.md`, `docs/CLINICAL_PROTOCOL.md` and
`docs/STRONG_BASELINE_FOLLOWUP.md`. The clinical extension supplements OULAD. Its protocol
was committed before clinical comparisons, after the original study; it is exploratory.

The clinical study uses all 101,766 UCI diabetes encounters from 71,518 patients. All
15 SplitMend configurations reached verified optima. Aggregate movement cost was 23.47%
lower than violation-first greedy, but only 0.008% lower than cost-aware greedy with
local exchanges (nine fewer changes in total; four wins and eleven ties). The latter
was faster. These results support constraint enforcement and optimality certification,
not a substantial advantage over strong heuristics. See `docs/RESULTS_INTERPRETATION.md`.

## Release

See `docs/RELEASE.md` for release maintenance and research-archive contents.
The repository contains the software, tests, experiment protocols, data-source records,
reference results and benchmark figures. The reproduction harness downloads the public
source datasets and rebuilds the derived assignments and result tables.

Manuscripts and submission forms are maintained separately from the software repository.
The benchmark scripts write their figures to `paper/figures/`.

License: MIT for software. Dataset licenses remain separate.
