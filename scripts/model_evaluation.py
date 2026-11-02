"""Fixed classifiers; no model or repair parameters tuned using test outcomes."""

import gzip
import json
import time

import numpy as np
from datasets import ROOT, classification_problem, load_har, load_oulad
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits


def main():
    rows = []
    for name in ["har", "oulad"]:
        if name == "har":
            frame, X = load_har()
        else:
            frame = load_oulad()
            numeric = ["num_of_prev_attempts", "studied_credits"]
            categorical = [
                "code_module",
                "code_presentation",
                "gender",
                "region",
                "highest_education",
                "imd_band",
                "age_band",
                "disability",
            ]
            X = frame[numeric + categorical]
        y = frame.label.to_numpy()
        for seed in range(5):
            samples, policy = classification_problem(frame, name, seed)
            test_ids = {s.id for s in samples if s.original == "test"}
            for method in ["original", "splitmend", "greedy", "group_resplit"]:
                if method == "original":
                    a = {s.id: s.original for s in samples}
                else:
                    with gzip.open(
                        ROOT / "results/assignments" / f"{name}_{seed}_{method}.json.gz", "rt"
                    ) as f:
                        obj = json.load(f)
                    if not obj["audit"]["valid"]:
                        continue
                    a = obj["assignments"]
                train = np.array([i for i, s in enumerate(samples) if a[s.id] == "train"])
                # Common original test rows only: lock adapters can pull additional related rows into test.
                test = np.array([i for i, s in enumerate(samples) if s.id in test_ids])
                val = np.array([i for i, s in enumerate(samples) if a[s.id] == "validation"])
                assert all(a[samples[i].id] == "test" for i in test)
                if name == "har":
                    model = make_pipeline(StandardScaler(), RidgeClassifier(alpha=1.0))
                else:
                    pre = ColumnTransformer(
                        [
                            ("num", make_pipeline(SimpleImputer(), StandardScaler()), numeric),
                            (
                                "cat",
                                make_pipeline(
                                    SimpleImputer(strategy="most_frequent"),
                                    OneHotEncoder(handle_unknown="ignore"),
                                ),
                                categorical,
                            ),
                        ]
                    )
                    model = make_pipeline(pre, RidgeClassifier(alpha=1.0, solver="lsqr"))

                def take(idx):
                    return X[idx] if name == "har" else X.iloc[idx]

                started = time.perf_counter()
                with threadpool_limits(limits=1):
                    model.fit(take(train), y[train])
                    for partition, idx in [("validation", val), ("common_test", test)]:
                        prediction = model.predict(take(idx))
                        rows.append(
                            {
                                "dataset": name,
                                "seed": seed,
                                "method": method,
                                "partition": partition,
                                "n_train": len(train),
                                "n_evaluated": len(idx),
                                "accuracy": accuracy_score(y[idx], prediction),
                                "macro_f1": f1_score(y[idx], prediction, average="macro"),
                                "elapsed_seconds": time.perf_counter() - started,
                            }
                        )
                print(name, seed, method, flush=True)
    (ROOT / "results/model_evaluation.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
