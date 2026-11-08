"""Recompute the complete fixed benchmark into a new directory."""
import argparse,json,subprocess,sys
from pathlib import Path
from experiment import ROOT,load,save,source

def compare(output):
    checks=[]
    for original in sorted((ROOT/'results/cases').glob('*/*.json.gz')):
        relative=original.relative_to(ROOT/'results')
        old,new=load(original)['summary'],load(output/relative)['summary']
        fields=['status','valid','objective','retained_moved','quarantined','changed']
        checks.append({'case':old['case'],'method':old['method'],
                       'matching_fields':{field:old[field]==new[field] for field in fields}})
    assert len(checks)==160
    primary=['status','valid','objective']
    assert all(all(c['matching_fields'][field] for field in primary) for c in checks)
    all_match=all(all(c['matching_fields'].values()) for c in checks)
    save(output/'reproduction_comparison.json',{'outputs':160,'all_primary_results_match':True,'all_match':all_match,'checks':checks,
         'scope':'Fresh run on the same development host; not external independent reproduction. Alternative optimal assignments may occur on different solver versions.'})
    print('All 160 statuses, validities and objectives match; all movement/quarantine counts match:',all_match)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'reproduced_results');a=p.parse_args()
    a.output=a.output.expanduser().resolve()
    if a.output.exists() and list(a.output.glob('cases/*')):
        raise SystemExit('Choose an empty output directory for a fresh reproduction.')
    source()
    for script,extra in [('test_bridge.py',[]),('experiment.py',['--output',str(a.output)]),
                         ('report.py',['--results',str(a.output)]),('controls.py',['--output',str(a.output)])]:
        subprocess.run([sys.executable,str(ROOT/script),*extra],check=True,cwd=ROOT)
    compare(a.output)

if __name__=='__main__':main()
