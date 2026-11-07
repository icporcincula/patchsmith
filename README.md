# patchsmith

A Hermes plugin with `implement_task` for bounded local coding and `apply_patch` for applying a reviewed proposal. Your main agent hands a **single, well-specified coding task** to a **local model** (served through a local OpenAI-compatible endpoint; only Ollama has been measured). The local model edits the code under hard budgets and the tool returns the diff.

Why: the expensive model keeps its context and tokens for planning and review. The mechanical edit-run-fix loop runs on your own machine, with zero API spend and no code leaving it.

## Install

```
hermes plugins install <owner>/patchsmith --enable
```

You need a local OpenAI-compatible server with a tool-calling model, for example `ollama pull qwen3.5:9b`.

## Configuration (all optional)

| Variable | Default | Meaning |
|---|---|---|
| `PS_ENDPOINT` | `http://127.0.0.1:11434/v1` | Local API base (must be a local address) |
| `PS_MODEL` | `qwen3.5:9b` | Model identifier |
| `PS_MAX_TURNS` | `25` | Model turns per task (hard cap 60) |
| `PS_CTX_BUDGET` | `24000` | Approximate token budget for the whole run |
| `PS_TEST_COMMAND` | none | Test command the model may run |

Each can also be passed as an argument of the tool call. If Hermes runs in WSL and Ollama on Windows, point `PS_ENDPOINT` at the Windows host address.

## The tool

`implement_task(task, workdir, max_turns?, test_command?, context_budget_tokens?, model?, endpoint?, keep_partial?, mode?, attempts?, fallback_model?)` returns JSON:
`status` (`done` / `blocked` / `error`), `reason`, `turns`, `tokens_est`, `files_changed`, `diff`, `note`, `transcript_path`, `patch_path`, `patch_sha256`, `base_head`, `applied`, `attempt_history`, `handback`.

## Propose, review, apply

Set `mode="propose"` to run the full loop in a temporary detached Git worktree. A plain directory is copied instead. Dirty, ignored and untracked files are copied so the model sees the current bytes. Linked checkout content is refused. The temporary checkout is removed when the run finishes, including on failure. Your original checkout receives no code, transcript or patch writes during proposal generation.

A successful proposal returns its diff, `patch_path`, SHA-256 in `patch_sha256`, `base_head`, and `applied: false`. The complete patch and provenance record live beside the transcript under `~/.patchsmith/proposals/<id>/`. The returned diff may be clipped; the saved patch is complete. Only ordinary text patches are supported.

1. Call `implement_task(task=..., workdir=..., test_command=..., mode="propose")`.
2. Show the returned diff for review and obtain the user's approval.
3. Call `apply_patch(patch_path=...)` with that exact saved path.

`apply_patch` verifies the stored hash, original HEAD and branch, affected file bytes/modes and index entries. It validates the patch's actual paths against the same jail and test-file restrictions as the coding loop, then runs `git apply --check` before applying. A stale or tampered patch is refused; unrelated local edits are preserved. The result reports `applied: true` only after application. Tests run in the isolated proposal; rerun the authorized tests after applying if you need verification against later unrelated edits.

The default `mode="apply"` retains direct-edit behavior and existing rollback rules. Git-backed proposals require an initial commit. Storage must be outside the chosen workdir. Detached worktrees share repository metadata; the configured test command remains trusted code, not an operating-system sandbox.

## Retries and failure handback

Set `attempts=3` for up to three fresh contexts (default one, maximum three). A blocked attempt or a claimed completion with failing configured tests can retry after its edits are rolled back. The next context receives the original task plus a clipped factual failure digest. Test-file changes, moved Git state, endpoint errors and incomplete rollback stop immediately. `keep_partial` affects the final failure only; intermediate attempts always roll back.

`max_turns` and `context_budget_tokens` apply to the whole call, shared across attempts. The token budget now counts cumulative prompt and completion use, using server usage when provided and character estimates otherwise. A request reserves its estimated prompt cost and caps the requested completion to the remaining allowance. Token accounting is approximate; a server reporting a larger prompt than estimated can exhaust the allowance after a response, before tool execution. Retries do not replenish either budget.

Optional `fallback_model` selects a different local model for the last allowed attempt only, at the same validated local endpoint. Early success ends the run before fallback. No fallback model was benchmarked; the evaluation uses the same model for every attempt.

Every run returns `attempt_history` with status, reason, model, turns, tokens, files touched and clipped test output for each attempt. Final failure also returns `handback`: `what_was_tried`, `last_failure`, `files_touched` (a list), and `suggested_next`. These are built from recorded facts and stop reasons. Without a configured test command, completion remains unverified.

## Safety model (enforced by the plugin, not requested of the model)

