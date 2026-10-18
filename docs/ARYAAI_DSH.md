# AryaAI development DSH with AryaStrata

This host's Qwen3.8-Flash-Next IQ3_XXS profile was measured on October 17, 2026.
See the [host benchmark](../bench/results/2026-10-17-aryastrata-qwen38-iq3xxs/README.md)
for exact measurements, source/build identities and raw records.

Qwen3.6 Q4 and Q8 are now also configured for the development app: each uses
262,144-token context, up to 8,192 output tokens, and text/image input. Their
PolyStrata profiles are `qwen3.6-35b-a3b-ud-q4_k_xl` and
`qwen3.6-35b-a3b-q8_0`. Each passed three isolated streaming/tool-result replay
checks through the development app's actual `dsh-llm-pi-ai` 0.2.0-rc.2 adapter.
See the [full Q4/Q8 host results](QWEN36_HOST_RESULTS.md). These adapter checks
do not establish acceptance of every native desktop workflow. Updated model
metadata is saved in the development profile; reload the development app to
refresh a model list that was already open.

## Applied development profile

MiniCPM-V 4.7 Q4_K_M is configured as
`minicpm-v-4.7-35b-a3b-q4_k_m`, with 262,144 total context tokens,
8,192 advertised output tokens within that budget, and text/image input.
The GPU vision profile passed three isolated development-adapter streaming and
tool-result replay checks. Low reasoning passed 18/18 corrected bounded coding
sessions and is recommended for these fixtures. See the
[MiniCPM host results](MINICPMV_HOST_RESULTS.md) for long-context checks,
timings, memory observations and the validator correction. Reload the development
app model list if the new entry is not visible. Existing default-model and
thinking preferences were preserved.

The running development app uses `%USERPROFILE%/profiles/desktop/cordis.patch.yml`.
The initial Qwen3.8 model's label, context, output capability and input modalities
were updated, followed by the two Qwen3.6 model entries. The provider key,
credentials reference, default-model selection, other
providers and existing low-thinking preference were preserved. The original file
is backed up locally under `local-data/dsh-desktop-profile-before-aryastrata.yml.bak`
in the AryaStrata checkout; it is excluded from Git. No AryaAI source code was changed.

The relevant configuration is:

```yaml
- id: agent-default-model
  name: '@deepseek-ai/dsh-agent-default-model'
  config:
    provider: strata
    model: qwen3.8-flash-next-iq3_xxs

- id: llm-pi-ai
  name: '@deepseek-ai/dsh-llm-pi-ai'
  config:
    providers:
      strata:
        apiKeyEnv: STRATA_API_KEY
        api: openai-completions
        baseURL: http://127.0.0.1:8080/v1
        outputBudgetMode: gateway
        models:
          - id: qwen3.8-flash-next-iq3_xxs
            name: AryaStrata Qwen3.8 Flash Next IQ3_XXS - 256K
            contextWindow: 262144
            maxTokens: 8192
            input: [text, image]
            reasoningEfforts:
              'off': 'none'
              low: low
              medium: medium
              high: high
```

This is an excerpt, not a replacement for the whole profile. The existing
credential reference was retained; no key is published here. The server is
loopback-only and currently does not require a key. A fresh chat ensures the
new model metadata is used.

## Context and output budget

The model label’s 256K means 256 × 1,024 = 262,144 tokens.
262,144 is the total context ceiling, not a guaranteed amount of user text plus
unlimited output. An 8,192-token output allowance leaves at most 253,952 input
tokens before any additional system/tool budgeting, and compaction can start
earlier. The near-ceiling retrieval benchmark used 258,300 input tokens and only
128 output tokens. It does not show that the same input fits with an 8K answer.

The profile previously advertised almost the whole context as output capability
and advertised image input. The new capability metadata reserves a practical
answer budget. Image input was subsequently enabled in both the server and this development profile; the published coding and speed benchmarks remain text-only measurements. The selected output cap
is a configuration choice, not a measured optimum for every coding task.

## What was tested

- Actual development `dsh-llm-pi-ai` **0.2.0-rc.2**, its streaming adapter and
  `BlockAssembler`: **3/3** structured tool calls and replayed tool results passed.
  The probe uses the development runtime's installed packages, an isolated
  Cordis context, and a public placeholder against the local model server.
- A separate OpenAI-compatible bounded coding-agent loop: **9/9** small Python
  read/edit/test sessions passed with thinking off and **9/9** with low thinking.
  Median session times were **4.74 s** and **6.49 s** respectively.
- Three six-turn agent-style speed sessions per configuration, with four tool
  schemas, measured prompt-cache reuse and follow-up latency. These summarize
  files and do not apply code patches.

The desktop profile is configured, but a native desktop session, approval flow,
compaction, reconnect/recovery and a large-repository coding workflow were not
qualified. The authenticated desktop API was not used. The adapter probe does
not execute a real filesystem tool; its controlled tool result tests streaming
and replay fidelity. Use the recorded results within those boundaries.

## Using the profile

Keep the existing low-thinking setting for normal work unless the task calls for
another level. Thinking off was faster on the three small fixtures; those tests
are too limited to establish that it is better for complex coding.

The measured host profile serves one model request at a time. Two simultaneous
clients queued: this was not a true batch-parallel test. Prefer sequential local
model calls when evaluating latency, and include the actual tool/system prompt
size when interpreting first-token times. Fresh 32K prompts took about 11 s;
the 258K retrieval prompts took about 102 s before the answer began.
