"""Finite reproduction of prior branch decoding, not a new circuit or proof.

Primary source: Gu et al., arXiv:2610.22367v1, Appendix A, A2/A11.
Original implementation; only integer recurrence, not quantum gates.
"""
import json
from pathlib import Path

def valuation(n):
    assert n
    return (abs(n) & -abs(n)).bit_length()-1

counts={'inputs':0,'active_steps':0,'ambiguous_decisions':0,'max_steps':0}
for modulus in range(3,128,2):
    for w in range(modulus):
        counts['inputs']+=1
        state=(0,modulus,w,0,1)
        steps=0
        while state[2]:
            z,f,g,fv,gv=state
            b=g&1
            swap=(z>=0 and b==1)
            if swap:
                nxt=(-z,g,(g-f)//2,2*gv,gv-fv)
            else:
                nxt=(z+1,f,(g+b*f)//2,2*fv,gv+b*fv)
            zz,ff,gg,ffv,ggv=nxt
            assert ff*ggv-gg*ffv==modulus
            assert ff%2 and ggv%2 and ffv%2==0
            assert bool(ffv%4==2)==bool(swap)
            if not swap and z<0:
                j=valuation(ffv); q=ffv//(2**j)
                decoded=((ggv*pow(q,-1,2**j))%(2**j))>>(j-1)
                decoded2=((modulus*pow(ff*q,-1,2**j))%(2**j))>>(j-1)
                assert decoded==b==decoded2
                counts['ambiguous_decisions']+=1
            elif swap or gg==0:
                decoded=1
            else:
                assert zz>=1
                decoded=0
            if swap:
                oldgv=ffv//2
                restored=(-zz,ff-2*gg,ff,oldgv-ggv,oldgv)
            else:
                oldfv=ffv//2
                restored=(zz-1,ff,2*gg-decoded*ff,oldfv,ggv-decoded*oldfv)
            assert restored==state
            state=nxt;steps+=1;counts['active_steps']+=1
            assert steps<600, 'inconclusive: finite step cap hit'
        counts['max_steps']=max(counts['max_steps'],steps)

result={'status':'PASS','source':'https://arxiv.org/html/2610.22367v1#A1',
        'range':'Every odd modulus3..127 and every integer input0<=w<p',
        'checks':counts,'scope':'Finite integer recurrence and backward decoding only. Composite moduli included. No quantum gate, phase, ancilla, resource, confidence, universal-proof or new-discovery claim.',
        'implementation':'Original small reproduction of previously published formulas A2 and A11; no third-party program copied.'}
out=Path(__file__).with_suffix('.json')
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
