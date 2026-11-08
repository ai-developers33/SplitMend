# Reproducing the SplitMend results and running the experiments

This guide covers **all five manuscript tables**. Choose the table-only check
to inspect the saved evidence, or the full rerun to execute the experiments.
The core package remains SplitMend **0.1.1**.

| Route | What it does | Requirements |
| --- | --- | --- |
| Rebuild saved tables | Verifies the files and regenerates Tables 1–5 from 1,140 archived method outputs | Python 3.11 or newer; standard library only |
| Full numerical rerun | Executes the three experiment suites, audits assignments, compares outcomes and produces fresh tables | Python 3.12 on Linux, `venv`, `pip`, internet for dependencies and missing original data |
| Source-data reconstruction | Additionally rebuilds the five extension cohorts from their source files | Full-run environment plus source-loader dependencies and larger downloads |

Reference experiments used Python **3.12.14 on x86-64 Linux**. Exact package
versions are in `research/original/SplitMend/requirements-experiments.lock` and
`requirements-baselines.lock`. The full pinned workflow has not been independently
validated on macOS or Windows. A Mac with Python 3.11 can perform the table-only
checks. No LLM API key or paid API call is required by these experiments.

## 1. Obtain the fixed research version

Run these commands in a terminal, choosing a destination folder that does not
already exist:

```sh
git clone --depth 1 --branch research-2026-11-07 https://github.com/ai-developers33/SplitMend.git SplitMend-review
cd SplitMend-review
git rev-parse HEAD
```

Expected commit:

```text
f35a470b03bcc1729ce4d702a224f9ff9a01f58f
```

The detached-HEAD notice is normal when checking out this fixed release. It
does not prevent running the experiments. All commands below, unless stated
otherwise, run from the **repository root**, where `pyproject.toml` and
`research/` are located.

