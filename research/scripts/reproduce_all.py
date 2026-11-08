"""Unified driver. Preserves references and writes fresh experiments elsewhere."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def call(command, cwd, log, pythonpath=None):
    env = os.environ.copy()
    if pythonpath:
        env['PYTHONPATH'] = str(pythonpath)
    started = time.perf_counter()
    print('Running', ' '.join(map(str, command)), flush=True)
    with log.open('w') as stream:
        subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    return {'log': log.name, 'seconds': time.perf_counter()-started}


def compare_original(reference, fresh):
    checks = []
    for name in ['main.json', 'external.json', 'strong_baseline_followup.json', 'clinical/runs.json']:
        old = json.loads((reference/name).read_text())
        new = json.loads((fresh/name).read_text())
        key = lambda r: (r.get('case', r['dataset']), r.get('seed', 0), r['method'])
        a, b = {key(r):r for r in old}, {key(r):r for r in new}
        assert a.keys() == b.keys(), name
        for k in sorted(a):
            fields = [f for f in ['valid','changed','objective','quarantined','status'] if f in a[k]]
            equal = {f:a[k][f] == b[k].get(f) for f in fields}
            checks.append({'file':name, 'key':k, 'equal':equal})
    report = {'method_outputs':len(checks), 'all_match':all(all(c['equal'].values()) for c in checks), 'checks':checks}
    assert report['method_outputs'] == 180
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['tables','audit','rerun'], default='tables')
    p.add_argument('--suites', nargs='+', choices=['original','single-group','bridge'],
                   default=['original','single-group','bridge'])
    p.add_argument('--output', type=Path, default=ROOT/'rerun')
    p.add_argument('--python', default=sys.executable)
    p.add_argument('--baseline-python')
    p.add_argument('--bootstrap', action='store_true')
    a = p.parse_args()
    if a.mode == 'tables':
        subprocess.run([sys.executable, str(ROOT/'scripts/build_tables.py')], check=True)
        return
    output = a.output.expanduser().resolve()
    if output.exists():
        raise SystemExit('Choose a new output directory; reference results are never overwritten.')
    output.mkdir(parents=True)
    logs = output/'logs'; logs.mkdir()
    interpreter = os.path.abspath(a.python) if os.path.sep in a.python else a.python
    baseline = a.baseline_python or interpreter
    if os.path.sep in baseline:
        baseline = os.path.abspath(baseline)
    if a.bootstrap:
        for name, requirements in [('main','requirements-experiments.lock'),('baselines','requirements-baselines.lock')]:
            envdir = ROOT/('.venv-'+name)
            subprocess.run([sys.executable,'-m','venv',str(envdir)],check=True)
            py = envdir/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
            subprocess.run([str(py),'-m','pip','install','-r',str(ROOT/'original/SplitMend'/requirements)],check=True)
            subprocess.run([str(py),'-m','pip','install','--no-deps',str(ROOT/'package/dist/splitmend-0.1.1-py3-none-any.whl')],check=True)
            if name == 'main':
                interpreter = str(py)
            else:
                baseline = str(py)
    report = {'mode':a.mode, 'external_independent_reproduction':False, 'steps':[], 'suites':{}}
    (output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    for suite in a.suites:
        if suite == 'original':
            work = output/'original_work'
            shutil.copytree(ROOT/'original/SplitMend', work,
                            ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','.venv*','*.pyc'))
            if a.mode == 'rerun':
                shutil.rmtree(work/'results')
                (work/'results').mkdir()
                commands = [[interpreter,work/'scripts/reproduce.py','--baseline-python',baseline]]
            else:
                commands = [[interpreter,'-m','pytest','-q'],
                            [interpreter,work/'scripts/verify_results.py'],
                            [interpreter,work/'scripts/verify_clinical.py']]
            for i, command in enumerate(commands):
                report['steps'].append(call(command,work,logs/f'original_{i}.log',work/'src'))
            if a.mode == 'rerun':
                report['suites'][suite] = compare_original(ROOT/'original/SplitMend/results',work/'results')
                (output/'original_comparison.json').write_text(json.dumps(report['suites'][suite],indent=2)+'\n')
                assert report['suites'][suite]['all_match'], 'Original numerical outcomes differ; inspect original_comparison.json.'
                report['steps'].append(call([interpreter, ROOT/'scripts/compare_original_outputs.py',
                    '--fresh',work/'results','--output',output/'original_and_downstream_comparison.json'],
                    ROOT,logs/'original_downstream_comparison.log'))
            else:
                report['suites'][suite] = {'tests_and_assignment_audits_passed':True}
        elif suite == 'single-group':
            work = ROOT/'benchmarks/single_group'
            if a.mode == 'rerun':
                command = [interpreter,work/'reproduce.py','--output',output/'single_group']
            else:
                dest = output/'single_group'; shutil.copytree(work/'results',dest)
                command = [interpreter,work/'audit_saved_results.py','--results',dest]
            report['steps'].append(call(command,work,logs/'single_group.log'))
            report['suites'][suite] = {'cases':200,'method_outputs':800,'completed':True}
        else:
            work = ROOT/'benchmarks/bridge'
            if a.mode == 'rerun':
                commands = [[interpreter,work/'reproduce.py','--output',output/'bridge']]
            else:
                dest = output/'bridge'; shutil.copytree(work/'results',dest)
                commands = [[interpreter,work/'test_bridge.py'],[interpreter,work/'report.py','--results',dest]]
            for i,command in enumerate(commands):
                report['steps'].append(call(command,work,logs/f'bridge_{i}.log'))
            report['steps'].append(call([interpreter, ROOT/'scripts/check_singleton_equivalence.py',
                '--output', output/'singleton_equivalence.json'], ROOT, logs/'singleton_equivalence.log'))
            report['suites'][suite] = {'cases':40,'method_outputs':160,'completed':True}
        (output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
    subprocess.run([interpreter,str(ROOT/'scripts/check_core_equivalence.py')],check=True)
    subprocess.run([interpreter,str(ROOT/'scripts/build_tables.py')],check=True)
    if a.mode == 'rerun' and set(a.suites) == {'original','single-group','bridge'}:
        subprocess.run([interpreter,str(ROOT/'scripts/build_tables.py'),
            '--original-results',str(output/'original_work/results'),
            '--single-group-results',str(output/'single_group'),
            '--bridge-results',str(output/'bridge'),'--output',str(output/'fresh_tables')],check=True)
    report['complete'] = True
    (output/'unified_reproduction.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Complete. Inspect',output/'unified_reproduction.json')


if __name__ == '__main__':
    main()
