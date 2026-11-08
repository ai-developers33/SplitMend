"""Public UCI clinical cohort and frozen patient/stratum repair policies."""

import hashlib
import json
import math
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from splitmend import Policy, Sample

ROOT = Path(__file__).resolve().parents[1]


def load_clinical():
    source = json.loads((ROOT / "data/clinical_sources.json").read_text())["sources"][0]
    path = ROOT / source["archive"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temp = path.with_suffix(".part")
        with urllib.request.urlopen(source["url"], timeout=60) as response:
            temp.write_bytes(response.read())
        temp.replace(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != source["sha256"]:
        raise ValueError("clinical source archive checksum mismatch")
    with zipfile.ZipFile(path) as archive:
        frame = pd.read_csv(
            archive.open("diabetic_data.csv"),
            dtype={"encounter_id": str, "patient_nbr": str},
        )
    if not frame.encounter_id.is_unique:
        raise ValueError("clinical encounter IDs must be unique")
    low_age = frame.age.str.extract(r"\[(\d+)-", expand=False).astype(int)
    frame["age_band"] = np.select(
        [low_age < 40, low_age < 60, low_age < 80],
        ["under40", "40to59", "60to79"],
        default="80plus",
    )
    frame["stratum"] = frame.readmitted + "|" + frame.age_band + "|" + frame.gender
    return frame


def clinical_problem(frame, seed, tolerance):
    rng = np.random.default_rng(seed)
    patients = np.array(sorted(frame.patient_nbr.unique()))
    test_patients = set(rng.permutation(patients)[: math.ceil(0.2 * len(patients))])
    is_test = frame.patient_nbr.isin(test_patients).to_numpy()
    partitions = np.full(len(frame), "train", dtype=object)
    partitions[is_test] = "test"
    for stratum in sorted(frame.stratum.unique()):
        indexes = np.flatnonzero((frame.stratum == stratum).to_numpy() & ~is_test)
        permuted = rng.permutation(indexes)
        partitions[permuted[: round(0.25 * len(indexes))]] = "validation"
    samples = [
        Sample(
            id="diabetes:" + row.encounter_id,
            original=partitions[i],
            groups=("patient:" + row.patient_nbr,),
            label=row.stratum,
            allowed=("test",) if is_test[i] else ("train", "validation"),
            locked=bool(is_test[i]),
        )
        for i, row in enumerate(frame.itertuples(index=False))
    ]

    def bounds(free_n, test_n):
        return {
            "train": (
                max(0, math.floor((0.75 - tolerance) * free_n)),
                min(free_n, math.ceil((0.75 + tolerance) * free_n)),
            ),
            "validation": (
                max(0, math.floor((0.25 - tolerance) * free_n)),
                min(free_n, math.ceil((0.25 + tolerance) * free_n)),
            ),
            "test": (test_n, test_n),
        }

    free_labels = Counter(s.label for s in samples if not s.locked)
    test_labels = Counter(s.label for s in samples if s.locked)
    labels = sorted(set(free_labels) | set(test_labels))
    policy = Policy(
        size_bounds=bounds(int((~is_test).sum()), int(is_test.sum())),
        label_bounds={label: bounds(free_labels[label], test_labels[label]) for label in labels},
    )
    context = {
        "rows": len(samples),
        "patients": len(patients),
        "test_patients": len(test_patients),
        "locked_test_rows": int(is_test.sum()),
        "joint_strata": len(labels),
        "tolerance": tolerance,
        "initial_counts": dict(Counter(partitions)),
    }
    return samples, policy, context
