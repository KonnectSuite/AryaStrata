# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit 4820a00e; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: ornith-1.5-35b-a3b-q8-0
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata-poly.exe --model Ornith-1.5-35B-Q8_0.gguf --max-context 262144 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --threads 15 --prompt-batch 512 --vram-reserve-mib 768 --tail-skip 6 --window 8 --kv q8_0 --kv-whole
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
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 107.6 (101.7-119.8) | 0.27 (0.26-0.30) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 1285.1 (1281.5-1286.4) | not measured | 3.14 (3.13-3.15) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 2392.3 (2388.5-2393.7) | not measured | 6.75 (6.75-6.75) |
| agent session, follow-up turns | 15297 (15275-15298) at the last turn | see below | up to 64 | 3 | see below | 107.6 (91.7-122.2) | 3.36 (2.93-3.60) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.2 % (68.2-68.2); earlier-turn tokens read again per session: 270 (248-271) (earlier turns that the cache did not hold; the 14453 (14453-14453) new tokens of the files are read once); first turn (nothing cached) first token: 1.16 s (1.14-1.29).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 475.8 | 1.29 | 116.4 |
| 1 | 3897 | 602 | 3295 | 983.9 | 3.363 | 107.6 |
| 2 | 5662 | 3890 | 1772 | 589.3 | 3.022 | 91.7 |
| 3 | 9224 | 5655 | 3569 | 1013.5 | 3.534 | 103.1 |
| 4 | 12242 | 9217 | 3025 | 906.7 | 3.35 | 104.7 |
| 5 | 15297 | 12235 | 3062 | 864.8 | 3.554 | 100.5 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 118 s.
