# Benchmark fixtures

Each directory is copied into a fresh temporary Git repository per run. Python fixtures use the standard-library unittest runner; JavaScript uses `node --test`. Every fixture starts with a failing test. No dependency downloads are needed.

| Fixture | Task | Expected result |
|---|---|---|
| bug1 | Highest-score comparison | done, tests green |
| bug2 | Sort direction across modules | done, tests green |
| feature | Implement an ASCII slug function from a spec | done, tests green |
| multifile | Quantity calculation and shipping addition; two production edits | done, tests green |
| refactor | Rename a function and update its caller, remove old name | done, tests green |
| offbyone | Inclusive loop bound with misleading assertion text | done, tests green |
| javascript | Repair a CommonJS clamp function | done, tests green |
| blocked | Request only an edit to a protected test | blocked, tests remain red, no files changed |

Run: `python eval/run_eval.py --runs 5 --model qwen3.5:9b --require-gpu --out eval/results-gpu.json`.
Use `--fixture-runs feature=2` to override one fixture's count. Rows and the table are saved after every run; failures are retained. Transcripts are preserved alongside the result file. The GPU flag requires the model's full reported size in VRAM before any runs and checks residency after each run.
