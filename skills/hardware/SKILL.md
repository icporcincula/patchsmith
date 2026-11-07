---
name: hardware
description: Inspect local hardware and models, explain tested versus estimated compatibility, and prepare a reproducible Patchsmith contributor benchmark.
---

Call inspect_hardware with no arguments to use the configured local endpoint. Never invent an endpoint or model. Inventory describes the Hermes host; WSL/container limits and a private-network model server can describe different machines. State that uncertainty before comparing them.

Present detected CPU, RAM, GPU total/free memory, backend version and installed models. Preserve unknown fields. Missing GPU probes do not prove CPU-only operation. Unified RAM is not dedicated free VRAM, and GPU cards are not pooled by the estimate.

Use tested_configurations as evidence with its provenance, counts, budgets and source path. Matching fields show similarities, not reproduced performance. Never fill historical unknown quantization/version fields from today's installed model metadata. Model names can change weights. Contributor supplied results remain unverified until independently reproduced. Keep implementation success separate from the expected blocked guardrail.

The estimate uses model weight bytes times 1.2 plus 2 GiB, and excludes context-dependent KV cache. Quote the classification exactly. A total-VRAM-only classification does not fit the observed free-VRAM budget; a loaded model already consumes memory. Describe it as a rough capacity screen, never a speed, context-length or coding-quality guarantee. Inventory can include embedding models; memory capacity does not establish generative or tool-calling support. Prefer an installed, actually tested configuration when applicable; suggest a local benchmark to resolve unknowns. Do not download or install models automatically.

For contributor evidence, use the repository command documented in benchmarks/README.md: python -B eval/benchmark.py --model MODEL --runs 5 --require-gpu --out benchmark-output. It exercises only bundled synthetic fixtures, exports a versioned report and retains raw results/transcripts. CPU/partial-offload tests omit --require-gpu and stay explicitly labelled. Keep failed runs. Review the bundle for local paths before publication; user initiates any pull request or upload. No automatic publication.
