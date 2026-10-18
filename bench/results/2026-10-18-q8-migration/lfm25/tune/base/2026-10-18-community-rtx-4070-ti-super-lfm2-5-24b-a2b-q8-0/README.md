# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit 4820a00e; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: lfm2.5-24b-a2b-q8-0
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata-poly.exe --model LFM2.5-24B-A2B-Q8_0.gguf --max-context 131072 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --prompt-batch 2048 --threads 15 --vram-reserve-mib 768 --tail-skip 0 --window 1 --kv-whole
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
| short chat | 39 (36-45) | 0 | 100 (100-100) | 9 | not measured | 88.7 (73.2-100.9) | 0.23 (0.21-0.25) |
| 4K prompt, fresh | 4126 (4126-4126) | 0 (0-0) | 24 cap | 3 | 2567.2 (2500.3-2605.1) | not measured | 1.63 (1.62-1.67) |
| 16K prompt, fresh | 16490 (16490-16490) | 0 (0-0) | 24 cap | 3 | 6000.9 (5997.7-6149.3) | not measured | 2.78 (2.73-2.79) |
| agent session, follow-up turns | 14761 (14753-14766) at the last turn | see below | up to 64 | 3 | see below | 99.4 (73.4-109.7) | 1.41 (1.32-1.52) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 67.5 % (67.5-67.5); earlier-turn tokens read again per session: 323 (323-325) (earlier turns that the cache did not hold; the 14067 (14059-14070) new tokens of the files are read once); first turn (nothing cached) first token: 0.55 s (0.55-0.57).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 396 | 0 | 396 | 718.6 | 0.568 | 73.9 |
| 1 | 3633 | 391 | 3242 | 2368.8 | 1.406 | 73.4 |
| 2 | 5432 | 3628 | 1804 | 1378.3 | 1.318 | 79.7 |
| 3 | 8707 | 5427 | 3280 | 2170.0 | 1.522 | 88.8 |
| 4 | 11776 | 8702 | 3074 | 2203.0 | 1.406 | 92.5 |
| 5 | 14761 | 11771 | 2990 | 1997.9 | 1.507 | 88.3 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 71 s.
