"""Run every frozen scenario and assess the pre-specified 20% target."""
from pathlib import Path
import argparse
from collections import Counter
import importlib.util
import json
import math
import platform
import sys
import time
from importlib.metadata import version

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import experiment_shared as shared
from enumeration import exhaustive
from neighborhood import all_pair_greedy


def make_problem(frame, folds, test, val, protocol):
    samples=[]
    for row in frame.itertuples(index=False):
        locked=row.participant in folds[test]
        original="test" if locked else "validation" if row.participant in folds[val] else "train"
        samples.append(shared.Sample(id=f"{row.participant}:{row.record}",original=original,
                       groups=("participant:"+row.participant,),label=row.label,
                       allowed=("test",) if locked else ("train","validation"),locked=locked))
    def bounds(n,fixed,tolerance):
        limits={p:(max(0,math.floor((target-tolerance)*n)),min(n,math.ceil((target+tolerance)*n)))
                for p,target in protocol["free_partition_targets"].items()}
        limits["test"]=(fixed,fixed)
        return limits
    free=Counter(s.label for s in samples if not s.locked)
    fixed=Counter(s.label for s in samples if s.locked)
    policy=shared.Policy(size_bounds=bounds(sum(free.values()),sum(fixed.values()),protocol["size_tolerance_pp"]/100),
                         label_bounds={label:bounds(free[label],fixed[label],protocol["label_tolerance_pp"]/100)
                                       for label in sorted(set(free)|set(fixed))})
    return samples,policy


def run_neighborhood(samples,policy,protocol):
    start=time.perf_counter()
    assignment,raw=all_pair_greedy(samples,policy,budget=protocol["greedy_search_seconds"])
    seconds=time.perf_counter()-start
    start=time.perf_counter()
    checked=shared.audit(samples,policy,assignment)
    audit_seconds=time.perf_counter()-start
    independent=shared.independent_check(samples,policy,assignment)
    assert independent["valid"]==checked["valid"]
    assert independent["changed"]==checked["changed"]==checked["objective"]
    groups={}
    for s in samples:
        assert groups.setdefault(s.groups[0],assignment[s.id])==assignment[s.id]
    row={"method":"all_pair_greedy","valid":independent["valid"],"changed":independent["changed"],
         "seconds":seconds,"external_audit_seconds":audit_seconds,"status":None,"lower_bound":None,
         "gap":None,"violations":independent["violations"]}
    return row,{"group_assignments":groups,"raw":raw,"library_audit":checked,"independent_audit":independent}


def summarize(output,protocol):
    all_cases=[]
    for folder in sorted(output.glob("cases/*")):
        paths=[folder/(m+".json") for m in protocol["methods"]]
        if not all(p.exists() for p in paths):continue
        rows={m:json.loads(p.read_text())["summary"] for m,p in zip(protocol["methods"],paths)}
        optimal=rows["splitmend"]
        valid=[r for m,r in rows.items() if m!="splitmend" and r["valid"]]
        best=min(valid,key=lambda r:(r["changed"],r["method"])) if valid else None
        row={"case":folder.name,"fold_seed":optimal["fold_seed"],"test_fold":optimal["test_fold"],
             "validation_fold":optimal["validation_fold"],"splitmend_valid":optimal["valid"],
             "splitmend_status":optimal["status"],"splitmend_changed":optimal["changed"],
             "greedy_valid":bool(best),"greedy_changed":best["changed"] if best else None,
             "chosen_greedy":best["method"] if best else None}
        for name,item in rows.items():
            row[name+"_valid"]=item["valid"]
            row[name+"_changed"]=item["changed"]
            row[name+"_seconds"]=item["seconds"]
        if optimal["valid"] and best:
            row["saved"]=best["changed"]-optimal["changed"]
            if optimal["status"]=="optimal":assert row["saved"]>=0
        all_cases.append(row)
    def statistics(rows):
        paired=[r for r in rows if "saved" in r]
        base=sum(r["greedy_changed"] for r in paired)
        return {"cases":len(rows),"optimal":sum(r["splitmend_status"]=="optimal" for r in rows),
                "infeasible":sum(r["splitmend_status"]=="infeasible" for r in rows),
                "unknown_or_feasible_unproven":sum(r["splitmend_status"] not in ["optimal","infeasible"] for r in rows),
                "greedy_valid":sum(r["greedy_valid"] for r in rows),"paired":len(paired),
                "paired_nonzero_greedy":sum(r["greedy_changed"]>0 for r in paired),
                "wins":sum(r["saved"]>0 for r in paired),"ties":sum(r["saved"]==0 for r in paired),
                "losses":sum(r["saved"]<0 for r in paired),"paired_splitmend_total":sum(r["splitmend_changed"] for r in paired),
                "paired_greedy_total":base,"paired_saved_total":sum(r["saved"] for r in paired),
                "aggregate_reduction_percent":100*sum(r["saved"] for r in paired)/base if base else 0}
    result=statistics(all_cases)
    result["by_fold_seed"]={str(seed):statistics([r for r in all_cases if r["fold_seed"]==seed])
                            for seed in protocol["fold_seeds"]}
    target=protocol["qualification"]
    result["complete"]=result["cases"]==40
    result["qualifies_for_20_percent_claim"]=bool(
        result["complete"] and result["unknown_or_feasible_unproven"]==0 and
        result["aggregate_reduction_percent"]>=target["minimum_aggregate_reduction_percent"] and
        result["paired"]>=target["minimum_paired_valid_cases_total"] and
        all(x["paired"]>=target["minimum_paired_valid_cases_per_fold_seed"] and x["aggregate_reduction_percent"]>0
            for x in result["by_fold_seed"].values()))
    shared.write(output/"summary.json",result)
    pd.DataFrame(all_cases).to_csv(output/"all_comparisons.csv",index=False)
    return result


