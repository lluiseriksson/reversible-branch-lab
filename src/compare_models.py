"""Finite like-for-like oracle comparison, not a full upstream circuit replay.

Prior sources: arXiv2610.22367v1 and andigu/uncompute commit64b5a13,
engine.py sections decode5_derive, _pprm_prog and pprm_level.
Original implementation of the described strategy; no source code copied.
"""
from clean_decoder import DAG
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,platform

P=2**256-2**32-977

def monomials(j):
    n=j-1;count=1<<(2*n);mask=(1<<n)-1
    coeff=[((P*pow((1+2*(i&mask))*(1+2*(i>>n)),-1,1<<j))%(1<<j))>>(j-1) for i in range(count)]
    for bit in [1<<k for k in range(2*n)]:
        for subset in range(count):
            if subset&bit:coeff[subset]^=coeff[subset^bit]
    terms=[]
    for subset,c in enumerate(coeff):
        if c:
            fs=tuple(i for i in range(n) if subset>>i&1)
            qs=tuple(i for i in range(n) if subset>>(n+i)&1)
            terms.append((fs,qs))
    return [fs+tuple(n+i for i in qs) for fs,qs in sorted(terms)]

def prefix_oracle(j,mbu):
    n=2*(j-1);flag=n;target=n+1;stack=[];gates=[];mint=0;records=0;peak=0
    def pop_to(depth):
        nonlocal records
        while len(stack)>depth:
            literal=stack.pop();wire=n+2+len(stack);prev=wire-1 if stack else flag
            if mbu:
                gates.extend([['HMR',wire,records],['CZC',records,prev,literal]]);records+=1
            else:gates.append(['CCX',prev,literal,wire])
    for literals in monomials(j):
        if not literals:gates.append(['CX',flag,target]);continue
        prefix=literals[:-1];same=0
        while same<min(len(stack),len(prefix)) and stack[same]==prefix[same]:same+=1
        pop_to(same)
        for literal in prefix[same:]:
            wire=n+2+len(stack);prev=wire-1 if stack else flag
            gates.append(['CCX',prev,literal,wire]);stack.append(literal);mint+=1;peak=max(peak,len(stack))
        leaf=n+1+len(stack) if stack else flag
        gates.append(['CCX',leaf,literals[-1],target])
    pop_to(0)
    return gates,{'inputs':n,'flag':flag,'target':target,'workspace':peak,'qubits':n+2+peak,'prefix_mints':mint,'records':records}

def arithmetic_oracle(j,mbu):
    dag=DAG(2*(j-1));out=dag.prune(dag.oracle(j,P));strict,layout=dag.gates(out)
    if not mbu:return strict,{**layout,'workspace':len(dag.nodes)+2,'records':0}
    seen=set();gates=[];records=0
    for gate in strict:
        if gate[0]=='CCX' and dag.n<=gate[3]<dag.n+len(dag.nodes):
            wire=gate[3]
            if wire in seen:
                gates.extend([['HMR',wire,records],['CZC',records,gate[1],gate[2]]]);records+=1
            else:seen.add(wire);gates.append(gate)
        else:gates.append(gate)
    return gates,{**layout,'workspace':len(dag.nodes)+2,'records':records}

def simulate(gates,state):
    # HMR outcomes are independent symbols, not random samples. No outcome
    # controls a basis-changing gate in this model. The phase is therefore
    # an exact GF(2) linear form in all measurement-record symbols.
    phase=0
    for g in gates:
        if g[0]=='X':state^=1<<g[1]
        elif g[0]=='CX':
            if state>>g[1]&1:state^=1<<g[2]
        elif g[0]=='CCX':
            if state>>g[1]&1 and state>>g[2]&1:state^=1<<g[3]
        elif g[0]=='HMR':
            if state>>g[1]&1:phase^=1<<g[2]
            state&=~(1<<g[1])
        elif g[0]=='CZC':
            if state>>g[2]&1 and state>>g[3]&1:phase^=1<<g[1]
        else:raise ValueError(g)
    return state,phase

def count(gates,layout):
    c={kind:sum(g[0]==kind for g in gates) for kind in ['CCX','CX','X','HMR','CZC']}
    return {'Toffoli':c['CCX'],'CNOT':c['CX'],'X':c['X'],'measurements':c['HMR'],'classically_conditioned_CZ':c['CZC'],'workspace':layout['workspace'],'qubits':layout['qubits'],'oracle_TQ':c['CCX']*layout['qubits'],'gate_sha256':hashlib.sha256(json.dumps(gates,separators=(',',':')).encode()).hexdigest()}

