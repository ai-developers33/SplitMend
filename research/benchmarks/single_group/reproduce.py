"""Run the complete screening in a fresh output directory and compare results."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import pandas as pd
from run_search import run
from audit_saved_results import audit

ROOT=Path(__file__).resolve().parent
DATASETS=["har70","pamap2","unimib","sleeptelemetry","extrasensory_revision"]


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--datasets",nargs="+",choices=DATASETS,default=DATASETS)
    p.add_argument("--output",type=Path,required=True,help="New, nonexistent output directory.")
    p.add_argument("--from-source",action="store_true",help="Also reconstruct cohorts; downloads about 1 GB for phase 1.")
    args=p.parse_args()
    output=args.output.resolve()
    if output.exists():raise SystemExit("Choose a new output directory; this command never reuses archived results.")
    if args.from_source:
        if set(args.datasets)&set(DATASETS[:3]):
            subprocess.run([sys.executable,str(ROOT/"download_sources.py")],check=True)
            subprocess.run([sys.executable,str(ROOT/"prepare.py")],check=True)
        for dataset in args.datasets:
            if dataset in DATASETS[3:]:subprocess.run([sys.executable,str(ROOT/"prepare_phase2.py"),"--dataset",dataset],check=True)
    comparisons=[];audits=[]
    for dataset in args.datasets:
        protocol=ROOT/("protocol.json" if dataset in DATASETS[:3] else "protocol_phase2.json")
        run(dataset,output/dataset,protocol)
        audits.append(audit(dataset,output))
        archived=pd.read_csv(ROOT/"results"/dataset/"all_comparisons.csv").set_index("case")
        fresh=pd.read_csv(output/dataset/"all_comparisons.csv").set_index("case")
        columns=[c for c in archived if not c.endswith("_seconds") and c!="chosen_greedy"]
        pd.testing.assert_frame_equal(archived[columns].sort_index(),fresh[columns].sort_index(),check_dtype=False)
        comparisons.append({"dataset":dataset,"cases":len(fresh),"all_status_validity_and_movement_results_match":True})
    (output/"rerun_comparison.json").write_text(json.dumps(comparisons,indent=2)+"\n")
    (output/"saved_assignment_audit.json").write_text(json.dumps(audits,indent=2)+"\n")
    print(json.dumps(comparisons,indent=2))


if __name__=="__main__":main()