def run(dataset,output,protocol_path=None):
    protocol_path=Path(protocol_path or ROOT/"protocol.json")
    protocol=json.loads(protocol_path.read_text())
    assert dataset in protocol["datasets"]
    cohort_path=ROOT/"data/derived"/(dataset+".csv.gz")
    cohort_meta=json.loads((ROOT/"data/derived"/(dataset+".json")).read_text())
    assert shared.sha(cohort_path)==cohort_meta["cohort_sha256"]
    for name,digest in json.loads((ROOT/"vendor_manifest.json").read_text()).items():
        assert shared.sha(ROOT/name)==digest,name
    frame=pd.read_csv(cohort_path,dtype={"participant":str})
    people=np.array(sorted(frame.participant.unique()))
    shared.write(output/"environment.json",{"python":sys.version,"platform":platform.platform(),
                  "packages":{n:version(n) for n in ["numpy","scipy","pandas","scikit-learn"]},
                  "protocol_sha256":shared.sha(protocol_path),"runner_sha256":shared.sha(__file__),
                  "cohort_sha256":cohort_meta["cohort_sha256"]})
    index=0
    for seed in protocol["fold_seeds"]:
        folds=[set(x) for x in np.array_split(np.random.default_rng(seed).permutation(people),5)]
        for test in range(5):
            for val in range(5):
                if test==val:continue
                case=f"seed{seed}_test{test}_val{val}"
                samples,policy=make_problem(frame,folds,test,val,protocol)
                fingerprint=shared.fingerprint(samples,policy)
                folder=output/"cases"/case
                before=shared.independent_check(samples,policy,{s.id:s.original for s in samples})
                assert not before["violations"].get("participant_separation",0)
                shared.write(folder/"problem_metadata.json",{"case":case,"dataset":dataset,"fold_seed":seed,
                    "test_fold":test,"validation_fold":val,"problem_sha256":fingerprint,"before":before,
                    "size_bounds":policy.size_bounds,"label_bounds":policy.label_bounds,
                    "test_participants":sorted(folds[test]),"original_validation_participants":sorted(folds[val])})
                cert=None
                if len(people)-len(folds[test])<=18:
                    cert=exhaustive(samples,policy)
                    shared.write(folder/"enumeration.json",cert)
                methods=protocol["methods"]
                rotation=index%len(methods)
                for method in methods[rotation:]+methods[:rotation]:
                    path=folder/(method+".json")
                    if path.exists():
                        old=json.loads(path.read_text())
                        assert old["problem_sha256"]==fingerprint
                        row=old["summary"]
                    else:
                        row,detail=run_neighborhood(samples,policy,protocol) if method=="all_pair_greedy" else shared.run_method(samples,policy,method,protocol)
                        row.update(dataset=dataset,case=case,fold_seed=seed,test_fold=test,validation_fold=val)
                        if method=="splitmend" and cert is not None:
                            assert row["status"]==("optimal" if cert["valid_allocations"] else "infeasible")
                            assert row["changed"]==cert["optimal_movement"]
                        shared.write(path,{"summary":row,"problem_sha256":fingerprint,**detail})
                result=summarize(output,protocol)
                print(json.dumps({"dataset":dataset,"case":case,"completed":result["cases"],"paired":result["paired"],
                                  "reduction_percent":result["aggregate_reduction_percent"]}),flush=True)
                index+=1
    print(dataset,json.dumps(summarize(output,protocol),indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dataset",default="all")
    parser.add_argument("--protocol",type=Path,default=ROOT/"protocol.json")
    parser.add_argument("--output",type=Path,default=ROOT/"results")
    args=parser.parse_args()
    for name in ([args.dataset] if args.dataset!="all" else json.loads(args.protocol.read_text())["datasets"]):
        run(name,args.output/name,args.protocol)
