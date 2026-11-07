# Local validation

## C1 — Hermes validation

The release copy excludes the private plan and generated files. The first invocation checked the source directory because of WSL argument handling. The corrected invocation produced the following output and exited zero.

```text
Clean copy: /root/li-test.jhWFqN

✓ manifest — plugin.yaml parses
✓ manifest fields — name, version, description present
✓ requires_hermes — spec '>=0.23.0' parses
✓ config schema — not declared
✓ requires_env — all entries UPPER_SNAKE
✓ oauth — not declared
✓ loadable — entry: __init__.py
✓ python dependencies — none declared
✓ capability probe — register() ran in isolation
✓ declared tools — matches registrations
✓ declared hooks — matches registrations
✓ declared middleware — matches registrations
✓ built-in tool collisions — no collisions
✓ security scan — safe
✓ no core override — no runtime rebinds of Hermes core
◆ Isolation — runs in the plugin host (plugins.isolation: host)

Validation passed.
[plugins] DEBUG HERMES_PLUGINS_DEBUG=1 — verbose plugin discovery logging enabled
[plugins] DEBUG Parsed manifest: key=local-implementer name=local-implementer kind=standalone source=user path=/root/.hermes/cache/scratch/hermes-plugin-doctor-v_hbmoad/plugins/li-test.jhWFqN
[plugins] DEBUG Loading plugin 'local-implementer' (source=user, kind=standalone, path=/root/.hermes/cache/scratch/hermes-plugin-doctor-v_hbmoad/plugins/li-test.jhWFqN)
[plugins] DEBUG Plugin local-implementer registered tool: implement_task
[plugins] DEBUG   registered: 1 tool(s), 0 hook(s), 0 middleware, 0 slash command(s), 0 CLI command(s)
Plugin Doctor: /root/li-test.jhWFqN
  manifest: local-implementer 0.1.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 1 tool(s), 0 hook(s)
Forbidden-word scan: zero matches
```

## C2 — Offline tests (gate failed)

The first Windows invocation failed during collection because pytest imported the hyphenated directory's entry point as a standalone module. The second invocation used the corrected test loader. The first WSL invocation reported `No module named pytest`. The second attempted to provision pytest from the offline cache.

Windows, second attempt

```text
Python 3.12.7
.....F...............s....                                               [100%]
================================== FAILURES ===================================
______________________________ test_auto_finish _______________________________
tests\test_loop.py:114: in test_auto_finish
    assert (result["status"], result["reason"]) == ("done", "auto_finish")
E   AssertionError: assert ('error', 'execution_error') == ('done', 'auto_finish')
E     
E     At index 0 diff: 'error' != 'done'
E     Use -v to get more diff
---------------------------- Captured stderr call -----------------------------
----------------------------------------
----------------------------------------
=========================== short test summary info ===========================
FAILED tests/test_loop.py::test_auto_finish - AssertionError: assert ('error'...
1 failed, 24 passed, 1 skipped in 12.10s
```

The auto-finish transcript shows that the Python assertion failed both before and after the one-character edit. The checkout had created `__pycache__/` during the first invocation. This is consistent with Python reusing timestamp-based bytecode for a same-size edit within one second. Symbolic links were unavailable to the Windows test process.

WSL, second attempt

```text
Python 3.14.9
Using CPython 3.14.9 interpreter at: /root/.hermes/tools/python-3.14.9+20261021-linux-x64/bin/python3
error: No solution found when resolving dependencies
  cause: Because pytest was not found in the cache and you require pytest, we can conclude that your requirements are unsatisfiable.

hint: Packages were unavailable because the network was disabled. When the network is disabled, registry packages may only be read from the cache.
```

Stopped at C2 under the checkpoint retry rule. C3–C6 remain pending.

## C3 / C5 — Real model, reliability
`python eval/run_eval.py --runs 5 --out eval/results.json`, Windows, Ollama qwen3.5:9b (CPU-only), default budgets.

