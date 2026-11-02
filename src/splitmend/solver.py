"""Integer partition repair, exact block aggregation and bounded conflict explanation."""

from __future__ import annotations

import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

from .audit import audit
from .model import QUARANTINE, Policy, Sample, fingerprint, validate


@dataclass
class Model:
    samples: list[Sample]
    policy: Policy
    blocks: list[list[Sample]]
    destinations: tuple[str, ...]
    costs: np.ndarray
    upper: np.ndarray
    matrix: object
    lower_rows: np.ndarray
    upper_rows: np.ndarray
    names: list[str | None]
    descriptions: dict

    def solve(self, seconds: float, enabled: set[str] | None = None, feasibility=False):
        mask = np.array([n is None or enabled is None or n in enabled for n in self.names])
        return milp(
            np.zeros_like(self.costs) if feasibility else self.costs,
            integrality=np.ones(len(self.costs)),
            bounds=Bounds(np.zeros(len(self.costs)), self.upper),
            constraints=LinearConstraint(
                self.matrix[mask], self.lower_rows[mask], self.upper_rows[mask]
            ),
            options={"time_limit": seconds, "mip_rel_gap": 0.0, "presolve": True},
        )


def _build(samples, policy, compress=True):
    usage = Counter(g for s in samples for g in s.groups)
    groups = sorted(g for g, n in usage.items() if n > 1)
    active = set(groups)
    buckets = defaultdict(list)
    for s in sorted(samples, key=lambda x: x.id):
        key = (
            tuple(sorted(active.intersection(s.groups))),
            s.original,
            s.label,
            None if s.allowed is None else tuple(sorted(s.allowed)),
            s.locked,
            s.weight,
        )
        if not compress:
            key = (*key, s.id)
        buckets[key].append(s)
    blocks = list(buckets.values())
    destinations = (
        (*policy.partitions, QUARANTINE) if policy.allow_quarantine else policy.partitions
    )
    k, d = len(policy.partitions), len(destinations)
    nx = len(blocks) * d
    gi = {g: nx + j * k for j, g in enumerate(groups)}
    size = nx + k * len(groups)
    costs, upper = np.zeros(size), np.ones(size)
    rr, cc, vv, lo, hi, names = [], [], [], [], [], []
    descriptions = {}

    def add(terms, lower, high, name=None, detail=None):
        row = len(lo)
        for col, val in terms:
            rr.append(row)
            cc.append(col)
            vv.append(val)
        lo.append(lower)
        hi.append(high)
        names.append(name)
        if name is not None:
            descriptions[name] = detail

    for b, members in enumerate(blocks):
        s, n = members[0], len(members)
        add([(b * d + p, 1) for p in range(d)], n, n)
        for p, dest in enumerate(destinations):
            col = b * d + p
            upper[col] = n
            costs[col] = (
                0
                if dest == s.original
                else s.weight * (policy.quarantine_cost if dest == QUARANTINE else 1)
            )
            if s.locked and dest != s.original:
                add(
                    [(col, 1)],
                    0,
                    0,
                    f"lock:block:{b}",
                    {
                        "kind": "lock",
                        "samples": [x.id for x in members[:5]],
                        "partition": s.original,
                    },
                )
            if dest != QUARANTINE and s.allowed is not None and dest not in s.allowed:
                add(
                    [(col, 1)],
                    0,
                    0,
                    f"eligibility:block:{b}",
                    {
                        "kind": "eligibility",
                        "samples": [x.id for x in members[:5]],
                        "allowed": list(s.allowed),
                    },
                )
            if dest != QUARANTINE:
                for g in sorted(active.intersection(s.groups)):
                    add(
                        [(col, 1), (gi[g] + p, -n)],
                        -np.inf,
                        0,
                        f"group:{g}",
                        {"kind": "group", "group": g},
                    )
    for g in groups:
        add([(gi[g] + p, 1) for p in range(k)], 0, 1, f"group:{g}", {"kind": "group", "group": g})
    for p, dest in enumerate(policy.partitions):
        if dest in policy.size_bounds:
            lower, high = policy.size_bounds[dest]
            add(
                [(b * d + p, 1) for b in range(len(blocks))],
                lower,
                high,
                f"size:{dest}",
                {"kind": "size", "partition": dest, "bounds": [lower, high]},
            )
        for label, bounds in sorted(policy.label_bounds.items()):
            if dest in bounds:
                lower, high = bounds[dest]
                add(
                    [
                        (b * d + p, 1)
                        for b, members in enumerate(blocks)
                        if members[0].label == label
                    ],
                    lower,
                    high,
                    f"label:{label}:{dest}",
                    {"kind": "label", "label": label, "partition": dest, "bounds": [lower, high]},
                )
    matrix = coo_matrix((vv, (rr, cc)), shape=(len(lo), size)).tocsr()
    return Model(
        samples,
        policy,
        blocks,
        destinations,
        costs,
        upper,
        matrix,
        np.array(lo),
        np.array(hi),
        names,
        descriptions,
    )


