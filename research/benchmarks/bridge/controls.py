"""Run no-quarantine controls and derive direct bound contradictions."""
from dataclasses import replace
from experiment import *

def run(output):
    frame,protocol=source();controls=[];contradictions=[]
    for args in scenarios(frame,protocol):
        seed,test,val,_=args;case=f'seed{seed}_test{test}_val{val}'
        samples,policy,original,locked,meta=problem(frame,protocol,*args)
        result=repair(samples,replace(policy,allow_quarantine=False),time_limit=60,explain=False)
        if result['assignments'] is not None:
            dest=np.array([DESTS.index(result['assignments'][r]) for r in frame.record],dtype=np.int8)
            checked=independent_audit(frame,original,locked,replace(policy,allow_quarantine=False),dest)
            assert checked['valid']
        controls.append({'case':case,'status':result['status'],'objective':result['objective'],
                         'seconds':result['seconds'],'solver_message':result.get('solver_message'),
                         'model':result.get('model')})
        native=load(output/'cases'/case/'splitmend.json.gz')['summary']
        if native['status']!='infeasible':continue
        fixed_students=set(frame.loc[locked,'student'])
        forced=(~locked)&frame.student.isin(fixed_students).to_numpy()
        certificates=[]
        for label in sorted(frame.label.unique()):
            available=int(((~locked)&(frame.label==label)).sum())
            required_q=int((forced&(frame.label==label)).sum())
            minimum=sum(policy.label_bounds[label][part][0] for part in ['train','validation'])
            if available-required_q<minimum:
                certificates.append({'label':label,'free_rows':available,'forced_quarantine':required_q,
                                     'maximum_retained':available-required_q,'required_retained_minimum':minimum})
        contradictions.append({'case':case,'forced_quarantine_total':int(forced.sum()),
                               'direct_count_contradictions':certificates})
    save(output/'no_quarantine_solver_controls.json',controls)
    save(output/'infeasibility_explanations.json',contradictions)
    print(json.dumps({'no_quarantine_statuses':dict(Counter(r['status'] for r in controls)),
                     'direct_infeasibility_certificates':sum(bool(r['direct_count_contradictions']) for r in contradictions)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results')
    args=parser.parse_args();run(args.output)
