# Patchsmith handoff

## Green increments

- Phase 0: renamed the plugin/toolset, configuration and transcript directory to Patchsmith. The tool remains `implement_task`; the source directory remains unchanged. Five Hermes environment settings now use `PS_` with no legacy fallback.
- Phase 1: eight fixtures, five GPU runs each, with independent test reruns and preserved transcripts. 35/35 implementation runs returned done with independently green tests; 5/5 protected-test requests returned blocked with tests still red and no files changed.
- The exact generated table is in `eval/results.table.md`; raw GPU evidence is in `eval/results-gpu.json`. Older CPU evidence remains archived. Only Ollama has been measured.
- Original in-Hermes invocation evidence remains in `eval/hermes-session-bug1.txt`; this is historical evidence from before the rename.

## Operational notes

- Hermes may hide tools behind tool_search. The earlier passing local-model session used `hermes config set tools.tool_search.enabled off`.
- WSL reaches Ollama on Windows through its gateway address. Configure `PS_ENDPOINT` in `~/.hermes/.env`; the existing plugin-owned settings were renamed in place without exposing their values.
- `PS_MODEL`, `PS_MAX_TURNS`, `PS_CTX_BUDGET`, and `PS_TEST_COMMAND` are optional. The benchmark used default budgets and explicitly selected `qwen3.5:9b`.
- The current plugin still edits in place. Propose/review/apply, retries, native status and skill integration remain later phases of the extension plan.

## User publication steps after Phase 1

1. Create the Patchsmith repository and push the green code when ready. The directory rename is yours to do.
2. Replace `<USER>` and the SHA placeholder in `catalog-entry.yaml` with the public repository and exact 40-character commit.
3. Add the catalog entry to a fork of NousResearch/hermes-agent and open the catalog PR. The same PR can receive later green revisions.
4. Retake the demo after the chosen feature phases. Confirm the contest allows synthesized narration before posting.

No repository, push, PR, post, or submission was created by this implementation.
