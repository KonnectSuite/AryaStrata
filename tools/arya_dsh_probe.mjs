/** Test the development DSH runtime's actual pi-ai adapter and block assembler.
 * This is a transport/tool-replay check, not a desktop-session acceptance test.
 * Uses a public placeholder key against the unauthenticated loopback engine;
 * never reads desktop cookies, credentials, or account state.
 */
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { resolve, join } from 'node:path';
import { readFile, writeFile } from 'node:fs/promises';

const args = Object.fromEntries(process.argv.slice(2).reduce((out, value, index, all) => {
  if (value.startsWith('--')) out.push([value.slice(2), all[index + 1]]);
  return out;
}, []));
if (!args['runtime-root'] || !args.out) throw Error('--runtime-root and --out are required');
const require = createRequire(join(resolve(args['runtime-root']), 'package.json'));
const load = name => import(pathToFileURL(require.resolve(name)).href);
const { Context } = await load('@deepseek-ai/cordis');
const Llm = await load('@deepseek-ai/dsh-llm');
const Pi = await load('@deepseek-ai/dsh-llm-pi-ai');
const version = JSON.parse(await readFile(require.resolve('@deepseek-ai/dsh-llm-pi-ai/package.json'), 'utf8')).version;
process.env.ARYA_BENCH_LOCAL_KEY = 'arya-local-placeholder';
const model = args.model || 'qwen3.8-flash-next-iq3_xxs';
// LFM2.5 always reasons. These UI levels explicitly alias its native mode;
// don't advertise an off mode or pretend this measures distinct effort levels.
const nativeLfm = args['native-lfm'] === 'yes';
const maxTokens = Number(args['max-tokens'] || 512);
const ctx = new Context();
const rows = [];
try {
  await ctx.plugin(Llm.default);
  await ctx.plugin(Pi, { providers: { strata: {
    apiKeyEnv: 'ARYA_BENCH_LOCAL_KEY', api: 'openai-completions', outputBudgetMode: 'gateway',
    baseURL: args.url || 'http://127.0.0.1:8080/v1',
    models: [{ id: model, contextWindow: Number(args.context || 262144), maxTokens: 8192, input: args.input === 'text' ? ['text'] : ['text', 'image'],
      reasoningEfforts: nativeLfm ? { low: 'high', medium: 'high', high: 'high' } : args.input === 'text' ? false : { off: 'none', low: 'low', medium: 'medium', high: 'high' } }],
  } } });
  const tools = [{ name: 'read_file', description: 'Read a file from the fixture workspace',
    parameters: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'] } }];
  async function assemble(messages) {
    const assembler = new Llm.BlockAssembler();
    const start = performance.now();
    for await (const chunk of ctx.llm.stream({ provider: 'strata', model, messages, tools,
      maxTokens, reasoningEffort: Llm.ReasoningEffortId(nativeLfm ? 'low' : 'off'),
      signal: AbortSignal.timeout(240000) })) assembler.push(chunk);
    return { message: assembler.message({ provider: 'strata', model,
      ...(assembler.replayState === undefined ? {} : { replayState: assembler.replayState }) }),
      finish: assembler.finish, usage: assembler.usage, seconds: (performance.now() - start) / 1000 };
  }
  for (let run = 0; run < Number(args.runs || 3); run++) {
    try {
      const messages = [Llm.createUserMessage({ content: [{ type: 'text', text:
        `Trial ${run}: use read_file to read build-info.txt, then report the exact build label returned by the tool. Do not guess.`
          + (nativeLfm ? ' The path argument must be the exact relative string build-info.txt, with no directory prefix.' : '') }],
        source: { kind: 'model', provider: 'strata', model } })];
      const first = await assemble(messages);
      const call = first.message.content.find(block => block.type === 'tool-call');
      if (!call || call.name !== 'read_file' || JSON.parse(call.arguments).path !== 'build-info.txt') {
        rows.push({ run, passed: false, first, error: 'Expected structured read_file call' });
      } else {
        const label = `ARYA-QWEN-${args.context || 262144}-${run}`;
        const second = await assemble([...messages, first.message, Llm.createToolResultMessage({
          callId: Llm.ToolCallId(call.id), content: [{ type: 'text', text: `Build label: ${label}` }], isError: false,
        })]);
        const text = second.message.content.filter(block => block.type === 'text').map(block => block.text).join('');
        rows.push({ run, passed: text.includes(label), first, second });
      }
    } catch (error) {
      rows.push({ run, passed: false, error: String(error) });
    }
    await writeFile(args.out, JSON.stringify({ model, contextWindow: Number(args.context || 262144), adapterVersion: version, maxTokens, nativeLfm, scope: 'DSH pi-ai adapter, streaming assembly and tool-result replay', results: rows }, null, 2));
    console.log('DSH adapter trial', run, rows.at(-1).passed ? 'PASS' : 'FAIL');
  }
} finally {
  await ctx.fiber.dispose();
}
process.exitCode = rows.length && rows.every(row => row.passed) ? 0 : 1;
