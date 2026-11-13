# Changelog

## Current

Pull requests to `main` are checked on Windows and Linux and merged manually by the maintainer. Coding tasks produce isolated proposals by default.

The Codex desktop beta exposes proposal generation, revision, comparison,
preflight, status, hardware inspection and a process-local task queue through
MCP. Owner-managed project profiles set per-checkout defaults. Coding results
report whether tests actually ran and passed.

## 2026-11-13

- Added sequential, proposal-only comparison of two local models.
- Added a process-local task queue and Codex queue/poll tools.
- Added an explicit verification outcome and test output to coding results.
- Added proposal revision from a saved patch and reviewer feedback.
- Added a read-only task preflight for Hermes and Codex.
- Exposed recent-run summaries and hardware inspection through the Codex MCP server.
- Added owner-managed per-project test and model profiles in private plugin storage.
- Added the Codex plugin marketplace, a proposal-only MCP tool and a stdio regression test.
- Defaulted coding tasks to proposal mode and preserved explicit direct apply for benchmarks and callers that need it.
- Protected additional Python, Go, and JavaScript/TypeScript test files and conventional test directories.
- Added offline CI and pre-commit checks, documented publishing, and replaced the placeholder GitHub install command.