- **No shell.** The model has only: `read_file`, `grep`, `glob`, `git_status`, `git_diff`, `write_file`, `edit_file`, `run_tests`, `finish`. `run_tests` runs only the configured test command.
- **Path jail.** Writes outside `workdir`, through links, or under `.git` / `node_modules` are refused.
- **Test files are read-only.** If they change anyway they are restored and the run is `blocked` (`test_files_modified`).
- **Budgets.** Shared total turn and token budgets end the run as `blocked`.
- **Repeat guard.** The same tool call three times without progress ends the run.
- **Auto-finish.** Green tests after an edit end the run as `done`, so a small model cannot talk itself out of a fix.
- **Revert on failure.** `blocked` / `error` runs revert the files they touched unless `keep_partial` is true.
- **HEAD/branch check.** A run that moves HEAD or branch is `blocked`.
- **Network.** Only the configured local endpoint; non-local endpoints are refused. No telemetry.
- The agent should pass only a `test_command` the user authorized: it executes in your checkout.

## Reliability (measured)

Measured in direct apply mode at `phase-1-green`, before proposal support. The proposal flow is verified separately in `eval/hermes-session-propose.txt`.

Command: `python -B eval/run_eval.py --runs 5 --model qwen3.5:9b --require-gpu --out eval/results-gpu.json`. Eight fixtures, five fresh checkouts each, default budgets. Model: `qwen3.5:9b` through Ollama. Every run records the loaded model's full size in VRAM, independently reruns tests, and saves its transcript. Only Ollama was measured; no second-backend results are claimed.

| fixture | runs | done | blocked | error | tests green | expected outcome | full GPU | median turns | median secs |
|---|---|---|---|---|---|---|---|---|---|
| bug1 | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 6 | 10.796999999991385 |
| bug2 | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 6 | 15.10999999998603 |
| feature | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 9 | 84.10900000002584 |
| multifile | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 7 | 22.0 |
| refactor | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 5 | 16.98499999998603 |
| offbyone | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 7 | 20.437000000005355 |
| javascript | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 6 | 24.65700000000652 |
| blocked | 5 | 0 | 5 | 0 | 0/5 | 5/5 | 5/5 | 5 | 11.984000000025844 |

35/35 implementation runs returned done with independently green tests; 5/5 protected-test requests returned blocked with tests still red and no files changed.

The blocked fixture intentionally requests a protected test edit; green tests would be an unexpected outcome for it. The expected-outcome column separates this guardrail result from implementation success. Failed runs are retained rather than rerolled. Raw per-run results, baseline and final test output, exact elapsed seconds, token estimates and GPU evidence are in `eval/results-gpu.json`; transcripts are in `eval/results-gpu.transcripts/`.

These are small synthetic tasks on one machine with one model, not evidence of large-project or ambiguous-task reliability. The older two-fixture CPU measurements remain in `eval/results.json` and `eval/results-cpu.table.md`.

## Hermes setup note

Hermes can hide plugin tools behind its `tool_search` layer. A small local agent model may fail to discover `implement_task` that way (it did in our test with a 9B model). If so, expose tools directly: `hermes config set tools.tool_search.enabled off`.

## When to use it vs `delegate_task`

Use `implement_task` for bounded, precisely specified edits that have a test command, where privacy or token spend matters. Use `delegate_task` (or your main model) for open-ended work, large refactors, or anything without a test to check.

## Known limits

- Well-specified single- or two-file tasks only; no claims beyond the table above.
- Needs a model with working tool calling.
- One task per directory at a time.

## Development

`python -m pytest tests -q` (offline; uses a scripted fake model server). License: MIT.

## Retry evaluation (Phase 3)

Command: `python -B eval/run_eval.py --runs 5 --attempts 3 --model qwen3.5:9b --require-gpu --out eval/results-retries-gpu.json`. Same eight fixtures, five fresh checkouts per fixture, default shared total budgets, no fallback model.

32/35 implementation runs succeeded on the first attempt; 32/35 succeeded within three attempts. 5/5 protected-test requests ended blocked with red tests and no edits. 40/40 runs retained full GPU residency.

No measured retry improvement in this sample. Phase 3 enforces a cumulative token allowance; the historical Phase 1 table used a per-request context allowance, so it is not a controlled before/after comparison. Failures are retained. The blocked fixture is a guardrail check, not an implementation success.

| fixture | runs | done | blocked | error | tests green | expected outcome | full GPU | median turns | median secs | first-attempt success | success within three |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bug1 | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 5 | 9.89100000000326 | 5/5 | 5/5 |
| bug2 | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 6 | 15.172000000020489 | 5/5 | 5/5 |
| feature | 5 | 2 | 3 | 0 | 2/5 | 2/5 | 5/5 | 11 | 97.70300000000861 | 2/5 | 2/5 |
| multifile | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 7 | 20.01600000000326 | 5/5 | 5/5 |
| refactor | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 5 | 17.453000000008615 | 5/5 | 5/5 |
| offbyone | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 7 | 20.062999999994645 | 5/5 | 5/5 |
| javascript | 5 | 5 | 0 | 0 | 5/5 | 5/5 | 5/5 | 5 | 18.75 | 5/5 | 5/5 |
| blocked | 5 | 0 | 5 | 0 | 0/5 | 5/5 | 5/5 | 17 | 44.39000000001397 | 0/5 | 0/5 |

Per-attempt records, failure handbacks and independent test results are in `eval/results-retries-gpu.json`, with release transcripts alongside. Timestamp and temporary Git identifiers are omitted from these release copies; full raw files remain in the private implementation archive. Numerical measurements are unchanged.
