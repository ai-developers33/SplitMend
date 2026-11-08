# What the experiments establish

Across four public datasets and 30 constructed repair cases, all SplitMend outputs
satisfied the supplied policies and were certified optimal by HiGHS within solver
numerical tolerances. This describes the tested finite problems, not every future
instance or a new optimization algorithm. All original results are retained.

## Clinical extension

The full UCI diabetes table supplies 101,766 encounters from 71,518 patients. A fixed
20% patient test cohort is locked; the remaining encounters are repaired into disjoint
patient groups with train/validation size and 25 outcome-age-gender stratum bounds.
Five seeds and three tolerances yield 15 cases. These are repeated configurations of
one dataset, not 15 independent cohorts. No hospital identifiers or admission dates
are available, and no clinical benefit or predictive accuracy is evaluated.

| Tolerance (percentage points) | SplitMend mean changes | Violation-first greedy | Cost-aware greedy + exchanges |
|---|---:|---:|---:|
| 1 | 7,618.0 | 10,881.8 | 7,619.8 |
| 2.5 | 7,610.2 | 9,833.8 | 7,610.2 |
| 5 | 7,606.0 | 9,120.6 | 7,606.0 |

All three methods are valid in all 15 cases. SplitMend saves 35,010 assignment changes
versus violation-first greedy: 23.468% of the baseline's aggregate movement. Against
cost-aware greedy with local exchanges it saves nine changes total: 0.00788%, with
four wins, eleven ties and no losses. The largest single-case saving is five records.
The cost-aware heuristic is faster. The clinical evidence therefore does not support
a substantial advantage over a well-designed heuristic. It supports optimum
certification, consistent policy enforcement and a reproducible comparison.

Patient majority fails the count policy in all 15 cases. Group re-splitting is valid
in four cases. Invalid outputs are retained and do not enter successful cost summaries.
Fresh constructors pursue a different objective, so their larger movement is not a
like-for-like test of optimal repair algorithms.

The protocol was committed before clinical comparisons, after the original study; it
is an exploratory extension, not external preregistration. All fixed tolerances and
seeds are reported. OULAD was supplemented rather than replaced.

## Previous datasets and stronger-baseline follow-up

HAR: mean 2,009.8 changed assignments versus 2,113.8 for the original greedy repair,
2,043.8 for cost-aware greedy with exchanges, 2,478.8 for group re-splitting, 2,482.2
for the DataSAIL I1 aligned adapter and 2,399.6 for dataset-splitter. The cost-aware
comparison is more informative: one win and four ties, saving 170 changes total
(1.66%). This follow-up was recorded after the clinical results and before running
these ten additional HAR/OULAD comparisons; no comparator parameters were retuned.
Its adapter fixes all groups forced into test and searches the remaining train/
validation assignments, not every possible free-group transfer into test.

OULAD: mean 2,140.6 changes. Majority, original greedy and cost-aware local repair all
tie the optimum and are faster. An approximately 80% reduction versus fresh splitting
measures preservation of old membership, not accuracy or training-time improvement.

Beijing: 1,128 of 420,204 windows require quarantine per configuration, preserving
99.73%. Direct temporal eligibility ties this result and is faster. This demonstrates
the policy mechanism, not a new time-series splitting algorithm.

## Correctness, practical scope and limitations

All 100 exhaustive small cases agree with enumeration. Aggregation preserves the
optimum in three selected compressed/uncompressed comparisons; model-size savings
are substantial for repeated HAR/Beijing profiles but small for OULAD. Twenty-one
new comparator tests and two archive-writing tests supplement the original 49 tests. All saved assignments are
re-audited and invalid baseline verdicts must reproduce as invalid.

Fixed classifiers demonstrate integration, without an improvement in accuracy.
Common test rows are identical but training and validation populations change.
The full harness covers 180 method runs on 30 cases; controls and classifiers are
additional checks, not independent datasets. The rerun is on the development host.
No external adoption, independent replication or novel dataset defects are claimed.
SoftwareX relevance rests on the reusable library, explicit policy representation,
qualified result statuses and evidence, not a guarantee of editorial acceptance.
