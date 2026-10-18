# Q4 -> Q8 on this host

RTX 4070 Ti SUPER 16 GiB, i9-14900KF, 63.8 GiB RAM, Windows 11 (10.0.26200),
AryaStrata 0.1.45 / commit 4820a00e, engine-poly prebuilt.
Same run config on both sides except the model file (and the pack that holds
the expert profile, which is routing statistics and so identical in kind).
Medians with ranges are in each suite's own README/results.json.

## gemma4

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | - | 68.0 | - |
| first token, short chat (s) | - | 0.4 | - |
| 4K prompt tok/s | - | 1,736.0 | - |
| 16K prompt tok/s | - | 3,460.6 | - |
| agent turn decode tok/s | - | 76.9 | - |
| agent cache hit % | - | 67.5 | - |

speed suite wall time: Q4 None s, Q8 100 s. Both runs report quant=Q8_0 (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | 9 of 9 passed |
| vision (OCR, chart, shapes, two images) | 12 of 12 passed |
| long-context agent (229,376-token repo) | not run |

| context length | recall | first token (s) |
| ---: | :---: | ---: |
| 65,536 | PASS | 20.71 |
| 131,072 | PASS | 54.12 |

## lfm25

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | - | 96.8 | - |
| first token, short chat (s) | - | 0.2 | - |
| 4K prompt tok/s | - | 2,642.2 | - |
| 16K prompt tok/s | - | 5,969.7 | - |
| agent turn decode tok/s | - | 99.5 | - |
| agent cache hit % | - | 67.5 | - |

speed suite wall time: Q4 None s, Q8 69 s. Both runs report quant=Q8_0 (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | 0 of 9 passed |
| vision (OCR, chart, shapes, two images) | not run |
| long-context agent (229,376-token repo) | not run |

| context length | recall | first token (s) |
| ---: | :---: | ---: |
| 65,536 | PASS | 9.74 |
| 131,072 | PASS | 24.03 |

## minicpmv

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | - | 83.2 | - |
| first token, short chat (s) | - | 0.3 | - |
| 4K prompt tok/s | - | 1,366.4 | - |
| 16K prompt tok/s | - | 2,541.3 | - |
| agent turn decode tok/s | - | 93.6 | - |
| agent cache hit % | - | 68.8 | - |

speed suite wall time: Q4 None s, Q8 116 s. Both runs report quant=Q8_0 (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | 9 of 9 passed |
| vision (OCR, chart, shapes, two images) | 12 of 12 passed |
| long-context agent (229,376-token repo) | not run |

| context length | recall | first token (s) |
| ---: | :---: | ---: |
| 65,536 | PASS | 34.58 |
| 131,072 | PASS | 86.03 |

## ornith

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | 92.4 | 107.8 | +16.7 % better |
| first token, short chat (s) | 0.3 | 0.3 | -13.4 % better |
| 4K prompt tok/s | 1,279.1 | 1,358.0 | +6.2 % better |
| 16K prompt tok/s | 2,428.7 | 2,615.1 | +7.7 % better |
| agent turn decode tok/s | 112.7 | 115.4 | +2.4 % better |
| agent cache hit % | 68.2 | 68.2 | -0.0 % worse |

speed suite wall time: Q4 108 s, Q8 102 s. Both runs report quant=Q8_0 (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | 9 of 9 passed |
| vision (OCR, chart, shapes, two images) | 12 of 12 passed |
| long-context agent (229,376-token repo) | 3 of 3 passed |

| context length | recall | first token (s) |
| ---: | :---: | ---: |
| 65,536 | PASS | 35.92 |
| 131,072 | PASS | 93.31 |

## tiel

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | - | 66.3 | - |
| first token, short chat (s) | - | 0.8 | - |
| 4K prompt tok/s | - | 472.0 | - |
| 16K prompt tok/s | - | 568.3 | - |
| agent turn decode tok/s | - | 67.2 | - |
| agent cache hit % | - | 69.5 | - |

speed suite wall time: Q4 None s, Q8 278 s. Both runs report quant=UD-Q8_K_XL (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | 9 of 9 passed |
| vision (OCR, chart, shapes, two images) | 8 of 12 passed |
| long-context agent (229,376-token repo) | not run |

| context length | recall | first token (s) |
| ---: | :---: | ---: |
| 65,536 | PASS | 151.28 |
| 131,072 | PASS | 338.66 |

## tool-snapshots

| measure | Q4 (as installed) | Q8 | change |
| --- | ---: | ---: | ---: |
| decode tok/s, short chat | - | - | - |
| first token, short chat (s) | - | - | - |
| 4K prompt tok/s | - | - | - |
| 16K prompt tok/s | - | - | - |
| agent turn decode tok/s | - | - | - |
| agent cache hit % | - | - | - |

speed suite wall time: Q4 None s, Q8 None s. Both runs report quant=- (the tool reads it from the file name, which these files do not carry); the model_name field is the reliable label.

| suite | result |
| --- | --- |
| agent core (tools, file edits, tests) | not run |
| vision (OCR, chart, shapes, two images) | not run |
| long-context agent (229,376-token repo) | not run |

## Tuned profiles

`--tail-skip 6` measured through the full suite, against the same family's shipped profile:

| Family | decode before | decode tuned | agent before | agent tuned | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| tiel | 66.3 | 82.6 | 67.2 | 84.4 | adopted |
| ornith | 107.8 | 107.6 | 115.4 | 107.6 | not adopted: the gain did not reproduce |

