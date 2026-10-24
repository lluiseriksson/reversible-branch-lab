"""Exact small Boolean-oracle diagnostic for a published divstep rule.
Not a circuit/resource superiority result, universal proof, or novel formula.
"""
import json,sys,platform
from pathlib import Path
from datetime import datetime,timezone
modulus=2**256-2**32-977
expected={2:3,3:3,4:11,5:26,6:79,7:268,8:1092}
rows=[]
for depth in range(2,11):
    n=depth-1;size=1<<(2*n);mask=(1<<n)-1
    values=[]
    for bits in range(size):
        f=1+2*(bits&mask);q=1+2*(bits>>n)
        values.append(((modulus*pow(f*q,-1,1<<depth))%(1<<depth))>>(depth-1))
    coeff=values[:]
    for variable in range(2*n):
        bit=1<<variable
        for subset in range(size):
            if subset&bit:coeff[subset]^=coeff[subset^bit]
    terms=[i for i,x in enumerate(coeff) if x]
    degree=max(x.bit_count() for x in terms)
    if depth in expected:assert len(terms)==expected[depth]
    # Reconstruct the entire truth table by applying the same involution.
    reconstructed=coeff[:]
    for variable in range(2*n):
        bit=1<<variable
        for subset in range(size):
            if subset&bit:reconstructed[subset]^=reconstructed[subset^bit]
    assert reconstructed==values
    rows.append({'depth':depth,'Boolean_inputs':size,'ANF_terms':len(terms),'algebraic_degree':degree,'agrees_with_prior_count':depth in expected,'truth_table_roundtrip':'PASS'})
result={'observed_utc':datetime.now(timezone.utc).isoformat(),'primary_source':'https://arxiv.org/html/2610.22367v1','scope':'Small exact oracle truth tables and their unique algebraic normal forms. Published A11 formula, published depth2..8 term counts. Depth9..10 are finite extensions, not an optimal circuit or new theorem. No phase/ancilla/gate/resource/novelty claim.','Python':platform.python_version(),'rows':rows,'next_falsifier':'Compare a complete clean decoder with the actual published factored circuit under identical controls and workspace. ANF term count is not a circuit lower bound.'}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
