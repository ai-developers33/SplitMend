import itertools
import json
import random

import pytest

from splitmend import QUARANTINE as Q
from splitmend import Policy, Sample, audit, interval_allowed, repair
from splitmend.cli import main
from splitmend.model import problem_dict


def test_lock_forces_reassignment():
    s = [Sample("a", "train", ("p:1",)), Sample("b", "test", ("p:1",), locked=True)]
    r = repair(s, Policy(partitions=("train", "test")))
    assert r["status"] == "optimal" and r["objective"] == 1
    assert r["assignments"] == {"a": "test", "b": "test"}


def test_conflicting_locks_have_witness():
    s = [Sample("a", "train", ("p:1",), locked=True), Sample("b", "test", ("p:1",), locked=True)]
    r = repair(s, Policy(partitions=("train", "test")))
    assert r["status"] == "infeasible" and r["assignments"] is None
    assert len(r["conflict"]["constraints"]) == 3


def test_quarantine_breaks_a_bridge_without_merging_unrelated_groups():
    s = [
        Sample("a", "train", ("a",), locked=True),
        Sample("bridge", "train", ("a", "b")),
        Sample("c", "test", ("b",), locked=True),
    ]
    p = Policy(partitions=("train", "test"), allow_quarantine=True)
    r = repair(s, p)
    assert r["assignments"] == {"a": "train", "bridge": Q, "c": "test"}
    assert r["objective"] == 10


def test_class_and_size_constraints():
    s = [Sample(str(i), "train", label=str(i % 2)) for i in range(8)]
    p = Policy(
        partitions=("train", "test"),
        size_bounds={"train": (4, 4), "test": (4, 4)},
        label_bounds={"0": {"test": (2, 2)}, "1": {"test": (2, 2)}},
    )
    r = repair(s, p)
    assert r["objective"] == 4 and r["after"]["valid"]


def test_compression_and_cost_weights():
    s = [
        Sample("a", "train", ("g",), weight=7),
        Sample("b", "test", ("g",)),
        Sample("c", "test", ("g",)),
    ]
    r = repair(s, Policy(partitions=("train", "test")))
    assert r["objective"] == 2
    assert set(r["assignments"].values()) == {"train"}


def test_capacity_conflict_is_irreducible():
    s = [Sample("a", "train")]
    p = Policy(partitions=("train", "test"), size_bounds={"train": (1, 1), "test": (1, 1)})
    r = repair(s, p)
    assert r["status"] == "infeasible"
    assert r["conflict"]["kind"] == "irreducible_constraint_set"
    assert len(r["conflict"]["constraints"]) == 2


def test_incomplete_conflict_not_labelled_irreducible():
    r = repair(
        [Sample("a", "train")],
        Policy(partitions=("train", "test"), size_bounds={"test": (2, 2)}),
        conflict_checks=0,
    )
    assert not r["conflict"]["complete"]


def test_temporal_boundary_and_quarantine():
    windows = {"train": (0, 10), "test": (12, 20)}
    assert interval_allowed(0, 10, windows) == ("train",)
    assert interval_allowed(9, 13, windows) == ()
    assert interval_allowed(12, 20, windows) == ("test",)
    r = repair(
        [Sample("x", "train", allowed=())],
        Policy(partitions=("train", "test"), allow_quarantine=True),
    )
    assert r["assignments"] == {"x": Q}


def test_clean_split_unchanged():
    s = [Sample("a", "train"), Sample("b", "test")]
    r = repair(s, Policy(partitions=("train", "test")))
    assert r["objective"] == 0 and r["reason"] == "unchanged_zero_cost"


@pytest.mark.parametrize(
    "sample",
    [
        Sample("a", "train", weight=0),
        Sample("a", "train", allowed=("bogus",)),
        Sample("a", "bogus"),
    ],
)
def test_bad_inputs_rejected(sample):
    with pytest.raises(ValueError):
        repair([sample], Policy())


def test_duplicate_ids_and_missing_assignments():
    with pytest.raises(ValueError):
        repair([Sample("a", "train"), Sample("a", "test")], Policy())
    with pytest.raises(ValueError):
        audit([Sample("a", "train")], Policy(), {})


def test_noop_empty():
    assert repair([], Policy())["objective"] == 0


def test_empty_infeasible():
    r = repair([], Policy(size_bounds={"train": (1, 2)}))
    assert r["status"] == "infeasible"


def test_locked_ineligible_record():
    r = repair([Sample("a", "train", allowed=("test",), locked=True)], Policy())
    assert r["status"] == "infeasible" and len(r["conflict"]["constraints"]) == 2


def test_timeout_without_incumbent_is_unknown(monkeypatch):
    from types import SimpleNamespace

    from splitmend.solver import Model

    monkeypatch.setattr(
        Model, "solve", lambda *a, **kw: SimpleNamespace(status=1, x=None, message="time limit")
    )
    r = repair([Sample("a", "train")], Policy(size_bounds={"test": (1, 1)}))
    assert r["status"] == "unknown" and r["assignments"] is None


def test_timeout_with_incumbent_is_feasible(monkeypatch):
    from splitmend.solver import Model

    original = Model.solve

    def limited(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result.status = 1
        return result

    monkeypatch.setattr(Model, "solve", limited)
    r = repair([Sample("a", "train")], Policy(size_bounds={"test": (1, 1)}))
    assert r["status"] == "feasible" and r["after"]["valid"]


def test_cli(tmp_path):
    path = tmp_path / "p.json"
    out = tmp_path / "r.json"
    path.write_text(json.dumps(problem_dict([Sample("a", "train")], Policy())))
    assert main(["repair", str(path), "--output", str(out)]) == 0
    assert json.loads(out.read_text())["after"]["valid"]
    assert main(["repair", str(path), "--output", str(path)]) == 4


@pytest.mark.parametrize("seed", range(30))
def test_optimum_against_exhaustive_enumeration(seed):
    rng = random.Random(seed)
    n = rng.randint(2, 5)
    parts = ("train", "test")
    s = [
        Sample(
            str(i),
            rng.choice(parts),
            groups=(f"g:{rng.randrange(3)}",),
            label=str(i % 2),
            locked=rng.random() < 0.12,
            weight=rng.randint(1, 3),
            allowed=rng.choice([None, None, ("train",), ("test",)]),
        )
        for i in range(n)
    ]
    p = Policy(
        partitions=parts,
        allow_quarantine=seed % 2 == 0,
        size_bounds={"train": (1, n), "test": (1, n)},
    )
    choices = (*parts, Q) if p.allow_quarantine else parts
    costs = []
    for values in itertools.product(choices, repeat=n):
        a = dict(zip([x.id for x in s], values))
        v = audit(s, p, a)
        if v["valid"]:
            costs.append(v["objective"])
    r = repair(s, p)
    u = repair(s, p, compress=False)
    if costs:
        assert r["status"] == u["status"] == "optimal"
        assert r["objective"] == u["objective"] == min(costs)
    else:
        assert r["status"] == u["status"] == "infeasible"
