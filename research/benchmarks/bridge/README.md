# SplitMend: certified bridge-quarantine benchmark

This archive tests an existing SplitMend feature on real OULAD enrolments: a retained record must agree with both its student group and its module-presentation group, while quarantined records do not connect those groups. The objective is

`retained rows moved + 10 × newly quarantined rows`.

## Main results

A fixed random sample of 1,000 students contains 1,134 original enrolments across all 22 module-presentations. Every enrolment of each selected student is retained in the input. The student sampling seed is 314159; no student, offering, label or scenario was selected using optimization results. This is a new, explicitly sampled policy-repair experiment, not a full-cohort OULAD result.

All 40 scenarios finished within the configured 60-second solver limit. SplitMend returned 36 certified optimal repairs and four proven infeasible instances. Maximum observed end-to-end solver-call time was 5.811 seconds, including model construction and the library's assignment audit; the median was 1.229 seconds.

| Comparator | Valid / all 40 | Certified valid pairs | SplitMend objective reduction | SplitMend retained-movement reduction |
|---|---:|---:|---:|---:|
| Violation-first bridge greedy | 20/40 | 20 | 13.14% | -235.32% |
| Cost-aware bridge greedy with exchanges | 23/40 | 23 | 5.66% | -17.04% |
| All-pair offering bridge greedy | 36/40 | 36 | 4.96% | 14.20% |
| Best valid greedy output per case | 36/40 | 36 | **3.72%** | **7.81%** |

A negative movement reduction means SplitMend moved more retained rows. That can lower the stated objective by avoiding expensive quarantine. Objective improvement must not be presented as movement improvement against every comparator. Each percentage is calculated from summed costs/counts over that row's paired valid cases; the first two rows cover different subsets and cannot be compared as if they covered all 36 feasible cases.

The best-valid-greedy portfolio selects the cheapest valid result among the three heuristics separately for each case, without reference to the MILP answer. It is the primary strong comparator:

| Metric, summed over all 36 feasible scenarios | Best greedy portfolio | SplitMend | Reduction |
|---|---:|---:|---:|
| Weighted objective | 26,890 | 25,890 | 3.72% |
| Retained enrolments moved | 5,250 | 4,840 | 7.81% |
| Quarantined enrolments | 2,164 | 2,105 | 2.73% |
| All changed enrolments, including quarantine | 7,414 | 6,945 | 6.33% |

These are sums over scenarios that reuse the cohort, not counts of unique people. SplitMend strictly improved the portfolio objective in 23 cases and tied in 13. There were no objective losses among the certified pairs. Portfolio objective reductions were 2.04% for seed 0 and 4.96% for seed 20261107.

The heuristics were faster. Median total times were 0.009, 0.015 and 0.110 seconds for violation-first, cost-aware and all-pair methods, respectively, versus 1.229 seconds for SplitMend. This study demonstrates certification and modest cost improvement, not a speed advantage or a 20% improvement over the strongest comparator.

## Why four scenarios are infeasible

Four initial validation choices share the same locked test fold. For the Withdrawn stratum, 262 rows remain outside test. Test-linked student constraints and eligibility force 44 of those rows into quarantine, leaving at most 218 retained rows. The train and validation lower bounds require 219. This direct count contradiction independently explains all four infeasible results. No method can satisfy those unchanged policies.

## What quarantine enables

Disabling quarantine makes all 40 scenarios infeasible. Each has a verified path of real enrolments connecting a locked test offering to an offering whose rows are prohibited from entering test. Without quarantine, group consistency forces both ends into the same partition. Independent graph witnesses and separate no-quarantine solver controls are included. With quarantine enabled, 36 cases become feasible.

This conclusion is conditional on the stated policy requiring both students and offerings to be disjoint. Sharing an offering is not automatically leakage for every learning task. Here the policy represents evaluation on unseen students and unseen course offerings. The experiment measures repair quality, not predictive accuracy, F1, or real deployment benefit.

## Singleton stripping: verified correction

The unchanged v0.1.1 solver already counts token usage, removes usage-one tokens from the active set, and forms aggregation keys from the remaining tokens. The full-cohort diagnostic therefore already aggregated 32,593 rows into 7,434 blocks and 40,416 variables. Its time limits were not caused by failing to strip 25,247 singleton student tokens.

This benchmark also strips singleton tokens explicitly before calling the solver. In the sampled cohort it removes 874 singleton tokens. Both with and without this redundant preprocessor, the solver constructs exactly the same 345 blocks and 1,824 variables: matrices, costs, variable bounds and constraint bounds match exactly. `singleton_equivalence.json` and `test_bridge.py` record these checks. Faster certification comes from the smaller cohort; it must not be attributed to a new aggregation fix.

## Fixed protocol and comparator scope

