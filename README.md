# SplitMend

SplitMend repairs **existing** machine-learning dataset partitions under explicit constraints.
It minimizes a weighted assignment-change objective, keeps locked records fixed, supports
group/duplicate separation and time-window eligibility, and independently verifies every
returned assignment. It uses SciPy's HiGHS integer optimizer; it does not call an LLM.

Version 0.1.1 is a research release. Publication on GitHub/PyPI is a separate release step.

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

## Reproduce

For the full evaluation, including the external tools in their separate environment:

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

See `docs/RELEASE.md` for wheel creation, TestPyPI/PyPI account setup, trusted publishing,
GitHub release preparation and SoftwareX submission items. You do not need approval from
the Python language developers to distribute a package. Uploading establishes a PyPI
project subject to PyPI's name and account policies.

The editable manuscript is in `paper/`. After running the experiments, install the
optional `paper` dependencies and run `python scripts/make_manuscript.py` to regenerate
its tables and DOCX. PDF conversion requires Microsoft Word or LibreOffice; the PDF
included in the research bundle was rendered and visually checked.

License: MIT for software. Dataset licenses remain separate.
