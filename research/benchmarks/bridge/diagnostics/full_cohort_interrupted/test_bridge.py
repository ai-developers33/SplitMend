"""Small feature checks independent of the full benchmark outcomes."""
import itertools
import numpy as np
import pandas as pd
from experiment import Sample,Policy,QUARANTINE,repair,audit,BridgeModel,independent_audit

def test_quarantine_breaks_bridge():
    samples=[Sample('left','train',('student:a','offering:x'),label='yes',locked=True),
             Sample('bridge','train',('student:a','offering:y'),label='yes'),
             Sample('right','validation',('student:b','offering:y'),label='yes',locked=True)]
    policy=Policy(partitions=('train','validation'),size_bounds={'train':(1,1),'validation':(1,1)},allow_quarantine=True,quarantine_cost=10)
    feasible=[]
    for assignment in itertools.product(('train','validation',QUARANTINE),repeat=3):
        result=audit(samples,policy,dict(zip(['left','bridge','right'],assignment)))
        if result['valid']:feasible.append(result['objective'])
    result=repair(samples,policy,time_limit=5,explain=False)
    assert feasible==[10] and result['objective']==10 and result['status']=='optimal'
    assert result['assignments']['bridge']==QUARANTINE
    no_q=Policy(partitions=policy.partitions,size_bounds=policy.size_bounds)
    assert repair(samples,no_q,time_limit=5,explain=False)['status']=='infeasible'

def test_decoder_has_real_quarantine_and_restoration():
    frame=pd.DataFrame({'record':[str(i) for i in range(6)],'student':['a','a','b','b','c','d'],
                        'offering':['A','B','B','C','A','B'],'label':['x']*6})
    original=np.array([0,1,1,2,0,1],dtype=np.int8);locked=original==2
    policy=Policy(size_bounds={'train':(0,6),'validation':(0,6),'test':(1,1)},
                  label_bounds={'x':{'train':(0,6),'validation':(0,6),'test':(1,1)}},allow_quarantine=True,quarantine_cost=10)
    model=BridgeModel(frame,original,locked,policy)
    dest=model.decode(model.initial_courses)
    check=independent_audit(frame,original,locked,policy,dest)
    assert check['valid'] and check['quarantined']==2 and check['objective']==20
    merged=model.initial_courses.copy();merged[1]=0
    dest=model.decode(merged)
    check=independent_audit(frame,original,locked,policy,dest)
    assert check['valid'] and check['quarantined']==1 and check['retained_moved']==2 and check['objective']==12

if __name__=='__main__':
    test_quarantine_breaks_bridge();test_decoder_has_real_quarantine_and_restoration()
    print('Exhaustive bridge check and quarantine/restoration checks passed.')
