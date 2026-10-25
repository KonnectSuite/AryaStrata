# Agentic coding and tool use on this host: the roster tuning of October 25, 2026

Host: **i9-14900KF, RTX 4070 Ti SUPER 16 GB (driver 610.88), 64 GB RAM, Windows 11**,
engine **0.1.45** (`strata.exe` for Qwen3.8, `strata-poly.exe` 0.1.45 for the six families).
Every number on this page was measured on this PC, on the day named, at the workload named.
Inherited vendor or community numbers are marked as such.

This page answers two reports from the user:

1. *"Before AryaCode, the Qwen3.8 Flash IQ3 model never hit an output limit. Now it cannot
   make a website."* — the cause was the output allowance the AryaCode adapter advertised,
   not the model. Section 1.
2. *"For the smaller MoEs I get the same numbers as a laptop with 8 GB of VRAM and 32 GB
   of RAM."* — the cause was `--kv-whole` reserving the whole 256K attention cache in VRAM
   at load, which starved the expert cache. Section 2.

The workload measured here is the one an agent actually runs, not a chat prompt: a
5,329-token cold turn (system prompt, six tool schemas, a task), a follow-up on the same
conversation, and a 43,007- or 63,138-token reference prompt built from this repository's
own documents, with tools on. Numbers come from the server's response usage plus
client-side timing (`agentic_bench.py`, `ab_config.py`), and the engine's own log line for
the same request is quoted beside them.

Noise floor: the vendor's published rule is that decode differences under **10%** are not
readable as real. Changes below are only claimed where they cleared that, and the
43K A/Bs are single requests, so the ranges are wider than the medians.

## 1. The output allowance: 8,192 tokens for every model

`@aryacode/dsh-local-llm` published every local model with `maxTokens: 8192`, because its
`outputDefault()` capped the default at a fixed 8K:

```ts
// 0.8.5
export function outputDefault(context: number, ceiling = 8192): number {
  return Math.max(1024, Math.min(ceiling, 8192, Math.floor(context / 4)))
}
```

For a 262,144-token model that is 3% of the window. The harness reports the value in every
request it records (`request/header.config.maxTokens`, `adapterDefaults.maxTokens: true`),
so the evidence is exact:

| Session | Model | Output | Finish |
| --- | --- | ---: | --- |
| 10-25 11:41 | `strata:qwen3.8-flash-next-iq3_xxs` | 8,192 | `max-tokens` — the website build |
| 10-25 11:32 | `strata:qwen3.8-flash-next-abliterated-iq2_xs` | 8,192 | `max-tokens` |
| 10-25 10:53 | `ninfer:qwen3.8-27b` | 8,192 | `max-tokens` |

The failing website session ended `turn/end reason={"kind":"max-tokens"}` with
`outputTokens: 8192` and a single `write` call whose arguments were cut off mid-file. Three
different models, the same ceiling: the cap, not the models.

**Fixed in 0.8.6** — the default follows the served window, bounded by the engine's own
allowance when it declares one:

```ts
// 0.8.6
export function outputDefault(context: number, ceiling = Number.POSITIVE_INFINITY): number {
  return Math.max(1024, Math.min(ceiling, Math.floor(context / 4)))
}
```

| Served window | Advertised before | Advertised now |
| ---: | ---: | ---: |
| 262,144 | 8,192 | **65,536** |
| 131,072 | 8,192 | **32,768** |
| 102,400 (NInfer) | 8,192 | **25,600** |

A per-model override still wins, so anything the Chat output limits editor set explicitly
does not change. The plugin's suite is 118/118, including three new tests for the window
fraction, the engine ceiling and the small-window floor. Release identity:
`@aryacode/dsh-local-llm` 0.8.6 (`3620fb7`), npm tarball sha256
`4d58072e…b884e659`, published in the Arya catalogue as `cc9ea18`.

**Same task, same model, same tools, only the allowance differs** (Qwen3.8 IQ3_XXS, low
effort, the user's own build prompt, a bounded agent loop that executes the model's
read/glob calls):

| Allowance | Result | Tool call | File written |
| ---: | --- | --- | --- |
| 8,192 | `finish: length` after 8,192 output tokens | 19,059 characters of arguments, cut mid-JSON | **none** |
| 65,536 | `finish: tool_calls` after 15,434 output tokens | 51,870 characters, valid JSON | **49,761 characters, has `</html>`** |

The write needs 15,434 tokens, 1.9x the old ceiling. This is the failure and the fix,
reproduced on this host with the user's task.

