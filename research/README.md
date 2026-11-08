# SplitMend expanded research evaluation

This directory integrates the original study and both extensions for Tables 1–5.
SplitMend's core remains **0.1.1**, byte-identical to the released wheel and the
repository source checked at commit `55e63c5a3b92cbf8c82024001d7132186d5870cc`.
The changes add experiments, saved evidence and reproduction utilities.

Start with the [reviewer reproduction guide](../docs/REPRODUCING.md) for numbered
steps, a fixed-release checkout, expected outputs and troubleshooting.

## Rebuild the tables without installing dependencies

From the repository root:

```sh
python3 research/scripts/verify_archive.py
python3 research/scripts/check_core_equivalence.py
python3 research/scripts/reproduce_all.py --mode tables
```

This recomputes Tables 1–5 from **1,140 saved method outputs**. It does not rerun
the optimizers. The seven result CSV files include the temporal and unmatched
diagnostic subtables. All original comparisons remain available.

## Run the numerical experiments again

Use Python 3.12 for the supplied pinned research dependencies:

```sh
python3.12 research/scripts/reproduce_all.py --mode rerun --bootstrap --output research-rerun-001
```

Use a new output directory for each run. The driver creates separate numerical
and external-baseline environments, runs all three suites, audits assignments,
checks the results and regenerates fresh tables. Completion is recorded in
`research-rerun-001/unified_reproduction.json`. A missing completion record means
the full run did not complete successfully. Do not discard failed outputs.

The original HAR, OULAD, Beijing and diabetes source ZIPs are omitted from Git.
The original suite downloads missing archives from the recorded public sources
and checks their hashes. Dependencies and those downloads require internet.
The two new suites contain their derived cohorts and smaller source inputs;
the single-group directory also documents rebuilding from larger public inputs.

The complete research archive is published at
[10.5281/zenodo.24046268](https://doi.org/10.5281/zenodo.24046268).
It includes the original source archives, earlier screening packages,
manuscripts and development-host rerun records omitted here. Selected large
original sensor archives still require separate downloads for source extraction;
installing dependencies also requires internet access.
The expanded repository snapshot is archived at
[10.5281/zenodo.24046217](https://doi.org/10.5281/zenodo.24046217).
The original package DOI `10.5281/zenodo.24021033` and earlier research DOI
`10.5281/zenodo.24021729` continue to identify their original versions.

## Scope and interpretation

Tables 1–3 retain HAR, OULAD, UCI diabetes and Beijing comparisons. Table 4 adds
HAR70+, PAMAP2, UniMiB SHAR, Sleep-EDF Telemetry and ExtraSensory (40 scenarios
each). Table 5 adds 40 OULAD student–offering scenarios with selective quarantine.

For PAMAP2, 12 policies are feasible and 28 are proven infeasible. The greedy
portfolio finds valid repairs in six of the 12 feasible policies; six valid
pairs out of 40 attempts is not a 34/40 failure rate on feasible policies.
The HAR70+ 48.54% movement reduction is a selected, exhaustively checked single
case, not an aggregate dataset improvement.

For coupled OULAD, 36 cases reach certified optima and four are proven infeasible.
The strongest per-case greedy portfolio has aggregate objective 26,890, versus
25,890 for SplitMend (3.72% lower). Retained movement is 5,250 versus 4,840;
quarantine is 2,164 versus 2,105. The first two greedy methods have different
valid subsets, so their objective totals are compared only on matched valid cases.
Faster greedy runtimes, ties and earlier full-cohort diagnostics remain reported.

The benchmark subdirectories are unmodified archived snapshots. Their historical
repository-status statements describe the time those snapshots were prepared.
The numerical runs were checked on the development host; external independent
reproduction is not claimed. macOS packaging commands are provided, but the
complete pinned numerical workflow was validated on Linux, not independently
on a Mac. Equivalent solver optima may have different assignments or decompositions.

## Layout

- `original/SplitMend/`: frozen original experiment code, derived inputs and outputs.
- `benchmarks/single_group/`: five-dataset sweep, cohorts, scripts and all outcomes.
- `benchmarks/bridge/`: coupled OULAD protocol, comparators, controls and outcomes.
- `package/`: release wheel and source used for equivalence checks.
- `scripts/`: unified reproduction, table generation and equivalence checks.
- `tables/`: saved manuscript tables and interpretation metadata.
- `CONTENTS_SHA256.json`: file hashes for this GitHub research subset.

Run the hash check before reproducing: new runs can create caches or regenerate
derived metadata. The nested original snapshots retain their own manifests;
those describe their original full archives. Use the top-level research manifest
for this subset. Software licensing does not replace each dataset's terms and
attribution; see `LICENSES.txt` and each benchmark's README.
