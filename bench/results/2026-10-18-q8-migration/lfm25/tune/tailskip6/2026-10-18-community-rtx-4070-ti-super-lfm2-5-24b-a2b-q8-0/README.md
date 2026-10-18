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
strata-poly.exe --model LFM2.5-24B-A2B-Q8_0.gguf --max-context 131072 --expert-profile expert-profile.txt --conversation-cache-mib 8192 --prompt-batch 2048 --threads 15 --vram-reserve-mib 768 --tail-skip 6 --window 1 --kv-whole
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
| short chat | 39 (36-45) | 0 | 100 (100-100) | 9 | not measured | 90.9 (76.4-101.6) | 0.21 (0.21-0.24) |
| 4K prompt, fresh | 4126 (4126-4126) | 0 (0-0) | 24 cap | 3 | 2661.6 (2639.1-2664.3) | not measured | 1.58 (1.57-1.58) |
| 16K prompt, fresh | 16490 (16490-16490) | 0 (0-0) | 24 cap | 3 | 5991.4 (5982.2-6007.5) | not measured | 2.78 (2.77-2.78) |
| agent session, follow-up turns | 14757 (14751-14765) at the last turn | see below | up to 64 | 3 | see below | 106.3 (77.6-117.3) | 1.39 (1.30-1.51) |

Ranges are the lowest and highest of the runs; `Runs` counts requests that returned a token.

### Agent session (conversation cache)

Cache hit over the follow-up turns: 67.5 % (67.5-67.5); earlier-turn tokens read again per session: 326 (321-327) (earlier turns that the cache did not hold; the 14060 (14059-14067) new tokens of the files are read once); first turn (nothing cached) first token: 0.55 s (0.53-0.56).

| Turn (run 1) | Prompt tokens | Reused | Read | Prompt tok/s | First token (s) | Decode tok/s |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 396 | 0 | 396 | 734.6 | 0.56 | 72.8 |
| 1 | 3637 | 391 | 3246 | 2405.2 | 1.384 | 77.6 |
| 2 | 5436 | 3632 | 1804 | 1377.7 | 1.318 | 88.6 |
| 3 | 8711 | 5431 | 3280 | 2187.5 | 1.51 | 91.1 |
| 4 | 11780 | 8706 | 3074 | 2215.2 | 1.399 | 96.4 |
| 5 | 14765 | 11775 | 2990 | 2026.4 | 1.499 | 86.6 |

Per-request data: `results.json`. Engine log lines from the start: `engine-log-excerpt.txt` (when this run started the server).

## Correctness and limitations

Not measured: this is a speed suite. The conversation uses the model's own replies, so token counts differ a little between runs. Machine details come from the server, `nvidia-smi`/`rocm-smi` and the OS; background load and power limits are not recorded. Total time of the suite: 65 s.
