"""Prepare the two datasets in the frozen phase-2 amendment."""
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import gzip
import io
import json
import urllib.request
import time
import zipfile
import pandas as pd
import numpy as np
import pyedflib
from prepare import ROOT, save, sha

BASE="https://physionet.org/files/sleep-edfx/1.0.0/"
SOURCE=ROOT/"data/source/sleepedf"


def annotation_only_edf(path):
    """Decode the unchanged single-record annotation-only EDF+ source.

    Uses the public EDF+ TAL encoding. Absolute header dates are not used for
    within-recording epoch IDs. Some original headers disagree about their
    calendar date, causing EDFlib to reject otherwise intact annotations.
    """
    data=path.read_bytes()
    assert data[:8].strip()==b"0"
    assert int(data[184:192])==512 and int(data[236:244])==1
    assert int(data[252:256])==1 and data[256:272].strip()==b"EDF Annotations"
    assert len(data)==512+2*int(data[472:480])
    annotations=[]
    for tal in data[512:].split(b"\x00"):
        if not tal:continue
        fields=tal.split(b"\x14")
        assert fields[-1]==b""
        texts=[x.decode("utf-8") for x in fields[1:-1] if x]
        if not texts:continue
        onset,duration=fields[0].split(b"\x15")
        annotations.extend((float(onset),float(duration),text) for text in texts)
    return annotations


def fetch(item):
    digest,name=item
    path=SOURCE/Path(name).name
    if not path.exists():
        for attempt in range(4):
            try:
                with urllib.request.urlopen(BASE+name,timeout=45) as response:
                    data=response.read()
                path.write_bytes(data)
                break
            except Exception:
                if attempt==3:raise
                time.sleep(2*(attempt+1))
    assert sha(path)==digest,name
    return {"name":path.name,"source_path":name,"url":BASE+name,
            "sha256":digest,"bytes":path.stat().st_size}


def sleeptelemetry():
    SOURCE.mkdir(parents=True,exist_ok=True)
    manifest=SOURCE/"SHA256SUMS.txt"
    if not manifest.exists():
        manifest.write_bytes(urllib.request.urlopen(BASE+manifest.name,timeout=120).read())
    assert sha(manifest)=="1bc88e19e2e921f7851d7cf61e31ceb8f6d670211ca546a323e9db5a77525edf"
    sources=[line.split() for line in manifest.read_text().splitlines()
             if ("sleep-telemetry/" in line and "Hypnogram.edf" in line) or line.endswith(" ST-subjects.xls")]
    assert len(sources)==45
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloaded=list(pool.map(fetch,sources))
    (SOURCE/"download_manifest.json").write_text(json.dumps(downloaded,indent=2)+"\n")
    metadata=pd.read_excel(SOURCE/"ST-subjects.xls",sheet_name="Blad1",header=None).iloc[2:]
    conditions={}
    for row in metadata.itertuples(index=False,name=None):
        person=int(row[0]);placebo=int(row[3]);temazepam=int(row[5])
        assert {placebo,temazepam}=={1,2}
        conditions[person,placebo]="placebo"
        conditions[person,temazepam]="temazepam"
    assert len(conditions)==44
    rows=[];excluded=Counter();file_summaries=[];seen=set();reader_checks=[]
    for item in sorted(downloaded,key=lambda x:x["name"]):
        name=item["name"]
        if not name.endswith("-Hypnogram.edf"):continue
        person=int(name[3:5]);night=int(name[5]);condition=conditions[person,night]
        assert (person,night) not in seen
        seen.add((person,night))
        path=SOURCE/name
        annotations=annotation_only_edf(path)
        try:
            with pyedflib.EdfReader(str(path)) as reader:
                onsets,durations,texts=reader.readAnnotations()
            assert annotations==list(zip(onsets,durations,texts))
            reader_checks.append({"name":name,"pyedflib":"exact_annotation_match"})
        except OSError as error:
            reader_checks.append({"name":name,"pyedflib":"source_header_rejected",
                                  "message":str(error),"action":"unchanged TAL bytes decoded directly"})
        current=Counter();last_stop=0
        for onset,duration,text in annotations:
            assert duration>=0 and onset>=last_stop
            last_stop=onset+duration
            stage=text.removeprefix("Sleep stage ")
            if stage not in ["W","1","2","3","4","R"]:
                assert text in ["Sleep stage ?","Movement time"],text
                excluded[text]+=float(duration)
                continue
            assert onset%30==0 and duration%30==0,(name,onset,duration,text)
            for t in range(int(onset),int(onset+duration),30):
                rows.append({"participant":f"ST{person:02d}","record":f"night{night}_second{t}",
                    "label":f"stage_{stage}:{condition}","sleep_stage":stage,"condition":condition,
                    "source_file":name,"onset_seconds":t})
                current[stage]+=1
        file_summaries.append({"name":name,"participant":person,"night":night,"condition":condition,
                               "retained_epochs":sum(current.values()),"stage_counts":dict(current)})
    assert seen==set(conditions)
    save("sleeptelemetry",rows,"All 44 Sleep Telemetry recordings / 22 participants. One record per scored 30-second epoch; six original R&K stages crossed with original placebo/temazepam treatment. Only unscored and movement intervals excluded, as frozen before optimization. No EEG signals are required for this assignment-repair task.")
    p=ROOT/"data/derived/sleeptelemetry.json"
    info=json.loads(p.read_text());info.update(preprocessing_sha256=sha(__file__),
        excluded_annotation_seconds=dict(excluded),recordings=file_summaries,
        source_doi="10.13026/C2X676",source_license="Open Data Commons Attribution License v1.0")
    info["annotation_reader_checks"]=reader_checks
    p.write_text(json.dumps(info,indent=2)+"\n")


