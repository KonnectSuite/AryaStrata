<h1 align="center">AryaStrata</h1>

Local AI for coding and coding agents, configured and benchmarked against our own host.

AryaStrata is a fork of **[PolyStrata](https://github.com/VecSzn/PolyStrata)** by VecSzn,
which is a fork of **[the original Strata](https://github.com/Niko1221/Strata)** by
Niko1221 and the Strata contributors. Their engines, tooling and research make this
fork possible. See [credits](CREDITS.md) and the original [MIT license](LICENSE).

## Our host

| Component | Hardware |
| --- | --- |
| CPU | Intel Core i9-14900KF, 24 cores / 32 threads |
| GPU | NVIDIA GeForce RTX 4070 Ti SUPER, 16 GB VRAM |
| RAM | 64 GB installed, 63.82 GiB reported by Windows |
| Storage | WD Blue SN580 2 TB SSD |
| OS | Windows 11 Home |

## Measured on this host

Qwen3.8-Flash-Next **IQ3_XXS**, upstream release engine **0.1.45**, native Windows.
The selected profile restores the old **262,144-token context ceiling**, with int8
KV, 32K resident KV, a 1,792 MiB VRAM reserve, MTP and 15 CPU expert workers.
Vision is off. These are measured settings for this host, not universal defaults.

October 17, 2026 results (medians):

| Metric | New-install baseline at 262K | Tuned at 262K |
| --- | ---: | ---: |
| Short-chat generation | 76.4 tokens/s | **86.1 tokens/s** |
| Short-chat first token | 0.447 s | **0.368 s** |
| Agent-style generation | 86.8 tokens/s | **95.6 tokens/s** |
| Agent-style follow-up first token | 2.105 s | 2.122 s |
| Fresh 32K prompt processing | 2,933.7 tokens/s | 2,915.0 tokens/s |

The observed short-chat median improved **12.7%**; prompt processing and follow-up
latency were largely unchanged. These are small, workload-specific comparisons
with overlapping run ranges, not a comparison against the old engine binary.
Agent-style speed sessions summarize files; correctness is tested separately.

- **18/18 bounded coding-agent sessions passed**: three Python fixtures, three
  runs each with thinking off and with low thinking, including read/edit/test tools.
- **3/3 development DSH adapter trials passed**: streaming tool calls and tool-result replay.
- **12/12 recall trials passed** across about 32K, 65K, 131K and **258,300 actual
  input tokens**. The largest inputs took a median **101.6 seconds to first token**.

These checks do not establish general repository-level coding quality or a fully
qualified native desktop workflow. Raw records, ranges, exact model/build hashes,
resource observations and methodology: [full host benchmark](bench/results/2026-10-17-aryastrata-qwen38-iq3xxs/README.md).

[Current host setup](docs/ARYASTRATA.md) · [AryaAI development DSH profile](docs/ARYAAI_DSH.md)

Historical feature lists and measurements from other machines remain attributed
in the [upstream README](docs/UPSTREAM_README.md).

## Run on this host

Start `run-iq3_xxs.bat` from this folder when the server is stopped. Setup generated
that launcher locally; it reuses the preserved downloads under `C:\AI\Strata-data`.

- Chat: [127.0.0.1:8080](http://127.0.0.1:8080).
- OpenAI-compatible base URL: `http://127.0.0.1:8080/v1`.
- Model: `qwen3.8-flash-next-iq3_xxs`.
- Keep the server on `127.0.0.1`; access from other devices requires an API key.

For a fresh installation, follow [installation](docs/INSTALL.md) or
[assistant setup instructions](docs/AI_SETUP.md). Other models and hardware paths
are inherited capabilities; they still need validation on this host.

## Project lineage and compatibility

**Original Strata → PolyStrata → AryaStrata.** The Qwen engine comes from original
Strata; the additional model engine and extensions come through PolyStrata.
AryaStrata currently uses the upstream release engine without engine-code changes.
Internal `strata-poly` names, `polystrata.py`, upstream release URLs, model repository
names, and historical benchmark artifacts retain their original identifiers for
compatibility and attribution. The app, installer messages and current docs use
AryaStrata branding. See [credits](CREDITS.md).
