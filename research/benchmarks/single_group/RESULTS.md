# SplitMend dataset screening: measured results

This is an exploratory search for a 20% aggregate movement reduction, not an independently preregistered performance claim. Phase 2 was selected after phase-1 outcomes were known. All attempted cases are retained.

## Complete comparisons

The comparator is the least-cost valid output among violation-first greedy, cost-aware greedy with local exchanges, and greedy with every one- and two-participant flip. An invalid result is reported as invalid and is not counted as a cost saving.

| Dataset | Cases | Optimal / infeasible / unresolved | Paired valid | Wins / ties | Fewer moves (aggregate) | Largest individual case |
|---|---:|---|---:|---|---:|---:|
| HAR70+ | 40 | 40 / 0 / 0 | 39 | 2 / 37 | 4.2922% | 48.5437% |
| PAMAP2 | 40 | 12 / 28 / 0 | 6 | 0 / 6 | 0.0000% | 0.0000% |
| UniMiB SHAR | 40 | 40 / 0 / 0 | 40 | 0 / 40 | 0.0000% | 0.0000% |
| Sleep-EDF Telemetry | 40 | 40 / 0 / 0 | 40 | 2 / 38 | 1.3661% | 25.7043% |
| ExtraSensory (policy revision) | 40 | 40 / 0 / 0 | 40 | 4 / 36 | 0.2439% | 6.6421% |

Aggregate reduction = 100 × (sum of comparator moves − sum of SplitMend moves) / sum of comparator moves, over every case where both methods produce a valid assignment. This is not an F1, precision, predictive-accuracy or runtime improvement. Repeated cases reuse the same source cohort; totals are not unique people or records saved in deployment.

## Decision

No candidate meets the frozen 20% aggregate screening rule. These results do not justify replacing the clinical benchmark with a dataset-wide 20% superiority claim. Existing clinical evidence remains relevant and should be preserved.

## Why the large individual gains do not establish an average gain

The HAR70+ case seed0_test2_val1 requires 954 moved five-second windows with SplitMend and 1,854 with the best valid tested greedy output: 48.54% fewer. Enumeration checks all 16,384 allocations of 14 free participants. The greedy output has no improving feasible single- or pair-participant move; a three-participant move can improve it. Its globally optimal assignment differs from the greedy output in six participant memberships.

The Sleep Telemetry case seed0_test2_val1 requires 4,035 moved 30-second epochs versus 5,431: 25.70% fewer. Enumeration checks all 262,144 allocations of 18 free participants. A strict feasible improvement requires at least four participant memberships to change together. The globally optimal solution is five membership changes away. These explanations are post-hoc illustrations selected from the full screening, not representative averages.

The full tables contain many ties because a feasible greedy solution frequently already has the minimum attainable movement. Exhaustive enumeration or a zero-gap solver certificate establishes those equalities. Large group sizes alone do not guarantee a substantial optimization advantage.

## Protocol and limitations

Each cohort uses all retained participants. Two fixed shuffle seeds (0 and 20261107) produce five participant folds each; all 20 ordered test/validation-fold pairs per seed are evaluated. Test participants remain locked. Other participants can move between train and validation. Targets are 75/25 of non-test observations, with ±5 percentage-point size bounds and ±8 percentage-point per-stratum bounds. Unit costs, no quarantine. These are constructed policy-revision scenarios on real observations, not errors discovered in the original dataset splits.

The 20% rule also requires at least 20 paired valid cases, at least five in each seed, positive aggregate gains in each seed and no unresolved optimizer runs. A small number of favorable cases cannot satisfy the rule. PAMAP2 has very few participants and many infeasible policy instances; infeasibility is independently checked rather than scored as success.

HAR70+ and PAMAP2 use nonempty non-overlapping five-second recorded-time bins with modal labels; all selected source rows contribute. UniMiB uses all official activity/fall segments. Sleep Telemetry uses every scored 30-second epoch across both nights and strata defined by sleep stage × original treatment condition. ExtraSensory uses every original annotation record, retaining unreported main activity as a distinct stratum.

Per-method timings are included in the raw files for transparency. Dataset jobs overlapped on this development host; these timings are not controlled standalone runtime benchmarks. This study establishes assignment costs and feasibility, not classifier performance or clinical utility. Same-host reruns are not external independent reproduction.

## Verification

The five vendored SplitMend core files match the recorded GitHub main commit (see repository_baseline.json). Each run checks assignments using the package audit and a separate row-level checker. audit_saved_results.py rechecks every saved group assignment from the source cohort counts without calling SplitMend. Every problem with at most 18 free participants is also exhaustively enumerated.

HAR70+ and Sleep Telemetry were rerun in a new output directory, including all 80 cases and all 320 method executions. The rerun comparison records statuses, validity and movement costs; timings may differ. The 44 original sleep annotation files also match MNE's independent decoder exactly. PyEDFlib accepts and matches 37; seven original calendar-date headers are rejected by PyEDFlib, so unchanged annotation bytes are decoded directly. No participant is removed for that reason.

The scripts, source URLs and hashes, derived cohorts, all method outputs, independent audits, enumerations and the fresh-rerun comparison are included. See README.md for commands and data attribution. No public repository or manuscript has been replaced by this screening.
