# Hardware and contributor benchmarks

Use the `inspect_hardware` Hermes tool or preload `patchsmith:hardware` with Hermes `-s`. Inspection is read-only and uses the configured PS_ENDPOINT. It does not load models. CPU, RAM and GPU fields describe the plugin host; private-network APIs may run on a different host. Windows and Linux have CPU/RAM probes, NVIDIA cards have total/free memory probes, Linux DRM exposes some other adapters. macOS reports CPU/RAM with dedicated GPU memory unknown. Unsupported probes stay unknown. Backend identity/version is detected for Ollama; other compatible APIs list served models with identity unverified. This does not scan all ports or disks for model files.

Memory estimates compare each installed model's reported weight bytes with a single GPU or system RAM: weights x 1.2 + 2 GiB. This is a rough capacity screen, excludes context-dependent KV cache/runtime needs, and does not predict speed or reliability. Unknown sizes produce no estimate. Current free VRAM can already include loaded models. Multiple cards are not pooled; system RAM is total capacity, not free memory.

`tested.json` contains only measurements with linked evidence. Historical missing fields are null. Shared GPU/model/backend fields do not establish equivalent weights or performance. The current maintainer evidence is one configuration, with both successes and failures preserved.

## Reproduce and contribute

Install Python, Git, Node (for the JavaScript fixture), and serve an already installed local tool-calling model through the configured endpoint. From the repository root:

```sh
python -B eval/benchmark.py --model qwen3.5:9b --runs 5 --attempts 3 --require-gpu --out benchmark-output
python -B eval/benchmark.py --validate benchmark-output/report.json
```

The command uses only bundled synthetic fixtures in fresh temporary checkouts, baseline failing tests and independent final test runs. `--require-gpu` verifies full Ollama GPU residency on every run. Omit it for CPU or partial-offload experiments: offload remains explicitly unmeasured, never counted as full GPU. Use `--fixtures bug1,blocked --runs 1` for a smoke run, not a full-suite reliability claim. PS_MAX_TURNS and PS_CTX_BUDGET configure budgets and are recorded. An existing output directory is refused; use a new directory for each experiment and retain failures.

The bundle contains `report.json`, `raw-results.json`, a raw result table and transcripts. The summary schema is version 1: suite identity/content hash and requested run counts; hardware and backend/version; model/quantization/weight size; attempt/turn/token budgets; per-run status, independent exit code, latency, turns, estimated tokens and measured GPU offload. Missing observations remain null. Reports from interrupted runners are incomplete; preflight failures have no benchmark claim. The validator checks structure and internally consistent counts/outcomes; it does not independently reproduce measurements.

To contribute after this repository is published, open a pull request adding the bundle under `benchmarks/contributions/<unique-name>/`, plus your reproduction command, OS/backend/model versions and quantization if the API could not report them. Review raw transcripts and command lines for local paths before sharing. These fixtures contain no private repository source; never add credentials or private tasks. Publication is initiated by the contributor. No command here uploads anything.

All contributions start as **contributor supplied; not independently reproduced**. A maintainer can reproduce the same fixture hash/model weights/budgets, retain the second run's evidence and then label it reproduced. Review all requested runs, including failures and expected blocked outcomes; do not equate the blocked guardrail with coding success. Do not add a configuration to `tested.json` based only on its model fitting in memory. No automatic model downloads, installation or public submission are included.
