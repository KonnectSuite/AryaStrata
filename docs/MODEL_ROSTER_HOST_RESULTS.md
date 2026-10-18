# Additional model host validation — October 18, 2026

Measured on the i9-14900KF, RTX 4070 Ti SUPER 16 GB, 64 GB DDR5-6000, Windows 11 host with NVIDIA driver 610.88. AryaStrata is a fork of PolyStrata (VecSzn), which is a fork of original Strata (Niko1221). See [credits](../CREDITS.md).

## Coding and integration checks

Counts are bounded fixtures, not a general coding-quality score. Coding uses six Python fixtures repeated three times per reasoning mode. Vision uses four synthetic fixtures repeated three times. Recall uses three deployment facts in repeated source excerpts. Long-agent uses three different coding fixtures with a shared long prefix; later tasks may reuse it. DSH checks cover streaming assembly and tool-result replay through the development adapter, not full desktop acceptance.

Standard coding requests allowed **1,400 output tokens per call, including reasoning**, and up to nine model turns per session. Larger-budget probes are reported separately.

| Model / quant | Context capacity | Vision | Threads | Coding off | Coding low | Images | Recall | Long code | DSH |
|---|---:|---|---:|---|---|---|---|---|---|
| MiniCPM-V 4.7 35B-A3B `Q4_K_M` | 262,144 | GPU | 15 | 16/18 | 18/18 | 12/12 | 6/6 | 3/3; image IDs 3/3 (low) | 3/3 |
| Gemma 4 26B-A4B `UD-Q4_K_M` | 262,144 | GPU | 15 | 16/18 | 13/18 | 12/12 | 6/6 | 2/3; image IDs 2/3 (none) | 3/3 |
| LFM2.5-24B-A2B `UD-Q4_K_XL` | 131,072 | text only | 15 | 0/18 | not run | not run | 0/6 | 0/3 (none) | 0/3 |
| Ornith 1.5 35B-A3B `APEX-I-QUALITY` | 262,144 | GPU | 15 | 16/18 | 18/18 | 12/12 | 6/6 | 3/3; image IDs 3/3 (low) | 3/3 |
| Tiel Coder 35B-A3B `UD-Q4_K_XL` | 262,144 | GPU | 15 | 16/18 | 18/18 | 8/12 | 6/6 | 3/3; image IDs 3/3 (low) | 3/3 |

MiniCPM coding counts come from `minicpmv/corrected/`: the original validator rejected normal set and dictionary methods. Original coding records and the restricted validator are retained for audit. Vision, recall, tuning and adapter records were unaffected. The remaining models use the corrected validator from their first measured run. Historical Qwen counts used the older stricter validator; no direct cross-model quality ranking is inferred.

**The LFM row above is the initial forced-off diagnostic, not its recommended deployment.** LFM2.5 always reasons; its corrected native-thinking coding, recall and DSH qualification is reported separately below, with a 4,096-token allowance. The initial adapter failures occurred before inference.

### Larger coding-output budget

These additional runs keep the same weights, engine settings, fixtures and tools. Increasing the output limit gives reasoning room to finish; compare both pass counts and complete-session latency. Original 1,400-token records above remain the fixed-budget comparison.

| Model | Reasoning | Output limit per call | Short coding | Median session, s | Long code | Image IDs reported |
|---|---|---:|---|---:|---|---|
| Gemma 4 26B-A4B | low | 4096 | 18/18 | 31.29 | 2/3 | 2/3 |

For short coding fixtures like these, use **Gemma 4 26B-A4B low reasoning with at least 4,096 output tokens per call**. The development app advertises 8,192 within the total context. This is a measured short-fixture recommendation, not a general quality ranking or proof of reliable full-context coding.


The larger allowance did not eliminate the long-context failure. Keep the failed response and missing image ID in view; MiniCPM and Ornith completed all three long coding/image fixtures, while Tiel completed those fixtures but missed build IDs in the separate short image suite.


| Larger-budget long fixture | First-call input | Cached input | Session, s | Code/tool checks | Image ID |
|---|---:|---:|---:|---|---|
| Gemma 4 26B-A4B: trim_history | 229844 | 0 | 311.67 | fail | no |
| Gemma 4 26B-A4B: merge_tool_results | 229859 | 208896 | 156.26 | pass | yes |
| Gemma 4 26B-A4B: summarize_usage | 229841 | 208896 | 134.05 | pass | yes |

