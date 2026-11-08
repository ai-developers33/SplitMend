"""Compare original-study rerun outcomes, including 80 classifier records."""
from pathlib import Path
import argparse
import json

ROOT=Path(__file__).resolve().parents[1]


def compare(reference,fresh):
    checks=[]
    filenames=['main.json','external.json','strong_baseline_followup.json','clinical/runs.json']
    for filename in filenames:
        old=json.loads((reference/filename).read_text())
        new=json.loads((fresh/filename).read_text())
        key=lambda r:(r.get('case',r['dataset']),r.get('seed',0),r['method'])
        a,b={key(r):r for r in old},{key(r):r for r in new}
        assert a.keys()==b.keys(),filename
        for k in sorted(a):
            fields=[f for f in ['valid','changed','objective','quarantined','status'] if f in a[k]]
            checks.append({'file':filename,'key':k,'matching_fields':{f:a[k][f]==b[k].get(f) for f in fields}})
    a=json.loads((reference/'model_evaluation.json').read_text())
    b=json.loads((fresh/'model_evaluation.json').read_text())
    key=lambda r:(r['dataset'],r['seed'],r['method'],r['partition'])
    a,b={key(r):r for r in a},{key(r):r for r in b}
    assert a.keys()==b.keys()
    downstream=[]
    for k in sorted(a):
        fields=[f for f in a[k] if f!='elapsed_seconds']
        downstream.append({'key':k,'matching_fields':{f:a[k][f]==b[k].get(f) for f in fields}})
    assert len(checks)==180 and len(downstream)==80
    report={'method_outputs':180,'classifier_records':80,
            'all_match':all(all(r['matching_fields'].values()) for r in checks+downstream),
            'method_checks':checks,'classifier_checks':downstream,
            'excluded':'Wall-clock timing only. Assignments may differ at equal cost.',
            'external_independent_reproduction':False}
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fresh',type=Path,required=True,help='Fresh original_work/results directory')
    p.add_argument('--reference',type=Path,default=ROOT/'original/SplitMend/results')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=compare(a.reference,a.fresh)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not k.endswith('_checks')},indent=2))
    if not report['all_match']:raise SystemExit(1)
