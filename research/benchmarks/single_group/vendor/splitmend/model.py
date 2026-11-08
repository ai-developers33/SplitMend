"""Public input model. Constraints express the user's evaluation task, not inferred truth."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

QUARANTINE = "__quarantine__"


@dataclass(frozen=True)
class Sample:
    id: str
    original: str
    groups: tuple[str, ...] = ()
    label: str = ""
    allowed: tuple[str, ...] | None = None
    locked: bool = False
    weight: int = 1


@dataclass(frozen=True)
class Policy:
    partitions: tuple[str, ...] = ("train", "validation", "test")
    size_bounds: dict[str, tuple[int, int]] = field(default_factory=dict)
    label_bounds: dict[str, dict[str, tuple[int, int]]] = field(default_factory=dict)
    allow_quarantine: bool = False
    quarantine_cost: int = 10


def validate(samples: list[Sample], policy: Policy) -> None:
    parts = policy.partitions
    if not parts or len(set(parts)) != len(parts) or QUARANTINE in parts:
        raise ValueError("partitions must be nonempty, unique and exclude __quarantine__")
    if any(not isinstance(p, str) or not p for p in parts):
        raise ValueError("partition names must be nonempty strings")
    if type(policy.allow_quarantine) is not bool:
        raise ValueError("allow_quarantine must be boolean")
    if type(policy.quarantine_cost) is not int or policy.quarantine_cost < 1:
        raise ValueError("quarantine_cost must be a positive integer")
    ids = set()
    for s in samples:
        if not isinstance(s.id, str) or not s.id or s.id in ids:
            raise ValueError("sample IDs must be unique nonempty strings")
        ids.add(s.id)
        if s.original not in parts and s.original != QUARANTINE:
            raise ValueError(f"unknown original partition for {s.id}")
        if not isinstance(s.label, str):
            raise ValueError("labels must be strings")
        if type(s.locked) is not bool or type(s.weight) is not int or s.weight < 1:
            raise ValueError("locked must be boolean and weight a positive integer")
        if len(set(s.groups)) != len(s.groups) or any(
            not isinstance(g, str) or not g for g in s.groups
        ):
            raise ValueError("groups must be unique nonempty namespaced strings")
        if s.allowed is not None and (
            len(set(s.allowed)) != len(s.allowed) or not set(s.allowed) <= set(parts)
        ):
            raise ValueError(
                "allowed must contain unique known partitions; empty means quarantine only"
            )
    for bounds in [policy.size_bounds, *policy.label_bounds.values()]:
        for p, pair in bounds.items():
            if p not in parts or len(pair) != 2 or any(type(n) is not int for n in pair):
                raise ValueError(
                    "bounds require known partition names and integer lower/upper pairs"
                )
            if not 0 <= pair[0] <= pair[1]:
                raise ValueError("bounds must satisfy 0 <= lower <= upper")


def interval_allowed(
    start: float, end: float, windows: dict[str, tuple[float, float]]
) -> tuple[str, ...]:
    """Partitions containing the ENTIRE half-open source/target interval [start, end).

    The caller supplies all source and target dependency times and any embargo gaps.
    No timestamp or dependence is inferred from feature values.
    """
    if not math.isfinite(start) or not math.isfinite(end) or start >= end:
        raise ValueError("record interval must be finite and nonempty")
    for low, high in windows.values():
        if math.isnan(low) or math.isnan(high) or low >= high:
            raise ValueError("partition windows must be ordered and nonempty")
    return tuple(p for p, (low, high) in windows.items() if low <= start and end <= high)


def problem_dict(samples: list[Sample], policy: Policy) -> dict:
    return {"schema_version": 1, "samples": [asdict(s) for s in samples], "policy": asdict(policy)}


def fingerprint(samples: list[Sample], policy: Policy) -> str:
    obj = problem_dict(sorted(samples, key=lambda s: s.id), policy)
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read_problem(path: str | Path) -> tuple[list[Sample], Policy]:
    obj = json.loads(Path(path).read_text())
    if obj.get("schema_version", 1) != 1:
        raise ValueError("unsupported problem schema")
    samples = []
    for row in obj["samples"]:
        row = dict(row)
        row["groups"] = tuple(row.get("groups", ()))
        if row.get("allowed") is not None:
            row["allowed"] = tuple(row["allowed"])
        samples.append(Sample(**row))
    values = dict(obj.get("policy", {}))
    if "partitions" in values:
        values["partitions"] = tuple(values["partitions"])
    policy = Policy(**values)
    validate(samples, policy)
    return samples, policy