```text
| bug | runs | done | blocked | error | tests green | median turns | median secs |
| bug1 | 5 | 5 | 0 | 0 | 5/5 | 6 | 206.5 |
| bug2 | 5 | 5 | 0 | 0 | 5/5 | 6 | 248.5 |
```

## C4 — Inside Hermes
Installed with `hermes plugins install file:///root/li-src --enable --yes-deps`; `hermes plugins show local-implementer` = enabled. First attempt failed (tool hidden behind tool_search; agent never called it). After `hermes config set tools.tool_search.enabled off`, the session in eval/hermes-session-bug1.txt: agent called `implement_task`, plugin transcript written, `python3 -m unittest -q` = OK, diff `min` -> `max`.

## C6 — Final gates (clean `git clone` copy, .git removed)
- `hermes plugins validate --install-deps`: exit 0, "Validation passed", security scan safe.
- `doctor --ci`: OK, 1 tool registered.
- Forbidden-word grep over tracked files: zero hits. Secret scan: only the word "token" (LLM tokens); no credentials.
- `python -m pytest tests -q` (Windows 3.12.7): 25 passed, 1 skipped (fixtures excluded from collection).

## Phase 0 — Patchsmith rename

Catalog collision check: no matches. Plugin name, toolset, install/catalog URLs, environment prefix, transcript directory and tests now use Patchsmith. `implement_task` and the checkout directory are unchanged. Historical run artifacts retain their original names and values. The five plugin-owned Hermes environment variable names were updated without displaying values.

```text
Python 3.12.7
25 passed, 1 skipped in 12.00s
Forbidden-word scan: zero matches
Clean copy: /root/ps-test.ySvZlR

âœ“ manifest â€” plugin.yaml parses
âœ“ manifest fields â€” name, version, description present
âœ“ requires_hermes â€” spec '>=0.23.0' parses
âœ“ config schema â€” not declared
âœ“ requires_env â€” all entries UPPER_SNAKE
âœ“ oauth â€” not declared
âœ“ loadable â€” entry: __init__.py
âœ“ python dependencies â€” none declared
âœ“ capability probe â€” register() ran in isolation
âœ“ declared tools â€” matches registrations
âœ“ declared hooks â€” matches registrations
âœ“ declared middleware â€” matches registrations
âœ“ built-in tool collisions â€” no collisions
âœ“ security scan â€” safe
âœ“ no core override â€” no runtime rebinds of Hermes core
â—† Isolation â€” runs in the plugin host (plugins.isolation: host)

Validation passed.
Plugin Doctor: /root/ps-test.ySvZlR
  manifest: patchsmith 0.1.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 1 tool(s), 0 hook(s)
[plugins] DEBUG HERMES_PLUGINS_DEBUG=1 â€” verbose plugin discovery logging enabled
[plugins] DEBUG Parsed manifest: key=patchsmith name=patchsmith kind=standalone source=user path=/root/.hermes/cache/scratch/hermes-plugin-doctor-xjjpt1u4/plugins/ps-test.ySvZlR
[plugins] DEBUG Loading plugin 'patchsmith' (source=user, kind=standalone, path=/root/.hermes/cache/scratch/hermes-plugin-doctor-xjjpt1u4/plugins/ps-test.ySvZlR)
[plugins] DEBUG Plugin patchsmith registered tool: implement_task
[plugins] DEBUG   registered: 1 tool(s), 0 hook(s), 0 middleware, 0 slash command(s), 0 CLI command(s)
```

## Phase 1 — Real-task GPU benchmark

Command: `python -B eval/run_eval.py --runs 5 --model qwen3.5:9b --require-gpu --out eval/results-gpu.json`

35/35 implementation runs returned done with independently green tests; 5/5 protected-test requests returned blocked with tests still red and no files changed.

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

