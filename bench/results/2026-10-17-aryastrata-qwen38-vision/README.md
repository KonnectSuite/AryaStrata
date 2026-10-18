# Qwen3.8 Flash Next vision smoke check

On the AryaStrata Windows host (i9-14900KF, RTX 4070 Ti SUPER 16 GB, 64 GB RAM),
GPU vision was enabled after the text benchmark suite. Engine release 0.1.45;
IQ3_XXS language model; BF16 `mmproj-Qwen3.8-Flash-Next-BF16.gguf` projector.
The existing 262,144 total context and 1,792 MiB reserve were retained.
Vision uses `strata-vision.exe`, GPU on, `max_tokens: 1024`.

The [synthetic image](shapes-text.png) was sent as a PNG data URL in an
OpenAI-compatible `image_url` content item alongside this text:

> Describe the two colored shapes, their left/right positions, and transcribe the text at the bottom.

Temperature 0, max output 180, thinking disabled. One trial, 2.114 seconds
wall time. The model correctly reported a red square on the left, blue circle
on the right, and `VISION 7319`. [Raw response and health](result.json).
Health reports `images: true`, `loaded: true`, context 262144.

This checks image understanding, not image generation, comprehensive vision
accuracy, the native DSH attachment workflow, or text performance with vision
loaded. Earlier text-only benchmark records remain unchanged.
