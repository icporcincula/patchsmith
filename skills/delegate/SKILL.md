---
name: delegate
description: Delegate a bounded, test-verified coding change to the configured local Patchsmith model. Use for a focused fix or mechanical change with clear acceptance criteria.
---

# Delegate one coding change

Use implement_task for a focused implementation change with a known test command: a small bug fix, caller update, or function with a precise specification. Keep exploratory design, broad rewrites, unclear requirements, and changes requiring test edits with the main agent. Split a large task before delegating.

Identify the checkout, implementation file hints, failing test name, and observable acceptance condition. Pass a test command authorized by the user for this checkout. Tests are read-only to the local loop. If a test command is unknown, inspect project instructions or ask for the missing command rather than inventing one.

Use the default proposal mode for review. Omit model and endpoint arguments so the plugin uses the configured PS_MODEL and PS_ENDPOINT; never guess an address or switch to a hosted provider. Existing defaults also supply turn and token budgets. Use attempts only when a fresh context may help; attempts share one total budget.

Example task: "Fix normalize_name in names.py. test_names.py::test_spaces currently fails. Collapse repeated spaces and trim the ends; preserve letter case. Acceptance: the configured test suite passes. Do not edit tests."

For a potentially slow run, use background=true and poll task_status with the exact job_id in the same Hermes process. Keep Hermes open. A running response is not a finished proposal; wait for the completed result before reviewing or applying. Completed handles are retained for the last 50 jobs in that process.

Read status, diff, and handback in the result. For a successful proposal, show the actual diff and saved patch path. Apply the exact returned patch_path with apply_patch when the user's authorization covers that application; otherwise obtain approval of the concrete diff. A proposal alone does not mean the source checkout changed. After application, run the authorized tests in the source checkout and report their result.

On blocked or error, use the factual handback to narrow the next task or continue in the main agent. Do not repeat an unchanged failed request indefinitely. A done result without a configured test command is unverified.

The user can run /patchsmith status to see the last five recorded runs and the estimated local token total. Counts include repeated prompt processing, not financial savings. If no ledger exists yet, status reports no recorded runs.
