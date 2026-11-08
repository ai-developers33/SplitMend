"""Small feature checks independent of the full benchmark outcomes."""
import itertools
import numpy as np
import pandas as pd
from experiment import Sample,Policy,QUARANTINE,repair,audit,BridgeModel,independent_audit,strip_singletons

def test_singletons_removed_before_aggregation():
    from splitmend.solver import _build
    samples=[Sample(str(i),'train',('offering:x','student:'+str(i)),label='x') for i in range(100)]
    samples += [Sample('bridge1','train',('offering:x','student:repeated'),label='x'),
                Sample('bridge2','validation',('offering:y','student:repeated'),label='x')]
    policy=Policy(allow_quarantine=True)
    stripped=strip_singletons(samples)
    assert all(len(s.groups)==1 for s in stripped[:100])
    before,after=_build(samples,policy),_build(stripped,policy)
    assert len(before.blocks)==len(after.blocks)==3
    assert np.array_equal(before.costs,after.costs)
    assert np.array_equal(before.upper,after.upper)
    assert (before.matrix!=after.matrix).nnz==0
    assert np.array_equal(before.lower_rows,after.lower_rows)
    assert np.array_equal(before.upper_rows,after.upper_rows)

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
    test_singletons_removed_before_aggregation()
    test_quarantine_breaks_bridge();test_decoder_has_real_quarantine_and_restoration()
    print('Singleton equivalence, exhaustive bridge and quarantine/restoration checks passed.')
