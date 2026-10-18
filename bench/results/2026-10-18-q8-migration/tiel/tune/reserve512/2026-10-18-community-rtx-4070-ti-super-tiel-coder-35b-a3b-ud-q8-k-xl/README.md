# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 1 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit 4820a00e; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: tiel-coder-35b-a3b-ud-q8-k-xl
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata-poly.exe --model Tiel-Coder-35B-A3B-UD-Q8_K_XL.gguf --max-context 262144 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --threads 15 --prompt-batch 512 --vram-reserve-mib 512 --tail-skip 0 --window 8 --kv q8_0 --kv-whole
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
| short chat | 224 (221-229) | 0 | 100 (100-100) | 3 | not measured | 67.5 (66.9-73.4) | 0.78 (0.78-0.79) |
| 4K prompt, fresh | 4025 (4025-4025) | 0 (0-0) | 24 cap | 1 | 517.4 (517.4-517.4) | not measured | 7.79 (7.79-7.79) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 1 | 600.1 (600.1-600.1) | not measured | 26.78 (26.78-26.78) |
| agent session, follow-up turns | 15504 (15504-15504) at the last turn | see below | up to 64 | 1 | see below | 63.2 (49.2-69.3) | 7.72 (4.93-8.48) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 69.5 % (69.5-69.5); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 14473 (14473-14473) new tokens of the files are read once); first turn (nothing cached) first token: 2.46 s (2.46-2.46).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 835 | 0 | 835 | 341.2 | 2.463 | 68.0 |
| 1 | 4106 | 844 | 3262 | 414.9 | 7.871 | 49.2 |
| 2 | 5892 | 4166 | 1726 | 350.4 | 4.934 | 69.3 |
| 3 | 9453 | 5941 | 3512 | 414.7 | 8.477 | 59.1 |
| 4 | 12450 | 9484 | 2966 | 393.8 | 7.542 | 64.2 |
| 5 | 15504 | 12492 | 3012 | 390.6 | 7.721 | 63.2 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 96 s.