All 40 runs recorded full model residency in GPU memory. Each started with failing tests, and final tests were rerun independently. All five two-file fixture runs changed both production files. Raw outcomes, test output and GPU evidence are committed under eval, alongside all 40 transcripts. No failed runs were discarded. Only Ollama was measured; the optional second backend was not available on PATH in Windows or WSL. The benchmark runner now has per-fixture counts, incremental result persistence and hardware-check failure recording.

```text
name, memory.total [MiB], driver_version
NVIDIA GeForce RTX 5060 Ti, 16311 MiB, 610.88
.................................s....                                   [100%]
37 passed, 1 skipped in 12.20s
Clean copy: /root/ps-test.RxKRpK

âœ“ manifest â€” plugin.yaml parses
âœ“ manifest fields â€” name, version, description present
âœ“ requires_hermes â€” spec '>=0.23.0' parses
âœ“ config schema â€” not declared
âœ“ requires_env â€” all entries UPPER_SNAKE
âœ“ oauth â€” not declared
âœ“ loadable â€” entry: __init__.py
âœ“ python dependencies â€” none declared
âœ“ capability probe â€” register() ran in isolation
âœ“ declared tools â€” matches registrations
âœ“ declared hooks â€” matches registrations
âœ“ declared middleware â€” matches registrations
âœ“ built-in tool collisions â€” no collisions
âœ“ security scan â€” safe
âœ“ no core override â€” no runtime rebinds of Hermes core
â—† Isolation â€” runs in the plugin host (plugins.isolation: host)

Validation passed.
Plugin Doctor: /root/ps-test.RxKRpK
  manifest: patchsmith 0.1.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 1 tool(s), 0 hook(s)
[plugins] DEBUG HERMES_PLUGINS_DEBUG=1 â€” verbose plugin discovery logging enabled
[plugins] DEBUG Parsed manifest: key=patchsmith name=patchsmith kind=standalone source=user path=/root/.hermes/cache/scratch/hermes-plugin-doctor-a9x9v4j0/plugins/ps-test.RxKRpK
[plugins] DEBUG Loading plugin 'patchsmith' (source=user, kind=standalone, path=/root/.hermes/cache/scratch/hermes-plugin-doctor-a9x9v4j0/plugins/ps-test.RxKRpK)
[plugins] DEBUG Plugin patchsmith registered tool: implement_task
[plugins] DEBUG   registered: 1 tool(s), 0 hook(s), 0 middleware, 0 slash command(s), 0 CLI command(s)
```

Forbidden-word scan: zero matches.

## Phase 2 — Initial pause (historical)

The phase initially paused after two real-Hermes post-apply verification failures despite 57 passed, 1 skipped offline. Both proposal turns left source bytes unchanged. The first apply produced correct bytes but changed permissions from 0777 to 0755; the attempted correction was not successfully verified in the installed runtime. Source and installed code were temporarily restored to Phase 1, and all unfinished work was archived privately. The user then explicitly overrode the stop rule and requested fixing the coding issue and continuing. Readable failed-attempt records are in `eval/phase2-diagnostics.json`; complete raw logs are preserved privately. The pause did not create a green Phase 2 tag.

## Phase 2 resumed by user

The user explicitly overrode the two-attempt stop rule and requested fixing the coding issue and continuing Phase 2. The archived implementation was restored for diagnosis. The previous stop notes describe historical state, not a permanent scope cut.

## Phase 2 — Propose / apply green

Implemented isolated proposal generation, a full saved patch with SHA-256 provenance and base HEAD, cleanup, and guarded application. The source checkout remains byte-identical during a proposal. Apply checks the saved hash, original HEAD and branch, affected-file bytes, modes and index entries, and actual patch paths. Test files and outside paths are refused. Git checks applicability before writing; original permissions and line endings are preserved. Default direct apply behavior remains available.

The Windows line-ending issue was fixed by disabling Git autocrlf conversion for plugin Git commands. The permission check was reproduced directly on Linux and passed after preserving original permissions. The corrected runtime was reinstalled from an immutable local commit with byte-for-byte source checks. A further agent-side endpoint override was fixed in the integration prompt by supplying the configured local endpoint explicitly. No performance failure caused the stop.

