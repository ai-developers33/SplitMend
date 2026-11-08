# SplitMend: complete dataset screening

This package records an exploratory search for a **20% aggregate reduction in
moved observations** relative to the best valid output of three greedy methods.
Read [RESULTS.md](RESULTS.md) and `results/screening_summary.csv` first. Individual
large gains are labelled as individual cases; every attempted comparison is
retained. The established clinical experiments have not been replaced.

## Reproduce from the included cohorts

Use Python **3.12** (the numerical dependency versions used here require it).
On a Mac with Homebrew, `brew install python@3.12` supplies that interpreter if
needed. Create a separate environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python reproduce.py --output my_fresh_run
```

The output directory must not exist. This command performs the experiments
again rather than loading the recorded answers, audits every assignment, and
compares validity, statuses and movement counts with the archive. It processes
five cohorts, 40 policy scenarios each, four methods per scenario. Exact runtime
depends on the machine. The archive was evaluated on one development host.

For the two independently enumerated illustrative cohorts only:

```bash
python reproduce.py --datasets har70 sleeptelemetry --output two_cohort_rerun
```

Inspect already saved results without optimization:

```bash
python audit_saved_results.py
python explain_cases.py
python summarize_search.py
```

`environment-full.txt` is a record of the observed development environment,
including unrelated release tools. Install from `requirements.txt`, not that
environment record. The vendored core is used explicitly; no editable source
checkout outside this folder is required.

## Rebuild from original public data

```bash
python reproduce.py --from-source --output source_rebuild_run
```

This additionally downloads the three larger source archives (about 1 GB),
checks their exact SHA256 digests, and regenerates cohorts before running. It
requires network access. The derived cohorts allow the numerical benchmark to
run offline after dependencies are installed. The small original sleep
annotations, participant spreadsheet and ExtraSensory labels are included.

The source downloads may be temporarily unavailable or change at the provider.
Hash mismatches stop the loader; it never silently substitutes a different
dataset. The original large HAR70+, PAMAP2 and UniMiB archives are not bundled.

An optional second-reader check of all original sleep annotations:

```bash
python -m pip install -r requirements-verification.txt
python verify_sleep_annotations.py
python plot_case_explanations.py
```

## What is measured

- Primary: policy validity and the number of observations moved from their
  original train/validation memberships.
- Test participants remain locked. All records for one participant stay
  together. Unit movement cost; quarantine disabled.
- The paired comparator selects the least movement among independently valid
  outputs from `violation_greedy`, `cost_greedy_local` and `all_pair_greedy`.
- The all-pair method examines every one- and two-participant flip during
  feasibility repair and subsequent cost descent. It is a deterministic local
  heuristic, not a claim to represent every possible heuristic.
- If a comparator produces no valid answer, its failure is reported separately
  and never converted to a movement-saving percentage.
- No classifier is trained. There are no new precision, recall, F1 or clinical
  efficacy claims.

`protocol.json` was frozen before phase-1 optimization outcomes. Phase 2 was
added after those outcomes and is separately recorded in
`protocol_phase2.json`. Neither file is an external preregistration. Data
selection is exploratory and all screened candidates are disclosed.

## Files

- `prepare.py`, `prepare_phase2.py`, `download_sources.py`: dataset adapters.
- `run_search.py`, `reproduce.py`: complete experiments and fresh reruns.
- `vendor/`: unmodified SplitMend 0.1.1 core and comparator dependencies.
- `experiment_shared.py`, `neighborhood.py`, `enumeration.py`: reusable
  experiment helpers and independent exhaustive verification.
- `data/derived/`: complete benchmark cohorts and structural summaries.
- `data/source/`: source manifests, small original inputs and attribution.
- `results/<dataset>/cases/`: every policy, assignment, audit, solver outcome
  and available exhaustive certificate.
- `results/screening_summary.csv`, `results/per_method_summary.csv`: regenerated
  tables. All single-run timings remain in the per-case files.
- `results/illustrative_case_explanations.json`: complete neighborhood analysis
  for the two post-hoc examples above 20%.
- `results/illustrative_neighborhoods.png` and `.svg`: plots of that exhaustive
  analysis, showing selected-case gains and the full aggregate results together.
- `fresh_reproduction/`: independently rerun HAR70+ and Sleep Telemetry cases on
  the same host; `rerun_comparison.json` records the outcome comparison.
- `repository_baseline.json`: the checked GitHub commit and core blob hashes.
- `CONTENTS_SHA256.json`: checksum inventory for this delivered archive.

## Dataset attribution and terms

Software code is covered by the included MIT license. **That license does not
relicense the source datasets.** Observe the original providers' terms and cite
their work when reusing these data.

| Dataset | Original source and citation | Terms |
|---|---|---|
| HAR70+ | Ustad et al., *Validation of an Activity Type Recognition Model Classifying Daily Physical Behavior in Older Adults: The HAR70+ Model*, Sensors (2023). [UCI DOI](https://doi.org/10.24432/C5CW3D) | CC BY 4.0, as listed by UCI |
| PAMAP2 | Reiss and Stricker, *Introducing a New Benchmarked Dataset for Activity Monitoring*, ISWC (2012). [UCI DOI](https://doi.org/10.24432/C5NW2H) | CC BY 4.0, as listed by UCI |
| UniMiB SHAR | Micucci, Mobilio and Napoletano, *UniMiB SHAR: A Dataset for Human Activity Recognition Using Acceleration Data from Smartphones*, Applied Sciences 7, 1101 (2017). [Paper DOI](https://doi.org/10.3390/app7101101); [author download page](http://www.sal.disco.unimib.it/technologies/unimib-shar/) | Original provider's research-use and citation terms; no separate MIT license is asserted for data |
| Sleep-EDF Telemetry | Kemp et al., *Analysis of a sleep-dependent neuronal feedback loop: the slow-wave microcontinuity of the EEG*, IEEE TBME 47(9), 1185–1194 (2000). [Dataset DOI](https://doi.org/10.13026/C2X676); [PhysioNet source and required citations](https://physionet.org/content/sleep-edfx/1.0.0/) | Open Data Commons Attribution License v1.0 |
| ExtraSensory | Vaizman et al., *Recognizing Detailed Human Context In the Wild from Smartphones and Smartwatches*, IEEE Pervasive Computing (2017). [Paper DOI](https://doi.org/10.1109/MPRV.2017.3971131); [provider site](https://extrasensory.ucsd.edu/) | Original provider's public-download and citation terms |

Derived tables retain the original participant identifiers and class semantics.
HAR70+ and PAMAP2 observations are converted to nonempty five-second windows;
UniMiB's official segments are unchanged; sleep annotations are expanded to
scored 30-second epochs; ExtraSensory's original annotation rows are retained.
No synthetic patients, participant groups or performance measurements are added.

## Repository status

This screening is a separate reviewable artifact. No public GitHub commit,
release, clinical result file or manuscript was replaced. The available GitHub
connection has read-only access. Any later integration should preserve the
complete screening and existing clinical evidence, state exactly which result
is an individual illustration, and avoid presenting a selected case as an
aggregate improvement.
