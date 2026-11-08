"""JSON CLI. No data files or split assignments are modified in place."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, audit, read_problem, repair


def main(argv=None):
    parser = argparse.ArgumentParser(prog="splitmend")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "repair"):
        p = sub.add_parser(name)
        p.add_argument("problem", type=Path)
        p.add_argument("--output", type=Path)
        if name == "repair":
            p.add_argument("--time-limit", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        samples, policy = read_problem(args.problem)
        result = (
            audit(samples, policy)
            if args.command == "audit"
            else repair(samples, policy, time_limit=args.time_limit)
        )
        payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output:
            if args.output.resolve() == args.problem.resolve():
                raise ValueError("output must not overwrite the input problem")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload)
        else:
            print(payload, end="")
        if args.command == "audit":
            return 0 if result["valid"] else 1
        return {"optimal": 0, "feasible": 0, "infeasible": 2, "unknown": 3}[result["status"]]
    except (ValueError, KeyError, TypeError, OSError) as e:
        print(f"splitmend: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
