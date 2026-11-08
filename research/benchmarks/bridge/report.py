"""Rebuild every problem, re-audit all rows, retain failures and solver gaps."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import argparse,json,shutil
import numpy as np
import pandas as pd
from experiment import ROOT,source,scenarios,problem,independent_audit,load,save,sha

def no_quarantine_witness(frame,original,locked):
    graph=defaultdict(list)
    for r in frame.itertuples(index=False):
        a,b='student:'+r.student,'offering:'+r.offering
        graph[a].append((b,r.record));graph[b].append((a,r.record))
    starts={'offering:'+x for x in frame.loc[locked,'offering']}
    targets={'offering:'+x for x in frame.loc[~locked,'offering']}
    parents={s:None for s in sorted(starts)};queue=deque(sorted(starts));target=None
    while queue:
        node=queue.popleft()
        if node in targets:target=node;break
        for nxt,record in graph[node]:
            if nxt not in parents:
                parents[nxt]=(node,record);queue.append(nxt)
    if target is None:
        return {'infeasible_without_quarantine':None,'proof':'No locked-to-free connectivity witness; no infeasibility conclusion from this check.'}
    path=[];node=target
    while parents[node] is not None:
        prev,record=parents[node];path.append({'from':prev,'to':node,'record':record});node=prev
    path.reverse()
    start_row=int(np.flatnonzero((frame.offering.to_numpy()==node.removeprefix('offering:'))&locked)[0])
    end_row=int(np.flatnonzero((frame.offering.to_numpy()==target.removeprefix('offering:'))&~locked)[0])
    return {'infeasible_without_quarantine':True,
            'locked_test_record':frame.iloc[start_row].record,
            'free_record_disallowing_test':frame.iloc[end_row].record,
            'equal_partition_path':path,
            'proof':'Without quarantine, each path record forces its two group tokens to share a partition. The locked endpoint fixes test; the free endpoint prohibits test. This is a structural certificate, not a solver run.'}

def reductions(pairs):
    def total(which,field):return sum(p[which][field] for p in pairs)
    result={'paired_valid':len(pairs)}
    for field in ['objective','retained_moved','quarantined','changed']:
        base,sm=total(0,field),total(1,field)
        result.update({f'greedy_{field}':base,f'splitmend_{field}':sm,
                       f'{field}_reduction_percent':100*(base-sm)/base if base else None})
    result['objective_wins']=sum(a['objective']>b['objective'] for a,b in pairs)
    result['objective_ties']=sum(a['objective']==b['objective'] for a,b in pairs)
    result['objective_losses']=sum(a['objective']<b['objective'] for a,b in pairs)
    return result

def run(results):
    frame,protocol=source()
    records=[];audits=[];certificates=[]
    for args in scenarios(frame,protocol):
        seed,test,val,_=args;case=f'seed{seed}_test{test}_val{val}'
        samples,policy,original,locked,meta=problem(frame,protocol,*args)
        folder=results/'cases'/case
        assert load(folder/'problem.json')==json.loads(json.dumps(meta))
        certificates.append({'case':case,**no_quarantine_witness(frame,original,locked)})
        for method in protocol['methods']:
            record=load(folder/(method+'.json.gz'))
            summary=record['summary']
            dest=record['assignments_in_source_row_order']
            if dest is None:
                assert method=='splitmend' and summary['status'] in ['unknown','infeasible','external_timeout'] and not summary['valid']
            else:
                dest=np.array(dest,dtype=np.int8)
                checked=independent_audit(frame,original,locked,policy,dest)
                assert all(summary[k]==v for k,v in checked.items()),(case,method)
                if method=='splitmend' and summary['status']=='optimal':
                    assert checked['valid'] and abs(summary['lower_bound']-checked['objective'])<1e-5 and summary['gap']==0
                if method=='splitmend' and summary['lower_bound'] is not None:
                    assert summary['lower_bound'] <= checked['objective']+1e-5
            records.append({**summary,'seed':seed,'test_fold':test,'validation_fold':val})
            audits.append({'case':case,'method':method,'audit_matches':True,'valid':summary['valid']})
    df=pd.DataFrame(records)
    df.to_csv(results/'all_results.csv',index=False)
    grouped={case:{r['method']:r for r in records if r['case']==case} for case in sorted(df.case.unique())}
    methods=protocol['methods'];rows=[]
    sm=[r for r in records if r['method']=='splitmend']
    for method in methods[:-1]:
        own=[r for r in records if r['method']==method]
        pairs=[(r[method],r['splitmend']) for r in grouped.values() if r[method]['valid'] and r['splitmend']['valid'] and r['splitmend']['status']=='optimal']
        rows.append({'comparator':method,'valid':sum(r['valid'] for r in own),'total':len(own),**reductions(pairs)})
    portfolio=[];portfolio_by_seed=defaultdict(list)
    for case,r in grouped.items():
        eligible=[r[m] for m in methods[:-1] if r[m]['valid']]
        if eligible and r['splitmend']['valid'] and r['splitmend']['status']=='optimal':
            best=min(eligible,key=lambda x:(x['objective'],x['method']))
            pair=(best,r['splitmend']);portfolio.append(pair);portfolio_by_seed[best['seed']].append(pair)
    rows.append({'comparator':'best_valid_greedy_portfolio','valid':sum(any(r[m]['valid'] for m in methods[:-1]) for r in grouped.values()),'total':40,**reductions(portfolio)})
    common={m:{field:sum(r[m][field] for r in grouped.values() if all(r[method]['valid'] for method in methods) and r['splitmend']['status']=='optimal') for field in ['objective','retained_moved','quarantined','changed']} for m in methods}
    common_count=sum(all(r[m]['valid'] for m in methods) and r['splitmend']['status']=='optimal' for r in grouped.values())
    result={'scenarios':40,'dataset':load(ROOT/'data/derived/cohort_manifest.json'),
            'splitmend_valid':sum(r['valid'] for r in sm),'splitmend_statuses':dict(Counter(r['status'] for r in sm)),
            'splitmend_gaps':[r['gap'] for r in sm if r['gap'] is not None],
            'comparisons':rows,'portfolio_by_seed':{str(s):reductions(p) for s,p in portfolio_by_seed.items()},
            'common_valid_count':common_count,'common_valid_totals':common,
            'no_quarantine_structurally_infeasible':sum(c['infeasible_without_quarantine'] is True for c in certificates),
            'external_independent_reproduction':False}
    save(results/'summary.json',result)
    pd.DataFrame(rows).to_csv(results/'comparison_summary.csv',index=False)
    save(results/'assignment_audit.json',{'all_match':True,'outputs_checked':len(audits),'rows_per_output':len(frame),'checks':audits})
    save(results/'no_quarantine_certificates.json',certificates)
    compact={k:v for k,v in result.items() if k not in ['dataset','splitmend_gaps']}
    compact['dataset']={k:v for k,v in result['dataset'].items() if k!='selected_students'}
    print(json.dumps(compact,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',type=Path,default=ROOT/'results');a=p.parse_args();run(a.results)
