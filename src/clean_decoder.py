"""Original, deliberately simple clean-gate baseline for the prior A11 oracle.

X/CNOT/Toffoli only. Compute a Boolean DAG, copy its output, reverse the DAG.
All retained DAG nodes count as workspace. Not an optimized circuit or paper.
"""
import json,hashlib,platform
from pathlib import Path
from datetime import datetime,timezone

class DAG:
    def __init__(self,n):self.n=n;self.nodes=[];self.cache={}
    def band(self,a,b):
        if not a or not b:return 0
        if a==1:return b
        if b==1 or a==b:return a
        key=tuple(sorted((a,b)))
        if key not in self.cache:
            self.cache[key]=1<<(self.n+len(self.nodes)+1)
            self.nodes.append(key)
        return self.cache[key]
    def add(self,a,b,n):
        carry=0;out=[]
        for i in range(n):
            x=a[i]^b[i];out.append(x^carry)
            if i+1<n:carry=self.band(a[i],b[i])^self.band(x,carry)
        return out
    def neg(self,a,n):return self.add([x^1 for x in a],[1]+[0]*(n-1),n)
    def mul(self,a,b,n):
        out=[0]*n
        for shift,bv in enumerate(b):
            if not bv:continue
            lane=[0]*shift+[self.band(a[i],bv) for i in range(n-shift)]
            out=self.add(out,lane,n)
        return out
    def oracle(self,j,p):
        n=j-1
        f=[1]+[1<<(i+1) for i in range(n)]
        q=[1]+[1<<(n+i+1) for i in range(n)]
        u=self.mul(f,q,j)
        x=[1];precision=1
        while precision<j:
            new=min(2*precision,j);xp=x+[0]*(new-len(x))
            ax=self.mul(u[:new],xp,new)
            two=[0,1]+[0]*(new-2)
            correction=self.add(two,self.neg(ax,new),new)
            x=self.mul(xp,correction,new);precision=new
        pp=[(p>>i)&1 for i in range(j)]
        return self.mul(x,pp,j)[j-1]
    def evaluate(self,bits,out):
        state=(bits<<1)|1
        for i,(a,b) in enumerate(self.nodes):
            if (a&state).bit_count()%2 and (b&state).bit_count()%2:
                state|=1<<(self.n+i+1)
        return (state&out).bit_count()%2
    def prune(self,out):
        needed=set();todo=[i-self.n-1 for i in range(self.n+1,self.n+len(self.nodes)+1) if out>>i&1]
        while todo:
            index=todo.pop()
            if index in needed:continue
            needed.add(index)
            for signal in self.nodes[index]:
                todo.extend(i-self.n-1 for i in range(self.n+1,self.n+index+1) if signal>>i&1)
        mapping={i:i for i in range(self.n+1)};nodes=[]
        def remap(signal):
            result=0
            for i,new in mapping.items():
                if signal>>i&1:result^=1<<new
            return result
        for index in sorted(needed):
            nodes.append(tuple(remap(x) for x in self.nodes[index]))
            mapping[self.n+index+1]=self.n+len(nodes)
        self.nodes=nodes
        return remap(out)
    def gates(self,out):
        k=len(self.nodes);sa=self.n+k;sb=sa+1;target=sb+1;flag=target+1
        def prep(mask,scratch):
            gates=[]
            if mask&1:gates.append(['X',scratch])
            for index in range(1,self.n+k+1):
                if mask>>index&1:gates.append(['CX',index-1,scratch])
            return gates
        compute=[]
        for i,(a,b) in enumerate(self.nodes):
            pa=prep(a,sa);pb=prep(b,sb)
            compute+=pa+pb+[['CCX',sa,sb,self.n+i]]+pb[::-1]+pa[::-1]
        # The scratch register is free after compute: form the linear output
        # once, condition its copy, and erase it. Flagged XOR terms need no
        # separate Toffoli for each term.
        linear=prep(out,sa)
        copy=linear+[['CCX',flag,sa,target]]+linear[::-1]
        return compute+copy+compute[::-1],{'inputs':self.n,'retained_DAG_nodes':k,'scratch':2,'target':target,'flag':flag,'qubits':self.n+k+4}

def simulate(gates,state):
    for gate in gates:
        if gate[0]=='X':state^=1<<gate[1]
        elif gate[0]=='CX':
            if state>>gate[1]&1:state^=1<<gate[2]
        else:
            if state>>gate[1]&1 and state>>gate[2]&1:state^=1<<gate[3]
    return state

def run_reference():
    prime=2**256-2**32-977
    rows=[]
    for j in range(2,9):
        n=j-1;dag=DAG(2*n);out=dag.prune(dag.oracle(j,prime));gates,layout=dag.gates(out)
        for bits in range(1<<(2*n)):
            f=1+2*(bits&((1<<n)-1));q=1+2*(bits>>n)
            expected=((prime*pow(f*q,-1,1<<j))%(1<<j))>>(j-1)
            assert dag.evaluate(bits,out)==expected
        simulations=0
        if j==6:
            for bits in range(1<<(2*n)):
                answer=dag.evaluate(bits,out)
                for flag in (0,1):
                    for target in (0,1):
                        state=bits|(target<<layout['target'])|(flag<<layout['flag'])
                        expected=state^((answer&flag)<<layout['target'])
                        assert simulate(gates,state)==expected
                        simulations+=1
            packet={'depth':j,'layout':layout,'gates':gates,'claim':'Clean controlled oracle for the prior A11 function; primitive permutation gates have no relative phases. Workspace starts and ends zero. Not the complete divstep walk.'}
            Path(__file__).with_name('depth6-gates.json').write_text(json.dumps(packet,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
        rows.append({'depth':j,'oracle_inputs_checked':1<<(2*n),'DAG_AND_nodes':len(dag.nodes),'Toffoli_count':sum(g[0]=='CCX' for g in gates),'CNOT_count':sum(g[0]=='CX' for g in gates),'X_count':sum(g[0]=='X' for g in gates),'workspace_qubits':len(dag.nodes)+2,'total_qubits':layout['qubits'],'controlled_clean_gate_basis_tests':simulations,'gate_list_sha256':hashlib.sha256(json.dumps(gates,separators=(',',':')).encode()).hexdigest()})
    result={'observed_utc':datetime.now(timezone.utc).isoformat(),'Python':platform.python_version(),'status':'PASS','scope':'Original naive compute-copy-uncompute baseline for a published decision formula. All oracle inputs depth2..8 checked, full controlled gate action and zero-workspace return exhaustively checked at depth6. Gates are X/CNOT/Toffoli, so no hidden relative phase. This is not the published optimized circuit, complete inversion algorithm, hardware model or formal assistant proof.','rows':rows,'research_disposition':'No superiority established. Retaining all nonlinear nodes is expensive in workspace. A comparison with the actual factored baseline and a useful low-workspace schedule is still required; ANF term count is not an optimal-circuit bound.'}
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))

if __name__ == '__main__':
    run_reference()
