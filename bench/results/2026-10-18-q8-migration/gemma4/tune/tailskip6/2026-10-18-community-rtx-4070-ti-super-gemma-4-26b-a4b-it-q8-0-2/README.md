# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit 4820a00e; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: gemma-4-26b-a4b-it-q8-0
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata-poly.exe --model gemma-4-26B-A4B-it-Q8_0.gguf --max-context 262144 --expert-profile expert-profile.txt --draft-model mtp-gemma-4-26B-A4B-it-Q8_0.gguf --conversation-cache-mib 8192 --threads 15 --prompt-batch 1024 --vram-reserve-mib 768 --tail-skip 6 --window 8 --kv-whole
```

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a AryaStrata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 48 (45-53) | 0 | 100 (100-100) | 9 | not measured | 87.4 (73.9-105.8) | 0.38 (0.35-0.40) |
| 4K prompt, fresh | 4101 (4101-4101) | 0 (0-0) | 24 cap | 3 | 1752.0 (1749.8-1768.3) | not measured | 2.36 (2.35-2.37) |
| 16K prompt, fresh | 16390 (16390-16390) | 0 (0-0) | 24 cap | 3 | 3428.2 (3406.1-3459.0) | not measured | 4.82 (4.81-4.93) |
| agent session, follow-up turns | 15505 (15501-15530) at the last turn | see below | up to 64 | 3 | see below | 85.9 (67.5-96.9) | 2.34 (2.08-2.60) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 67.5 % (67.5-67.5); earlier-turn tokens read again per session: 247 (243-272) (earlier turns that the cache did not hold; the 14897 (14897-14897) new tokens of the files are read once); first turn (nothing cached) first token: 0.65 s (0.64-0.77).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 396 | 0 | 396 | 530.4 | 0.769 | 91.9 |
| 1 | 3822 | 389 | 3433 | 1523.3 | 2.275 | 86.9 |
| 2 | 5658 | 3815 | 1843 | 870.1 | 2.134 | 67.5 |
| 3 | 9290 | 5651 | 3639 | 1422.0 | 2.602 | 79.8 |
| 4 | 12352 | 9283 | 3069 | 1294.9 | 2.401 | 84.1 |
| 5 | 15530 | 12345 | 3185 | 1353.1 | 2.373 | 77.7 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 89 s.
