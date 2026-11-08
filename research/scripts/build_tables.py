"""Regenerate Tables 1-5 from raw saved method outputs; standard library only."""
from pathlib import Path
from collections import defaultdict, Counter
import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def save_table(folder, name, rows):
    (folder/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    with (folder/(name+'.csv')).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def reduction(old,new):
    return 100*(old-new)/old if old else None


def build(folder,original=None,sweep_results=None,bridge_results=None):
    folder.mkdir(parents=True,exist_ok=True)
    original = original or ROOT/'original/SplitMend/results'
    runs = sum((load(original/name) for name in ['main.json','external.json','strong_baseline_followup.json']),[])
    table1=[]
    methods=[('splitmend','SplitMend'),('greedy','Original greedy repair'),
             ('cost_greedy_local','Cost-aware greedy + exchanges'),('group_resplit','Group re-split'),
             ('datasail_i1_aligned','DataSAIL I1'),('dataset_splitter','dataset-splitter')]
    for method,label in methods:
        row={'method':label}
        for dataset in ['har','oulad']:
            valid=[r for r in runs if r['dataset']==dataset and r['method']==method and r['valid']]
            assert len(valid)==5,(method,dataset)
            row[dataset+'_mean_changes']=statistics.mean(r['changed'] for r in valid)
        table1.append(row)
    save_table(folder,'table1',table1)
    clinical=load(original/'clinical/runs.json');table2=[]
    for tolerance in [0.01,0.025,0.05]:
        row={'tolerance_pp':100*tolerance}
        for method in ['splitmend','violation_greedy','cost_greedy_local']:
            valid=[r for r in clinical if r['tolerance']==tolerance and r['method']==method and r['valid']]
            assert len(valid)==5
            row[method+'_mean_changes']=statistics.mean(r['changed'] for r in valid)
        table2.append(row)
    save_table(folder,'table2',table2)
    table3=[]
    for r in load(original/'aggregation.json'):
        assert r['equal_optimum'] and r['compressed']['objective']==r['expanded']['objective']
        c,e=r['compressed']['model']['variables'],r['expanded']['model']['variables']
        table3.append({'dataset':r['dataset'].upper(),'rows':r['n'],'compressed_variables':c,
                       'row_variables':e,'objective':r['compressed']['objective'],
                       'variable_reduction_percent':reduction(e,c)})
    save_table(folder,'table3',table3)
    beijing=[r for r in runs if r['dataset']=='beijing' and r['method']=='splitmend']
    assert len(beijing)==5 and all(r['quarantined']==1128 and r['n']==420204 for r in beijing)
    save_table(folder,'table3_temporal',[{'dataset':'Beijing PM2.5','scenarios':5,'complete_spans_per_case':420204,
        'quarantined_per_case':1128,'retained_percent':100*(420204-1128)/420204}])
    sweep=ROOT/'benchmarks/single_group';table4=[]
    sweep_results=sweep_results or sweep/'results'
    labels={'har70':'HAR70+','pamap2':'PAMAP2','unimib':'UniMiB SHAR',
            'sleeptelemetry':'Sleep-EDF Telemetry','extrasensory_revision':'ExtraSensory'}
    for dataset,label in labels.items():
        cases=[]
        for d in sorted((sweep_results/dataset/'cases').iterdir()):
            methods={m:load(d/(m+'.json'))['summary'] for m in ['splitmend','violation_greedy','cost_greedy_local','all_pair_greedy']}
            sm=methods['splitmend'];valid=[r for m,r in methods.items() if m!='splitmend' and r['valid']]
            if sm['status']=='optimal':
                assert sm['valid'] and sm['gap']==0.0
                assert math.isclose(sm['lower_bound'],sm['changed'],rel_tol=1e-9,abs_tol=1e-6)
            best=min(valid,key=lambda r:(r['changed'],r['method'])) if valid else None
            cases.append((sm,best))
            if (d/'enumeration.json').exists():
                e=load(d/'enumeration.json');assert sm['changed']==e['optimal_movement']
                assert (sm['status']=='optimal')==bool(e['valid_allocations'])
        assert len(cases)==40
        pairs=[(s,g) for s,g in cases if s['status']=='optimal' and s['valid'] and g]
        old=sum(g['changed'] for s,g in pairs);new=sum(s['changed'] for s,g in pairs)
        row={'dataset':label,'attempted':40,'optimal':sum(s['status']=='optimal' for s,g in cases),
             'infeasible':sum(s['status']=='infeasible' for s,g in cases),
             'unresolved':sum(s['status'] not in ['optimal','infeasible'] for s,g in cases),
             'valid_pairs':len(pairs),'greedy_failures_on_feasible':sum(s['status']=='optimal' and not g for s,g in cases),
             'greedy_moved':old,'splitmend_moved':new,'aggregate_reduction_percent':reduction(old,new),
             'wins':sum(s['changed']<g['changed'] for s,g in pairs),
             'ties':sum(s['changed']==g['changed'] for s,g in pairs)}
        table4.append(row)
    save_table(folder,'table4',table4)
    bridge=ROOT/'benchmarks/bridge';cases=defaultdict(dict)
    bridge_results=bridge_results or bridge/'results'
    for p in sorted((bridge_results/'cases').glob('*/*.json.gz')):
        r=load(p)['summary'];cases[r['case']][r['method']]=r
    assert len(cases)==40
    no_quarantine=load(bridge_results/'no_quarantine_solver_controls.json')
    assert len(no_quarantine)==40 and all(r['status']=='infeasible' for r in no_quarantine)
    assert all(r['splitmend']['status'] in ['optimal','infeasible'] for r in cases.values())
    assert sum(r['splitmend']['status']=='infeasible' for r in cases.values())==4
    feasible=[r for r in cases.values() if r['splitmend']['status']=='optimal']
    assert len(feasible)==36
    for case in feasible:
        sm=case['splitmend']
        assert sm['valid'] and sm['gap']==0.0
        assert math.isclose(sm['lower_bound'],sm['objective'],rel_tol=1e-9,abs_tol=1e-6)
    methods=['violation_first_bridge','cost_aware_bridge_exchanges','all_pair_bridge']
    table5=[];unmatched=[]
    for method in methods+['best_valid_greedy_per_case']:
        pairs=[]
        for r in feasible:
            valid=[r[m] for m in methods if r[m]['valid']]
            g=min(valid,key=lambda x:(x['objective'],x['method'])) if method=='best_valid_greedy_per_case' else r[method]
            if g['valid']:pairs.append((g,r['splitmend']))
        row={'comparator':method,'valid_pairs':len(pairs),'feasible_cases':36}
        for field in ['quarantined','retained_moved','objective']:
            row['comparator_'+field]=sum(g[field] for g,s in pairs)
            row['splitmend_'+field]=sum(s[field] for g,s in pairs)
        for who in ['comparator','splitmend']:
            assert row[who+'_objective']==row[who+'_retained_moved']+10*row[who+'_quarantined']
        row['objective_reduction_percent']=reduction(row['comparator_objective'],row['splitmend_objective'])
        row['wins']=sum(s['objective']<g['objective'] for g,s in pairs)
        row['ties']=sum(s['objective']==g['objective'] for g,s in pairs)
        row['losses']=sum(s['objective']>g['objective'] for g,s in pairs)
        table5.append(row)
        if method in methods:
            unmatched.append({'method':method,'cases':36,'valid':sum(r[method]['valid'] for r in feasible),
                              **{f:sum(r[method][f] for r in feasible) for f in ['quarantined','retained_moved','objective']}})
    save_table(folder,'table5',table5);save_table(folder,'table5_unmatched_diagnostics',unmatched)
    with gzip.open(bridge/'data/derived/cohort.csv.gz','rt') as f:cohort=list(csv.DictReader(f))
    parent={r['offering']:r['offering'] for r in cohort}
    def find(a):
        while parent[a]!=a:
            parent[a]=parent[parent[a]];a=parent[a]
        return a
    student=defaultdict(list)
    for r in cohort:student[r['student']].append(r['offering'])
    for offers in student.values():
        for o in offers[1:]:parent[find(o)]=find(offers[0])
    sizes=Counter(find(o) for o in parent)
    explanations=load(sweep/'results/illustrative_case_explanations.json')
    tail=next(r for r in explanations if r['dataset']=='har70')
    assert tail['greedy_movement']==1854 and tail['splitmend_movement']==954
    tail['regret_relative_to_optimum_percent']=100*(1854-954)/954
    note={'scope':'Repeated policy scenarios, not independent cohorts. No classifier metrics in Tables 4-5.',
          'table4_comparator':'Best valid of three internal greedy methods, chosen without the MILP answer.',
          'pamap2':{'feasible':12,'infeasible':28,'greedy_valid_feasible':6,'greedy_failed_feasible':6},
          'har70_tail_case':tail,
          'bridge':{'feasible':36,'infeasible':4,'offering_component_sizes':sorted(sizes.values(),reverse=True),
             'maximum_repair_call_seconds':max(r['splitmend']['seconds'] for r in cases.values()),
             'median_repair_call_seconds':statistics.median(r['splitmend']['seconds'] for r in cases.values()),
             'no_quarantine_control':'Modified policy: all 40 scenarios solver-proven infeasible. Not an external splitter comparison.',
             'infeasibility_explanation':'Separate count audit: 262 free Withdrawn rows minus 44 forced exclusions = 218, below required 219.'}}
    (folder/'interpretation.json').write_text(json.dumps(note,indent=2)+'\n')
    text=['# Regenerated manuscript tables','', 'All values are regenerated from archived method outputs.','']
    for name,rows in [('Table 1',table1),('Table 2',table2),('Table 3',table3),('Table 4',table4),('Table 5',table5)]:
        fields=list(rows[0]);text += ['## '+name,'','| '+' | '.join(fields)+' |','| '+' | '.join(['---']*len(fields))+' |']
        for r in rows:text.append('| '+' | '.join(str(r[f]) for f in fields)+' |')
        text.append('')
    (folder/'all_tables.md').write_text('\n'.join(text)+'\n')
    return {'tables':[1,2,3,4,5],'raw_method_outputs':1140,'generated_from_saved_results':True,
            'inputs':{'original':str(original),'single_group':str(sweep_results),'bridge':str(bridge_results)}}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'tables')
    p.add_argument('--original-results',type=Path)
    p.add_argument('--single-group-results',type=Path)
    p.add_argument('--bridge-results',type=Path)
    a=p.parse_args()
    print(json.dumps(build(a.output,a.original_results,a.single_group_results,a.bridge_results)))
