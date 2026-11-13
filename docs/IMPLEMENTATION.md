# Implementation notes

## Current scope

Patchsmith is published at `icporcincula/patchsmith`. Proposal mode is the default for synchronous and background runs. The tool schema, runtime and ledger use the same default; the benchmark runner explicitly selects direct apply to preserve its measurement protocol. File editing, post-test restoration and patch application share the protected test-path policy. GitHub CI checks lint, byte-compilation and the offline tests on Windows and Linux.

Phases 0 through 4 and the additional hardware/community-benchmark phase are complete. Phase 4 adds a Hermes delegation skill, recent-run status, and a local token ledger. Phase 5 is complete; its measured candidate was reverted after a fixture success regression.

## Codex desktop beta

The repo marketplace installs the same Python engine behind a local stdio MCP
server. Its only tool accepts a task and an absolute checkout path, fixes the
mode to `propose`, and returns the existing engine result as MCP structured
content and JSON text. The Codex entry point defaults `PS_DATA_DIR` to
`~/.patchsmith` before loading the engine. Hermes retains its per-profile
storage default. Tests and the endpoint come from the process environment.

The stdio regression test starts the packaged entry point and a scripted
loopback model. It checks that the server rejects an apply-mode override and
returns a tested patch while preserving the source file.

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


## Publication preparation and remaining work

Local Git preparation is complete on main, with implementation history and green phase tags retained. Commits efb789f and bd99a6a add the publishing guide, private/generated-file exclusions and consistent LF text attributes. No remote is configured and no push or submission has been performed. See docs/PUBLISHING.md for the owner handoff.

A fresh local clone at bd99a6a contained 175 tracked files matching their committed bytes, excluded private/generated content, and passed the offline suite: 99 passed, 1 skipped in 44.57s. A pattern-based credential scan over reachable Git blobs found zero matches; this is not an exhaustive secret audit. These checks do not replace the final Hermes installation gate.

Remaining required delivery work: connect the owner's empty remote once its URL is available, publish the source, complete repository/catalog URLs and the full source SHA, align final release documentation, retake and review the <=90-second demo with separate captions and voice disclosure, rerun the clean-clone offline/Hermes gates, and prepare SUBMISSION.md. Catalog submission, public posting and the form remain owner steps. No final video retake or submission draft is complete yet.

Phase 5 speed/context measurements are complete. The candidate did not meet the keep rule; final delivery preparation is next.


## Phase 5: measured context experiment

Phase 5 is complete. The repo-map and failure-digest candidate was reverted. Implementation successes: 33/35 before, 32/35 after. Overall median turns: 6.0 before, 5.0 after; overall median seconds: 16.8125 before, 22.125000000029104 after. Both cohorts retained all 40 runs and recorded full GPU residency. Protected-test outcomes remain separate from implementation successes.

Same qwen3.5:9b model digest, quantization, loaded context, local Ollama 0.17.6 endpoint, eight fixtures, five runs each, one attempt, 25 total turns and 24000 cumulative estimated tokens. One sequential cohort per version; stochastic responses and order/thermal effects are uncontrolled. Offline fake-model tests briefly overlapped the baseline. No extra GPU model workload was started. Small synthetic fixtures do not establish gains on large repositories.

| fixture | expected before | expected after | median turns before | median turns after | median secs before | median secs after |
|---|---|---|---|---|---|---|
| bug1 | 5 | 5 | 5 | 5 | 9.51600000000326 | 11.0 |
| bug2 | 5 | 5 | 6 | 7 | 14.905999999959022 | 20.20299999997951 |
| feature | 3 | 2 | 8 | 8 | 43.32799999997951 | 95.51500000001397 |
| multifile | 5 | 5 | 7 | 5 | 21.34399999998277 | 22.03100000001723 |
| refactor | 5 | 5 | 6 | 5 | 19.10899999999674 | 22.57799999997951 |
| offbyone | 5 | 5 | 7 | 6 | 19.96799999999348 | 24.71899999998277 |
| javascript | 5 | 5 | 5 | 5 | 16.81300000002375 | 24.67200000002049 |
| blocked | 5 | 5 | 5 | 4 | 12.01600000000326 | 10.76600000000326 |

The candidate added a depth-limited, git-visible map with at most 100 entries, 2000 display characters, six symbols per file and 128 KiB of source reads. Failure digests extracted unittest/pytest/Node failures and assertions, preserved exit status and original test output, and remained inside existing output/token limits. Candidate tests: 106 passed, 2 skipped in 47.83s. The map followed the existing path jail and visibility rules; source was never imported or executed.

The candidate is reverted. Reproduction and comparison are in eval/phase5-candidate.patch, eval/phase5-reproduction.json and eval/phase5_compare.py. Public evidence omits disposable Git base identifiers, transient transcript paths and incidental start/check/residency-expiry timestamps. Relative links to the released transcripts remain in the result files. Every run, failure, outcome and numeric measurement is retained. Untouched originals and candidate source are preserved privately at C:/tmp/patchsmith-phase5-originals/experiment. The saved candidate patch reproduces all measured source hashes in a fresh baseline clone.


Final retained-runtime gate: 99 passed, 1 skipped in 44.05s. Clean-copy Hermes validate --install-deps and doctor --ci passed with four tools, safe security scan and matching declarations. An immutable local reinstall verified runtime bytes against source. All 80 runs and numeric measurements match the untouched originals after the disclosed identifier/path/timestamp omissions. The active loop is byte-identical to the pre-experiment source; candidate-only module and tests were removed. No publication occurred.
