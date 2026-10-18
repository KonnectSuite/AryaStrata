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
strata.exe --pack iq3_xxs --native Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00001-of-00002.gguf --ple-gguf Qwen3.8-Flash-Next-GSQ-RCO-IQ3_XXS-00002-of-00002.gguf --expert-profile expert-profile.bin --expert-cache auto --prefill auto --spec 4 --mtp rt --kv int8 --max-context 262144 --kv-resident 32768 --vram-reserve-mib 1792 --pcie-frac 0.20 --spec-min-p 0.70 --pool-workers 15 --adapt-every 1 --adapt-swaps 80 --adapt-decay 0.97
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 86.1 (70.0-105.0) | 0.37 (0.32-0.77) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 2037.7 (1873.9-2075.3) | not measured | 1.99 (1.96-2.16) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 2983.3 (2887.6-2983.8) | not measured | 5.42 (5.41-5.59) |
| 32K prompt, fresh | 32049 (32049-32049) | 0 (0-0) | 24 cap | 3 | 2915.0 (2913.3-2941.4) | not measured | 11.03 (10.93-11.04) |
| agent session, follow-up turns | 15530 (15525-15548) at the last turn | see below | up to 64 | 3 | see below | 95.6 (58.1-112.6) | 2.12 (1.98-2.23) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 66.8 % (66.8-67.0); earlier-turn tokens read again per session: 71 (4-72) (earlier turns that the cache did not hold; the 14653 (14651-14654) new tokens of the files are read once); first turn (nothing cached) first token: 1.05 s (1.04-1.13).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 606.8 | 1.04 | 67.0 |
| 1 | 2362 | 638 | 1724 | 827.5 | 2.122 | 74.7 |
| 2 | 5835 | 2425 | 3410 | 1611.7 | 2.141 | 78.7 |
| 3 | 8865 | 5898 | 2967 | 1403.6 | 2.139 | 58.1 |
| 4 | 11827 | 8928 | 2899 | 1411.9 | 2.096 | 110.3 |
| 5 | 15548 | 11890 | 3658 | 1708.9 | 2.164 | 85.6 |

### Concurrency: 2 clients

Total 55.6 tok/s (53.4-61.3); first token p50 1.498 s, p95 2.689 s; request latency p50 3.176 s, p95 4.749 s; errors 0. Server parallel slots: 1 (requests beyond that wait their turn).

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 135 s.
