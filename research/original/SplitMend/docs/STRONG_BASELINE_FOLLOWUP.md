# Additional comparison prompted by the clinical extension

After observing that the frozen cost-aware clinical heuristic was competitive, apply
the same method and unchanged parameters to all five HAR and all five OULAD cases.
This extension is recorded before these additional comparisons. It is not an external
preregistration. Do not discard the original violation-first greedy or other outputs.

The existing raw sample manifests and policies are reused. Under patient separation,
every member of a group containing a locked test observation must move to test.
Resolve these forced assignments before the heuristic, then restrict remaining groups
to training/validation, matching the scope of the earlier constructor adapters. The
original full policy and original movement objective are independently checked after
the heuristic. Fixed-group movement contributes a constant to the original objective.
The two-partition heuristic does not explore moving unrelated free groups into test;
document this scope rather than presenting it as a general three-partition solver.

Run the exact 60-second cost-aware search and 256-profile exchange pool already fixed
in CLINICAL_PROTOCOL.md, with no outcome-based retuning. Retain failures and near-ties.