### LFM native-thinking deployment correction

[Liquid AI documents LFM2.5-24B-A2B as an always-reasoning model](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B). The initial forced-off coding and recall records above are diagnostics, not the recommended deployment. The initial DSH text-only declaration incorrectly marked it non-reasoning; all three calls were rejected before inference with `UNSUPPORTED_REASONING_EFFORT`.

The deployment probe in `lfm25/prompt-tuned/` uses native thinking, 4,096 output tokens per call, and explicit fixture-path/tool-order instructions. These changes were combined; improved counts cannot be attributed to any one change or compared as equal-budget model rankings. The tool validator and engine were unchanged. Recall replays exactly the same hashed prompts with native thinking and the larger output budget.

| Native-thinking check | Passed |
|---|---|
| coding | 18/18 |
| recall | 2/6 |
| long | 0/3 |
| dsh | 3/3 |

**Do not choose this LFM profile for large-context coding agents based on these tests.** It can allocate and execute at native capacity, but the measured recall and long tool-task failures remain. Short coding success does not qualify long-context reliability; use MiniCPM or Ornith for the full-context coding/image workload validated in this batch.

The AryaAI low/medium/high UI choices explicitly alias the same native mode (`high` on the wire); distinct effort levels were not measured. Off is not offered. Text-only means no image input, not no reasoning. Use at least the measured 4,096-token output allowance for similar work; the app advertises up to 8,192 within total context. The exact system suffix is recorded in the probe protocol. First-token times include the first reasoning token when emitted, not completion of the JSON answer; complete coding-session times include the tool loop.

| Actual input tokens | Prefill tok/s | First token, s | Decode tok/s | Recall |
|---:|---:|---:|---:|---|
| 65,228 | 7124.2 | 9.2 | 131.3 | 1/3 |
| 122,618 | 5790.1 | 21.3 | 101.5 | 1/3 |

| Native-thinking long fixture | First-call input | Cached input | Session, s | Code/tool checks |
|---|---:|---:|---:|---|
| trim_history | 107056 | 0 | 52.94 | fail |
| merge_tool_results | 107074 | 73728 | 44.98 | fail |
| summarize_usage | 107054 | 73728 | 45.53 | fail |

## Observed limits

Tiel missed the build ID in four of twelve synthetic image trials: it transcribed `ARYA-5907` as `ARYA-507` or `ARYA-5007`. Vision input works, but these records do not support perfect screenshot transcription. Its reasoning-off history-trimming failures were incorrect code, while low reasoning passed the short coding fixtures.

Gemma low reasoning passed 13/18 standard-budget coding sessions, versus 16/18 off. Some low-mode calls exhausted the 1,400-token allowance before writing a patch; the separate 4,096-token probe tests that constraint. The initial Gemma long-input tools failed before inference because they assumed text merges; the repaired tools use the server tokenizer loader and preserve the original diagnostic logs.

MiniCPM, Ornith and Tiel use low reasoning for this style of coding; Gemma recommendations depend on the separately reported output-budget probe. LFM is text-only and uses native thinking; its initial forced-off records are not its deployment qualification. None of these fixture counts establishes broad repository-level coding quality.

## AryaAI model IDs

The selected quants are Q4 variants or higher: Ornith APEX-I-QUALITY mixes 4-, 5- and 6-bit expert weights. Other weight quants were not compared in this batch.

| Model | Exact local model ID |
|---|---|
| MiniCPM-V 4.7 35B-A3B | `minicpm-v-4.7-35b-a3b-q4_k_m` |
| Gemma 4 26B-A4B | `gemma-4-26b-a4b-ud-q4_k_m` |
| LFM2.5-24B-A2B | `lfm2.5-24b-a2b-ud-q4_k_xl` |
| Ornith 1.5 35B-A3B | `ornith-1.5-35b-a3b-apex-i-quality` |
| Tiel Coder 35B-A3B | `tiel-coder-35b-a3b-ud-q4_k_xl` |

## Retained engine settings

All profiles use one request slot, a 768 MiB VRAM reserve, whole-cache allocation and no tail skipping. Temperature was zero in the benchmark requests. Existing app-wide sampling and thinking preferences were preserved. The local provider request and stream-idle timeouts are 20 minutes; configuration was accepted by the actual development adapter.

