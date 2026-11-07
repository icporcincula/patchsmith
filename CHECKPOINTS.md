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
