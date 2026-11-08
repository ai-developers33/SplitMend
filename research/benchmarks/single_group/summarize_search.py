"""Regenerate the complete screening tables; refuse incomplete datasets."""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parent
NAMES={"har70":"HAR70+","pamap2":"PAMAP2","unimib":"UniMiB SHAR","sleeptelemetry":"Sleep-EDF Telemetry","extrasensory_revision":"ExtraSensory (policy revision)"}


def main():
    rows=[];method_rows=[]
    for dataset,title in NAMES.items():
        p=ROOT/"results"/dataset
        summary=json.loads((p/"summary.json").read_text())
        assert summary["complete"],dataset
        cohort=json.loads((ROOT/"data/derived"/(dataset+".json")).read_text())
        cases=pd.read_csv(p/"all_comparisons.csv")
        valid=cases[cases.splitmend_valid&cases.greedy_valid&(cases.greedy_changed>0)]
        max_percent=float((100*valid.saved/valid.greedy_changed).max()) if len(valid) else 0
        rows.append({"dataset":dataset,"name":title,"observations":cohort["observations"],"participants":cohort["participants"],
            "strata":cohort["labels"],"attempted":summary["cases"],"optimal":summary["optimal"],"infeasible":summary["infeasible"],
            "unresolved":summary["unknown_or_feasible_unproven"],"paired_valid":summary["paired"],
            "nonzero_paired_cases":summary["paired_nonzero_greedy"],"wins":summary["wins"],"ties":summary["ties"],
            "splitmend_paired_total":summary["paired_splitmend_total"],"greedy_paired_total":summary["paired_greedy_total"],
            "total_saved":summary["paired_saved_total"],"aggregate_reduction_percent":summary["aggregate_reduction_percent"],
            "largest_individual_case_percent":max_percent,"qualifies":summary["qualifies_for_20_percent_claim"]})
        for method in ["violation_greedy","cost_greedy_local","all_pair_greedy"]:
            pairs=cases[cases.splitmend_valid&cases[method+"_valid"]]
            base=float(pairs[method+"_changed"].sum());exact=float(pairs.splitmend_changed.sum())
            method_rows.append({"dataset":dataset,"method":method,"valid_outputs":int(cases[method+"_valid"].sum()),
                "paired":len(pairs),"greedy_movement":base,"splitmend_movement":exact,
                "aggregate_reduction_percent":100*(base-exact)/base if base else 0,
                "method_median_seconds":float(cases[method+"_seconds"].median()),
                "splitmend_median_seconds":float(cases.splitmend_seconds.median())})
    table=pd.DataFrame(rows);table.to_csv(ROOT/"results/screening_summary.csv",index=False)
    pd.DataFrame(method_rows).to_csv(ROOT/"results/per_method_summary.csv",index=False)
    report=["# SplitMend dataset screening: measured results", "",
        "This is an exploratory search for a 20% aggregate movement reduction, not an independently preregistered performance claim. Phase 2 was selected after phase-1 outcomes were known. All attempted cases are retained.","",
        "## Complete comparisons","",
        "The comparator is the least-cost valid output among violation-first greedy, cost-aware greedy with local exchanges, and greedy with every one- and two-participant flip. An invalid result is reported as invalid and is not counted as a cost saving.","",
        "| Dataset | Cases | Optimal / infeasible / unresolved | Paired valid | Wins / ties | Fewer moves (aggregate) | Largest individual case |",
        "|---|---:|---|---:|---|---:|---:|"]
    for r in rows:
        report.append(f"| {r['name']} | {r['attempted']} | {r['optimal']} / {r['infeasible']} / {r['unresolved']} | {r['paired_valid']} | {r['wins']} / {r['ties']} | {r['aggregate_reduction_percent']:.4f}% | {r['largest_individual_case_percent']:.4f}% |")
    report += ["", "Aggregate reduction = 100 × (sum of comparator moves − sum of SplitMend moves) / sum of comparator moves, over every case where both methods produce a valid assignment. This is not an F1, precision, predictive-accuracy or runtime improvement. Repeated cases reuse the same source cohort; totals are not unique people or records saved in deployment.","",
        "## Decision","",
        ("At least one candidate meets the frozen screening rule; any paper claim must still state the comparator, policy design, exploratory selection and full results." if any(r['qualifies'] for r in rows) else
         "No candidate meets the frozen 20% aggregate screening rule. These results do not justify replacing the clinical benchmark with a dataset-wide 20% superiority claim. Existing clinical evidence remains relevant and should be preserved."),"",
        "## Why the large individual gains do not establish an average gain","",
        "The HAR70+ case seed0_test2_val1 requires 954 moved five-second windows with SplitMend and 1,854 with the best valid tested greedy output: 48.54% fewer. Enumeration checks all 16,384 allocations of 14 free participants. The greedy output has no improving feasible single- or pair-participant move; a three-participant move can improve it. Its globally optimal assignment differs from the greedy output in six participant memberships.","",
        "The Sleep Telemetry case seed0_test2_val1 requires 4,035 moved 30-second epochs versus 5,431: 25.70% fewer. Enumeration checks all 262,144 allocations of 18 free participants. A strict feasible improvement requires at least four participant memberships to change together. The globally optimal solution is five membership changes away. These explanations are post-hoc illustrations selected from the full screening, not representative averages.","",
        "The full tables contain many ties because a feasible greedy solution frequently already has the minimum attainable movement. Exhaustive enumeration or a zero-gap solver certificate establishes those equalities. Large group sizes alone do not guarantee a substantial optimization advantage.","",
        "## Protocol and limitations","",
        "Each cohort uses all retained participants. Two fixed shuffle seeds (0 and 20261107) produce five participant folds each; all 20 ordered test/validation-fold pairs per seed are evaluated. Test participants remain locked. Other participants can move between train and validation. Targets are 75/25 of non-test observations, with ±5 percentage-point size bounds and ±8 percentage-point per-stratum bounds. Unit costs, no quarantine. These are constructed policy-revision scenarios on real observations, not errors discovered in the original dataset splits.","",
        "The 20% rule also requires at least 20 paired valid cases, at least five in each seed, positive aggregate gains in each seed and no unresolved optimizer runs. A small number of favorable cases cannot satisfy the rule. PAMAP2 has very few participants and many infeasible policy instances; infeasibility is independently checked rather than scored as success.","",
        "HAR70+ and PAMAP2 use nonempty non-overlapping five-second recorded-time bins with modal labels; all selected source rows contribute. UniMiB uses all official activity/fall segments. Sleep Telemetry uses every scored 30-second epoch across both nights and strata defined by sleep stage × original treatment condition. ExtraSensory uses every original annotation record, retaining unreported main activity as a distinct stratum.","",
        "Per-method timings are included in the raw files for transparency. Dataset jobs overlapped on this development host; these timings are not controlled standalone runtime benchmarks. This study establishes assignment costs and feasibility, not classifier performance or clinical utility. Same-host reruns are not external independent reproduction.","",
        "## Verification","",
        "The five vendored SplitMend core files match the recorded GitHub main commit (see repository_baseline.json). Each run checks assignments using the package audit and a separate row-level checker. audit_saved_results.py rechecks every saved group assignment from the source cohort counts without calling SplitMend. Every problem with at most 18 free participants is also exhaustively enumerated.","",
        "HAR70+ and Sleep Telemetry were rerun in a new output directory, including all 80 cases and all 320 method executions. The rerun comparison records statuses, validity and movement costs; timings may differ. The 44 original sleep annotation files also match MNE's independent decoder exactly. PyEDFlib accepts and matches 37; seven original calendar-date headers are rejected by PyEDFlib, so unchanged annotation bytes are decoded directly. No participant is removed for that reason.","",
        "The scripts, source URLs and hashes, derived cohorts, all method outputs, independent audits, enumerations and the fresh-rerun comparison are included. See README.md for commands and data attribution. No public repository or manuscript has been replaced by this screening."]
    (ROOT/"RESULTS.md").write_text("\n".join(report)+"\n")
    print(table[["name","paired_valid","aggregate_reduction_percent","qualifies"]].to_string(index=False))


if __name__=="__main__":main()
