# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-17 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit dc2080ba; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: qwen3.8-flash-next-iq3_xxs
- Context: 32768 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata.exe --pack iq3_xxs --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --max-context 32768 --kv int8 --pool-workers 15 --vram-reserve-mib 1500
```

## Method

Run by `python tools/strata_bench.py --clients 2` against the HTTP API of a AryaStrata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 80.4 (56.4-93.5) | 0.42 (0.38-0.60) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 2114.2 (2056.5-2138.2) | not measured | 1.94 (1.92-1.98) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 2970.3 (2917.3-2995.4) | not measured | 5.44 (5.39-5.53) |
| agent session, follow-up turns | 15529 (15516-15560) at the last turn | see below | up to 64 | 3 | see below | 95.7 (76.2-114.2) | 1.91 (1.76-2.29) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 66.8 % (66.6-67.1); earlier-turn tokens read again per session: 72 (2-143) (earlier turns that the cache did not hold; the 14653 (14652-14653) new tokens of the files are read once); first turn (nothing cached) first token: 1.03 s (1.01-1.07).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 627.6 | 1.006 | 51.7 |
| 1 | 2344 | 620 | 1724 | 827.7 | 2.128 | 76.2 |
| 2 | 5817 | 2337 | 3480 | 1811.9 | 1.943 | 77.0 |
| 3 | 8847 | 5881 | 2966 | 1596.3 | 1.902 | 95.7 |
| 4 | 11809 | 8911 | 2898 | 1332.1 | 2.22 | 76.3 |
| 5 | 15516 | 11859 | 3657 | 1908.2 | 1.957 | 100.6 |

### Concurrency: 2 clients

Total 53.5 tok/s (50.9-60.4); first token p50 1.713 s, p95 3.497 s; request latency p50 3.62 s, p95 4.97 s; errors 0. Server parallel slots: 1 (requests beyond that wait their turn).

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 100 s.
