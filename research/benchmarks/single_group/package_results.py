"""Bundle complete code, prepared data and evidence; exclude giant originals."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
EXCLUDED={"har70.zip","pamap2.zip","PAMAP2_Dataset.zip","unimib.zip",
          "robustness_original.py","enumeration_original.py","CONTENTS_SHA256.json"}


def main():
    for name in ["har70","pamap2","unimib","sleeptelemetry","extrasensory_revision"]:
        summary=json.loads((ROOT/"results"/name/"summary.json").read_text())
        assert summary["complete"] and summary["cases"]==40,name
    checks=json.loads((ROOT/"results/saved_assignment_audit.json").read_text())
    assert checks["all_match"] and len(checks["datasets"])==5
    rerun=json.loads((ROOT/"fresh_reproduction/rerun_comparison.json").read_text())
    assert len(rerun)==2 and all(x["all_status_validity_and_movement_results_match"] for x in rerun)
    assert json.loads((ROOT/"data/derived/sleep_annotation_crosscheck.json").read_text())["all_annotations_match"]
    assert (ROOT/"RESULTS.md").exists()
    paths=[p for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name not in EXCLUDED
           and "__pycache__" not in p.parts and p.suffix not in [".pyc",".log"]]
    digests={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    manifest=ROOT/"CONTENTS_SHA256.json"
    manifest.write_text(json.dumps(digests,indent=2)+"\n")
    target=ROOT.parent/"SplitMend_Dataset_Search_Results.zip"
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in [*paths,manifest]:archive.write(p,Path("SplitMend_Dataset_Search")/p.relative_to(ROOT))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for relative,digest in digests.items():
            assert hashlib.sha256(archive.read("SplitMend_Dataset_Search/"+relative)).hexdigest()==digest
    print(json.dumps({"path":str(target),"bytes":target.stat().st_size,"files":len(paths)+1,
                      "sha256":hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__=="__main__":main()
