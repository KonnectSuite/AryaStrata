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
strata-poly.exe --model Tiel-Coder-35B-A3B-UD-Q8_K_XL.gguf --max-context 262144 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --threads 15 --prompt-batch 512 --vram-reserve-mib 768 --tail-skip 0 --window 8 --kv q8_0 --kv-whole --stage-mib 4096
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
| short chat | 224 (221-229) | 0 | 100 (100-100) | 3 | not measured | 65.5 (65.2-74.1) | 0.78 (0.77-0.80) |
| 4K prompt, fresh | 4025 (4025-4025) | 0 (0-0) | 24 cap | 1 | 513.6 (513.6-513.6) | not measured | 7.84 (7.84-7.84) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 1 | 606.9 (606.9-606.9) | not measured | 26.50 (26.50-26.50) |
| agent session, follow-up turns | 15508 (15508-15508) at the last turn | see below | up to 64 | 1 | see below | 63.9 (54.5-67.7) | 7.75 (4.95-8.53) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 69.5 % (69.5-69.5); earlier-turn tokens read again per session: 5 (5-5) (earlier turns that the cache did not hold; the 14473 (14473-14473) new tokens of the files are read once); first turn (nothing cached) first token: 2.40 s (2.40-2.40).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 835 | 0 | 835 | 349.5 | 2.397 | 68.3 |
| 1 | 4106 | 844 | 3262 | 421.5 | 7.749 | 54.5 |
| 2 | 5884 | 4158 | 1726 | 349.5 | 4.947 | 67.7 |
| 3 | 9445 | 5933 | 3512 | 412.2 | 8.53 | 63.9 |
| 4 | 12458 | 9492 | 2966 | 393.3 | 7.552 | 63.9 |
| 5 | 15508 | 12496 | 3012 | 389.2 | 7.766 | 60.5 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 95 s.
