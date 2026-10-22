# Brief: `propose_change` has an undiscoverable contract, so agents retry it forever

**Status:** open
**Reported by:** field engineer running local models (Qwen3.6-35B-A3B UD-Q4_K_XL)
**Symptom as reported:** "made a good plan but failed every tool use"
**Symptom as measured:** reads and queries worked; the *edit* tool failed 13 times in a row
**Severity:** high for any agent that has to edit an L5X, independent of model size or quant

---

## 1. Summary

`propose_change(request: string)` accepts a free-form string but validates it against a
JSON change-set schema that is **documented nowhere**: not in the tool description, not in the
`rockwell-l5x` skill, and not in the error messages. Every rejected call returns the same
generic sentence, so a model has no way to learn the contract from failure.

Result: the agent plans correctly, then burns its entire remaining context retrying the same
call with different guesses, and never completes the edit. A stronger model does not fix this;
it only guesses luckier.

---

## 2. Evidence

### 2.1 Source session

```
Tool Fail/dsh-session-session-5cef01e7-...zip   (DeepSeek API run, 131 tool calls — not the subject)
Tool Fail/dsh-session-session-91e91869-5e2b-4cde-ad9d-5eeb2a4f0c49.zip   <-- the failing run
```

Model: `strata:qwen3.6-35b-a3b-ud-q4_k_xl`. 55 steps, 62 tool calls, 15 failed results.

### 2.2 What worked

Steps 1–33 issued and completed normally:

| tool | result |
|---|---|
| `skill` (rockwell-l5x) | skill body returned |
| `glob` | file list returned |
| `studio_sdk_status` | `{"available":true,...}` |
| `open_project` ×3 | project ids returned |
| `export_acd_to_l5x` ×2 | L5X written |
| `project_overview` | overview returned |
| `compare_projects` | revision hashes returned |
| `get_component` ×4 | routines returned |
| `grep` ×2 | 28 and 136 matches |

So the tool transport, schemas, and argument marshalling all work.

### 2.3 What failed

| step | tool | error |
|---|---|---|
| 1 | `todo_write` | `"todos[0].tags" is not a declared property (additionalProperties: false)` |
| 25 | `get_component` | `COMPONENT_NOT_FOUND: tag VFD_FEEDBACK not found` |
| **34–46** | **`propose_change`** | `INVALID_CHANGE_SET` / `UNSUPPORTED_REQUEST` / `INVALID_REQUEST` ×13 |

Steps 34–46 are consecutive. The run ends there.

### 2.4 What the model actually sent

Step 36 — free-form prose in a parameter that expects JSON:

```json
{"project_id":"2a6cac9d-...","output_path":"...\\Seco_Cooler_HOOD_DB_Temp.l5x",
 "request":"Add Bridge VFD dynamic brake temperature alarming:\n\n1. In HOOD program, routine A03_Trolley_Bridge_VFD_Inputs, insert a new rung at the end ... XIC(BridgeVFD_DB_OK)OTE(B_T_Drive.Dyn_Brake_Temp);"}
```

→ `UNSUPPORTED_REQUEST: Provide an explicit JSON edit request`

Steps 40–41, 42–46 — correct top-level shape, guessed operation names:

```json
{"version":1,"operations":[{"kind":"set_tag_description","name":"SYSTEM_ALARM_RESET","scope":"","description":"System-wide alarm reset"}]}
```

→ `INVALID_REQUEST: Edit request must be an object with operation`
→ `INVALID_REQUEST: Unsupported operation or missing edit fields`

---

## 3. Root cause

Three compounding gaps:

1. **The parameter is a string.** `request` is `type: string` in the tool schema, so the nested
   JSON contract cannot be expressed to the model natively. The model sees "an explicit JSON edit
   request" and has to invent the shape.
2. **The operation vocabulary is not documented.** Neither the tool description nor the
   `rockwell-l5x` skill lists valid `kind` values or their fields.
3. **The error does not teach.** Every wrong guess returns the same sentence:
   `Unsupported operation; arbitrary XML replacement is not accepted`. No list, no hint, no
   pointer. Retrying with a different guess has the same expected value as retrying identically.

Gap 3 is what turns a one-shot failure into a 13-step spiral.

---

## 4. Reproduction and probe transcript

