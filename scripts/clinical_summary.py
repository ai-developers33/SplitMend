"""Summarize every clinical case; do not suppress near-ties or invalid baselines."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / "results/clinical"
    frame = pd.read_json(output / "runs.json")
    expected = {
        (seed, tol, method)
        for seed in range(5)
        for tol in [0.01, 0.025, 0.05]
        for method in [
            "majority",
            "group_resplit",
            "violation_greedy",
            "cost_greedy_local",
            "splitmend",
        ]
    }
    actual = set(zip(frame.seed, frame.tolerance, frame.method))
    if actual != expected or len(frame) != 75:
        raise ValueError("clinical run is incomplete or duplicated")
    frame.to_csv(output / "all_runs.csv", index=False)
    summaries = []
    for (tolerance, method), group in frame.groupby(["tolerance", "method"]):
        valid = group[group.valid]
        summaries.append(
            {
                "tolerance": float(tolerance),
                "method": method,
                "valid": int(group.valid.sum()),
                "runs": len(group),
                "mean_changed_valid": float(valid.changed.mean()) if len(valid) else None,
                "median_verified_seconds": float(group.verified_seconds.median()),
                "optimal": int((group.status == "optimal").sum()),
            }
        )
    comparisons = []
    candidate = frame[frame.method == "splitmend"]
    for method in ["majority", "group_resplit", "violation_greedy", "cost_greedy_local"]:
        other = frame[frame.method == method]
        paired = candidate.merge(other, on=["case", "seed", "tolerance"], suffixes=("_s", "_b"))
        paired = paired[paired.valid_s & paired.valid_b]
        delta = paired.changed_b - paired.changed_s
        comparisons.append(
            {
                "baseline": method,
                "paired_valid_cases": len(paired),
                "splitmend_better": int((delta > 0).sum()),
                "ties": int((delta == 0).sum()),
                "splitmend_worse": int((delta < 0).sum()),
                "total_fewer_changes": int(delta.sum()),
                "aggregate_reduction_percent": float(100 * delta.sum() / paired.changed_b.sum())
                if len(paired)
                else None,
                "largest_per_case_reduction": int(delta.max()) if len(paired) else None,
            }
        )
    result = {
        "cases": len(candidate),
        "rows": len(frame),
        "summaries": summaries,
        "comparisons": comparisons,
        "note": "Paired costs use cases where both methods return valid assignments. All invalid results remain in all_runs.csv.",
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    pd.DataFrame(summaries).to_csv(output / "summary.csv", index=False)
    lines = [
        "| Tolerance | Method | Valid | Mean changes (valid only) | Median verified seconds |",
        "|---:|---|---:|---:|---:|",
    ]
    for row in summaries:
        mean = "NA" if row["mean_changed_valid"] is None else f"{row['mean_changed_valid']:,.1f}"
        lines.append(
            f"| {row['tolerance']:.3f} | {row['method']} | {row['valid']}/{row['runs']} | {mean} | {row['median_verified_seconds']:.3f} |"
        )
    (output / "tables.md").write_text("\n".join(lines) + "\n")
    comparison = candidate.merge(
        frame[frame.method == "cost_greedy_local"],
        on=["case", "seed", "tolerance"],
        suffixes=("_s", "_b"),
    )
    comparison["extra_changes_greedy"] = comparison.changed_b - comparison.changed_s
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), layout="constrained")
    labels = ["1 pp", "2.5 pp", "5 pp"]
    for i, tolerance in enumerate([0.01, 0.025, 0.05]):
        for method, shift, color in [
            ("splitmend", -0.14, "#b54e24"),
            ("violation_greedy", 0.14, "#1d6094"),
        ]:
            group = frame[(frame.tolerance == tolerance) & (frame.method == method) & frame.valid]
            axes[0].scatter(
                [i + shift] * len(group),
                group.changed,
                color=color,
                s=25,
                label=method.replace("_", " ") if i == 0 else None,
            )
        group = comparison[comparison.tolerance == tolerance]
        axes[1].scatter(
            i + (group.seed - 2) * 0.045,
            group.extra_changes_greedy,
            color="#234e35",
            s=25,
        )
    axes[0].set_ylabel("Changed encounter assignments")
    axes[0].legend(fontsize=8)
    axes[1].set_ylabel("Extra assignment changes\n(cost-aware greedy − SplitMend)", fontsize=9)
    axes[1].axhline(0, color="gray", linewidth=0.8)
    for ax in axes:
        ax.set_xticks(range(3), labels)
        ax.set_xlabel("Allowed partition-fraction tolerance")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.2)
    (ROOT / "paper/figures").mkdir(parents=True, exist_ok=True)
    for suffix in ["png", "svg"]:
        fig.savefig(ROOT / "paper/figures" / f"clinical.{suffix}", dpi=300)
    plt.close(fig)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
