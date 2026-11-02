# What the experiments establish

All 15 SplitMend repairs were feasible under the supplied policies and certified optimal
by HiGHS. This is a statement about the tested finite problems, not a guarantee that
every future instance will solve within a time budget.

HAR: mean 2,009.8 changed assignments versus 2,113.8 for greedy repair, 2,478.8 for group
re-splitting, 2,482.2 for the DataSAIL I1 aligned adapter and 2,399.6 for dataset-splitter.
The 4.92% greedy comparison is the most informative edit-cost comparison because both
methods attempt to repair. The fresh constructors optimize a different goal.

OULAD: mean 2,140.6 changes. The majority and greedy rules tie this optimum and are faster.
An approximately 80% reduction relative to fresh splitting measures preservation of old
membership, not a new accuracy improvement or training-time saving.

Beijing: 1,128 of 420,204 windows require quarantine per configuration, preserving 99.73%.
The direct temporal eligibility baseline ties this result and is faster. The case
demonstrates the generic policy mechanism, not a new time-series splitting algorithm.

All 100 exhaustive small cases agree with enumeration. Aggregation leaves the optimum
unchanged in the three selected compressed/uncompressed comparisons; it substantially
reduces model size on repeated HAR/Beijing profiles but barely reduces the selected
OULAD case. Not every dataset benefits equally.

The fixed classifiers do not establish improved predictive performance. Common test
rows are kept identical; training and validation populations change. Five seeds do not
constitute five independent datasets. No external users or independent-host replications
are claimed. The software has a plausible SoftwareX contribution but empirical scope
and adoption remain limits relevant to reviewers.
