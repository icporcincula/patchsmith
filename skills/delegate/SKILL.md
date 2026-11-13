---
name: delegate
description: Delegate a bounded, test-verified coding change to the configured local Patchsmith model. Use for a focused fix or mechanical change with clear acceptance criteria.
---

# Delegate one coding change

Use implement_task for a focused implementation change with a known test command: a small bug fix, caller update, or function with a precise specification. Keep exploratory design, broad rewrites, unclear requirements, and changes requiring test edits with the main agent. Split a large task before delegating.

Identify the checkout, implementation file hints, failing test name, and observable acceptance condition. The user configures the test command for this checkout through `PS_TEST_COMMAND`. Tests are read-only to the local loop.

Use the default proposal mode for review. Omit model and endpoint arguments so the plugin uses the configured PS_MODEL and PS_ENDPOINT; never guess an address or switch to a hosted provider. Existing defaults also supply turn and token budgets. Use attempts only when a fresh context may help; attempts share one total budget.

Example task: "Fix normalize_name in names.py. test_names.py::test_spaces currently fails. Collapse repeated spaces and trim the ends; preserve letter case. Acceptance: the configured test suite passes. Do not edit tests."

In Hermes, use background=true for a potentially slow run and poll task_status with the exact job_id in the same Hermes process. Keep Hermes open and wait for the completed result. Completed handles are retained for the last 50 jobs in that process. In Codex, pass only the task and absolute workdir and wait for the synchronous result.

Read status, diff, and handback in the result. For a successful proposal, show the actual diff and saved patch path. Obtain approval of the concrete diff before applying it. In Hermes, use apply_patch with the exact returned path. In Codex, verify the saved patch hash, confirm the checkout still matches the proposed base when one is reported, and check the patch against the current checkout before applying. After application, run the authorized tests in the source checkout and report their result.

On blocked or error, use the factual handback to narrow the next task or continue in the main agent. Do not repeat an unchanged failed request indefinitely. A done result without a configured test command is unverified.

The user can run /patchsmith status to see the last five recorded runs and the estimated local token total. Counts include repeated prompt processing, not financial savings. If no ledger exists yet, status reports no recorded runs.
