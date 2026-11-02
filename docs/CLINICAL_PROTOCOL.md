# Clinical extension protocol

Recorded on 2026-11-02 before running any clinical repair comparison. This is an
exploratory extension motivated after observing the original three-dataset results;
it is not an external preregistration. OULAD and all original outcomes remain in the
study, irrespective of the clinical outcome.

## Dataset and interpretation

Use the complete UCI Diabetes 130-US Hospitals for Years 1999-2008 encounter table
(DOI 10.24432/C5230J, CC BY 4.0). Keep all rows, including unknown gender values.
Record the archive SHA256 and original schema. Patient identifiers define dependency
groups; encounter identifiers identify rows. Do not interpret encounter IDs as dates.
The released table does not support a hospital-specific split or chronological
admission split unless actual site IDs or admission timestamps are present.

This is a retrospective workflow simulation for evaluation on previously unseen
patients, not a clinical trial, new diagnosis model, clinical efficacy study or claim
that the source authors supplied defective partitions. No patient is reidentified.

## Prespecified workflow and constraints

For seeds 0, 1, 2, 3 and 4, reserve 20% of distinct patient IDs as a fixed test cohort
using a seeded random permutation. Every encounter of these patients is locked to
test. Remaining encounters initially receive train/validation assignments at a 75/25
ratio within joint outcome/age/gender strata. The repair task is to remove patient
overlap between training and validation while preserving this existing test cohort.
Free encounters are eligible only for train or validation. Quarantine is disabled;
every row has unit movement cost. Test cohort selection is independent of repairs.

Joint strata are the three published readmission categories, four fixed age bands
(under 40, 40-59, 60-79, 80+) and the published gender field. These bounds preserve
evaluation coverage; they do not establish fairness or clinical representativeness.
Known stratum membership may vary between encounters of the same patient.

Use three tolerance settings: 0.01, 0.025 and 0.05. For the total free encounter count
and each free stratum count N, validation bounds are floor((0.25-tolerance)*N) through
ceil((0.25+tolerance)*N); training bounds use 0.75 in the same way. Bounds are inclusive
and are clipped to [0,N]. Locked test counts are fixed exactly. Thus tolerance is an
absolute allowance in the fraction of available encounters assigned to a partition,
not a relative percentage change in prevalence. Small strata are retained with the
same rounding rule; no post-outcome stratum removal or tolerance adjustment is allowed.

Run all 15 seed/tolerance combinations, including infeasible or time-limited cases.
Do not choose a winning tolerance as the sole headline result.

## Comparators and budgets

Compare SplitMend, patient-majority repair, a violation-first greedy repair, a
cost-aware greedy repair with subsequent local exchanges, and patient group re-splitting.
All use the same locked test cohort, eligibility, count bounds and independent verifier.
The two greedy repairs share a compact two-partition count representation. They start
from patient-majority assignments, preserve group integrity and only flip unlocked
patients. The violation-first variant chooses the greatest decrease in total count
violation, breaking ties by added movement cost. The cost-aware variant instead
minimizes added movement cost per unit decrease in violation. Equivalent patient
profiles may be represented by counts without changing a candidate's cost or effect.

After the cost-aware variant becomes feasible, allow feasible improving single-patient
moves and pair exchanges. For pair exchanges, examine up to the 256 lowest-cost flip
profiles in each direction, in deterministic order, and select the best feasible
negative-cost exchange. Stop when no improving exchange in this neighborhood exists,
the 60-second combined search budget expires, or 10,000 iterations are reached.
Greedy failure is a heuristic failure, not proof of mathematical infeasibility.

SplitMend receives a 60-second optimization budget, with conflict explanation disabled
for benchmark timing. Report preprocessing and verification overhead separately where
available. A feasible incumbent is never described as a certified optimum. The
violation-first greedy receives the same 60-second search budget and iteration cap.
Fixed method parameters must not be retuned after viewing clinical outcomes.

## Outcomes and checks

Primary: validity, movement cost among valid repairs, solver status/bound/gap and wall
time. Report all per-case outcomes and paired cost differences only where both outputs
are valid. Report ties, losses, heuristic failures, timeouts and infeasibility explicitly.
Fresh split constructors do not optimize movement cost; interpret that comparison
accordingly. Five seeds are repeated partitions of one dataset, not five datasets.

Verify no rows are dropped, every original test record stays fixed, no patient spans
retained partitions, and every size/stratum bound holds. Check new comparator logic on
small controlled cases against the row-level verifier and enumeration. Preserve source
data, derived problems, assignments, policy hashes and raw results for reproduction.
Clinical prediction accuracy, clinician benefit and improved patient outcomes are not
endpoints of this extension.
