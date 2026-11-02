"""New clinical comparators must satisfy the public audit before claiming a gain."""

import itertools
import sys
from collections import defaultdict
from pathlib import Path
from random import Random

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from clinical_baselines import greedy_repair  # noqa: E402

from splitmend import Policy, Sample, audit  # noqa: E402


@pytest.mark.parametrize("seed", range(20))
def test_clinical_comparators_against_small_enumeration(seed):
    rng = Random(seed)
    samples = [Sample("locked", "test", ("patient:locked",), "a", ("test",), True)]
    for group in range(4):
        for index in range(rng.randint(1, 3)):
            samples.append(
                Sample(
                    f"{group}:{index}",
                    rng.choice(["train", "validation"]),
                    (f"patient:{group}",),
                    rng.choice(["a", "b"]),
                    ("train", "validation"),
                )
            )
    n = len(samples) - 1
    policy = Policy(
        size_bounds={"train": (1, n - 1), "validation": (1, n - 1), "test": (1, 1)},
        label_bounds={
            "a": {"train": (0, n), "validation": (0, n), "test": (1, 1)},
            "b": {"train": (0, n), "validation": (0, n), "test": (0, 0)},
        },
    )
    grouped = defaultdict(list)
    for sample in samples:
        if not sample.locked:
            grouped[sample.groups[0]].append(sample)
    best = None
    for values in itertools.product(["train", "validation"], repeat=len(grouped)):
        assignment = {"locked": "test"}
        for members, value in zip(grouped.values(), values):
            assignment.update({s.id: value for s in members})
        checked = audit(samples, policy, assignment)
        if checked["valid"]:
            best = checked["objective"] if best is None else min(best, checked["objective"])
    for mode in [False, True]:
        assignment, stats = greedy_repair(samples, policy, cost_aware=mode, budget=2)
        checked = audit(samples, policy, assignment)
        assert assignment["locked"] == "test"
        assert set(assignment) == {s.id for s in samples}
        assert not checked["violation_counts"].get("group_overlap")
        assert (stats["remaining_count_violation"] == 0) == checked["valid"]
        if checked["valid"]:
            assert best is not None and checked["objective"] >= best


def test_clinical_cross_stratum_patient_and_exact_bounds():
    rows = [
        Sample("a", "train", ("patient:1",), "young", ("train", "validation")),
        Sample("b", "validation", ("patient:1",), "old", ("train", "validation")),
        Sample("c", "validation", ("patient:2",), "young", ("train", "validation")),
        Sample("d", "train", ("patient:2",), "old", ("train", "validation")),
    ]
    policy = Policy(
        size_bounds={"train": (2, 2), "validation": (2, 2)},
        label_bounds={label: {"train": (1, 1), "validation": (1, 1)} for label in ["young", "old"]},
    )
    for mode in [False, True]:
        assignment, _ = greedy_repair(rows, policy, cost_aware=mode)
        result = audit(rows, policy, assignment)
        assert result["valid"]
        assert result["objective"] == 2
