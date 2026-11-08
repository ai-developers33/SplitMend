"""Prepare the three pre-specified candidate datasets without outcome filtering."""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import numpy as np
import pandas as pd
from scipy.io import loadmat

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"data/source"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def windows(person, stamps, labels):
    stamps=np.asarray(stamps,dtype=np.int64)
    labels=np.asarray(labels,dtype=np.int64)
    assert np.all(np.diff(stamps)>=0),person
    bins=(stamps-stamps[0])//5_000_000_000
    cuts=np.r_[0,np.flatnonzero(np.diff(bins)!=0)+1,len(labels)]
    result=[]
    for lo,hi in zip(cuts[:-1],cuts[1:]):
        counts=np.bincount(labels[lo:hi])
        label=int(counts.argmax())
        result.append({"participant":person,"record":int(bins[lo]),"label":f"activity_{label:02d}",
                       "source_first_row":int(lo),"source_stop_row":int(hi),"raw_samples":int(hi-lo),
                       "mode_fraction":float(counts[label]/(hi-lo))})
    assert sum(r["raw_samples"] for r in result)==len(labels)
    return result


def save(name, rows, notes):
    frame=pd.DataFrame(rows)
    assert not frame.duplicated(["participant","record"]).any()
    directory=ROOT/"data/derived"
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(name+".csv.gz")
    frame.to_csv(path,index=False,compression={"method":"gzip","mtime":0})
    groups=frame.groupby("participant").size()
    counts=pd.crosstab(frame.participant,frame.label)
    summary={"dataset":name,"observations":len(frame),"participants":len(groups),
             "labels":int(frame.label.nunique()),"records_per_participant":groups.describe().to_dict(),
             "label_counts":frame.label.value_counts().to_dict(),
             "participants_per_label":(counts>0).sum().to_dict(),
             "cohort_sha256":sha(path),"preprocessing_sha256":sha(__file__),"notes":notes}
    if "raw_samples" in frame:
        summary["source_rows_retained"]=int(frame.raw_samples.sum())
        summary["mixed_label_windows"]=int((frame.mode_fraction<1).sum())
    (directory/(name+".json")).write_text(json.dumps(summary,indent=2)+"\n")
    counts.to_csv(directory/(name+"_participant_labels.csv"))
    print(json.dumps(summary),flush=True)


def prepare():
    for item in json.loads((SOURCE/"download_manifest.json").read_text()):
        assert sha(SOURCE/item["name"])==item["sha256"],item["name"]
    rows=[]
    with zipfile.ZipFile(SOURCE/"har70.zip") as z:
        for name in sorted(z.namelist()):
            if not name.endswith(".csv"):continue
            with z.open(name) as f:d=pd.read_csv(f,usecols=["timestamp","label"])
            stamps=pd.to_datetime(d.timestamp).to_numpy(dtype="datetime64[ns]").astype(np.int64)
            assert set(d.label)<=set([1,3,4,5,6,7,8])
            rows.extend(windows(Path(name).stem,stamps,d.label))
    save("har70",rows,"All 18 original participants and seven labels; all source observations retained in nonempty five-second recorded-time windows.")
    rows=[]
    with zipfile.ZipFile(SOURCE/"pamap2.zip") as outer:
        outer.extract("PAMAP2_Dataset.zip",SOURCE)
    with zipfile.ZipFile(SOURCE/"PAMAP2_Dataset.zip") as z:
        for name in sorted(z.namelist()):
            if "/Protocol/" not in name or not name.endswith(".dat"):continue
            with z.open(name) as f:d=pd.read_csv(f,sep=r"\s+",header=None,usecols=[0,1])
            assert not d.isna().any().any()
            stamps=np.rint(d[0].to_numpy()*1_000_000_000).astype(np.int64)
            rows.extend(windows(Path(name).stem,stamps,d[1]))
    save("pamap2",rows,"All nine Protocol participants, including subject109, and all Protocol labels including 0 (transient activities). Optional sessions excluded by the pre-specified task. Five-second recorded-time windows.")
    with zipfile.ZipFile(SOURCE/"unimib.zip") as z:
        matrix=loadmat(io.BytesIO(z.read("UniMiB-SHAR/data/acc_labels.mat")))["acc_labels"]
        assert matrix.shape==(11771,3)
        rows=[{"participant":f"subject{int(person):03d}","record":i,"label":f"activity_{int(label):02d}",
               "source_trial":int(trial)} for i,(label,person,trial) in enumerate(matrix)]
        (SOURCE/"unimib_acc_labels.mat").write_bytes(z.read("UniMiB-SHAR/data/acc_labels.mat"))
    save("unimib",rows,"All 11771 official AF-17 segments, 30 participant identifiers and 17 activity/fall labels. Subject and trial columns interpreted according to the original archive readme. No additional windowing.")


if __name__=="__main__":prepare()
