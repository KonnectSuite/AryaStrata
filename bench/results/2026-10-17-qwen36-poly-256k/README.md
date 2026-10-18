# Qwen3.6 Q4/Q8 host measurements

See the [host report](../../../docs/QWEN36_HOST_RESULTS.md) for conclusions,
measurements, configuration, and limits. This run started October 17, 2026 and
continued October 18 after a power interruption. Completed trials were retained;
both model files were SHA-256 verified again after restart.

Hardware: i9-14900KF, RTX 4070 Ti SUPER 16 GB, 64 GB DDR5-6000, Windows 11.
Both models use the source-matched PolyStrata 0.1.45 backend, 262,144-token
capacity, fully allocated Q8_0 KV, GPU vision at up to 1,024 image tokens, one
conversation slot, and no tail skipping. The retained profiles use 15 CPU
threads, window 8 and prompt batch 512. Q6 was not tested.

Each quant passed:

- 18 coding sessions with reasoning off and 18 with low reasoning: six bounded
  fixtures repeated three times at each setting.
- 12 synthetic image checks: four fixtures repeated three times.
- Six three-fact recall trials: three at each input length, 131,031 and 254,191
  actual tokens.
- Three long-context coding/image fixtures, starting around 230,827 input
  tokens. Their code checks and image-ID reporting both passed. Later fixtures
  reused 208,896 prefix tokens; cold and reused-prefix latencies are separate.
- Three development DSH adapter streaming/tool-result replay checks.

`Q4/` and `Q8/` contain the validation records and generated fixture images.
The calibration files preserve every tuning candidate and confirmation run.
`summary.json` records the selected settings; `profiles/` contains exact host
profiles with paths to adjust for another checkout. `installed-service.json`
records final health and discoverable model IDs. `diagnostics/` preserves the
native-backend startup failures that motivated selecting PolyStrata.

`protocol.json` includes model URLs, sizes, SHA-256 values, engine fingerprints,
binary hashes and benchmark-tool hashes. `tool-snapshots/` preserves the source
matching the recorded tool hashes, including Windows line endings. The later
long-agent CLI fix only makes failures return a failing exit status and adds run
metadata to error rows; it does not change request generation or per-case scores.
`resources.jsonl` retains telemetry across the original and recovery sessions.

These are performance and bounded functional checks, not a real-repository
coding-quality benchmark. Recall prompts repeat source excerpts. Vision checks
use generated images. The small fixtures do not establish equal general quality
between weight quants. Q8 briefly left only 0.10 GiB of system RAM available;
paging was not measured. No active KV streaming through system RAM is claimed.

AryaStrata is a fork of PolyStrata (VecSzn), which is a fork of Niko1221's
original Strata. Original credits and the MIT notice are preserved in the repository.
