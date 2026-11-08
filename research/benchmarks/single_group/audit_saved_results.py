"""Check stored assignments from cohort counts without calling SplitMend.

Each participant is an indivisible group in these protocols. Counting all
cohort rows per participant and label is therefore an exact assignment audit,
not a sampling approximation. Checks both valid and invalid method outputs.
"""
from pathlib import Path
from collections import Counter
import argparse
import json
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parent


def audit(dataset,results):
    frame=pd.read_csv(ROOT/"data/derived"/(dataset+".csv.gz"),dtype={"participant":str})
    counts=pd.crosstab(frame.participant,frame.label)
    sizes=counts.sum(axis=1)
    assert int(sizes.sum())==len(frame)
    groups={"participant:"+p:p for p in counts.index}
    checks=[]
    for folder in sorted((results/dataset/"cases").glob("*")):
        problem=json.loads((folder/"problem_metadata.json").read_text())
        locked=set(problem["test_participants"])
        initial_val=set(problem["original_validation_participants"])
        original={p:"test" if p in locked else "validation" if p in initial_val else "train" for p in counts.index}
        for method in ["violation_greedy","cost_greedy_local","all_pair_greedy","splitmend"]:
            record=json.loads((folder/(method+".json")).read_text())
            summary=record["summary"]
            assert record["problem_sha256"]==problem["problem_sha256"]
            assignment=record["group_assignments"]
            if not assignment:
                assert method=="splitmend" and summary["status"] in ["infeasible","unknown"]
                assert not summary["valid"] and summary["changed"] is None
            else:
                assert set(assignment)==set(groups),(dataset,folder.name,method)
                by_person={groups[g]:part for g,part in assignment.items()}
                allowed=all(part=="test" if p in locked else part in ["train","validation"] for p,part in by_person.items())
                changed=sum(int(sizes[p]) for p,part in by_person.items() if part!=original[p])
                totals=Counter();strata={label:Counter() for label in counts.columns}
                for p,part in by_person.items():
                    totals[part]+=int(sizes[p])
                    for label in counts.columns:strata[label][part]+=int(counts.loc[p,label])
                valid=allowed and all(lo<=totals[part]<=hi for part,(lo,hi) in problem["size_bounds"].items())
                valid=valid and all(lo<=strata[label][part]<=hi for label,limits in problem["label_bounds"].items() for part,(lo,hi) in limits.items())
                assert valid==summary["valid"]==record["independent_audit"]["valid"]
                assert changed==summary["changed"]==record["independent_audit"]["changed"]
                if method=="splitmend" and summary["status"]=="optimal":
                    assert valid and abs(summary["lower_bound"]-changed)<1e-6 and summary["gap"]==0
            if method=="splitmend" and (folder/"enumeration.json").exists():
                certificate=json.loads((folder/"enumeration.json").read_text())
                assert summary["status"]==("optimal" if certificate["valid_allocations"] else "infeasible")
                assert summary["changed"]==certificate["optimal_movement"]
            checks.append({"case":folder.name,"method":method,"valid":summary["valid"],"changed":summary["changed"],"audit_matches":True})
    assert len(checks)==160,(dataset,len(checks))
    return {"dataset":dataset,"cases":40,"method_assignments_checked":len(checks),"all_match":True,"checks":checks}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--datasets",nargs="+",default=["har70","pamap2","unimib","sleeptelemetry","extrasensory_revision"])
    p.add_argument("--results",type=Path,default=ROOT/"results")
    args=p.parse_args()
    results=[audit(name,args.results) for name in args.datasets]
    output={"method":"Exact cohort-level count audit of saved participant assignments; no SplitMend calls.","datasets":results,"all_match":all(x["all_match"] for x in results)}
    (args.results/"saved_assignment_audit.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"datasets":len(results),"method_assignments_checked":sum(x["method_assignments_checked"] for x in results),"all_match":output["all_match"]}))