```text
58 passed, 1 skipped in 30.64s
Proposal Hermes process exit: 0
Proposal checkout byte comparison: identical
Apply Hermes process exit: 0
Ran 2 tests in 0.000s
OK
Real Hermes propose, review, approval and apply: passed
```

The real session is preserved in `eval/hermes-session-propose.txt` and `.jsonl`; its complete model-loop transcript is `eval/phase2-proposal-transcript.jsonl`, and the applied patch is `eval/phase2-demo.patch`. The first agent response displayed the exact diff before the second, explicit approval turn called apply_patch. The successful run cleaned up its isolated checkout. Earlier unsuccessful integration runs remain documented; no benchmark rows were changed or rerolled.

Final clean-copy gate:

```text

✓ manifest — plugin.yaml parses
✓ manifest fields — name, version, description present
✓ requires_hermes — spec '>=0.23.0' parses
✓ config schema — not declared
✓ requires_env — all entries UPPER_SNAKE
✓ oauth — not declared
✓ loadable — entry: __init__.py
✓ python dependencies — none declared
✓ capability probe — register() ran in isolation
✓ declared tools — matches registrations
✓ declared hooks — matches registrations
✓ declared middleware — matches registrations
✓ built-in tool collisions — no collisions
✓ security scan — safe
✓ no core override — no runtime rebinds of Hermes core
◆ Isolation — runs in the plugin host (plugins.isolation: host)

Validation passed.
Plugin Doctor: /root/ps-phase2-green.51kabtdk
  manifest: patchsmith 0.1.0 (standalone)
  OK: runtime discovery, manifest parsing, import, and registration passed
  registrations: 2 tool(s), 0 hook(s)
```

Forbidden-word scan over release files: zero matches.

## Phase 3 — Retry and structured handback

- Added attempts (default 1, maximum 3), fresh contexts with clipped failure facts, rollback between attempts, optional same-endpoint fallback only on the final allowed attempt, and factual failure handbacks. Turn and cumulative token budgets are shared across the entire call. Configured tests are verified before accepting a completion. Guardrail, endpoint and rollback failures do not retry.
- Windows verification: 73 passed, 1 skipped in 42.51s. The skip is the existing Windows link test. Coverage includes shared turn/token limits, dirty-byte rollback, failed-test recovery, fallback timing, final-only partial edits, proposal isolation and table columns.
- Clean-copy Hermes validate --install-deps and doctor --ci passed with two tools; no collisions and security scan safe.
- GPU command and exact generated table:

`python -B eval/run_eval.py --runs 5 --attempts 3 --model qwen3.5:9b --require-gpu --out eval/results-retries-gpu.json`

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

32/35 implementation runs succeeded on the first attempt; 32/35 succeeded within three attempts. 5/5 protected-test requests ended blocked with red tests and no edits. 40/40 runs retained full GPU residency.

No measured retry improvement; no improvement claim is made. The stricter cumulative token allowance differs from the historical Phase 1 per-request context check; the tables are not a controlled budget comparison. All failures remain in the evidence. The final input-error handback and independent-success predicate were hardened with regression tests (13 passed in 0.47s); all recorded first-attempt successes also passed independent tests. The final handback wording was tightened after benchmark startup to distinguish a stop fact from a model note; budget and edit-loop behavior did not change.

Full original evidence, including incidental timestamp and temporary Git identifier matches in the release scan, is preserved at `C:\tmp\patchsmith-phase3-raw-20261107-160728`. Release copies omit those identifier fields only. All numerical measurements and every run are retained.

Final release scan: zero forbidden matches over tracked text, all tracked text UTF-8. Staged whitespace check passed. Installed runtime and README match the final source bytes after immutable local reinstall. Original console whitespace is preserved in the private raw archive.


