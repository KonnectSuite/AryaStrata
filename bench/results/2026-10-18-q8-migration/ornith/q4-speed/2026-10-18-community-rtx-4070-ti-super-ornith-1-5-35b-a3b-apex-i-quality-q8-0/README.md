# Community benchmark on NVIDIA GeForce RTX 4070 Ti SUPER

Measured on 2026-10-18 with `tools/strata_bench.py` (suite 1, 3 runs per test, medians with ranges). Speeds are the engine's own timings; first-token times are measured by the client over HTTP. Speed only: no correctness check was run.

## Hardware and software

- GPU and VRAM: NVIDIA GeForce RTX 4070 Ti SUPER, 16 GiB VRAM
- CPU: Intel(R) Core(TM) i9-14900KF (24 cores, 32 threads); installed RAM: 63.8 GiB; storage: not measured
- OS: Windows 11 (10.0.26200); GPU driver: 610.88; CUDA: not read
- AryaStrata: project 0.1.45, commit 4820a00e; engine 0.1.45
- Background workloads and power limits: not recorded

## Model and configuration

- Model and quantization: ornith-1.5-35b-a3b-apex-i-quality-Q8_0
- Context: 262144 tokens; parallel slots: 1
- Settings: the install's own configuration, unchanged; thinking off for the suite; temperature 0

```text
strata-poly.exe --model Ornith-1.5-35B-A3B-APEX-MTP-I-Quality.gguf --max-context 262144 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --threads 15 --prompt-batch 512 --vram-reserve-mib 768 --tail-skip 0 --window 8 --kv q8_0 --kv-whole
```

## Method

Run by `python tools/strata_bench.py` against the HTTP API of a AryaStrata server (already running); model loading is not timed. One warm-up chat and a 1K prompt are discarded first. Every prompt starts with a unique tag, so the conversation cache cannot help the fresh-prompt tests.

- short chat: the three questions of `tools/ab_engine.py`, up to 100 new tokens, 3 runs
- 4K / 16K prompts: generated word lists sized by a calibration request, 24 new tokens, 3 fresh prompts each
- agent session: system prompt and four tools, then 5 turns that each add about 1500 words of a project file and continue from the model's own earlier answers (the way agent clients resend a conversation), 64 new tokens per turn, 3 sessions; the cache numbers come from the answer's usage (`cached_tokens`) and timings (`prompt_n`)
- concurrency (when run): N requests sent at the same moment, total tokens over the wall time of the burst, latency over all requests

## Results

| Configuration | Actual prompt tokens | Reused tokens | Generated tokens | Runs | Prompt tok/s median and range | Decode tok/s median and range | TTFT seconds median and range |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| short chat | 46 (43-51) | 0 | 100 (100-100) | 9 | not measured | 92.4 (78.9-101.9) | 0.32 (0.28-0.36) |
| 4K prompt, fresh | 4019 (4019-4019) | 0 (0-0) | 24 cap | 3 | 1279.1 (1273.0-1290.0) | not measured | 3.15 (3.13-3.18) |
| 16K prompt, fresh | 16058 (16058-16058) | 0 (0-0) | 24 cap | 3 | 2428.7 (2425.2-2435.2) | not measured | 6.63 (6.62-6.64) |
| agent session, follow-up turns | 15283 (15280-15295) at the last turn | see below | up to 64 | 3 | see below | 112.7 (83.7-127.0) | 3.22 (2.73-3.60) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 68.2 % (68.2-68.2); earlier-turn tokens read again per session: 256 (253-268) (earlier turns that the cache did not hold; the 14453 (14453-14453) new tokens of the files are read once); first turn (nothing cached) first token: 1.17 s (1.14-1.28).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 609 | 0 | 609 | 478.5 | 1.28 | 97.7 |
| 1 | 3892 | 602 | 3290 | 927.4 | 3.601 | 91.8 |
| 2 | 5655 | 3885 | 1770 | 610.3 | 2.92 | 83.7 |
| 3 | 9216 | 5648 | 3568 | 1087.3 | 3.293 | 98.9 |
| 4 | 12223 | 9209 | 3014 | 946.0 | 3.216 | 99.0 |
| 5 | 15280 | 12216 | 3064 | 930.8 | 3.303 | 101.2 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 108 s.
