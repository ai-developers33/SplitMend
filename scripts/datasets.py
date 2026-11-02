"""Real observations and explicitly constructed evaluation workflows."""

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from splitmend import Policy, Sample

ROOT = Path(__file__).resolve().parents[1]
PARTS = ("train", "validation", "test")


def nested(name, inner):
    return zipfile.ZipFile(
        io.BytesIO(zipfile.ZipFile(ROOT / "data/raw" / f"{name}.zip").read(inner))
    )


def load_har():
    z = nested("har", "UCI HAR Dataset.zip")
    frames = []
    xs = []
    for part in ("train", "test"):
        base = f"UCI HAR Dataset/{part}/"
        y = np.loadtxt(z.open(base + f"y_{part}.txt"), dtype=int)
        g = np.loadtxt(z.open(base + f"subject_{part}.txt"), dtype=int)
        x = np.loadtxt(z.open(base + f"X_{part}.txt"))
        frames.append(
            pd.DataFrame(
                {
                    "id": [f"{part}:{i + 1}" for i in range(len(y))],
                    "group": g.astype(str),
                    "label": y.astype(str),
                    "official": part,
                }
            )
        )
        xs.append(x)
    return pd.concat(frames, ignore_index=True), np.vstack(xs)


def load_oulad():
    z = zipfile.ZipFile(ROOT / "data/raw/oulad.zip")
    f = pd.read_csv(z.open("studentInfo.csv"))
    f["id"] = f["code_module"] + ":" + f["code_presentation"] + ":" + f["id_student"].astype(str)
    f["group"] = f["id_student"].astype(str)
    f["label"] = f["final_result"]
    assert f["id"].is_unique
    return f


def bounds_for(frame, originals):
    n = len(frame)
    proportions = {p: float(np.mean(originals == p)) for p in PARTS}
    # Additive tolerances stated before solving. All classes retain nonzero coverage.
    sizes = {
        p: (max(1, int(np.floor((v - 0.05) * n))), min(n, int(np.ceil((v + 0.05) * n))))
        for p, v in proportions.items()
    }
    labels = {}
    for label, count in frame["label"].value_counts().items():
        labels[str(label)] = {
            p: (
                max(1, int(np.floor((v - 0.08) * count))),
                min(int(count), int(np.ceil((v + 0.08) * count))),
            )
            for p, v in proportions.items()
        }
    return Policy(partitions=PARTS, size_bounds=sizes, label_bounds=labels)


def classification_problem(frame, dataset, seed):
    n = len(frame)
    originals = np.full(n, "train", dtype=object)
    if dataset == "har":
        train = np.flatnonzero(frame.official.to_numpy() == "train")
        _, val = train_test_split(
            train, test_size=0.2, random_state=seed, stratify=frame.label.iloc[train]
        )
        originals[frame.official.to_numpy() == "test"] = "test"
        originals[val] = "validation"
    else:
        train_val, test = train_test_split(
            np.arange(n), test_size=0.2, random_state=seed, stratify=frame.label
        )
        _, val = train_test_split(
            train_val, test_size=0.25, random_state=seed, stratify=frame.label.iloc[train_val]
        )
        originals[test] = "test"
        originals[val] = "validation"
    samples = [
        Sample(
            row.id,
            str(originals[i]),
            groups=(f"{dataset}:person:{row.group}",),
            label=str(row.label),
            locked=originals[i] == "test",
        )
        for i, row in enumerate(frame.itertuples())
    ]
    return samples, bounds_for(frame, originals)


def load_beijing():
    z = nested("beijing", "PRSA2017_Data_20130301-20170228.zip")
    frames = []
    for name in sorted(z.namelist()):
        if name.endswith(".csv"):
            f = pd.read_csv(z.open(name))
            dates = pd.to_datetime(f[["year", "month", "day", "hour"]])
            # Integer hours, retain the actual supplied chronological observations.
            f["t"] = (dates - pd.Timestamp("2013-03-01")).dt.total_seconds().astype("int64") // 3600
            frames.append(f)
    return pd.concat(frames, ignore_index=True)


def temporal_problem(frame, configuration):
    end = int(frame.t.max()) + 1
    cut1 = int(end * (0.6 + 0.05 * configuration))
    cut2 = int(end * (0.8 + 0.025 * configuration))
    samples = []
    # 24 source hours ending at t, target at t+24. Full dependency span [t-23,t+25).
    for station, f in frame.groupby("station", sort=True):
        for t in f.t.to_numpy()[23:-24]:
            original = "train" if t < cut1 else "validation" if t < cut2 else "test"
            start, stop = int(t) - 23, int(t) + 25
            allowed = (
                ("train",)
                if stop <= cut1
                else ("validation",)
                if start >= cut1 and stop <= cut2
                else ("test",)
                if start >= cut2
                else ()
            )
            samples.append(Sample(f"{station}:{t}", original, label=station, allowed=allowed))
    p = Policy(
        partitions=PARTS,
        allow_quarantine=True,
        quarantine_cost=10,
        size_bounds={p: (1, len(samples)) for p in PARTS},
    )
    return (
        samples,
        p,
        {"cut1_hour": cut1, "cut2_hour": cut2, "source_hours": 24, "forecast_horizon_hours": 24},
    )
