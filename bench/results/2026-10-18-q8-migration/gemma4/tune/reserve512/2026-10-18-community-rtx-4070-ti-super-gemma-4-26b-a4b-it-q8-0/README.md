# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 1 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

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
strata-poly.exe --model gemma-4-26B-A4B-it-Q8_0.gguf --max-context 262144 --expert-profile expert-profile.txt --draft-model mtp-gemma-4-26B-A4B-it-Q8_0.gguf --conversation-cache-mib 8192 --threads 15 --prompt-batch 1024 --vram-reserve-mib 512 --tail-skip 0 --window 8 --kv-whole
```

## Method

Run by `python tools/strata_bench.py --runs 1` against the HTTP API of a AryaStrata server (started by the benchmark from the install configuration); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 1 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 1 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 1 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 48 (45-53) | 0 | 100 (100-100) | 3 | not measured | 56.2 (51.7-82.9) | 0.39 (0.37-0.40) |
| 4K prompt, fresh | 4101 (4101-4101) | 0 (0-0) | 24 cap | 1 | 1747.3 (1747.3-1747.3) | not measured | 2.38 (2.38-2.38) |
| 16K prompt, fresh | 16390 (16390-16390) | 0 (0-0) | 24 cap | 1 | 3469.9 (3469.9-3469.9) | not measured | 4.95 (4.95-4.95) |
| agent session, follow-up turns | 15528 (15528-15528) at the last turn | see below | up to 64 | 1 | see below | 66.6 (56.6-71.8) | 2.37 (2.11-2.52) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 67.5 % (67.5-67.5); earlier-turn tokens read again per session: 270 (270-270) (earlier turns that the cache did not hold; the 14897 (14897-14897) new tokens of the files are read once); first turn (nothing cached) first token: 0.77 s (0.77-0.77).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 396 | 0 | 396 | 523.7 | 0.774 | 56.4 |
| 1 | 3822 | 389 | 3433 | 1495.3 | 2.317 | 56.6 |
| 2 | 5658 | 3815 | 1843 | 886.8 | 2.106 | 60.4 |
| 3 | 9290 | 5651 | 3639 | 1451.4 | 2.524 | 66.6 |
| 4 | 12351 | 9283 | 3068 | 1311.8 | 2.371 | 70.1 |
| 5 | 15528 | 12344 | 3184 | 1345.3 | 2.385 | 71.8 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 36 s.
