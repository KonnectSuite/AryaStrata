# AryaStrata

AryaStrata is KonnectSuite's fork of [PolyStrata](https://github.com/VecSzn/PolyStrata),
which is a fork of [Niko1221's original Strata](https://github.com/Niko1221/Strata).
See [credits](../CREDITS.md). This fork will
track configuration and changes against measurements on our own hardware.
Inherited benchmark reports remain attributed to their original machines and authors.

## First target machine

Detected locally on October 17, 2026. The user confirmed this PC as the target,
with coding and local coding agents as the first priority.

| Component | Detected hardware |
| --- | --- |
| CPU | Intel Core i9-14900KF, 24 cores, 32 logical processors |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER |
| GPU memory | 16,376 MiB reported by NVIDIA |
| NVIDIA driver | 610.88 |
| System memory | 63.82 GiB reported by Windows |
| Storage | WD Blue SN580 2TB SSD, 1,863.02 GiB capacity |
| OS | Windows 11 Home, version 10.0.26200 |

The initial inspection found Python 3.11 installed. CMake and nvcc were not
found on PATH; this does not establish whether they are installed elsewhere.
NVIDIA reported about 14,899 MiB of GPU memory occupied during inspection.
That is an observation of an active desktop, not a benchmark or available-memory target.

Starting source revision: `dc2080ba16d7f9f644cd01c3d5ff3237b2ae0f85`.

## Establish our baseline

1. Target confirmed: this Windows PC, for coding and local coding agents.
2. Choose one model and quantization using [AI_SETUP.md](AI_SETUP.md) and
   [BACKENDS.md](BACKENDS.md). Confirm the download size and destination before setup.
3. Install and run the existing engine first. Keep the API on `127.0.0.1`.
4. Check available RAM, SSD space and VRAM immediately before running. Identify
   other GPU workloads with the user before stopping anything.
5. Verify a real response and a representative task. Record correctness as well as speed.
6. Save raw measurements under `bench/results/<date>-aryastrata-<workload>/`.
   Record source revision, engine version/build, model file and revision, launch
   settings, actual prompt/output token counts, warm/cold state, prompt processing,
   time to first token, generation speed, peak RAM/VRAM, and errors.
7. Repeat each case at least three times and report medians. Change one setting
   at a time, comparing the modified build to a same-day unmodified baseline.

Start with short prompts and a 32K context ceiling; expand only after checking
memory use and correctness. Treat this as an experiment plan, not a measured optimum.
Follow [COMMUNITY_BENCHMARKS.md](COMMUNITY_BENCHMARKS.md) for reporting conventions.

## Deferred coding comparison

Tiel Coder `UD-Q3_K_XL` was considered before the existing Qwen installation was found:
setup lists a 17.2 GB download and supports Windows. This is a candidate baseline,
not a claim that it is the best model for this machine. Start at 32,768 tokens,
without vision, then check tool calls, code edits and tests before tuning speed.
The C: drive had 462.1 GiB free during inspection.

The user chose to set up the preserved Qwen3.8 model first. Tiel has not been
downloaded or installed. If chosen later, its proposed setup command is:

```powershell
.\START-HERE.bat --yes --family tiel --model UD-Q3_K_XL --context 32768 --vision no --data-dir C:\AryaStrata\local-data --no-start
```

Keep downloaded files in the ignored `local-data` folder. Inspect setup's runtime
requirements before allowing any system compiler or toolkit installation.

## Existing model migration (October 17, 2026)

The user requested removal of the old installations while preserving reusable
downloads. The old Strata engine and Python environment and the Ornith llama.cpp
runtime were removed (2.67 GiB total); their dedicated launchers were renamed
with `.disabled-aryastrata-20261017`. Models, vision files, prepared packs,
settings, old source code and prior benchmark artifacts were preserved in place.

- `C:\AI\Strata-data`: Qwen3.8 IQ3_XXS, both GGUF shards, plus existing auxiliary data.
- `C:\AI\Ornith35\models`: Ornith 1.5 Q4_K_M and its vision projector.

Qwen's files match the supported native model path. Ornith's architecture is
supported, but this exact Q4_K_M file still needs a load and correctness test.
Prefer testing the preserved downloads before downloading Tiel. No model files
were moved or redownloaded. The local removal inventory is saved under
`local-data/runtime-removal-inventory.json` (ignored by Git).

## New-fork results

AryaStrata's first Qwen inference checks passed on October 17, 2026:

- Release engine 0.1.45 (CUDA 13.0, including sm_89) installed in this checkout.
- Existing Qwen3.8 IQ3_XXS shards, prepared pack and MTP data reused in place.
- Local server: `http://127.0.0.1:8080`, OpenAI base URL `/v1`, model
  `qwen3.8-flash-next-iq3_xxs`.
- Context 32,768; int8 KV; MTP on; 15 expert workers; vision off.
- `--vram-reserve-mib 1500`: the initial unreserved start warned of 184 MiB free;
  after restarting with the reserve, the engine reported 1,151 MiB free.
- Health and model-list endpoints confirmed the model loaded.
- A short coding request returned `def add(a, b): return a + b` (formatted across
  two lines). A second request returned a structured `read_file` tool call with
  `{"path":"README.md"}`. No actual tool was executed by that check.
- Local response records are under the ignored `local-data` folder. These are
  smoke checks, not a speed benchmark or a full coding-agent evaluation.

Start again with `run-iq3_xxs.bat` in this checkout (only when the current server
is stopped). Runtime configuration is in the ignored `strata-iq3_xxs.json`.
The server runs as a hidden background process. Its PID is in
`local-data/qwen-server.pid`; the current validation server log is
`local-data/tuned262-server.log` and its engine log is `local-data/tuned262-engine.log`.

FreeToken was also uninstalled at the user's request: its dedicated WSL Python
environment at `/opt/arya-freetoken/venv` was removed, with its package inventory
saved beside it. Its 22 GB Qwen3.6 NVFP4 download remains under
`/opt/arya-freetoken/models/qwen36-nvfp4`; compatibility with this engine has not
been tested. No FreeToken startup service or running server was found.

## Measured profile and results, October 17, 2026

The initial 32K setup above is a historical smoke check. The current measured
profile uses the old installation's **262,144-token ceiling**:

```text
--max-context 262144 --kv int8 --kv-resident 32768
--vram-reserve-mib 1792 --pool-workers 15
--pcie-frac 0.20 --spec 4 --spec-min-p 0.70
--adapt-every 1 --adapt-swaps 80 --adapt-decay 0.97
```

MTP and default suffix drafting are enabled; the engine reports lookup windows up
to 6. Vision is off. `fit_max_tokens` is enabled. Calibration is saved using setup's
per-hardware/per-model/per-context settings format so updates can retain it.

The same-day 262K-ceiling API comparison measured **76.4 → 86.1 tokens/s** for
short chat and **86.8 → 95.6 tokens/s** for agent-style generation. Fresh 32K
prompt processing was **2,933.7 → 2,915.0 tokens/s**, with about **11 seconds** to
first token. Agent follow-up latency was essentially unchanged at about **2.1 s**.
Three repetitions were used; the full report preserves ranges and sample counts.

The old configuration already used PCIe 0.20, draft floor 0.70 and 15 workers.
The calibration favored 80 cache swaps over its old 160. This is not an old-engine
versus new-engine measurement, and no custom engine build is claimed.

All **18 small read/edit/test coding sessions**, **3 development DSH adapter
streaming/replay checks**, and **12 three-fact recall trials** passed. The largest
recall inputs were **258,300 actual tokens**, three runs, with median first-token
latency **101.6 seconds**. This validates those retrieval trials, not arbitrary
reasoning or large-repository coding at that size.

The development DSH profile now selects the same Qwen model with its full context,
**8,192-token output capability** and text-only input. Its low-thinking preference
was preserved. Details and the adapter-test boundary: [AryaAI DSH](ARYAAI_DSH.md).

[Full benchmark and raw records](../bench/results/2026-10-17-aryastrata-qwen38-iq3xxs/README.md).

The existing
[RTX 4070 Ti SUPER report](../bench/results/2026-10-05-community-rtx-4070-ti-super/README.md)
used a Ryzen CPU and Linux; its numbers are reference data, not results from this PC.
Hardware-specific engine defaults should change only after a repeatable improvement
is measured here.