def extrasensory():
    source=ROOT/"data/source/extrasensory_original_labels.zip"
    if not source.exists():
        url="https://extrasensory.ucsd.edu/data/additional_data_files/ExtraSensory.per_uuid_original_labels.zip"
        with urllib.request.urlopen(url,timeout=120) as response:source.write_bytes(response.read())
    assert sha(source)=="7c017f75cbf3ca6d157a6ecfd8aacb1173493d9864772ab648ba27ac81373e79"
    labels=["LYING_DOWN","SITTING","STANDING_IN_PLACE","STANDING_AND_MOVING","WALKING","RUNNING","BICYCLING"]
    chunks=[]
    with zipfile.ZipFile(source) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".csv.gz"):continue
            columns=["original_label:"+label for label in labels]
            d=pd.read_csv(io.BytesIO(gzip.decompress(archive.read(name))),usecols=["timestamp",*columns])
            matrix=d[columns].to_numpy()
            assert np.isin(matrix,[0,1]).all()
            selected=np.array(labels,dtype=object)[matrix.argmax(axis=1)]
            selected[matrix.sum(axis=1)==0]="UNREPORTED_MAIN_ACTIVITY"
            selected[matrix.sum(axis=1)>1]="MULTIPLE_MAIN_ACTIVITIES"
            chunks.append(pd.DataFrame({"participant":name.split(".")[0],"record":d.timestamp,"label":selected}))
    frame=pd.concat(chunks,ignore_index=True)
    assert len(frame)==377346 and frame.participant.nunique()==60
    save("extrasensory_revision",frame.to_dict("records"),"Exact full cohort from the earlier ExtraSensory pilot, without outcome-based row filtering; policy revision starts from whole-participant folds, unlike the earlier row-leakage repair task.")
    path=ROOT/"data/derived/extrasensory_revision.json"
    info=json.loads(path.read_text());info.update(preprocessing_sha256=sha(__file__),
        source_sha256=sha(source),source_paper_doi="10.1109/MPRV.2017.3971131")
    path.write_text(json.dumps(info,indent=2)+"\n")


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--dataset",choices=["sleeptelemetry","extrasensory_revision"],required=True)
    args=p.parse_args()
    sleeptelemetry() if args.dataset=="sleeptelemetry" else extrasensory()
