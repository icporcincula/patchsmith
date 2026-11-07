# Implementation notes

## Current scope

Phases 0 through 4 are complete. Phase 4 adds a Hermes delegation skill, recent-run status, and a local token ledger. Phase 5 remains optional and must be measured before keeping performance changes. Final delivery preparation follows the latest green phase.

## Planned follow-up: hardware compatibility and community benchmarks

After Phase 4, consider a small hardware inspection tool paired with a skill that explains suitable local configurations. Finish final delivery preparation first if the schedule is tight. This is planned work, not a current capability.

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
