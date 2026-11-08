"""Post-hoc explanations of the two observed >20% individual cases.

These cases are illustrative, selected after outcomes. The headline screening
statistic remains the aggregate of every paired valid case in each dataset.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent


def explain(dataset,case):
    folder=ROOT/"results"/dataset/"cases"/case
    problem=json.loads((folder/"problem_metadata.json").read_text())
    methods={m:json.loads((folder/(m+".json")).read_text()) for m in ["violation_greedy","cost_greedy_local","all_pair_greedy","splitmend"]}
    greedy=min((r for m,r in methods.items() if m!="splitmend" and r["summary"]["valid"]),key=lambda r:r["summary"]["changed"])
    exact=methods["splitmend"]
    frame=pd.read_csv(ROOT/"data/derived"/(dataset+".csv.gz"),dtype={"participant":str})
    counts=pd.crosstab(frame.participant,frame.label)
    locked=set(problem["test_participants"])
    people=sorted(set(frame.participant)-locked)
    initial=np.array([p in problem["original_validation_participants"] for p in people],dtype=np.int64)
    final=np.array([greedy["group_assignments"]["participant:"+p]=="validation" for p in people],dtype=np.int64)
    vectors=np.c_[counts.loc[people].sum(axis=1),counts.loc[people].to_numpy()]
    limits=[problem["size_bounds"],*[problem["label_bounds"][label] for label in counts.columns]]
    totals=vectors.sum(axis=0)
    low=np.array([max(b["validation"][0],int(n)-b["train"][1]) for b,n in zip(limits,totals)])
    high=np.array([min(b["validation"][1],int(n)-b["train"][0]) for b,n in zip(limits,totals)])
    n=len(people);assert n<=18
    best_by_radius={};count_by_radius={};best_global=None
    for first in range(0,1<<n,16384):
        masks=np.arange(first,min(first+16384,1<<n),dtype=np.int64)
        a=(masks[:,None]>>np.arange(n))&1
        c=a@vectors
        valid=((c>=low)&(c<=high)).all(axis=1)
        a=a[valid]
        costs=(a!=initial)@vectors[:,0]
        radius=(a!=final).sum(axis=1)
        for r in np.unique(radius):
            values=costs[radius==r];value=int(values.min())
            best_by_radius[int(r)]=min(best_by_radius.get(int(r),value),value)
            count_by_radius[int(r)]=count_by_radius.get(int(r),0)+len(values)
        if len(costs):best_global=min(best_global if best_global is not None else int(costs.min()),int(costs.min()))
    base=greedy["summary"]["changed"];opt=exact["summary"]["changed"]
    assert best_global==opt
    return {"dataset":dataset,"case":case,"selection":"Post-hoc individual illustration; not a dataset-wide estimate.",
            "greedy_movement":base,"splitmend_movement":opt,"reduction_percent":100*(base-opt)/base,
            "free_participants":n,"allocations_enumerated":1<<n,
            "valid_allocations":sum(count_by_radius.values()),
            "best_feasible_cost_at_each_distance_from_greedy":best_by_radius,
            "minimum_participants_that_must_change_together_for_strict_improvement":min(r for r,c in best_by_radius.items() if c<base),
            "no_improving_single_or_pair_move":all(c>=base for r,c in best_by_radius.items() if r<=2)}


if __name__=="__main__":
    rows=[explain("har70","seed0_test2_val1"),explain("sleeptelemetry","seed0_test2_val1")]
    (ROOT/"results/illustrative_case_explanations.json").write_text(json.dumps(rows,indent=2)+"\n")
    print(json.dumps(rows,indent=2))
