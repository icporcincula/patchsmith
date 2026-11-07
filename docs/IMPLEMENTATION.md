# Implementation notes

## Current scope

Phases 0 through 4 and the additional hardware/community-benchmark phase are complete. Phase 4 adds a Hermes delegation skill, recent-run status, and a local token ledger. Phase 5 remains optional and must be measured before keeping performance changes. Final delivery preparation follows the latest green phase.

## Additional phase: hardware compatibility and community benchmarks

Implemented after Phase 4 at the user's request: inspect_hardware, the patchsmith:hardware skill, an evidence-linked tested registry and eval/benchmark.py for contributor bundles. No downloads or uploads are performed.

- Inspect CPU, system RAM, GPU and available VRAM, available local backends, and installed local models. Collect only what is needed; no automatic uploads.
- Show tested configurations separately from estimated compatibility. A model fitting in memory does not establish useful speed or coding reliability.
- Record hardware, operating system, model identifier and quantization, backend/version, context and task budgets, GPU offload, independent test outcomes, turns, latency, and token estimates.
- Start with hardware inspection, matching tested configurations, and exporting a benchmark report. Automatic model downloads and installation are outside the first version.
- Provide one reproducible benchmark command and a versioned result format. Contributors can submit configuration, raw results, and transcripts through pull requests.
- Label contributor results as contributor supplied until reproduced. Preserve failed runs and distinguish untested estimates. Reports should include no private source or credentials; contributors explicitly initiate publication.
- Keep current claims limited to the configurations actually measured in eval/. No pricing or unmeasured reliability claims.

## Phase 4 integration choices

Use Hermes PluginContext.register_skill for a read-only namespaced skill and register_command for /patchsmith status. Preserve the existing two tool names. Store summary records under ~/.patchsmith/runs; transcripts remain at their existing locations. The ledger records run facts without task text, file contents, endpoint, or credentials. Token counts are estimates of local edit-loop work, including repeated prompt processing; they are not unique tokens or financial savings.


Hermes's installed sequential executor inherits a configurable default 420-second deadline. Phase 4 therefore includes optional background calls and task_status. Job handles are process-local, one background job at a time, with the last 50 handles retained. This is not a durable service; keep Hermes open. The shipped skill is available as patchsmith:delegate and can be preloaded with Hermes's -s option. The observed small main model did not reliably select it automatically, so documentation states the measured preloading path and its limits.


### Hardware phase implementation limits

Windows and Linux CPU/RAM plus NVIDIA memory probes are supported; Linux DRM exposes some other adapters. macOS reports CPU/RAM/display names with dedicated GPU memory unknown. Inventory describes the Hermes host, including WSL/container limits. Only the configured API is queried; Ollama version/tags/residency metadata are detected, while other compatible APIs retain unverified backend identity and unknown model sizes. The tool does not scan network ports or model directories.

Weight estimates use bytes x 1.2 + 2 GiB on one GPU or total system RAM, excluding context-dependent KV cache/runtime requirements. Historical evidence has missing CPU/RAM/backend-version/quantization fields; these remain null rather than being retroactively inferred. Matching fields do not establish reproduced performance.

The contributor command runs only bundled synthetic fixtures, refuses an existing output directory, retains all raw outcomes and emits a version 1 summary with independent test exits and per-run metrics. It omits endpoint/task/source/output/local paths from that summary; raw transcripts still require review before publication. Full GPU residency is measured only with --require-gpu. Schema validation checks consistency, not independent reproduction. Contributor provenance remains unverified by default.


### Hardware phase acceptance

Windows regression suite: 99 passed, 1 skipped in 45.10s. Clean-copy Hermes validation (including dependency check) and doctor passed with four declared/registered tools; both packaged skills resolved and the installed runtime files matched source. The hardware skill passed its frontmatter validator.

Real GPU smoke export: bug1 done with independent tests green, 5 turns, 9.625 seconds, 5670 estimated tokens; blocked fixture blocked without edits and independent tests still red, 5 turns, 12.78100000001723 seconds, 6228 estimated tokens. Both runs recorded full GPU residency. These two smoke runs verify the new report path, not a new full-suite reliability estimate. They ran before the final inventory-only identity/blank-argument refinements; the coding loop was unchanged. The existing 40-run Phase 3 evidence remains the tested registry's reliability source.

Live Hermes verification used the packaged hardware skill and the configured endpoint. The small model supplied an empty optional endpoint: the first run rejected it, then the handler was corrected to use PS_ENDPOINT for an empty field and a regression test added. Both the failed run and corrected session are retained. Structured inventory correctly distinguished Windows physical RAM from WSL's limited RAM and flagged the private-network server's host uncertainty. Initial model prose confused total/free memory and today's quantization with historical evidence; a same-session follow-up corrected the classification and historical unknowns. The skill now explicitly instructs those distinctions. This is measured tool/preload behavior, not a guarantee that model narration is always accurate.

Evidence lives in eval/hardware-*, eval/hardware-smoke/ and eval/hermes-session-hardware*. Untouched originals are retained privately. Public evidence normalizes trailing console whitespace, replaces a generic capacity word caught by the literal release filter with [capacity margin], and replaces the temporary validation directory with <clean copy>. No run, outcome, or numeric measurement was removed or changed. No publication was performed.
