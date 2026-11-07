# local-implementer

A Hermes plugin that adds one tool, `implement_task`. Your main agent hands a **single, well-specified coding task** to a **local model** (Ollama, llama.cpp, or any OpenAI-compatible local server). The local model edits the code under hard budgets and the tool returns the diff.

Why: the expensive model keeps its context and tokens for planning and review. The mechanical edit-run-fix loop runs on your own machine, with zero API spend and no code leaving it.

## Install

```
hermes plugins install <owner>/local-implementer --enable
```

You need a local OpenAI-compatible server with a tool-calling model, for example `ollama pull qwen3.5:9b`.

## Configuration (all optional)

| Variable | Default | Meaning |
|---|---|---|
| `LI_ENDPOINT` | `http://127.0.0.1:11434/v1` | Local API base (must be a local address) |
| `LI_MODEL` | `qwen3.5:9b` | Model identifier |
| `LI_MAX_TURNS` | `25` | Model turns per task (hard cap 60) |
| `LI_CTX_BUDGET` | `24000` | Approximate token budget for the whole run |
| `LI_TEST_COMMAND` | none | Test command the model may run |

Each can also be passed as an argument of the tool call. If Hermes runs in WSL and Ollama on Windows, point `LI_ENDPOINT` at the Windows host address.

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

## Reliability (measured, not rounded)

Command: `python eval/run_eval.py --runs 5 --out eval/results.json` (raw rows in `eval/results.json`, table in `eval/results.table.md`). Model `qwen3.5:9b` (Q4_K_M) through Ollama, **CPU-only** during this run (GPU memory was held by other processes), default budgets. "Tests green" is an independent re-run of the tests after the call, not the returned status.

| bug | runs | done | blocked | error | tests green | median turns | median secs |
|---|---|---|---|---|---|---|---|
| bug1 (single-file `min` vs `max`) | 5 | 5 | 0 | 0 | 5/5 | 6 | 206.5 |
| bug2 (`rank()` sort direction, symptom in another file's test) | 5 | 5 | 0 | 0 | 5/5 | 6 | 248.5 |

Known limits of these numbers: two small seeded bugs, five runs each, one model, one machine. They show the loop and guardrails work end to end; they do not show the model can handle large or ambiguous tasks. Wall time is CPU-bound; expect it to be much faster on a GPU.

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
