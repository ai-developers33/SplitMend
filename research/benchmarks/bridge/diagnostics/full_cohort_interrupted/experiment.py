"""Frozen forty-scenario benchmark; all original enrolments and all outcomes."""
from pathlib import Path
import argparse
from collections import Counter,defaultdict
import gzip,hashlib,json,math,os,platform,sys,time
from dataclasses import asdict
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'))
from splitmend import Sample,Policy,QUARANTINE,repair,audit
from bridge_greedy import BridgeModel,run as greedy_run
PARTS = ('train','validation','test')
DESTS = (*PARTS,QUARANTINE)

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    text = json.dumps(data,sort_keys=True,indent=2,allow_nan=False)+'\n'
    if path.suffix == '.gz': path.write_bytes(gzip.compress(text.encode(),mtime=0))
    else: path.write_text(text)
def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_text())

def source():
    protocol=load(ROOT/'protocol.json')
    assert sha(ROOT/'data/source/studentInfo.csv') == protocol['source_csv_sha256']
    for path,digest in load(ROOT/'vendor_manifest.json').items(): assert sha(ROOT/path)==digest
    frame=pd.read_csv(ROOT/'data/source/studentInfo.csv',dtype={'id_student':str})
    frame['student']=frame.id_student
    frame['offering']=frame.code_module+':'+frame.code_presentation
    frame['label']=frame.final_result
    frame['record']=['enrolment:'+str(i) for i in range(len(frame))]
    assert not frame.duplicated(['student','offering']).any()
    return frame,protocol

def scenarios(frame,protocol):
    courses=np.array(sorted(frame.offering.unique()))
    for seed in protocol['fold_seeds']:
        folds=[set(x) for x in np.array_split(np.random.default_rng(seed).permutation(courses),5)]
        for test in range(5):
            for val in range(5):
                if test != val: yield seed,test,val,folds

def problem(frame,protocol,seed,test,val,folds):
    original=np.array([2 if c in folds[test] else 1 if c in folds[val] else 0 for c in frame.offering],dtype=np.int8)
    locked=original == 2
    samples=[Sample(id=r.record,original=PARTS[int(p)],groups=('student:'+r.student,'offering:'+r.offering),
                    label=r.label,allowed=('test',) if lock else ('train','validation'),locked=bool(lock))
             for r,p,lock in zip(frame.itertuples(index=False),original,locked)]
    def limits(n,fixed,tol):
        d={part:(max(0,math.floor((target-tol)*n)),min(n,math.ceil((target+tol)*n)))
           for part,target in protocol['free_partition_targets'].items()}
        d['test']=(fixed,fixed)
        return d
    free=Counter(frame.loc[~locked,'label']);fixed=Counter(frame.loc[locked,'label'])
    policy=Policy(size_bounds=limits(int((~locked).sum()),int(locked.sum()),protocol['size_tolerance_pp']/100),
                  label_bounds={l:limits(free[l],fixed[l],protocol['label_tolerance_pp']/100) for l in sorted(set(frame.label))},
                  allow_quarantine=True,quarantine_cost=10)
    meta={'seed':seed,'test_fold':test,'validation_fold':val,'test_offerings':sorted(folds[test]),
          'original_validation_offerings':sorted(folds[val]),'policy':asdict(policy),
          'rows':len(frame),'free_rows':int((~locked).sum()),'locked_rows':int(locked.sum())}
    return samples,policy,original,locked,meta

def independent_audit(frame,original,locked,policy,dest):
    assert len(dest)==len(frame) and np.isin(dest,[0,1,2,3]).all()
    violations=Counter()
    violations['locks']=int((dest[locked]!=original[locked]).sum())
    violations['eligibility']=int(((dest[~locked]!=0)&(dest[~locked]!=1)&(dest[~locked]!=3)).sum())
    kept=frame.loc[dest<3,['student','offering','label']].copy()
    kept['partition']=dest[dest<3]
    for group in ['student','offering']:
        violations[group+'_overlap']=int((kept.groupby(group).partition.nunique()>1).sum())
    for p,part in enumerate(PARTS):
        n=int((dest==p).sum());lo,hi=policy.size_bounds[part]
        violations['size']+=int(not lo<=n<=hi)
        for label,limits in policy.label_bounds.items():
            n=int(((dest==p)&(frame.label.to_numpy()==label)).sum());lo,hi=limits[part]
            violations['label']+=int(not lo<=n<=hi)
    q=int((dest==3).sum());moved=int(((dest<3)&(dest!=original)).sum())
    violations={k:v for k,v in violations.items() if v}
    return {'valid':not violations,'violations':violations,'objective':moved+10*q,
            'quarantined':q,'retained_moved':moved,'changed':moved+q,
            'retained':len(frame)-q,'counts':{part:int((dest==p).sum()) for p,part in enumerate(DESTS)}}

def execute(start,stop,output):
    frame,protocol=source()
    save(output/'environment.json',{'python':sys.version,'platform':platform.platform(),
         'numpy':np.__version__,'pandas':pd.__version__,'protocol_sha256':sha(ROOT/'protocol.json'),
         'runner_sha256':sha(__file__),'heuristics_sha256':sha(ROOT/'bridge_greedy.py')})
    for index,args in enumerate(scenarios(frame,protocol)):
        if not start<=index<stop:continue
        seed,test,val,_=args
        name=f'seed{seed}_test{test}_val{val}'
        folder=output/'cases'/name
        samples,policy,original,locked,meta=problem(frame,protocol,*args)
        save(folder/'problem.json',meta)
        save(folder/'before.json',independent_audit(frame,original,locked,policy,original))
        methods=protocol['methods'];rotation=index%len(methods)
        for method in methods[rotation:]+methods[:rotation]:
            path=folder/(method+'.json.gz')
            if path.exists():continue
            began=time.perf_counter()
            if method=='splitmend':
                raw=repair(samples,policy,time_limit=protocol['budgets_seconds'],explain=False)
                dest=np.array([DESTS.index(raw['assignments'][r]) for r in frame.record],dtype=np.int8) if raw['assignments'] is not None else None
                details={k:v for k,v in raw.items() if k not in ['assignments','before','after']}
                status=raw['status']
            else:
                model=BridgeModel(frame,original,locked,policy)
                dest,details=greedy_run(model,method,protocol['budgets_seconds'])
                status='heuristic'
            seconds=time.perf_counter()-began
            checked=independent_audit(frame,original,locked,policy,dest) if dest is not None else {'valid':False,'objective':None,'changed':None,'quarantined':None,'retained_moved':None,'retained':None}
            if dest is not None:
                library=audit(samples,policy,{s.id:DESTS[int(d)] for s,d in zip(samples,dest)})
                assert all(library[k]==checked[k] for k in ['valid','objective','quarantined','changed'])
            summary={'case':name,'method':method,'status':status,'seconds':seconds,**checked}
            if method=='splitmend':
                summary.update(lower_bound=raw['lower_bound'],gap=raw['gap'])
                assert raw['objective']==checked['objective']
            save(path,{'summary':summary,'assignments_in_source_row_order':dest.tolist() if dest is not None else None,'details':details})
            print(json.dumps({k:summary.get(k) for k in ['case','method','status','valid','objective','retained_moved','quarantined','seconds','gap']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=0);p.add_argument('--stop',type=int,default=40)
    p.add_argument('--output',type=Path,default=ROOT/'results');a=p.parse_args()
    execute(a.start,a.stop,a.output)