The expanded source snapshot is archived at
[10.5281/zenodo.24046217](https://doi.org/10.5281/zenodo.24046217).
The complete research archive, including materials omitted from Git, is at
[10.5281/zenodo.24046268](https://doi.org/10.5281/zenodo.24046268).

## 2. Verify the files before running anything

```sh
python3 --version
python3 research/scripts/verify_archive.py
python3 research/scripts/check_core_equivalence.py
```

Both checks must report `"all_match": true`. The first checks the research
manifest; the second confirms that the four core-source copies match the
versioned 0.1.1 wheel. At the fixed GitHub release, the manifest checks **2,784
files**. A checksum failure means that the checked files differ from their
manifest; resolve that difference before interpreting experimental results.

## 3. Rebuild Tables 1–5 from saved results

```sh
python3 research/scripts/reproduce_all.py --mode tables
```

Expected summary fields:

```json
{"tables": [1, 2, 3, 4, 5], "raw_method_outputs": 1140, "generated_from_saved_results": true}
```

The command writes the following files under `research/tables/`:

| Manuscript result | CSV file | Evaluation covered |
| --- | --- | --- |
| Table 1 | `table1.csv` | HAR and original single-group OULAD comparisons |
| Table 2 | `table2.csv` | UCI diabetes across 15 policies |
| Table 3 | `table3.csv` | Exact Block Aggregation comparisons |
| Table 3 temporal companion | `table3_temporal.csv` | Beijing temporal-span quarantine |
| Table 4 | `table4.csv` | Five datasets, 40 scenarios each |
| Table 5 | `table5.csv` | Coupled OULAD and matched valid-pair costs |
| Table 5 diagnostic companion | `table5_unmatched_diagnostics.csv` | Unmatched totals, including invalid heuristic outputs |

JSON versions, `all_tables.md` and `interpretation.json` are also generated.
For the fixed release, this command should leave the tracked table files
unchanged:

```sh
git diff --exit-code -- research/tables
```

No output and exit status zero mean that the regenerated files match the
committed files. This route checks table aggregation from saved records;
it **does not rerun the optimizers or establish a fresh numerical reproduction**.

## 4. Execute the full numerical experiments

Use the reference Python series and a new, nonexistent output directory:

```sh
python3.12 --version
python3.12 research/scripts/reproduce_all.py --mode rerun --bootstrap --output ../splitmend-rerun-001
```

The command creates separate environments at `research/.venv-main` and
`research/.venv-baselines`, installs the supplied pinned dependencies and wheel,
and runs these suites sequentially:

| Suite | Main tables | Policy scenarios | Saved method outputs |
| --- | --- | ---: | ---: |
| `original` | 1–3 | 30 | 180 |
| `single-group` | 4 | 200 | 800 |
| `bridge` | 5 | 40 | 160 |
| Total | 1–5 | 270 | 1,140 |

Tests, controls, aggregation checks and downstream classifier records are
additional to these 1,140 method outputs. The original suite also compares
80 downstream classifier records. These are repeated policy scenarios, not
270 independently sampled datasets.

The original suite downloads missing HAR, OULAD, Beijing and diabetes source
archives and checks the recorded hashes. The extension suites use the included
derived cohorts by default. Installing dependencies and downloading missing
data require internet access. Runtime depends on the machine and network;
the saved timing values are observations from the development host.

Run one unified job at a time within a checkout because the bootstrap uses
shared environment directories. For another attempt, choose a fresh output
name, such as `../splitmend-rerun-002`. Keep the previous output and logs.

## 5. Check that the numerical run completed

The full rerun must exit successfully and create:

```text
../splitmend-rerun-001/unified_reproduction.json
```

Inspect it with:

```sh
python3 -m json.tool ../splitmend-rerun-001/unified_reproduction.json
```

It must contain `"mode": "rerun"`, `"complete": true`, and all three suite
entries. An absent completion file, nonzero exit code or `progress.json` alone
does not establish a completed reproduction.

| Output relative to `../splitmend-rerun-001/` | What to inspect |
| --- | --- |
| `logs/` | Per-stage command output and errors |
| `original_comparison.json` | All 180 original method outputs match the selected reference fields |
| `original_and_downstream_comparison.json` | `all_match: true` for 180 method outputs and 80 classifier records, excluding timing |
| `single_group/rerun_comparison.json` | Five datasets, 40 cases each, with matching status, validity and movement results |
| `single_group/saved_assignment_audit.json` | Assignment audits against cohort counts and declared constraints |
| `bridge/reproduction_comparison.json` | `outputs: 160` and `all_primary_results_match: true`; inspect `all_match` separately |
| `singleton_equivalence.json` | `cases: 40` and `all_equivalent: true` |
| `fresh_tables/` | Tables recomputed from the new numerical outputs |

Use **`fresh_tables/`** when reporting a new full experiment run.
`research/tables/` is regenerated from the saved reference outputs even during
the full workflow. The driver creates `fresh_tables/` only when all three
suites are rerun together.

The bridge comparison requires matching **status, validity and objective**.
It reports movement and quarantine differences separately because equally
optimal solutions can have different decompositions. Read `all_match` before
claiming that every component count is identical. Timing and the identities
of equally optimal assignments can also vary. A timeout or unresolved result
must remain visible and must not be described as a certified optimum.

The reference Table 4 outcomes include 12 feasible and 28 infeasible PAMAP2
policies; greedy succeeds in 6 of the 12 feasible policies. Reference Table 5
has 36 optimal and four infeasible cases. Its best-valid-greedy comparison is
26,890 versus 25,890 aggregate objective cost. These serve as interpretation
checks, not reasons to discard different outcomes from a new environment.

## 6. Run an individual suite

For example, to rerun only the coupled OULAD benchmark:

```sh
python3.12 research/scripts/reproduce_all.py --mode rerun --bootstrap --suites bridge --output ../splitmend-bridge-001
```

Replace `bridge` with `original` for Tables 1–3 or `single-group` for Table 4,
and choose a different output directory. Individual-suite runs write their
suite outputs and completion report; they do not create a complete
`fresh_tables/` directory for all five tables. Use step 4 for that purpose.

## 7. Optionally reconstruct the extension cohorts from source data

After step 4 has created the environments, use:

```sh
research/.venv-main/bin/python -m pip install -r research/requirements/single_group_source_loaders.txt
research/.venv-main/bin/python research/benchmarks/single_group/reproduce.py --from-source --output ../splitmend-source-rerun-001
```

This installs the recorded source-reader dependencies, retrieves the larger
original archives where required, reconstructs cohorts and reruns the five
single-group datasets. It requires additional network access and storage.
See [the source reconstruction protocol](../research/benchmarks/single_group/README.md#rebuild-from-original-public-data)
for exact source files and provider conditions. Hash mismatches must be
investigated; do not silently replace the recorded data with another version.

## Alternative: start from the complete Zenodo archive

Download the ZIP and SHA-256 text file from
[the complete archive record](https://zenodo.org/records/24046268), place them
in the same directory, and check integrity before extraction. On macOS:

```sh
shasum -a 256 -c SplitMend_Research_Archive_0.1.1_DOI_24046268_SHA256.txt
```

On Linux, use `sha256sum -c` with the same checksum filename. After extraction:

```sh
cd SplitMend_Unified_Research_Archive_0.1.1
python3 scripts/verify_archive.py
python3 scripts/check_core_equivalence.py
python3 scripts/reproduce_all.py --mode tables
python3.12 scripts/reproduce_all.py --mode rerun --bootstrap --output ../splitmend-archive-rerun-001
```

The archive has `scripts/` at its top level, whereas the GitHub repository
uses `research/scripts/`. The archive contains the original source ZIPs,
historical evidence and manuscript files omitted from Git. It still needs
internet for dependency installation; selected large original sensor archives
require separate downloads for source reconstruction. Each dataset retains its
own license and attribution requirements.

## Troubleshooting and reporting a reproduction

- **`python3.12` is missing:** install Python 3.12 with `venv` support on the
  Linux machine used for the full run. Python 3.11 remains sufficient for
  step 3, but is not the reference interpreter for the pinned experiment locks.
- **Output directory already exists:** choose a new directory name; preserve
  the previous run for diagnosis.
- **A dependency or source download fails:** retain the error log and confirm
  network access, platform compatibility and availability of the pinned
  version. A failed download is not an experimental outcome.
- **A comparison assertion fails:** retain the new outputs, solver statuses,
  bounds and logs. Report the mismatch, including any alternative optimal
  decomposition, instead of editing the reference values or dropping the case.

For a reproduction report, record the commit or archive DOI, Python and package
versions, operating system and hardware, exact command, exit status, completion
report and relevant comparison reports. Existing validation records document
development-host checks. The script's provenance fields do not automatically
establish independent external reproduction; reviewers should record their own
environment and findings separately.
