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
strata-poly.exe --model Tiel-Coder-35B-A3B-UD-Q8_K_XL.gguf --max-context 262144 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --threads 15 --prompt-batch 512 --vram-reserve-mib 768 --tail-skip 6 --window 8 --kv q8_0 --kv-whole
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
| short chat | 224 (221-229) | 0 | 100 (100-100) | 3 | not measured | 81.0 (77.9-87.2) | 0.72 (0.69-0.73) |
| 4K prompt, fresh | 4025 (4025-4025) | 0 (0-0) | 24 cap | 1 | 578.3 (578.3-578.3) | not measured | 6.99 (6.99-6.99) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 1 | 686.4 (686.4-686.4) | not measured | 23.41 (23.41-23.41) |
| agent session, follow-up turns | 15512 (15512-15512) at the last turn | see below | up to 64 | 1 | see below | 77.1 (66.6-78.9) | 6.69 (4.39-7.40) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 69.4 % (69.4-69.4); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 14473 (14473-14473) new tokens of the files are read once); first turn (nothing cached) first token: 2.19 s (2.19-2.19).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 835 | 0 | 835 | 384.7 | 2.191 | 75.7 |
| 1 | 4106 | 844 | 3262 | 476.4 | 6.872 | 66.6 |
| 2 | 5881 | 4155 | 1726 | 394.1 | 4.388 | 77.1 |
| 3 | 9441 | 5929 | 3512 | 474.9 | 7.404 | 70.3 |
| 4 | 12450 | 9484 | 2966 | 453.7 | 6.547 | 78.9 |
| 5 | 15512 | 12500 | 3012 | 450.9 | 6.69 | 77.4 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 84 s.