def parallel_check(j,gates,layout):
    # One bit per complete basis input, including supplied flag and target.
    # These are exact finite truth tables, not floating point simulation.
    n=layout['inputs'];cases=1<<(n+2);full=(1<<cases)-1
    def plane(variable):
        run=1<<variable
        return (((1<<run)-1)<<run)*(full//((1<<(2*run))-1))
    state=[0]*layout['qubits']
    for i in range(n):state[i]=plane(i)
    state[layout['flag']]=plane(n);state[layout['target']]=plane(n+1)
    initial=state[:];phase={}
    for g in gates:
        if g[0]=='X':state[g[1]]^=full
        elif g[0]=='CX':state[g[2]]^=state[g[1]]
        elif g[0]=='CCX':state[g[3]]^=state[g[1]]&state[g[2]]
        elif g[0]=='HMR':phase[g[2]]=phase.get(g[2],0)^state[g[1]];state[g[1]]=0
        elif g[0]=='CZC':phase[g[1]]=phase.get(g[1],0)^(state[g[2]]&state[g[3]])
        else:raise ValueError(g)
    wrong_phase=0
    for coefficient in phase.values():wrong_phase|=coefficient
    nw=j-1;mask=(1<<nw)-1;payload=bytearray((1<<n)//8)
    for bits in range(1<<n):
        answer=((P*pow((1+2*(bits&mask))*(1+2*(bits>>nw)),-1,1<<j))%(1<<j))>>(j-1)
        payload[bits//8]|=answer<<(bits%8)
    one=int.from_bytes(payload,'little');oracle=sum(one<<(k*(1<<n)) for k in range(4))
    expected=initial[:];expected[layout['target']]^=initial[layout['flag']]&oracle
    return state==expected,wrong_phase,cases

rows=[];negative=[]
for j in range(5,9):
    row={'depth':j,'models':{}}
    for family,builder in [('arithmetic',arithmetic_oracle),('prefix_reconstruction',prefix_oracle)]:
        for mbu in (False,True):
            gates,layout=builder(j,mbu);key=family+('_MBU' if mbu else '_unitary')
            metrics=count(gates,layout);tests=0
            all_basis_ok,wrong_phase,parallel_cases=parallel_check(j,gates,layout)
            assert all_basis_ok and wrong_phase==0,(j,key,'parallel truth-table failure')
            metrics['parallel_complete_basis_cases']=parallel_cases
            if family=='prefix_reconstruction' and j==5:assert layout['prefix_mints']==12
            if j==6:
                n=j-1;mask=(1<<n)-1
                for bits in range(1<<(2*n)):
                    answer=((P*pow((1+2*(bits&mask))*(1+2*(bits>>n)),-1,1<<j))%(1<<j))>>(j-1)
                    for flag in (0,1):
                        for target in (0,1):
                            state=bits|(flag<<layout['flag'])|(target<<layout['target'])
                            expected=state^((answer&flag)<<layout['target'])
                            final,phase=simulate(gates,state)
                            assert final==expected,(family,mbu,bits,flag,target)
                            assert phase==0,(family,mbu,bits,'measurement-dependent phase')
                            tests+=1
                if mbu:
                    drop=next(i for i,g in enumerate(gates) if g[0]=='CZC')
                    bad=gates[:drop]+gates[drop+1:];witness=None
                    for bits in range(1<<(2*n)):
                        state=bits|(1<<layout['flag'])
                        if simulate(bad,state)[1]:witness=bits;break
                    assert witness is not None,'Phase checker failed to detect an omitted correction'
                    negative.append({'family':family,'mutation':'omit first conditional CZ','witness_input':witness,'detected':True})
            metrics['complete_basis_tests']=tests
            metrics['all_measurement_records_symbolically_checked']=bool(mbu)
            row['models'][key]=metrics
    rows.append(row)
result={'status':'PASS','observed_utc':datetime.now(timezone.utc).isoformat(),'Python':platform.python_version(),'scope':'Finite supplied-flag controlled oracles. Original arithmetic DAG versus independent reconstruction of the described prefix traversal; not execution of upstream engine or a complete point adder. Identical Toffoli cost model, with measurement-based cleanup explicitly distinguished from unitary cleanup.','rows':rows,'negative_phase_controls':negative,'record_model':'Independent X-measurement outcomes; only conditional diagonal phase corrections. Exact phase bitmask covers every measurement record for each enumerated basis input.','excluded':'Depth-flag creation, data routing, register packing, complete walk, predicate death after later use, hardware error correction, physical time, upstream global gate counts and optimized resource superiority.','novelty_or_paper_score':None}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