## Phase 4: Hermes skill, status, and local ledger

Implemented the read-only `patchsmith:delegate` skill using `PluginContext.register_skill(name, path, description)` and `/patchsmith status` using `register_command(name, handler, args_hint)`. Verified the actual installed manager resolves the namespaced skill to the packaged file and dispatches the command. Unsupported command declaration fields were excluded; the supported manifest declares exactly three tools: implement_task, apply_patch, task_status. The registration test separately verifies the command and skill.

Each completed coding call records status, reason, turns, seconds, estimated local tokens, files, mode, and artifact paths under ~/.patchsmith/runs. Unique records become visible only after complete writes. Concurrent writes retain every run; invalid records are reported and excluded from totals. Ledger failures add a warning without changing completed edits. Proposal records contain the final saved patch path. Prior transcripts are not backfilled; patch application does not add another model run.

Inspected `agent/tool_executor.py`: `_DEFAULT_CONCURRENT_TOOL_TIMEOUT_S = 420.0`; the sequential deadline inherits that default through `_resolve_sequential_tool_timeout`. The installed `register_tool` SDK does not expose execution_timeout. Added opt-in background=true with immediate process-local job_id and task_status polling. One background job runs at a time, up to 50 completed handles retained, no restart durability. Keep Hermes open; proposal mode is preferred. Tests verify nonblocking start, busy refusal, completion, repeated polls, invalid/expired handles, and the actual handler-loop-ledger path.

