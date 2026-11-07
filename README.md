# patchsmith

A Hermes plugin that adds one tool, `implement_task`. Your main agent hands a **single, well-specified coding task** to a **local model** (served through a local OpenAI-compatible endpoint; only Ollama has been measured). The local model edits the code under hard budgets and the tool returns the diff.

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

`implement_task(task, workdir, max_turns?, test_command?, context_budget_tokens?, model?, endpoint?, keep_partial?)` returns JSON:
`status` (`done` / `blocked` / `error`), `reason`, `turns`, `tokens_est`, `files_changed`, `diff`, `note`, `transcript_path`.

## Safety model (enforced by the plugin, not requested of the model)

- **No shell.** The model has only: `read_file`, `grep`, `glob`, `git_status`, `git_diff`, `write_file`, `edit_file`, `run_tests`, `finish`. `run_tests` runs only the configured test command.
- **Path jail.** Writes outside `workdir`, through links, or under `.git` / `node_modules` are refused.
- **Test files are read-only.** If they change anyway they are restored and the run is `blocked` (`test_files_modified`).
- **Budgets.** Turn cap and context budget end the run as `blocked`.
- **Repeat guard.** The same tool call three times without progress ends the run.
- **Auto-finish.** Green tests after an edit end the run as `done`, so a small model cannot talk itself out of a fix.
- **Revert on failure.** `blocked` / `error` runs revert the files they touched unless `keep_partial` is true.
- **HEAD/branch check.** A run that moves HEAD or branch is `blocked`.
- **Network.** Only the configured local endpoint; non-local endpoints are refused. No telemetry.
- The agent should pass only a `test_command` the user authorized: it executes in your checkout.

## Reliability (measured)

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
