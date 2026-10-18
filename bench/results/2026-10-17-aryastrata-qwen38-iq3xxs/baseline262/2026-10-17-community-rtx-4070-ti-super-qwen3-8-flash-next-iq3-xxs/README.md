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
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata.exe --pack iq3_xxs --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --spec-min-p 0.5 --mtp rt --kv int8 --pool-workers 15 --max-context 262144 --kv-resident 32768 --vram-reserve-mib 1792
```

## Method

Run by `python tools/strata_bench.py --clients 2 --long` against the HTTP API of a AryaStrata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 76.4 (59.8-89.4) | 0.45 (0.38-0.89) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 2058.9 (1908.1-2068.8) | not measured | 1.98 (1.97-2.15) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 2879.2 (2789.2-2951.2) | not measured | 5.60 (5.49-5.80) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 3 | 2933.7 (2898.9-2947.4) | not measured | 10.96 (10.91-11.09) |
| agent session, follow-up turns | 15526 (15512-15555) at the last turn | see below | up to 64 | 3 | see below | 86.8 (52.1-110.7) | 2.10 (1.89-2.28) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 66.9 % (66.8-67.0); earlier-turn tokens read again per session: 73 (4-74) (earlier turns that the cache did not hold; the 14652 (14651-14654) new tokens of the files are read once); first turn (nothing cached) first token: 1.07 s (1.06-1.10).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 583.5 | 1.065 | 67.0 |
| 1 | 2379 | 656 | 1723 | 920.5 | 1.893 | 52.1 |
| 2 | 5852 | 2372 | 3480 | 1606.4 | 2.198 | 84.1 |
| 3 | 8882 | 5915 | 2967 | 1424.8 | 2.105 | 94.1 |
| 4 | 11834 | 8936 | 2898 | 1321.3 | 2.236 | 92.3 |
| 5 | 15555 | 11897 | 3658 | 1691.2 | 2.195 | 86.8 |

### Concurrency: 2 clients

Total 57.4 tok/s (54.7-62.1); first token p50 1.597 s, p95 3.108 s; request latency p50 3.276 s, p95 4.624 s; errors 0. Server parallel slots: 1 (requests beyond that wait their turn).

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 139 s.
