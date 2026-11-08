"""Cross-check every source TAL against MNE's independent EDF reader."""
import json
from importlib.metadata import version
import mne
from prepare_phase2 import SOURCE, ROOT, annotation_only_edf, sha

checks=[]
for path in sorted(SOURCE.glob("*-Hypnogram.edf")):
    original=annotation_only_edf(path)
    annotations=mne.read_annotations(path)
    independent=list(zip(annotations.onset,annotations.duration,annotations.description))
    assert original==independent,path.name
    checks.append({"file":path.name,"sha256":sha(path),"annotations":len(original),"exact_match":True})
assert len(checks)==44
result={"mne_version":version("mne"),"files_checked":len(checks),"all_annotations_match":True,"checks":checks}
(ROOT/"data/derived/sleep_annotation_crosscheck.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="checks"}))
