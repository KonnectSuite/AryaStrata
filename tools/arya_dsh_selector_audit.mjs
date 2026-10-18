/** Check the installed roster's selector metadata without making model requests. */
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({ options: {
  config: { type: 'string' },
  'runtime-root': { type: 'string' },
  out: { type: 'string' },
} });
if (!values.config || !values['runtime-root'] || !values.out) {
  throw new Error('--config, --runtime-root and --out are required');
}
const config = JSON.parse(await readFile(values.config, 'utf8'));
const endpoint = new URL(config.baseURL);
if (endpoint.protocol !== 'http:' || endpoint.hostname !== '127.0.0.1') {
  throw new Error('Use the non-secret loopback provider export');
}
const require = createRequire(join(resolve(values['runtime-root']), 'package.json'));
const load = name => import(pathToFileURL(require.resolve(name)).href);
const { Context } = await load('@deepseek-ai/cordis');
const Llm = await load('@deepseek-ai/dsh-llm');
const Pi = await load('@deepseek-ai/dsh-llm-pi-ai');
const expected = new Map([
  ['qwen3.8-flash-next-iq3_xxs', 'graded'],
  ['qwen3.6-35b-a3b-ud-q4_k_xl', 'binary'],
  ['qwen3.6-35b-a3b-q8_0', 'binary'],
  ['minicpm-v-4.7-35b-a3b-q4_k_m', 'binary'],
  ['gemma-4-26b-a4b-ud-q4_k_m', 'binary'],
  ['lfm2.5-24b-a2b-ud-q4_k_xl', 'native'],
  ['ornith-1.5-35b-a3b-apex-i-quality', 'binary'],
  ['tiel-coder-35b-a3b-ud-q4_k_xl', 'graded'],
]);
const models = config.models.map(model => ({
  ...model, contextWindow: Number(model.contextWindow), maxTokens: Number(model.maxTokens),
}));
const ctx = new Context();
const results = [];
try {
  await ctx.plugin(Llm.default);
  await ctx.plugin(Pi, { providers: { strata: {
    api: config.api, baseURL: config.baseURL, models, reasoning: 'low',
  } } });
  for (const [model, kind] of expected) {
    const { reasoning } = await ctx.llm.resolveModelInfo('strata', model);
    const acceptedEfforts = reasoning?.efforts.map(effort => String(effort.id)) ?? [];
    const wanted = kind === 'native' ? ['low', 'medium', 'high'] : ['off', 'low', 'medium', 'high'];
    const singleMode = reasoning?.singleMode === true;
    results.push({
      model,
      passed: singleMode === (kind !== 'graded')
        && JSON.stringify(acceptedEfforts) === JSON.stringify(wanted),
      singleMode, acceptedEfforts,
      selector: kind === 'native' ? ['Native thinking']
        : kind === 'graded' ? ['Off', 'Low', 'Medium', 'High'] : ['Off', 'On'],
    });
  }
} finally {
  await ctx.fiber.dispose();
}
const report = {
  passed: results.length === expected.size && results.every(result => result.passed),
  scope: 'Actual development adapter capability metadata; browser acceptance tracked separately',
  results,
};
await writeFile(values.out, JSON.stringify(report, null, 2) + '\n');
console.log(`${results.filter(result => result.passed).length}/${expected.size} selector descriptors passed`);
process.exitCode = report.passed ? 0 : 1;