- For each of the two fixed fold seeds, shuffle the 22 sorted offering IDs and divide them into five folds. Test all 20 ordered choices of distinct test and initial validation folds: 40 scenarios total.
- All rows in the test fold are locked. Remaining rows may enter train, validation or quarantine. Initial assignments are consistent by offering, while repeated students create real cross-offering connections.
- Targets for the non-test cohort are 75% train and 25% validation, with size tolerance ±5 percentage points and per-outcome tolerance ±8 percentage points. Bounds refer to original non-test counts; quarantine does not change the denominator.
- Every enrolment has unit weight. Quarantine costs 10, retained reassignment costs 1. No artificial duplicates, feature clusters, extra records or generated group links are used.
- The old single-group heuristic adapters reject multi-group inputs. The three included methods are explicitly new extensions of their search strategies, not unchanged legacy implementations or external state-of-the-art libraries.
- Given offering assignments, the adapters choose student retention destinations, quarantine incompatible enrolments, trim upper-bound excess, and perform student-coordinate repair/restoration. Violation-first searches single-offering changes; cost-aware adds opposing-offering exchanges after feasibility; all-pair searches all one/two-offering changes. `bridge_greedy.py` specifies tie breaking and stopping rules. The all-pair name refers to offerings, not an exhaustive joint search over all students and offerings.
- Both the solver and heuristic searches have a 60-second configured budget. All attempted statuses are preserved. Objective comparisons require a valid greedy answer and a valid MILP answer with certified optimal status and matching bound.

There are ten locked-test policy structures, each tested under four different initial validation assignments. Forty scenarios are not forty independent datasets. An overlapping-group problem can also include multiple balance constraints; neither the old nor new experiments imply a general theorem that two-exchange local search is globally optimal.

## Reproduction

The archive includes the original `studentInfo.csv`, provenance hashes, the selected-student manifest, the unmodified vendored SplitMend source, the new comparator code, all assignments, raw statuses/bounds, summaries, controls and a complete fresh local rerun. It requires no API calls or data downloads after installing dependencies.

Use Python 3.12, the version used for the recorded experiment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python reproduce.py
```

This reruns all 160 primary method outputs, audits their assignments, recomputes the comparison table, runs 40 no-quarantine controls, and compares primary results with the archived run. Choose a new empty output directory with `--output` for another fresh run.

The saved fresh rerun reproduced all 160 statuses, validities, objectives, retained-movement counts and quarantine counts. Both runs' assignments were re-audited from the original rows using a separate implementation. This is reproduction on the same development host, not external independent reproduction. Different platforms or solver versions can select alternative optimal assignments; certification and objective agreement are the primary checks, and the harness reports any differences in movement/quarantine decomposition.

Important files:

- `protocol.json`: cohort choice and experimental policy fixed before outcomes.
- `implementation_manifest.json`, `vendor_manifest.json`, `SHA256SUMS.txt`: source and implementation checksums.
- `results/summary.json`, `results/comparison_summary.csv`: aggregate results, including common-valid-case totals and both seed results.
- `results/all_results.csv`: every method/scenario, including invalid outputs and infeasible cases.
- `results/cases/`: complete assignments in the selected cohort's original source-row order, diagnostics and solver bounds.
- `results/assignment_audit.json`: audit of all 160 primary outputs.
- `results/no_quarantine_certificates.json`, `results/no_quarantine_solver_controls.json`: independent structural witnesses and solver controls.
- `results/infeasibility_explanations.json`: the four direct count contradictions.
- `fresh_reproduction/`: the second complete run and comparison with the original results.
- `diagnostics/full_cohort_interrupted/`: earlier full-cohort outputs, frozen code/policy and interruption record. That run was stopped at the user's request. Some incumbents were uncertified and more expensive than greedy; they are preserved as a scalability diagnostic and are not included in the certified comparison table.

## Source attribution and limits

Kuzilek, J., Hlosta, M., and Zdrahal, Z. (2017). *Open University Learning Analytics dataset*. Scientific Data 4, 170171. https://doi.org/10.1038/sdata.2017.171. Dataset release: https://doi.org/10.6084/m9.figshare.5081998.v1. Original archive: https://ndownloader.figshare.com/files/8606371. Data license: CC BY 4.0. Original archive SHA256: `90dda45037939953f979072fa70a809ebe07e90ec783c408762af7698a3825ec`.

The original source table has 32,593 enrolments, 28,785 distinct student IDs and 22 module-presentations. The full source table is included so the random subset is independently reconstructible; it is not relabelled as a newly collected dataset. Code is distributed under the accompanying MIT license; that license does not replace the source data's CC BY attribution conditions.

The supported conclusion is narrow: on this preselected complete-student sample, selective quarantine restores feasibility under a two-namespace policy, and certified repair modestly improves the best of three custom greedy extensions. Broader accuracy, superiority across datasets, full-cohort runtime, or a 20% strong-comparator improvement are not established.
