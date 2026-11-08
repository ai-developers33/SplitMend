# Regenerated manuscript tables

All values are regenerated from archived method outputs.

## Table 1

| method | har_mean_changes | oulad_mean_changes |
| --- | --- | --- |
| SplitMend | 2009.8 | 2140.6 |
| Original greedy repair | 2113.8 | 2140.6 |
| Cost-aware greedy + exchanges | 2043.8 | 2140.6 |
| Group re-split | 2478.8 | 10717.8 |
| DataSAIL I1 | 2482.2 | 10909.2 |
| dataset-splitter | 2399.6 | 10760.8 |

## Table 2

| tolerance_pp | splitmend_mean_changes | violation_greedy_mean_changes | cost_greedy_local_mean_changes |
| --- | --- | --- | --- |
| 1.0 | 7618 | 10881.8 | 7619.8 |
| 2.5 | 7610.2 | 9833.8 | 7610.2 |
| 5.0 | 7606 | 9120.6 | 7606 |

## Table 3

| dataset | rows | compressed_variables | row_variables | objective | variable_reduction_percent |
| --- | --- | --- | --- | --- | --- |
| HAR | 1904 | 234 | 5730 | 396 | 95.91623036649214 |
| OULAD | 1999 | 8634 | 8778 | 1008 | 1.6404647983595353 |
| BEIJING | 2000 | 132 | 8000 | 10000 | 98.35 |

## Table 4

| dataset | attempted | optimal | infeasible | unresolved | valid_pairs | greedy_failures_on_feasible | greedy_moved | splitmend_moved | aggregate_reduction_percent | wins | ties |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HAR70+ | 40 | 40 | 0 | 0 | 39 | 1 | 26956 | 25799 | 4.292179848642232 | 2 | 37 |
| PAMAP2 | 40 | 12 | 28 | 0 | 6 | 6 | 9622 | 9622 | 0.0 | 0 | 6 |
| UniMiB SHAR | 40 | 40 | 0 | 0 | 40 | 0 | 9926 | 9926 | 0.0 | 0 | 40 |
| Sleep-EDF Telemetry | 40 | 40 | 0 | 0 | 40 | 0 | 114340 | 112778 | 1.3661011019765612 | 2 | 38 |
| ExtraSensory | 40 | 40 | 0 | 0 | 40 | 0 | 379730 | 378804 | 0.24385747768151056 | 4 | 36 |

## Table 5

| comparator | valid_pairs | feasible_cases | comparator_quarantined | splitmend_quarantined | comparator_retained_moved | splitmend_retained_moved | comparator_objective | splitmend_objective | objective_reduction_percent | wins | ties | losses |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| violation_first_bridge | 20 | 36 | 1470 | 1089 | 756 | 2535 | 15456 | 13425 | 13.14052795031056 | 18 | 2 | 0 |
| cost_aware_bridge_exchanges | 23 | 36 | 1481 | 1345 | 2300 | 2692 | 17110 | 16142 | 5.657510227936879 | 14 | 9 | 0 |
| all_pair_bridge | 36 | 36 | 2160 | 2105 | 5641 | 4840 | 27241 | 25890 | 4.959436144047575 | 24 | 12 | 0 |
| best_valid_greedy_per_case | 36 | 36 | 2164 | 2105 | 5250 | 4840 | 26890 | 25890 | 3.718854592785422 | 23 | 13 | 0 |

