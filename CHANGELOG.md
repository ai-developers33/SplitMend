# Changes

## 0.1.1

Add the full UCI diabetes admission cohort as an exploratory fourth dataset without
removing the earlier results. Archive a protocol fixed before the clinical comparisons,
15 clinical policies, five methods, source provenance, all assignments and independent
checks. Add a cost-aware greedy comparator with local exchanges and transparently apply
it to the previous classification cases. It nearly ties the clinical optima and ties
OULAD; report those limits alongside improvements over weaker comparators. Extend the
one-command harness to 180 method runs, add 21 comparator checks and two file-writing
checks, and update the paper. Compressed results are now written to temporary files,
flushed and atomically replaced after an archive check detected two incomplete files
in an earlier rerun; verification refuses incomplete artifacts.
The library's repair algorithm is unchanged. Public publication remains pending.

## 0.1.0

Initial research release: immutable input records and policies; weighted assignment
repair; group, lock, eligibility, size and class constraints; optional quarantine;
exact record-profile aggregation; row-level verification; solver-status distinctions;
bounded conflict explanations; JSON API/CLI; tests, real-data comparisons and release
workflows. Public index publication is pending owner account setup.
