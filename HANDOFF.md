# Handoff

## What works (verified)
- C1 validate + doctor green; C2 offline tests 25 passed / 1 skipped (Windows, Python 3.12.7).
- C3/C5: qwen3.5:9b via Ollama, bug1 5/5 and bug2 5/5 done with independently re-run tests green (eval/results.table.md).
- C4: Hermes (WSL) loads the installed plugin; a one-shot `hermes chat` session called `implement_task` and the bug1 fixture went green (eval/hermes-session-bug1.txt).

## Caveats
- Only 2 small seeded bugs x 5 runs; extra bugs from PLAN C5 not added. Numbers were measured on CPU (GPU memory was held by other processes): ~3.5-4 min per run.
- Hermes defers plugin tools behind tool_search by default. A local 9B agent never found `implement_task` that way (first attempt failed, 8 wasted calls). The passing session used `hermes config set tools.tool_search.enabled off`. Mention this in the demo setup.
- WSL has no pytest offline; the Hermes fixture session used `python3 -m unittest -q`. Fixtures are unittest-style so both runners work.
- The failure path (endpoint down, bad workdir) is covered by offline tests, not re-run against Hermes.
- `/patchsmith status` slash command not built (cut per plan).

## Manual steps for the user
1. Ollama on Windows listens on all interfaces already; WSL reaches it at the gateway IP (`ip route`, was 172.22.208.1). Put `PS_ENDPOINT=http://<gateway>:11434/v1` in `~/.hermes/.env`.
2. Free GPU memory before recording the demo (inference was CPU-only).
3. Create the public GitHub repo (needs your explicit go-ahead), push, put the 40-char SHA in `catalog-entry.yaml`, replace `<USER>`.
4. Fork NousResearch/hermes-agent, add `plugin-catalog/patchsmith.yaml`, open the PR. PLAN.md is gitignored; do not push it.
5. Demo + X post + form (deadline 5PM EST Nov 11).