def _direct_conflict(samples, policy):
    locks = {}
    for s in sorted(samples, key=lambda x: x.id):
        if not s.locked:
            continue
        if s.original == QUARANTINE:
            if not policy.allow_quarantine:
                return [{"kind": "lock", "sample": s.id}, {"kind": "quarantine_disabled"}]
            continue
        if s.allowed is not None and s.original not in s.allowed:
            return [
                {"kind": "lock", "sample": s.id, "partition": s.original},
                {"kind": "eligibility", "sample": s.id, "allowed": list(s.allowed)},
            ]
        for g in sorted(s.groups):
            if g in locks and locks[g].original != s.original:
                return [
                    {"kind": "group", "group": g},
                    {"kind": "lock", "sample": locks[g].id, "partition": locks[g].original},
                    {"kind": "lock", "sample": s.id, "partition": s.original},
                ]
            locks[g] = s
    return None


def _explain(model, max_checks, seconds):
    enabled = set(model.descriptions)
    checks, unknown = 0, False
    for name in sorted(model.descriptions):
        if checks >= max_checks:
            unknown = True
            break
        trial = enabled - {name}
        result = model.solve(seconds, trial, feasibility=True)
        checks += 1
        if result.status == 2:
            enabled = trial
        elif result.status != 0:
            unknown = True
    return {
        "kind": "irreducible_constraint_set" if not unknown else "unreduced_conflicting_set",
        "complete": not unknown,
        "checks": checks,
        "constraints": [model.descriptions[n] for n in sorted(enabled)],
    }


def repair(
    samples: list[Sample],
    policy: Policy,
    *,
    time_limit: float = 60,
    explain: bool = True,
    conflict_checks: int = 64,
    conflict_time_limit: float = 2,
    compress: bool = True,
) -> dict:
    """Return optimal/feasible/infeasible/unknown, and publish assignments only after audit.

    'optimal' means HiGHS proved optimality at its numerical tolerances, or the
    unchanged assignment has zero cost. Time limits never imply infeasibility.
    Conflict sets are irreducible only when all deletion checks finish; they are
    not claimed to have minimum cardinality.
    """
    if not math.isfinite(time_limit) or time_limit <= 0:
        raise ValueError("time_limit must be positive and finite")
    if conflict_checks < 0 or not math.isfinite(conflict_time_limit) or conflict_time_limit <= 0:
        raise ValueError("invalid conflict explanation budget")
    started = time.perf_counter()
    samples = list(samples)
    validate(samples, policy)
    before = audit(samples, policy)
    result = {
        "schema_version": 1,
        "input_sha256": fingerprint(samples, policy),
        "before": before,
        "assignments": None,
        "after": None,
        "conflict": None,
        "objective": None,
        "lower_bound": None,
        "gap": None,
    }
    if before["valid"]:
        result.update(
            status="optimal",
            reason="unchanged_zero_cost",
            objective=0,
            lower_bound=0,
            gap=0,
            assignments={s.id: s.original for s in samples},
            after=before,
            model={"rows": len(samples), "blocks": 0, "variables": 0},
        )
    else:
        witness = _direct_conflict(samples, policy)
        if not samples:
            witness = before["violations"]
        if witness is not None:
            result.update(
                status="infeasible",
                reason="direct_conflict",
                conflict={"kind": "direct_witness", "complete": True, "constraints": witness},
            )
        else:
            model = _build(samples, policy, compress)
            result["model"] = {
                "rows": len(samples),
                "blocks": len(model.blocks),
                "variables": len(model.costs),
                "constraints": len(model.names),
            }
            solved = model.solve(time_limit)
            result["solver_message"] = str(solved.message)
            if solved.status == 2:
                result.update(status="infeasible", reason="solver_proved_infeasible")
                if explain:
                    result["conflict"] = _explain(model, conflict_checks, conflict_time_limit)
            elif solved.x is None:
                result.update(status="unknown", reason="no_verified_incumbent")
            else:
                d = len(model.destinations)
                if np.max(np.abs(solved.x - np.rint(solved.x))) > 1e-5:
                    raise RuntimeError("solver returned a nonintegral incumbent")
                assignment = {}
                for b, members in enumerate(model.blocks):
                    offset = 0
                    for p, dest in enumerate(model.destinations):
                        count = int(round(solved.x[b * d + p]))
                        if count < 0:
                            raise RuntimeError("negative block count")
                        for s in members[offset : offset + count]:
                            assignment[s.id] = dest
                        offset += count
                    if offset != len(members):
                        raise RuntimeError("block reconstruction lost records")
                after = audit(samples, policy, assignment)
                if not after["valid"]:
                    raise RuntimeError("independent verifier rejected the solver incumbent")
                result.update(
                    status="optimal" if solved.status == 0 else "feasible",
                    reason="solver",
                    assignments=assignment,
                    after=after,
                    objective=after["objective"],
                )
                for attr, key in [("mip_dual_bound", "lower_bound"), ("mip_gap", "gap")]:
                    value = getattr(solved, attr, None)
                    if value is not None and math.isfinite(value):
                        result[key] = float(value)
    result["seconds"] = time.perf_counter() - started
    return result
