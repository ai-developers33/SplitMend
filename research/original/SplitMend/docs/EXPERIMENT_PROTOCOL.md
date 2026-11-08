# Evaluation protocol recorded before experiments

Date: 2026-11-02. Version: 1.0. No empirical outcome is assumed.

Research questions: Can repair preserve locked assignments and satisfy explicit separation,
eligibility, size and class constraints? How many existing assignments must change compared
with group-majority repair, scikit-learn re-splitting, and DataSAIL where applicable? Does
exact aggregation reduce optimization size without changing the optimum? Can conflicts
be explained and reproduced?

Data: complete UCI HAR feature/subject/label release; OULAD studentInfo.csv; complete
Beijing multi-site hourly release. Original archives, URLs, licenses, hashes and derived
sample manifests are retained. These are retrospective workflow simulations on real data,
not claims that dataset authors published defective splits. Deliberately contradictory
locks and small mathematical problems are separate controlled tests.

Seeds: 0, 1, 2, 3, 4. Main experiments: (1) create a validation split from a fixed HAR
test set, (2) repair row-random OULAD partitions for an unseen-student task while locking
the existing test rows, (3) enforce complete source/target time-window containment on
Beijing forecast examples. Also test clean no-op cases and conflicting locks. A record
is excluded only when policy explicitly permits quarantine.

Primary measures: verified validity; weighted edit cost; reassigned and quarantined
records; wall time; solver lower bound/gap; model sizes. Invalid outputs are not counted
as cheap successful repairs. Baselines are audited by exactly the same verifier and
their limitations are reported. Fresh splits without lock support receive no credit
for violating locks. Where a baseline can preserve locks through an adapter, report it.

Correctness: exhaustive enumeration of seeded problems with at most 7 rows; uncompressed
vs compressed model comparison; independent row-level audit; inconsistent and infeasible
policies; CLI and installed wheel checks. Numerical optimality is relative to HiGHS
tolerances. Time-limited incumbents are distinguished from proved optima.

Impact: rerun fixed simple classifiers on HAR and OULAD; compare held-out performance
on common test records, together with retention and partition changes. Do not tune on
test outcomes. Beijing measures temporal eligibility and retention, not a claimed new
forecasting method. Report all predefined seeds, including failures. Group-level or
dataset-level summaries are used; seeds are not independent new datasets.

Limits: no claim to infer unknown dependencies, restore blindness after past test
exposure, preserve comparability with an official benchmark after changing its split,
or establish user adoption. A second local environment is not independent-host replication.

Implementation-stage addendum: baseline generation times and the common row-level audit
are recorded separately; their sum is `verified_seconds`. SplitMend's call also includes
its internal before/after checks and fingerprinting. DataSAIL 1.4.0 is the available PyPI
release (the repository's main branch identified itself as 1.4.1). It uses relative
ratio bounds, unlike the absolute policy bounds. In addition to epsilon=0.10, delta=0.20,
run a tighter epsilon=0.02, delta=0.05 configuration for ALL seeds, retaining both sets
of results. This follows observing native ratio outputs outside the common policy; it
is not a preregistered comparison, and invalid native outputs are not called bugs.

A further `datasail_i1_aligned` adapter computes conservative relative tolerances from
the common absolute lower and upper bounds, using complementary lower bounds for the
two unlocked partitions. All ten cases are run. This is the main DataSAIL comparison;
the two fixed-tolerance variants remain in the archive to make the implementation-stage
change visible. Main repair results were not used to tune SplitMend's objective or bounds.
