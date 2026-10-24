"""Replay finite controls without changing frozen expected artifacts."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for entry in manifest['files']:
    path=(ROOT/entry['path']).resolve()
    assert path.is_relative_to(ROOT), 'Manifest path escapes project'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],entry['path']

def scientific(value):
    value=dict(value)
    for name in ['observed_utc','Python']:value.pop(name,None)
    return value

summary=[]
with tempfile.TemporaryDirectory(prefix='branch-replay-') as temporary:
    work=Path(temporary).resolve()
    assert work.is_relative_to(Path(tempfile.gettempdir()).resolve())
    assert work.name.startswith('branch-replay-')
    for program in ['branch_replay.py','anf_diagnostic.py','clean_decoder.py','compare_models.py']:
        shutil.copy2(ROOT/'src'/program,work/program)
        run=subprocess.run([sys.executable,'-B',str(work/program)],cwd=work,capture_output=True,text=True,encoding='utf-8',check=True)
        result=json.loads(run.stdout)
        expected=json.loads((ROOT/'results'/Path(program).with_suffix('.json')).read_text(encoding='utf-8'))
        assert scientific(result)==scientific(expected),program
        summary.append({'program':program,'status':result['status'] if 'status' in result else 'PASS'})
    generated=(work/'depth6-gates.json').read_bytes()
    assert generated==(ROOT/'results'/'depth6-gates.json').read_bytes()

print(json.dumps({'status':'PASS','manifest_entries':len(manifest['files']),'replays':summary,'depth6_gate_list_sha256':hashlib.sha256(generated).hexdigest(),'scope':'Frozen finite controls and specified reference oracle; no superiority, complete protocol, universal novelty or formal-proof claim.'},indent=2))
