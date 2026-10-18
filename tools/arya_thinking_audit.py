"""Audit installed model thinking controls through the actual server renderer, without GPU inference."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from strata_tokenizer import Tokenizer
from serve.frontend import ChatTemplate,effort_kwargs
from serve.server import MockEngine,Service

def audit(root):
    rows=[]
    for profile in sorted(root.glob('strata-*.json')):
        cfg=json.loads(profile.read_text(encoding='utf-8-sig'));identity=cfg['model_name']
        folder=Path(cfg['tokenizer']);template=folder/'chat_template.jinja';tok=Tokenizer.from_dir(folder)
        svc=Service(MockEngine(tok,'READY'),tok,ChatTemplate(template),model_name=identity)
        distinct=identity.startswith(('qwen3.8-','tiel-'));native=identity.startswith('lfm')
        modes=({'off':'none'} if not native else {})|({'low':'low','medium':'medium','high':'high'} if distinct else {'low':'high','medium':'high','high':'high'})
        cases=[]
        for tools in [None,[{'name':'read_file','description':'Read a fixture','parameters':{'type':'object','properties':{'path':{'type':'string'}},'required':['path']}}]]:
            messages=[{'role':'user','content':'Reply READY.'}]
            prompts={level:svc.render_prompt(messages,tools,effort_kwargs(level)) for level in ['none','low','medium','high']}
            hashes={k:hashlib.sha256(v.encode()).hexdigest() for k,v in prompts.items()}
            if distinct:assert len({hashes[k] for k in ['low','medium','high']})==3,(identity,'effort levels render identically')
            else:assert len({hashes[k] for k in ['low','medium','high']})==1,(identity,'unexpected distinct effort controls')
            if not native:assert hashes['none']!=hashes['high'],(identity,'thinking off does not change the prompt')
            if native:assert prompts['high'].endswith('<think>'),identity
            cases.append({'tools':bool(tools),'raw_wire_prompt_sha256':hashes,'on_modes_distinct':distinct,'advertised_mode_to_wire':modes})
        rows.append({'model':identity,'template_sha256':hashlib.sha256(template.read_bytes()).hexdigest(),'capability':'distinct efforts' if distinct else 'native thinking only' if native else 'thinking off/on; effort labels alias on','cases':cases,'passed':True})
        print(identity,rows[-1]['capability'],flush=True)
    assert len(rows)==8,len(rows)
    return {'passed':True,'scope':'Actual installed tokenizers/templates and Service.render_prompt, with and without tools. This verifies controls and aliasing, not model quality or a guarantee of visible reasoning on every reply.','results':rows}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(audit(a.root),indent=2),encoding='utf-8')
