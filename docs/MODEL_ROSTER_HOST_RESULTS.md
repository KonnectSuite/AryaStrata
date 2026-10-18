# Additional model host validation — October 18, 2026

Measured on the i9-14900KF, RTX 4070 Ti SUPER 16 GB, 64 GB DDR5-6000, Windows 11 host with NVIDIA driver 610.88. AryaStrata is a fork of PolyStrata (VecSzn), which is a fork of original Strata (Niko1221). See [credits](../CREDITS.md).

## Coding and integration checks

Counts are bounded fixtures, not a general coding-quality score. Coding uses six Python fixtures repeated three times per reasoning mode. Vision uses four synthetic fixtures repeated three times. Recall uses three deployment facts in repeated source excerpts. Long-agent uses three different coding fixtures with a shared long prefix; later tasks may reuse it. DSH checks cover streaming assembly and tool-result replay through the development adapter, not full desktop acceptance.

| Model ID | Context capacity | Vision | Threads | Coding off | Coding low | Images | Recall | Long code | DSH |
|---|---:|---|---:|---|---|---|---|---|---|
| `minicpm-v-4.7-35b-a3b-q4_k_m` | 262,144 | GPU | 15 | 16/18 | 18/18 | 12/12 | 6/6 | 3/3; image IDs 3/3 (low) | 3/3 |

MiniCPM coding counts come from `minicpmv/corrected/`: the original validator rejected normal set and dictionary methods. Original coding records and the restricted validator are retained for audit. Vision, recall, tuning and adapter records were unaffected. The remaining models use the corrected validator from their first measured run. Historical Qwen counts used the older stricter validator; no direct cross-model quality ranking is inferred.

## Retained engine settings

All profiles use one request slot, a 768 MiB VRAM reserve, whole-cache allocation and no tail skipping. Temperature was zero in the benchmark requests. Existing app-wide sampling and thinking preferences were preserved.

| Model | CPU threads | Window | Prompt batch | KV format |
|---|---:|---|---:|---|
| minicpmv | 15 | no draft block | 512 | q8_0 |

## Measured long-input performance

Vision was enabled for vision-capable families throughout these text recall trials. Actual input length is distinct from allocated capacity. Output and tool turns must fit within that capacity.

| Model | Actual input, median tokens | Prefill tok/s | First token, s | Decode tok/s | Recall |
|---|---:|---:|---:|---:|---|
| minicpmv | 131031 | 1379.6 | 95.1 | 54.2 | 3/3 |
| minicpmv | 254191 | 960.1 | 265.0 | 34.6 | 3/3 |

## Coding latency and memory

Times include tool loops. RAM covers the whole PC; resource peaks span tuning and validation. Paging and accuracy relative to uncompressed KV were not measured.

| Model | Coding off, median s | Coding low, median s | Peak RAM, GiB | Least available RAM, GiB | Peak GPU, MiB |
|---|---:|---:|---:|---:|---:|
| minicpmv | 3.61 | 5.82 | 55.54 | 8.28 | 15988 |

## Tuning and reproducibility

CPU threads 8, 15 and 20 were compared using two runs of three short coding prompts, up to 384 output tokens each. Window sweeps, where present in the completed records, compare 1, 4 and 8 with the best exploratory thread count; MiniCPM has no draft block and its sweep only varied threads. Candidate selection was followed by baseline/candidate/candidate/baseline confirmations. A candidate needed over 2% median gain and both paired runs faster. Expert placement remains adaptive across sequential runs, so cache history is a limitation; this does not establish a universal optimum. Prompt batch and sampling settings were held fixed in these sweeps. No tail layers were skipped.

Qwen-architecture families use Q8_0 KV and whole-cache allocation at 262,144 capacity. Gemma and LFM use FP16 KV; Q8_0 KV is not supported for those architectures by this engine. LFM is text-only at its documented 131,072-token context. Weight precision and KV precision are separate settings.

[Raw results and exact profiles](../bench/results/2026-10-18-model-roster/summary.json). Model fingerprints, engine build, per-call responses, tool traces, images, tuning confirmations and five-second resource samples accompany the summary. Exact benchmark tools are archived in `tool-snapshots/`.

With the selected profile loaded on `127.0.0.1:8080`, reproduce the vision-capable checks from the repository root:

```powershell
.\.venv\Scripts\python.exe tools/arya_agent_bench.py --model <model-id> --suite all --think low --runs 3 --out agent-low.json
.\.venv\Scripts\python.exe tools/arya_vision_bench.py --model <model-id> --runs 3 --out vision
.\.venv\Scripts\python.exe tools/arya_context_bench.py --tokenizer <profile-tokenizer-directory> --lengths 131072,253952 --runs 3 --out context.json
.\.venv\Scripts\python.exe tools/arya_long_agent_bench.py --model <model-id> --tokenizer <profile-tokenizer-directory> --context 262144 --tokens 229376 --think low --runs 1 --out long-agent
```

Repeat the short coding command with `--think none` for off-mode results. Use the recorded long-agent reasoning mode when reproducing that run. For text-only LFM, omit the vision command, use recall lengths `65536,122880`, and give the long-agent command `--context 131072 --tokens 106496 --think none --text-only`. Keep output directories distinct between modes. Context and long-agent tools support `--resume` for matching saved trials.

Do not infer full real-repository coding quality, natural-image accuracy, multi-user performance or quantization superiority from these bounded checks. Failures are retained in the raw reports.
