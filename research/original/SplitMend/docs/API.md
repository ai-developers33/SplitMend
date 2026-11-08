# API and mathematical contract

## Inputs

`Sample(id, original, groups=(), label='', allowed=None, locked=False, weight=1)`
describes one record. IDs are unique nonempty strings. Partition names and labels are
strings. Weights are positive integers. A group token describes a user-declared
dependence, for example `patient:123` or `duplicate:SHA256`. All retained records sharing
a token must occupy the same partition. Multiple group tokens per row are supported.

`allowed=None` permits all ordinary partitions; `allowed=()` permits none. Quarantine
is a separate destination only when enabled in the policy. A lock fixes the original
assignment, including quarantine if that was the original assignment.

`Policy(partitions, size_bounds, label_bounds, allow_quarantine, quarantine_cost)`
specifies inclusive integer [lower, upper] counts. Counts exclude quarantined rows.
`label_bounds` maps each class name to a map of partition bounds. No fraction or class
balance is silently inferred. Inconsistent but well-formed constraints yield an
infeasibility result; malformed inputs raise `ValueError`.

`interval_allowed(start, end, windows)` returns windows fully containing the finite,
half-open dependency interval [start, end). Include feature-history and target-label
times. Embargo gaps are represented by gaps between the supplied windows. This helper
does not discover causal dependencies or inspect a dataframe's feature engineering.

## Objective

An unchanged row has cost zero. Reassigning a row to another ordinary partition costs
its weight. Newly assigning it to quarantine costs its weight times quarantine_cost.
Moving an originally quarantined row back into a partition costs its weight. The
objective is the sum of these costs, subject to all constraints.

For every row i and destination p, the conceptual variable x[i,p] is binary with
sum_p x[i,p] = 1. For each group g and ordinary partition p, y[g,p] is binary with
sum_p y[g,p] <= 1 and x[i,p] <= y[g,p] for rows containing g. Quarantine has no such
group linkage: removing a bridge record can disconnect two distinct dependence groups.
Locks and eligibility zero prohibited assignment variables. Size and class constraints
bound sums of the appropriate assignment variables.

The implementation aggregates rows having identical active group tokens, original
partition, label, eligibility, lock and weight. An aggregate assignment variable is
integer in [0, block_size]. This aggregation is exact: each original assignment can be
summed into a feasible block assignment with identical objective, and each integer block
assignment can be expanded into row assignments because all member constraints and
costs are identical. Singleton group tokens are safely omitted from the optimizer.
The returned row mapping is verified by an independent implementation of the constraints.

## Repair and explanation

`repair(samples, policy, time_limit=60, explain=True, conflict_checks=64,
conflict_time_limit=2, compress=True)` returns a JSON-serializable dictionary.
The solver time limit excludes input validation, model construction and output audit;
conflict explanation has a separate budget per feasibility check. It is not a strict
whole-call deadline. All solver statuses and any incumbent lower bound/gap are retained.

`optimal` means zero unchanged cost or HiGHS optimality at numerical tolerances.
`feasible` means a verified incumbent without an optimality proof. `unknown` is never
reported as infeasible. No assignments are returned for infeasible or unknown results.
Solver outputs failing row-level verification raise an error rather than being exported.

Direct lock/group or lock/eligibility contradictions produce a small witness. Other
infeasible problems use deletion tests over named constraint families. A completed
explanation is irreducible relative to those families and the assignment axioms; it is
not necessarily the smallest conflicting set. Budget exhaustion is reported explicitly.

`audit(samples, policy, assignments=None)` checks complete row-level membership, groups,
eligibility, locks, quarantine permission, size bounds and class bounds. Omitted
assignments mean the original split. Unknown, missing or additional IDs are errors.

## Reproducibility limits

Input SHA256 identifies the canonical row metadata and policy, not the complete feature
matrix. Dataset archive hashes separately identify source bytes. Multiple assignments
may have the same optimal cost; solver/platform changes can select different optima.
Pin the published environment when reproducing exact assignments. Timings depend on
hardware and load. Never interpret a repaired split as undoing past test exposure.