Verified live against a real export, 2026-10-22:

```
open_project("...Seco_Cooler_baseline_uploaded.L5X")
  -> project_id 4d902843-6064-4260-9907-646daf15af8c

prepare_change_set(request='{"version":1,"operations":[]}')
  -> INVALID_CHANGE_SET: version must be 1 with between 1 and 100 operations
      (top-level shape CONFIRMED)

prepare_change_set(request='{"version":1,"operations":[{"kind":"set_tag_description",
                   "name":"SYSTEM_ALARM_RESET","scope":"","description":"test"}]}')
  -> INVALID_CHANGE_SET: Unsupported operation; arbitrary XML replacement is not accepted

prepare_change_set(request='{"version":1,"operations":[{"kind":"bogus"}]}')
  -> INVALID_CHANGE_SET: Unsupported operation; arbitrary XML replacement is not accepted
      (identical message for a clearly-invalid kind — no enumeration)
```

Note that `prepare_change_set` and `propose_change` share the schema and the message, so the probe
is valid evidence for both.

---

## 5. Required changes

### P0 — make the error enumerate the contract

In the change-set validator, replace the generic rejection with a message that states what is
accepted. Minimum viable:

```
INVALID_CHANGE_SET: unsupported operation "set_tag_description".
Supported operations: <list of kinds>, each: {"kind": ..., <required fields>}.
Example: {"version":1,"operations":[{"kind":"<kind>", ...}]}
```

**Acceptance:** a model that sends an invalid `kind` receives the list, and its next attempt
uses a valid one. Measure on the failing session shape: ≤2 `propose_change` attempts.

### P1 — publish the schema where the model will see it

Either:

- (preferred) change `request` from `type: string` to a structured object schema
  (`{"version":1,"operations":[{...}]}` with `kind` as an enum and per-kind `required`
  fields), so the contract is native and validated client-side; or
- add the full change-set schema, with one worked example per operation kind, to the
  `rockwell-l5x` skill body so it is in context before the first edit attempt.

**Acceptance:** a local model with no prior knowledge emits a syntactically valid change set on
its first or second attempt.

### P2 — related: undeclared properties on `todo_write`

Same class of failure, one step earlier: the model added `tags` to each todo, and
`additionalProperties: false` rejected the whole call. Consider either declaring `tags`
(if it is meaningful) or making the error name the accepted property set.

---

## 6. Where to look

The tool implementation was **not** found in this workspace. A case-insensitive search for the
error string across

```
C:\Users\KNPhu\profiles\desktop\node_modules
C:\Users\KNPhu\AppData\Local\Programs\AryaAI\resources
```

returned nothing, so it is most likely compiled into the application bundle or served by a
separate process rather than present as readable JS/Python.

Start from the string `arbitrary XML replacement is not accepted` and the identifiers
`INVALID_CHANGE_SET`, `UNSUPPORTED_REQUEST`, `INVALID_REQUEST`.

Relevant tool surface for context (schemas are in the agent's tool list):

- `prepare_change_set(project_id, request)` — "Validate a version-1 JSON operations array"
- `propose_change(project_id, request, output_path)` — "Create a new draft L5X from an explicit JSON edit request"
- `validate_change_set(project_id, request)`
- `apply_change_set(project_id, request, source_sha256, output_path)`

---

## 7. What this is not

- **Not a model-quality problem.** The plan this model produced was ranked first of seven local
  models on a separate L5X task (96.7/100 on grounding + coverage). Its reads here were clean.
- **Not specific to Qwen3.6 or to 4-bit quantisation.** Nothing in the failure depends on the
  model's weights; it depends on information the model was never given.
- **Not a transport or schema-validation bug.** `additionalProperties`, required fields and the
  version check all behaved correctly — they simply refuse without explaining.

---

## 8. Verification the fixer should run

1. Open the export used above
   (`Seco Cooler/Seco_Cooler_baseline_uploaded.L5X`, sha256 `dd50283e...`).
2. Send an invalid `kind`; confirm the reply enumerates valid operations.
3. Re-run the failing session's edit request through one local model with the fix in place;
   confirm it converges in ≤2 attempts and produces a draft L5X.
4. Confirm the same request still fails safely (no file written, no source mutation) when the
   change set is genuinely malformed.