**The trade-off, stated plainly:** a larger allowance reserves more of the context for the
answer. `compaction-basic` computes its pressure budget as `window - request maxTokens -
headroom`; at 262,144 with 65,536 allowed and the default 64K headroom, the live-context
budget is 131,072 tokens instead of 188,416. If a session needs more live context and
accepts shorter writes, lower the model's allowance with **AryaStrata → Chat output
limits**; the editor's range is 1,024 to the window minus 1,024.

## 2. `--kv-whole` cost the PolyStrata models their expert cache

`--kv-whole` gives the attention caches VRAM for the whole configured context at load,
instead of letting them grow with the conversation. The option exists for AMD cards, where
ROCm does not hand VRAM back (see `AMD_HIP.md`), and setup writes it there. On this NVIDIA
card it does the opposite of what the small MoEs need:

- Qwen3.6 q8_0 KV is 11,968 bytes a token (the engine prints 544 bytes a row, 2 rows, 11
  attention layers). At **262,144 tokens that is 3.0 GiB reserved before the first prompt**.
- The expert cache is what makes these models fast: an expert it holds is read at VRAM
  speed, one it does not is read from system RAM or the SSD. 3.0 GiB of VRAM is roughly
  1,600 routed experts at Qwen3.6's Q4 expert size.

Measured, Qwen3.6 UD-Q4_K_XL, one 43,007-token prompt with tools, fresh engine each arm:

| Arm | Experts in VRAM | Prompt read | Decode |
| --- | ---: | ---: | ---: |
| `--kv-whole` (shipped) | 4,467 | 1,846 tok/s | 75.9 tok/s |
| without `--kv-whole` | **6,055** | **2,937 tok/s** | **111.7 tok/s** |
| change | +36% | **+59%** | **+47%** |

The attention cache still grows to the same 3.0 GiB when a conversation actually reaches
262K; the difference is that a normal 20K-100K session no longer pays for it up front. The
`--vram-reserve-mib 512` in the same config covers the CUDA-graph headroom that `Q8_KV.md`
measured as necessary.

## 3. What changed, per model

| Model | Config | Change | Why |
| --- | --- | --- | --- |
| Qwen3.8 Flash Next IQ3_XXS | `strata-iq3_xxs.json` | none | already the calibrated config from `.tune/SETTINGS-REPORT.md`; `--vram-reserve-mib 1000`, `--kv-resident 32768`, MTP, 15 workers |
| Qwen3.8 Flash Next abliterated IQ2_XS | `strata-abliterated-iq2_xs.json` | none | same settings; CPU vision encoder already |
| Qwen3.6 35B-A3B UD-Q4_K_XL | `strata-qwen36s-ud-q4_k_xl.json` | removed `--kv-whole`; `--prompt-batch 512 → 2048`; `--vram-reserve-mib 768 → 512` | section 2; the wider prompt batch reads long prompts faster |
| Qwen3.6 35B-A3B Q8_0 | `strata-qwen36s-q8_0.json` | same three | same |
| Ornith 1.5 35B-A3B APEX-I-QUALITY | `strata-ornith-apex-i-quality.json` | added `--kv q8_0`; `--prompt-batch` 1,024 → 2048 | Q8_0 KV is byte-identical for `qwen35moe` (15/15 exact answers in `Q8_KV.md`) and halves the cache; measured +14% prompt read, +8% decode |
| Flint 40B-A2.5B UD-Q4_K_XL | `strata-flint-ud-q4_k_xl.json` | none | already `--prompt-batch 2048`; `--kv q8_0` does not exist for the `flint` architecture (the engine gates it to `qwen35moe`) |

The Qwen3.8 vision encoder was measured both ways: GPU 2,895 tok/s prompt / 147.4 decode,
CPU 2,918 / 154.0 at 43K — inside each other's noise. It stays on the GPU (faster images);
the installer's CPU rule is a robustness choice, not a speed one here.

## 4. Before and after

### 4.1 The clean pairs: same prompt, same protocol, one variable

One 43,007-token prompt built from this repository's documents, tools on, a 160-token
reply that ran to `length` in both arms, fresh engine each arm, `temperature 0`.

| Model | Arm | Prompt read | Decode |
| --- | --- | ---: | ---: |
| Qwen3.6 UD-Q4_K_XL | shipped (`--kv-whole`, batch 512, reserve 768) | 1,846 tok/s | 75.9 tok/s |
| | tuned as shipped (no `--kv-whole`, batch 2048, reserve 512) | **3,268 tok/s (+77%)** | **116.7 tok/s (+54%)** |
| Ornith 1.5 APEX | shipped (fp16 KV, batch 1,024) | 2,239 tok/s | 66.1 tok/s |
| | tuned (`--kv q8_0`, batch 2048) | **2,554 tok/s (+14%)** | **71.4 tok/s (+8%)** |

