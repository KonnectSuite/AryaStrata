/** Verify saved model capabilities through the actual development adapter.
 * A loopback-only relay records effort fields, never headers or credentials.
 * Responses record tool fidelity and reasoning lengths, not reasoning text.
 */
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { join, resolve } from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';
import http from 'node:http';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>{if(v.startsWith('--'))a.push([v.slice(2),x[i+1]]);return a;},[]));
if(!args.config||!args['runtime-root']||!args.out)throw Error('--config, --runtime-root and --out required');
const cfg=JSON.parse(await readFile(args.config,'utf8'));const target=new URL(cfg.baseURL);
if(target.protocol!=='http:'||target.hostname!=='127.0.0.1')throw Error('Audit requires unauthenticated loopback HTTP');
const initial=await (await fetch(target.origin+'/health')).json();const wire=[];
const relay=http.createServer(async(req,res)=>{
  try{
    const chunks=[];for await(const chunk of req)chunks.push(chunk);const body=Buffer.concat(chunks);const parsed=JSON.parse(body.toString());
    wire.push({model:parsed.model,effort:parsed.reasoning_effort??parsed.reasoning?.effort??null,maxTokens:parsed.max_completion_tokens??parsed.max_tokens,templateKwargs:parsed.chat_template_kwargs??null});
    const upstream=await fetch(target.origin+req.url,{method:req.method,headers:{'Content-Type':'application/json'},body});
    res.writeHead(upstream.status,{'Content-Type':upstream.headers.get('content-type')??'application/json'});
    if(upstream.body)await pipeline(Readable.fromWeb(upstream.body),res);else res.end();
  }catch(e){if(!res.headersSent)res.writeHead(502);res.end(JSON.stringify({error:String(e)}));}
});
await new Promise(r=>relay.listen(0,'127.0.0.1',r));
const require=createRequire(join(resolve(args['runtime-root']),'package.json'));const load=n=>import(pathToFileURL(require.resolve(n)).href);
const {Context}=await load('@deepseek-ai/cordis');const Llm=await load('@deepseek-ai/dsh-llm');const Pi=await load('@deepseek-ai/dsh-llm-pi-ai');
const version=JSON.parse(await readFile(require.resolve('@deepseek-ai/dsh-llm-pi-ai/package.json'),'utf8')).version;
const models=cfg.models.map(m=>({...m,contextWindow:Number(m.contextWindow),maxTokens:Number(m.maxTokens)}));
process.env.ARYA_AUDIT_KEY='arya-local-placeholder';const ctx=new Context();const rows=[];let restored=false;
const tools=[{name:'read_file',description:'Read a fixture file',parameters:{type:'object',properties:{path:{type:'string'}},required:['path']}}];
async function save(){await writeFile(args.out,JSON.stringify({passed:rows.length===models.reduce((n,m)=>n+Object.keys(m.reasoningEfforts).length,0)&&rows.every(r=>r.passed)&&restored,adapterVersion:version,scope:'Saved development capability maps, actual SDK streaming/tool replay and observed loopback effort fields; not a desktop GUI or model-quality benchmark.',restored,results:rows},null,2));}
try{
  await ctx.plugin(Llm.default);await ctx.plugin(Pi,{providers:{strata:{apiKeyEnv:'ARYA_AUDIT_KEY',api:cfg.api,baseURL:`http://127.0.0.1:${relay.address().port}/v1`,outputBudgetMode:cfg.outputBudgetMode,timeoutMs:Number(cfg.timeoutMs||1200000),streamIdleTimeoutMs:Number(cfg.streamIdleTimeoutMs||1200000),models}}});
  for(const model of models)for(const mode of Object.keys(model.reasoningEfforts)){
    const start=performance.now();const wireStart=wire.length;
    try{
      async function assemble(messages){
        const a=new Llm.BlockAssembler();for await(const c of ctx.llm.stream({provider:'strata',model:model.id,messages,tools,maxTokens:4096,reasoningEffort:Llm.ReasoningEffortId(mode),signal:AbortSignal.timeout(360000)}))a.push(c);
        return {message:a.message({provider:'strata',model:model.id,...(a.replayState===undefined?{}:{replayState:a.replayState})}),finish:a.finish};
      }
      const messages=[Llm.createUserMessage({content:[{type:'text',text:`Connection audit ${model.id}-${mode}. Use read_file with the exact relative path build-info.txt, no directory prefix. Then report the exact build label returned by the tool. Do not guess.`}],source:{kind:'model',provider:'strata',model:model.id}})];
      const first=await assemble(messages);const call=first.message.content.find(b=>b.type==='tool-call');
      if(!call||call.name!=='read_file'||JSON.parse(call.arguments).path!=='build-info.txt')throw Error('Structured read_file failed: '+JSON.stringify(first.finish));
      const label=`ARYA-AUDIT-${rows.length}-${mode}`;
      const second=await assemble([...messages,first.message,Llm.createToolResultMessage({callId:Llm.ToolCallId(call.id),content:[{type:'text',text:`Build label: ${label}`}],isError:false})]);
      const answer=second.message.content.filter(b=>b.type==='text').map(b=>b.text).join('');
      const observed=wire.slice(wireStart);const expected=model.reasoningEfforts[mode];
      const reasoningChars=[first,second].reduce((n,r)=>n+r.message.content.filter(b=>b.type==='reasoning').reduce((s,b)=>s+String(b.text??b.content??'').length,0),0);
      const passed=answer.includes(label)&&observed.length===2&&observed.every(r=>r.model===model.id&&r.effort===expected);
      rows.push({model:model.id,mode,expectedWireEffort:expected,observed,toolReplayPassed:answer.includes(label),reasoningChars,passed,seconds:(performance.now()-start)/1000});
    }catch(e){rows.push({model:model.id,mode,passed:false,error:String(e),observed:wire.slice(wireStart)});}
    await save();console.log(model.id,mode,rows.at(-1).passed?'PASS':'FAIL');
  }
}finally{
  await ctx.fiber.dispose();await new Promise(r=>relay.close(r));
  try{
    const response=await fetch(target.origin+'/v1/chat/completions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:initial.model,messages:[{role:'user',content:'Reply READY.'}],max_tokens:512,temperature:0,reasoning_effort:initial.model.startsWith('lfm')?'high':'none'}),signal:AbortSignal.timeout(360000)});
    const data=await response.json();const health=await(await fetch(target.origin+'/health')).json();restored=response.ok&&health.model===initial.model&&health.loaded&&Boolean(data.choices?.[0]);
  }catch{}
  await save();
}
process.exitCode=rows.every(r=>r.passed)&&restored?0:1;
