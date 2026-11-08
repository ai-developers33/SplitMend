"""One entry point for installation and all experiments. No paid service is used."""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = []


def run(command):
    print("Running:", " ".join(map(str, command)), flush=True)
    started = time.perf_counter()
    subprocess.run(list(map(str, command)), cwd=ROOT, check=True)
    STEPS.append({"command": list(map(str, command)), "seconds": time.perf_counter() - started})


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--bootstrap",
        action="store_true",
        help="create two isolated environments using the lock files",
    )
    p.add_argument("--baseline-python", default=sys.executable)
    args = p.parse_args()
    completion = ROOT / "results/reproduction.json"
    completion.parent.mkdir(parents=True, exist_ok=True)
    completion.unlink(missing_ok=True)
    main_python = sys.executable
    baseline_python = args.baseline_python
    if args.bootstrap:
        for suffix in ["experiments", "baselines"]:
            env = ROOT / f".venv-{suffix}"
            run([sys.executable, "-m", "venv", env])
            interpreter = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            run([interpreter, "-m", "pip", "install", "-r", ROOT / f"requirements-{suffix}.lock"])
            run([interpreter, "-m", "pip", "install", "--no-deps", "-e", ROOT])
            if suffix == "experiments":
                main_python = interpreter
            else:
                baseline_python = interpreter
    run([main_python, "-m", "pytest", "-q"])
    for script in [
        "download_data.py",
        "run_experiments.py",
        "correctness.py",
        "model_evaluation.py",
    ]:
        run([main_python, ROOT / "scripts" / script])
    run([baseline_python, ROOT / "scripts/external_baselines.py"])
    run([main_python, ROOT / "scripts/strong_baseline_followup.py"])
    run([main_python, ROOT / "scripts/clinical_experiments.py"])
    run([main_python, ROOT / "scripts/clinical_summary.py"])
    run([main_python, ROOT / "scripts/summarize.py"])
    run([main_python, ROOT / "scripts/verify_results.py"])
    run([main_python, ROOT / "scripts/verify_clinical.py"])
    counts = {
        name: len(json.loads((ROOT / "results" / name).read_text()))
        for name in [
            "main.json",
            "external.json",
            "strong_baseline_followup.json",
            "clinical/runs.json",
        ]
    }
    assert counts == {
        "main.json": 55,
        "external.json": 40,
        "strong_baseline_followup.json": 10,
        "clinical/runs.json": 75,
    }, counts
    record = {
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "independent_reproduction": False,
        "description": "Full sequential rerun on the development host; all subprocesses succeeded.",
        "counts": counts,
        "steps": STEPS,
    }
    completion.write_text(json.dumps(record, indent=2) + "\n")
    print(
        "REPRODUCTION COMPLETE: 180 runs across original, external, clinical and follow-up comparisons verified.",
        flush=True,
    )


if __name__ == "__main__":
    main()