The same pair at the 63,138-token prompt, where both arms again ran to `length` at 256
tokens: Qwen3.6 Q4 prompt read **1,924 → 2,605 tok/s (+35%)**, decode 77.2 → 82.9
(inside noise); Qwen3.6 Q8 prompt read **1,961 → 2,630 tok/s (+34%)**, decode 66.3 → 73.3
(+11%). The gain is largest in the 20K-50K range an agent actually works in, and narrows as
the conversation grows and both arms pay for a smaller expert cache.

### 4.2 The roster at 63,138 tokens after tuning

One request each, tools on; prompt read is `prompt_tokens / time-to-first-token`, so it is
comparable across arms. Decode is the engine's own line where it exists; for the PolyStrata
engines the client-side figure includes streaming overhead and is quoted only where the
reply ran to 256 tokens.

| Model | Prompt read | Decode | Note |
| --- | ---: | ---: | --- |
| Qwen3.8 IQ3_XXS | 2,782 tok/s | 86.4 tok/s | engine line; 69.7-100.1 across this session's runs |
| Qwen3.8 abliterated IQ2_XS | 2,755 tok/s | 107.3 tok/s | engine line |
| Qwen3.6 UD-Q4_K_XL | 2,605 tok/s | 82.9 tok/s | client, 256 tokens |
| Qwen3.6 Q8_0 | 2,630 tok/s | 73.3 tok/s | client, 256 tokens |
| Ornith 1.5 APEX | 2,643 tok/s | 73.7 tok/s | client, 104 tokens |
| Flint 40B-A2.5B | 3,190 tok/s | 70.5 tok/s | client, 256 tokens |

**Run-to-run spread is larger than the vendor's 10% rule on decode.** The same Qwen3.8
IQ3_XXS, same 256-token probe, read 69.7 to 100.1 tok/s across runs in this session
depending on draft acceptance (55-95%) and expert-cache warmth; the abliterated IQ2_XS
measured 81.5 to 218.9 on the same kind of request. Absolute decode is therefore a range,
not a constant, and only the interleaved pairs in 4.1 are used for claims of change.

## 5. Tested and not adopted

- **`--prompt-batch 1024` without removing `--kv-whole`**: 1,886 tok/s, inside the
  baseline's range — the batch width only paid off once the expert cache had room.
- **`--vram-reserve-mib 512` alone** (768 → 512 with batch 1024): no measurable change on
  its own; kept because it matches the reserve `Q8_KV.md` measured as OOM-free.
- **CPU vision encoder on Qwen3.8 IQ3_XXS**: within noise (section 3); reverted to GPU.
- **`--tail-skip` on Qwen3.6 Q4**: the shipped config has 0 (the upstream default for this
  family is 6). Left at 0: it changes answers, and no measured gain was established for
  this workload.
- **`--kv q8_0` on Flint**: refused by the engine — `q8_0` is implemented for `qwen35moe`
  only in v1.

## 6. What remains open

- **Flint at 262,144 with fp16 KV.** No quantized KV exists for its architecture, so a
  256K ceiling costs about 3 GiB once a conversation is that long and squeezes the expert
  cache from 6,217 to about 4,400 experts. At the 43K-63K sizes measured here it does not
  shrink below the Qwen3.6 tuning, which is why it was left alone. If Flint speed matters
  more than the last 128K of context, `--max-context 131072` is the lever.
- **Sampling.** `strata-qwen36s-*`, `strata-ornith-*` and `strata-flint-*` carry a sampling
  block with `temperature 1.0`, `top_p 0.95`, `top_k 20` and `presence_penalty 1.5`. The
  last is Qwen's long-form writing recommendation; for code and tool calls it is
  questionable, but changing it is a quality change that this session did not measure.
  It is the next thing to A/B on tool-argument validity, not a number to change blind.
- **Cold first token after a load.** The PolyStrata engines are 3-10x slower on the first
  prompt after loading (Ornith 6.2 s at 5,329 tokens, Qwen3.6 Q8 13.6-15.4 s; the same
  prompt on the next turn is 0.26 s). This is graph capture plus first-touch expert reads,
  not the configured settings; it is the one remaining "it feels like a laptop" moment.
- **A 250K-token request through the tuned Qwen3.6 Q4** was not re-run after the change;
  the 43K and 63K measurements are what is established. The attention cache still grows to
  the same size at 262K, but a full-depth run is the check to make before promising
  "256K is as fast as before".

## 7. How the numbers were taken

`agentic_bench.py` (workload and roster run), `ab_config.py` (per-config A/B: unload, load,
43K prompt, engine log facts), `website_agent.py` (the failing session's task, bounded tool
loop), `session_speed.py` (decode rate the user actually experienced, from this machine's
own session logs). The tools live outside this repository; the measurements above are the
part that belongs in it.