Windows final command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest tests -q -p no:cacheprovider --tb=short`.

```text
82 passed, 1 skipped in 44.24s
```

Skill validator: `Skill is valid!`. Clean-copy validate --install-deps and doctor --ci both exited 0, safe security scan, no tool collisions, 3 tools. Actual manager resolves `/patchsmith` and `patchsmith:delegate`; the skill bytes match source. Evidence: eval/phase4-validation.txt and eval/phase4-status.txt.

Real Hermes acceptance used `-s patchsmith:delegate` through the supported skill-preloading mechanism. The coding tool call omitted both model and endpoint and used existing configured defaults. One successful isolated proposal: 5 turns, 5774 estimated local tokens, 8.29107088500001 seconds. The source byte comparison passed, temporary proposal checkout was removed, and the saved patch passed 2 independent unittest tests when applied in a separate disposable copy. The original checkout stayed unchanged. Final facts are in eval/phase4-skill-gate.json; full session evidence is eval/hermes-session-skill.jsonl and .txt.

Honesty and corrected checks: the initial suite found ledger status treated a file at its directory location as an empty history; fixed and rechecked. The first live take did not load the skill, invented model/endpoint overrides, and failed its local request; retained as eval/hermes-session-skill-failed.jsonl and .txt. Native skill preloading fixed the integration path. The successful coding run initially showed only a prose summary; a same-session follow-up displayed the actual returned diff and saved path without another coding run. The first resume helper used a different turn cap and was refused by Hermes before model execution; keeping the launch limit resolved it. The final response, rather than incremental text chunks, was used to verify the verbatim diff. No coding results were rerolled or omitted.

The actual status command reports 2 recorded runs, including the error, and 5774 estimated local tokens. No retry reliability or speed improvement is claimed here. Phase 3's benchmark remains unchanged.

Original Phase 4 evidence is also preserved privately at C:/tmp/patchsmith-phase4-raw. Release evidence keeps all identifiers and measurements; only trailing console whitespace was normalized in phase4-validation.txt and hermes-session-skill.txt. The forbidden-pattern scan over all tracked and pending release text returned zero hits before staging. Final staged checks are recorded in eval/phase4-gate.txt.

The approved hardware inspection and contributor benchmark idea is recorded as a planned follow-up in docs/IMPLEMENTATION.md. Hardware detection, recommendations, downloads, and result submission are not implemented in this phase. No publication occurred.


## Additional hardware phase: green

User requested implementation after Phase 4. Added inspect_hardware, patchsmith:hardware, an evidence-linked tested registry, a reproducible contributor benchmark command, versioned reports and an outcome-consistency validator. No added dependencies, automatic downloads, uploads or publication.

Acceptance: 99 passed, 1 skipped in 45.10s. Clean-copy validate --install-deps and doctor --ci passed with 4 tools; both native skills resolve; installed runtime bytes match source. Hardware skill validation passed. Windows inventory detected CPU/RAM/GPU and Ollama metadata; real Hermes inventory detected the WSL host limits and private-network endpoint uncertainty.

| smoke fixture | status | independent test exit | turns | seconds | tokens_est | full GPU |
|---|---|---|---|---|---|---|
| bug1 | done | 0 | 5 | 9.625 | 5670 | true |
| blocked | blocked | 1 | 5 | 12.78100000001723 | 6228 | true |

Both smoke outcomes were expected; blocked made no edits. No full-suite reliability increase claimed. Raw results and transcripts are retained, including the live blank-endpoint failure before its regression fix. The live model needed a follow-up to accurately distinguish free/total VRAM and historical unknown quantization; both responses are retained. See docs/IMPLEMENTATION.md for measured limits and release-copy normalization. A harness discovery initialization issue and a helper quoting/format assertion issue were corrected without changing model measurements. Next planned work remains final delivery preparation; optional speed/context work is separate.


## Phase 5: speed and context experiment

Phase 5 is complete. The repo-map and failure-digest candidate was reverted. Implementation successes: 33/35 before, 32/35 after. Overall median turns: 6.0 before, 5.0 after; overall median seconds: 16.8125 before, 22.125000000029104 after. Both cohorts retained all 40 runs and recorded full GPU residency. Protected-test outcomes remain separate from implementation successes.

Same qwen3.5:9b model digest, quantization, loaded context, local Ollama 0.17.6 endpoint, eight fixtures, five runs each, one attempt, 25 total turns and 24000 cumulative estimated tokens. One sequential cohort per version; stochastic responses and order/thermal effects are uncontrolled. Offline fake-model tests briefly overlapped the baseline. No extra GPU model workload was started. Small synthetic fixtures do not establish gains on large repositories.

Commands (only the output path differs):

`python -B eval/run_eval.py --runs 5 --attempts 1 --model qwen3.5:9b --require-gpu --out eval/phase5-before.json`

`python -B eval/run_eval.py --runs 5 --attempts 1 --model qwen3.5:9b --require-gpu --out eval/phase5-after.json`

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

Decision: reverted. The keep rule required no per-fixture expected-outcome regression and a lower overall median turns or seconds. Candidate regression suite: 106 passed, 2 skipped in 47.83s; the extra skip is unavailable Windows link creation. The comparison helper rejected incomplete, GPU, model-identity, outcome and budget mismatches; identical cohorts produce no gain. Public evidence omits disposable Git base identifiers, transient transcript paths and incidental start/check/residency-expiry timestamps. Relative links to the released transcripts remain in the result files. Every run, failure, outcome and numeric measurement is retained. Untouched originals and candidate source are preserved privately at C:/tmp/patchsmith-phase5-originals/experiment. The saved candidate patch reproduces all measured source hashes in a fresh baseline clone.


Final retained-runtime gate: 99 passed, 1 skipped in 44.05s. Clean-copy Hermes validate --install-deps and doctor --ci passed with four tools, safe security scan and matching declarations. An immutable local reinstall verified runtime bytes against source. All 80 runs and numeric measurements match the untouched originals after the disclosed identifier/path/timestamp omissions. The active loop is byte-identical to the pre-experiment source; candidate-only module and tests were removed. No publication occurred.

Release formatting: generated tables use LF; four empty context lines in the saved patch omit trailing spaces. Ordinary git apply in a fresh baseline clone still reproduces all candidate source hashes. Complete staged whitespace and release-text checks passed. Final gate facts: eval/phase5-gate.json.
