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
- Phase 2 adds isolated `mode="propose"` and guarded `apply_patch`. Default `mode="apply"` retains direct edits. Phase 3 adds bounded retries and factual handbacks; native status and skill integration remain later phases.

## User publication steps after Phase 1

1. Create the Patchsmith repository and push the green code when ready. The directory rename is yours to do.
2. Replace `<USER>` and the SHA placeholder in `catalog-entry.yaml` with the public repository and exact 40-character commit.
3. Add the catalog entry to a fork of NousResearch/hermes-agent and open the catalog PR. The same PR can receive later green revisions.
4. Retake the demo after the chosen feature phases. Confirm the contest allows synthesized narration before posting.

No repository, push, PR, post, or submission was created by this implementation.

## Phase 2 — Propose, review, apply

- `implement_task(..., mode="propose")` copies current checkout bytes into a detached temporary Git worktree, or a plain temporary directory for non-Git input. It returns a full saved patch, hash and base HEAD; the returned diff may be clipped. The checkout receives no model edits, transcript or patch files. Temporary worktrees are removed.
- Proposal records and transcripts live outside the checkout under `~/.patchsmith/proposals/`. Linked source content and storage inside the checkout are refused.
- After reviewing the diff and obtaining approval, call `apply_patch(patch_path=...)`. It refuses moved HEAD/branch, changed affected-file bytes/modes/index entries, tampering, protected tests and outside paths. Git checks the full patch before applying; line endings and original permissions are preserved.
- Windows offline tests: 58 passed, 1 skipped. Clean-copy Hermes validation and doctor register two tools without collisions.
- The real Hermes session in `eval/hermes-session-propose.txt` contains a proposal turn showing the diff, a separate approval turn calling `apply_patch`, byte-identical source verification before approval, cleaned-up isolation, and two independently passing tests afterward.
- Earlier integration failures were fixed after the user's explicit stop-rule override. Readable diagnostic records are in `eval/phase2-diagnostics.json`; original raw streams remain in the private implementation archive. The public GPU benchmark remains the unchanged Phase 1 direct-mode benchmark.

Known bounds: ordinary text patches only; Git proposals need an initial commit; linked checkout content is refused. Worktrees share Git metadata. The configured test command is trusted code, not an operating-system sandbox. Applying a proposal does not rerun tests automatically.

## Phase 3 — Retries and handbacks

`attempts=1..3` shares total turns and cumulative tokens across fresh contexts. Intermediate failures roll back even with `keep_partial=true`; only the final failure can retain edits. Optional `fallback_model` uses the same local endpoint on the final allowed attempt only. Failures return a factual `handback` plus per-attempt records. Configured tests must pass for completion.

32/35 implementation runs succeeded on the first attempt; 32/35 succeeded within three attempts. 5/5 protected-test requests ended blocked with red tests and no edits. 40/40 runs retained full GPU residency. See `eval/results-retries-gpu.table.md`; no stronger reliability claim is supported. Windows suite: 73 passed, 1 skipped. Clean-copy Hermes validation and doctor passed. Native status and skill support remain future work.


Phase 4 adds `patchsmith:delegate`, `/patchsmith status`, private summary records under `~/.patchsmith/runs`, and optional process-local background calls with `task_status`. Keep Hermes open for background work; handles do not survive a restart. The hardware compatibility feature and contributor benchmark format are planned in `docs/IMPLEMENTATION.md` and remain unimplemented.
