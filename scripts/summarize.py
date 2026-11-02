"""Generate paper tables and plots from saved observations, with invalid runs visible."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = json.loads((ROOT / "results/main.json").read_text()) + json.loads(
        (ROOT / "results/external.json").read_text()
    )
    followup = ROOT / "results/strong_baseline_followup.json"
    if followup.exists():
        rows += json.loads(followup.read_text())
    f = pd.DataFrame(rows)
    f.to_csv(ROOT / "results/all_runs.csv", index=False)
    summaries = []
    for (dataset, method), g in f.groupby(["dataset", "method"], sort=True):
        v = g[g.valid]
        summaries.append(
            {
                "dataset": dataset,
                "method": method,
                "valid": int(g.valid.sum()),
                "runs": len(g),
                "mean_changed_valid": float(v.changed.mean()) if len(v) else None,
                "min_changed_valid": int(v.changed.min()) if len(v) else None,
                "max_changed_valid": int(v.changed.max()) if len(v) else None,
                "median_verified_seconds": float(g.verified_seconds.median()),
                "mean_quarantined_valid": float(v.quarantined.mean()) if len(v) else None,
            }
        )
    (ROOT / "results/summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    pd.DataFrame(summaries).to_csv(ROOT / "results/summary.csv", index=False)
    table = [
        "| Dataset | Method | Valid runs | Mean changes on valid runs | Median verified seconds |",
        "|---|---|---:|---:|---:|",
    ]
    for r in summaries:
        changed = "NA" if r["mean_changed_valid"] is None else f"{r['mean_changed_valid']:.1f}"
        table.append(
            f"| {r['dataset']} | {r['method']} | {r['valid']}/{r['runs']} | {changed} | {r['median_verified_seconds']:.3f} |"
        )
    (ROOT / "results/tables.md").write_text("\n".join(table) + "\n")
    tex = [
        r"\begin{tabular}{llrr}",
        r"\hline",
        r"Dataset & Method & Valid & Mean changes \\",
        r"\hline",
    ]
    for r in summaries:
        method = r["method"].replace("_", r"\_")
        changed = "--" if r["mean_changed_valid"] is None else f"{r['mean_changed_valid']:.1f}"
        tex.append(f"{r['dataset']} & {method} & {r['valid']}/{r['runs']} & {changed}" + r" \\")
    tex.extend([r"\hline", r"\end{tabular}"])
    (ROOT / "results/table1.tex").write_text("\n".join(tex) + "\n")
    model = pd.read_json(ROOT / "results/model_evaluation.json")
    model.groupby(["dataset", "method", "partition"])[
        ["accuracy", "macro_f1"]
    ].mean().reset_index().to_csv(ROOT / "results/model_summary.csv", index=False)
    methods = [
        "splitmend",
        "greedy",
        "cost_greedy_local",
        "group_resplit",
        "datasail_i1_aligned",
        "dataset_splitter",
    ]
    names = [
        "SplitMend",
        "Greedy repair",
        "Cost-aware greedy\nwith local exchanges",
        "Group re-split",
        "DataSAIL I1\nwith adapter",
        "dataset-splitter\nwith adapter",
    ]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for ax, dataset in zip(axes, ["har", "oulad"]):
        for i, method in enumerate(methods):
            g = f[(f.dataset == dataset) & (f.method == method) & f.valid]
            if len(g):
                ax.scatter(
                    [i] * len(g), g.changed, s=28, color="#1d6094" if i else "#b54e24", alpha=0.8
                )
                ax.plot([i - 0.22, i + 0.22], [g.changed.mean()] * 2, color="black", lw=1.8)
        ax.set_xticks(range(len(methods)), names, rotation=25, ha="right", fontsize=8)
        ax.set_title("HAR" if dataset == "har" else "OULAD")
        ax.set_ylabel("Records with changed assignments")
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
    (ROOT / "paper/figures").mkdir(parents=True, exist_ok=True)
    fig.savefig(ROOT / "paper/figures/changes.png", dpi=300)
    fig.savefig(ROOT / "paper/figures/changes.svg")
    plt.close(fig)
    print("\n".join(table))


if __name__ == "__main__":
    main()
