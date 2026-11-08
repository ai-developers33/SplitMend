"""Rebuild all 40 OULAD models with and without explicit singleton stripping."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'benchmarks/bridge'))
from experiment import source, scenarios, problem
from splitmend.solver import _build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    frame, protocol = source()
    full_groups = {
        row.record: ('student:' + row.student, 'offering:' + row.offering)
        for row in frame.itertuples(index=False)
    }
    usage = Counter(g for groups in full_groups.values() for g in groups)
    checks = []
    for scenario in scenarios(frame, protocol):
        stripped, policy, _, _, metadata = problem(frame, protocol, *scenario)
        unstripped = [replace(s, groups=full_groups[s.id]) for s in stripped]
        before, after = _build(unstripped, policy), _build(stripped, policy)
        equal = {
            'block_members': [[s.id for s in b] for b in before.blocks]
                            == [[s.id for s in b] for b in after.blocks],
            'destinations': before.destinations == after.destinations,
            'matrix': before.matrix.shape == after.matrix.shape
                      and (before.matrix != after.matrix).nnz == 0,
            'constraint_names': before.names == after.names,
        }
        for field in ['costs', 'upper', 'lower_rows', 'upper_rows']:
            equal[field] = bool(np.array_equal(getattr(before, field), getattr(after, field)))
        seed, test, val, _ = scenario
        checks.append({
            'case': f'seed{seed}_test{test}_val{val}', 'equal': equal,
            'blocks': len(before.blocks), 'variables': len(before.costs),
            'singleton_tokens_removed': metadata['singleton_group_tokens_removed'],
        })
    report = {
        'cases': len(checks), 'all_equivalent': all(all(c['equal'].values()) for c in checks),
        'rows': len(frame), 'students': int(frame.student.nunique()),
        'singleton_tokens': sum(n == 1 for n in usage.values()),
        'scope': 'Matrix equivalence of the released v0.1.1 internal filtering and explicit preprocessing; no new optimizer change.',
        'checks': checks,
    }
    assert report['cases'] == 40 and report['all_equivalent']
    assert all(c['blocks'] == 345 and c['variables'] == 1824 for c in checks)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