| Model | CPU threads | Window | Prompt batch | KV format |
|---|---:|---|---:|---|
| minicpmv | 15 | no draft block | 512 | q8_0 |
| gemma4 | 15 | 8 | 1024 | fp16 |
| lfm25 | 15 | 1 | 2048 | fp16 |
| ornith | 15 | 8 | 512 | q8_0 |
| tiel | 15 | 8 | 512 | q8_0 |

## Measured long-input performance

Vision was enabled for vision-capable families throughout these text recall trials. Actual input length is distinct from allocated capacity. Output and tool turns must fit within that capacity.

| Model | Actual input, median tokens | Prefill tok/s | First token, s | Decode tok/s | Recall |
|---|---:|---:|---:|---:|---|
| minicpmv | 131,031 | 1379.6 | 95.1 | 54.2 | 3/3 |
| minicpmv | 254,191 | 960.1 | 265.0 | 34.6 | 3/3 |
| gemma4 | 130,710 | 2509.0 | 52.1 | 82.9 | 3/3 |
| gemma4 | 253,589 | 1692.8 | 149.9 | 54.8 | 3/3 |
| lfm25 | 65,229 | 6824.7 | 9.6 | 124.1 | 0/3 |
| lfm25 | 122,619 | 5598.1 | 22.0 | 99.9 | 0/3 |
| ornith | 131,031 | 1476.9 | 88.8 | 58.5 | 3/3 |
| ornith | 254,191 | 1032.5 | 246.4 | 42.2 | 3/3 |
| tiel | 131,209 | 1480.8 | 88.7 | 74.2 | 3/3 |
| tiel | 254,369 | 1047.7 | 243.0 | 49.2 | 3/3 |

## Combined long-context agent sessions

Each row is a different bounded task, not a repetition of one task. Cache reuse is reported from the first call of each session. Keep cold processing and later reused prefixes separate when judging agent latency. Image-ID reporting is separate from code/tool success.

| Model | Reasoning | Fixture | First-call input | Cached input | Session, s | Agent checks | Image ID reported |
|---|---|---|---:|---:|---:|---|---|
| minicpmv | low | trim_history | 230715 | 0 | 369.55 | pass | yes |
| minicpmv | low | merge_tool_results | 230729 | 208896 | 80.34 | pass | yes |
| minicpmv | low | summarize_usage | 230712 | 208896 | 92.07 | pass | yes |
| gemma4 | none | trim_history | 229846 | 0 | 280.26 | fail | no |
| gemma4 | none | merge_tool_results | 229861 | 208896 | 45.96 | pass | yes |
| gemma4 | none | summarize_usage | 229843 | 208896 | 65.93 | pass | yes |
| lfm25 | none | trim_history | 106955 | 0 | 27.70 | fail | not applicable |
| lfm25 | none | merge_tool_results | 106973 | 73728 | 49.34 | fail | not applicable |
| lfm25 | none | summarize_usage | 106953 | 73728 | 18.29 | fail | not applicable |
| ornith | low | trim_history | 230825 | 0 | 528.11 | pass | yes |
| ornith | low | merge_tool_results | 230839 | 208896 | 86.44 | pass | yes |
| ornith | low | summarize_usage | 230822 | 208896 | 83.83 | pass | yes |
| tiel | low | trim_history | 231137 | 0 | 452.29 | pass | yes |
| tiel | low | merge_tool_results | 231151 | 208896 | 65.76 | pass | yes |
| tiel | low | summarize_usage | 231134 | 208896 | 79.29 | pass | yes |

## Coding latency and memory

Times include tool loops. RAM covers the whole PC; resource peaks span tuning and validation, including superseded validator runs for MiniCPM. Paging and accuracy relative to uncompressed KV were not measured.

| Model | Coding off, median s | Coding low, median s | Peak RAM, GiB | Least available RAM, GiB | Peak GPU, MiB |
|---|---:|---:|---:|---:|---:|
| minicpmv | 3.61 | 5.82 | 55.54 | 8.28 | 15988 |
| gemma4 | 10.48 | 15.71 | 41.70 | 22.11 | 15984 |
| lfm25 | 1.36 | not run | 36.84 | 26.98 | 15236 |
| ornith | 4.21 | 8.20 | 45.93 | 17.88 | 15757 |
| tiel | 3.37 | 4.39 | 44.52 | 19.30 | 15815 |

## Tuning and reproducibility

CPU threads 8, 15 and 20 were compared using two runs of three short coding prompts, up to 384 output tokens each. Window sweeps, where present in the completed records, compare 1, 4 and 8 with the best exploratory thread count; MiniCPM has no draft block and its sweep only varied threads. Candidate selection was followed by baseline/candidate/candidate/baseline confirmations. A candidate needed over 2% median gain and both paired runs faster. Expert placement remains adaptive across sequential runs, so cache history is a limitation; this does not establish a universal optimum. Prompt batch and sampling settings were held fixed in these sweeps. No tail layers were skipped.

### Short-prompt tuning confirmations

These are medians from the paired short-prompt confirmations, not decode rates after a full input. Only LFM retained a candidate change: window 1 instead of 8. MiniCPM baseline and candidate both used 15 threads.

| Model | Baseline tok/s | Candidate tok/s | Retained candidate |
|---|---:|---:|---|
| MiniCPM-V 4.7 35B-A3B | 137.3 | 138.3 | no |
| Gemma 4 26B-A4B | 148.0 | 144.2 | no |
| LFM2.5-24B-A2B | 194.9 | 201.9 | yes |
| Ornith 1.5 35B-A3B | 125.8 | 125.9 | no |
| Tiel Coder 35B-A3B | 150.2 | 150.4 | no |

Qwen-architecture families use Q8_0 KV and whole-cache allocation at 262,144 capacity. Gemma and LFM use FP16 KV; Q8_0 KV is not supported for those architectures by this engine. LFM is text-only at its documented 131,072-token context. Weight precision and KV precision are separate settings.

[Raw results and exact profiles](../bench/results/2026-10-18-model-roster/summary.json). Model fingerprints, engine build, per-call responses, tool traces, images, tuning confirmations and five-second resource samples accompany the summary. Exact benchmark tools are archived in `tool-snapshots/`.

With the selected profile loaded on `127.0.0.1:8080`, reproduce the vision-capable checks from the repository root:

```powershell
.\.venv\Scripts\python.exe tools/arya_agent_bench.py --model <model-id> --suite all --think low --runs 3 --out agent-low.json
.\.venv\Scripts\python.exe tools/arya_vision_bench.py --model <model-id> --runs 3 --out vision
.\.venv\Scripts\python.exe tools/arya_context_bench.py --tokenizer <profile-tokenizer-directory> --lengths 131072,253952 --runs 3 --out context.json
.\.venv\Scripts\python.exe tools/arya_long_agent_bench.py --model <model-id> --tokenizer <profile-tokenizer-directory> --context 262144 --tokens 229376 --think low --runs 1 --out long-agent
```

Repeat the short coding command with `--think none` for off-mode results. Use the recorded long-agent reasoning mode when reproducing that run. To reproduce only the initial failed forced-off LFM diagnostics, omit the vision command, use recall lengths `65536,122880`, and give the long-agent command `--context 131072 --tokens 106496 --think none --text-only`. The corrected deployment probes use the archived `gemma_budget4096_probe.py.txt` and `lfm_native_deployment_probe.py.txt` sources with the recorded request fields, exact system suffix and selected profiles. The LFM adapter probe can be repeated with `tools/arya_dsh_probe.mjs --input text --native-lfm yes --max-tokens 4096`, plus its runtime root, model ID, context and output-path arguments. Keep output directories distinct between modes. Context and long-agent tools support `--resume` for matching saved trials.

Do not infer full real-repository coding quality, natural-image accuracy, multi-user performance or quantization superiority from these bounded checks. Failures are retained in the raw reports.

## Live service readiness

The normal loopback service discovered all eight installed profiles. Sequential
switch-on-request smoke checks returned `READY` for all five models in this
batch and then Qwen3.6 Q4. Each loaded the recorded native capacity; image
capability was enabled for the four vision families and absent for LFM.
Qwen3.6 Q4 was restored as the final active model. These short routing checks
are not speed measurements or desktop GUI acceptance tests.

See [the service record](../bench/results/2026-10-18-model-roster/service-readiness.json).
The benchmark tokenizer/validator regression checks passed all 13 tests, the
repository branding check passed, and all 19 original README image lines and
nine supported model-family rows were preserved. All 11 staged current and
historical benchmark-tool archives matched their recorded SHA-256 fingerprints.
