"""Bounded model orchestration and post-run verification."""

from collections import Counter
import json
import os
from pathlib import Path
import tempfile
from time import monotonic
from threading import Lock

from .llm import LocalModel
from .tools import Jail, Session, TRANSCRIPTS, clip, linked

BRIEF = Path(__file__).with_name("brief.md")
ACTIVE = set()
ACTIVE_LOCK = Lock()
TOOLS = (
    ("read_file", "Read up to 400 numbered lines.", {"path": "string", "start": "integer?", "end": "integer?"}),
    ("grep", "Search visible files with a regex.", {"pattern": "string", "path": "string?"}),
    ("glob", "List visible files matching a glob.", {"pattern": "string"}),
    ("git_status", "Show working tree status.", {}),
    ("git_diff", "Show the working tree diff.", {"path": "string?"}),
    ("write_file", "Write a non-test file.", {"path": "string", "content": "string"}),
    ("edit_file", "Replace one exact, unique occurrence.", {"path": "string", "old": "string", "new": "string"}),
    ("run_tests", "Run the configured test command without extra arguments.", {}),
    ("finish", "End the task with status done or blocked and a short note.", {"status": "string", "note": "string"}),
)
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object",
                       "properties": {key: {"type": kind.rstrip("?")} for key, kind in fields.items()},
                       "required": [key for key, kind in fields.items() if not kind.endswith("?")],
                       "additionalProperties": False},
    }}
    for name, description, fields in TOOLS
]
TOOL_FIELDS = {name: fields for name, _, fields in TOOLS}


def emit(log, value):
    log.write(json.dumps(value) + "\n")
    log.flush()


def estimate(value):
    return (len(json.dumps(value)) + 2) // 3


def usage_count(usage, field):
    value = usage.get(field)
    return value if type(value) is int and value > 0 else 0


def dispatch(session, call, calls):
    name = call["function"]["name"]
    try:
        if name not in TOOL_FIELDS:
            raise ValueError(f"Unknown tool: {name}")
        fields = TOOL_FIELDS[name]
        values = json.loads(call["function"]["arguments"] or "{}")
        if not isinstance(values, dict) or values.keys() - fields.keys():
            raise ValueError("Expected an object with only declared arguments.")
        for key, kind in fields.items():
            if key not in values and kind.endswith("?"):
                continue
            expected = int if kind.rstrip("?") == "integer" else str
            if type(values.get(key)) is not expected:
                raise ValueError(f"{key} must be {kind.rstrip('?')}.")
        signature = name, json.dumps(values, sort_keys=True)
        calls[signature] += 1
        if calls[signature] >= 3:
            return "Repeated tool call without progress.", True
        before = session.written.copy()
        output = getattr(session, name)(**values)
        if name == "run_tests":
            session.last_test = output
        if session.written != before:
            calls.clear()
        return output, False
    except Jail as exc:
        return f"REFUSED: {exc}", False
    except Exception as exc:
        return f"ERROR: {exc}", False


def run_loop(session, client, task, turns, budget, log, result):
    messages = [
        {"role": "system", "content": BRIEF.read_text(encoding="utf-8")},
        {"role": "user", "content": task},
    ]
    calls = Counter()
    adjustment = 0
    idle = 0
    green_turn = None
    emit(log, {"event": "start", "model": client.model, "endpoint": client.url,
               "max_turns": turns, "context_budget": budget})
    for turn in range(1, turns + 1):
        prompt = estimate([messages, TOOL_SCHEMAS])
        remaining = budget - result["tokens_est"] - prompt - adjustment
        if remaining <= 0:
            if session.green:
                return "done", "auto_finish", "Tests passed after the final edit."
            return "blocked", "context_budget", "The next request would exceed the context budget."
        result["turns"] += 1
        emit(log, {"event": "turn", "turn": turn, "context_est": prompt + adjustment})
        message, usage = client.complete(messages, TOOL_SCHEMAS, min(2048, remaining))
        observed = usage_count(usage, "prompt_tokens")
        if observed:
            adjustment = max(adjustment, observed - prompt)
        completion = usage_count(usage, "completion_tokens") or estimate(message)
        used = (observed or prompt + adjustment) + completion
        result["tokens_est"] += used
        emit(log, message)
        if result["tokens_est"] > budget:
            return "blocked", "context_budget", "The model response exhausted the context budget."
        messages.append(message)
        tool_calls = message.get("tool_calls", [])
        idle = 0 if tool_calls else idle + 1
        for call in tool_calls:
            output, repeated = dispatch(session, call, calls)
            reply = {"role": "tool", "tool_call_id": call["id"], "content": clip(output)}
            emit(log, reply)
            messages.append(reply)
            if session.finished:
                status, note = session.finished
                return status, "model_blocked" if status == "blocked" else None, note
            if repeated:
                if session.green:
                    return "done", "auto_finish", "Tests passed after the final edit."
                return "blocked", "loop_detected", "The model repeated the same tool call three times."
        if session.green:
            if green_turn is None:
                green_turn = turn
            if turn > green_turn or turn == turns:
                return "done", "auto_finish", "Tests passed after the final edit."
        else:
            green_turn = None
        if idle >= 3:
            return "blocked", "no_tool_calls", "The model stopped calling tools."
        if not tool_calls:
            messages.append({"role": "user", "content": "Use a tool or call finish."})
    return "blocked", "max_turns", f"Reached the limit of {turns} model turns."


def configured(args, key, env, default):
    return args[key] if key in args else os.environ.get(env, default)


def positive(value, name, ceiling=None):
    if type(value) is not int and (not isinstance(value, str) or not value.isascii() or not value.isdecimal()):
        raise ValueError(f"{name} must be a positive integer.")
    number = int(value)
    if number < 1 or (ceiling is not None and number > ceiling):
        raise ValueError(f"{name} must be in the supported range (1–{ceiling or 'unbounded'}).")
    return number


def handback(history):
    last = history[-1]
    reason = last.get("reason")
    advice = {
        "max_turns": "Split the task into a smaller change and name the target file.",
        "context_budget": "Split the task and provide a focused failing test and file hint.",
        "tests_failed": "Inspect the failing test output and name the implementation file to fix.",
        "model_blocked": "Clarify the acceptance requirement and name the target file; keep tests read-only.",
        "test_files_modified": "Provide a failing test and request changes only to implementation files.",
    }.get(reason, "Inspect the failure, provide a focused failing test, and name the target file.")
    return {"what_was_tried": clip("; ".join(
                f"Attempt {r['attempt']} with {r['model']}: {r['status']} ({r.get('reason') or 'finished'}), "
                f"{r['turns']} turns; files: {', '.join(r['files_touched']) or '(none)'}" for r in history), 2000),
            "last_failure": clip((last.get("test_output") if last.get("test_output", "").startswith(("exit ", "Test command"))
                                  and not last["test_output"].startswith("exit 0") else None)
                                 or (f"Stopped: {last['status']} ({reason})." if reason == "model_blocked"
                                     else last["note"]), 2000),
            "files_touched": sorted({name for r in history for name in r["files_touched"]}),
            "suggested_next": advice}


def execute(session, client, task, turns, budget, keep, log_dir=None, attempts=1, fallback=None):
    in_place = log_dir is None
    log_dir = log_dir or session.root / TRANSCRIPTS
    if linked(log_dir):
        raise Jail("The transcript directory must not be a link.")
    log_dir.mkdir(mode=0o700, exist_ok=True)
    result = {"turns": 0, "tokens_est": 0, "files_changed": [], "diff": "", "transcript_path": None,
              "patch_path": None, "patch_sha256": None, "base_head": None, "applied": False,
              "attempt_history": [], "handback": None}
    with tempfile.NamedTemporaryFile(prefix="run-", suffix=".jsonl", dir=log_dir, mode="w",
                                     encoding="utf-8", delete=False) as log:
        result["transcript_path"] = log.name
        retry_task = task
        for attempt in range(1, attempts + 1):
            before = head = None
            start_turns, start_tokens = result["turns"], result["tokens_est"]
            active_client = fallback if fallback is not None and attempt == attempts else client
            session.last_test = ""
            try:
                before = session.test_snapshot()
                head = session.head()
                result["base_head"] = head[1].strip() or None
                status, reason, note = run_loop(session, active_client, retry_task,
                                               turns - result["turns"], budget, log, result)
                if status == "done" and session.argv and not session.green:
                    session.last_test = session.run_tests()
                    if not session.green:
                        status, reason, note = "blocked", "tests_failed", "Configured tests did not pass after an edit."
            except Exception as exc:
                status, reason, note = "error", "execution_error", str(exc)
            try:
                if before is not None:
                    changed, failures = session.restore_tests(before)
                    if changed:
                        status, reason = "blocked", "test_files_modified"
                        note = "Test files changed during the run: " + ", ".join(changed)
                        if failures:
                            note += ". Restore failed for " + ", ".join(failures)
                if head is not None and session.head() != head:
                    status, reason, note = "blocked", "git_state_changed", "HEAD or branch changed."
            except Exception as exc:
                status, reason, note = "error", "verification_error", f"{note} Verification failed: {exc}"
            row = {"attempt": attempt, "model": active_client.model, "status": status, "reason": reason,
                   "note": clip(note), "turns": result["turns"] - start_turns,
                   "tokens_est": result["tokens_est"] - start_tokens,
                   "files_touched": sorted(session.written), "test_output": clip(session.last_test, 2000)}
            result["attempt_history"].append(row)
            emit(log, {"event": "attempt", **row})
            retry = (status == "blocked" and reason not in {"test_files_modified", "git_state_changed"}
                     and attempt < attempts and result["turns"] < turns and result["tokens_est"] < budget)
            if status != "done" and (retry or not keep):
                failures = session.rollback()
                if failures:
                    status, reason = "error", "rollback_failed"
                    note += ". Rollback skipped: " + ", ".join(failures)
                    row.update(status=status, reason=reason, note=clip(note))
                    retry = False
            if not retry:
                break
            retry_task = task + "\n\nPrevious attempt facts (edits were rolled back):\n" + json.dumps(handback(result["attempt_history"]))
            # Keep the same object for proposal capture, but discard all attempt state.
            session.original.clear()
            session.written.clear()
            session.created_dirs.clear()
            session.finished = None
            session.green = False
        try:
            result["files_changed"], result["diff"] = session.patch()
        except (OSError, Jail) as exc:
            note += f". Could not read the final patch: {exc}"
        result.update(status=status, note=clip(note), applied=in_place and bool(result["files_changed"]))
        if reason:
            result["reason"] = reason
        if status != "done":
            result["handback"] = handback(result["attempt_history"])
        emit(log, {"event": "result", **result})
    return result


def _implement(args):
    task, workdir = args.get("task"), args.get("workdir")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be a nonempty string.")
    if not isinstance(workdir, str) or not workdir.strip() or not Path(workdir).is_dir():
        raise ValueError("workdir must be an existing directory.")
    root = Path(workdir).resolve(strict=True)
    mode = args.get("mode", "apply")
    if mode not in {"apply", "propose"}:
        raise ValueError("mode must be apply or propose.")
    turns = positive(configured(args, "max_turns", "PS_MAX_TURNS", 25), "max_turns", 60)
    budget = positive(configured(args, "context_budget_tokens", "PS_CTX_BUDGET", 24000),
                      "context_budget_tokens")
    attempts = positive(args.get("attempts", 1), "attempts", 3)
    fallback_model = args.get("fallback_model")
    if fallback_model is not None and (not isinstance(fallback_model, str) or not fallback_model.strip()):
        raise ValueError("fallback_model must be a nonempty local model identifier.")
    keep = args.get("keep_partial", False)
    if type(keep) is not bool:
        raise ValueError("keep_partial must be a boolean.")
    endpoint = configured(args, "endpoint", "PS_ENDPOINT", "http://127.0.0.1:11434/v1")
    model = configured(args, "model", "PS_MODEL", "qwen3.5:9b")
    command = configured(args, "test_command", "PS_TEST_COMMAND", "")
    if not isinstance(endpoint, str) or not isinstance(model, str) or not model.strip():
        raise ValueError("endpoint and model must be nonempty strings.")
    if not isinstance(command, str):
        raise ValueError("test_command must be a string.")
    client = LocalModel(endpoint, model)
    fallback = LocalModel(endpoint, fallback_model) if fallback_model is not None else None
    with ACTIVE_LOCK:
        if root in ACTIVE:
            raise ValueError("A task is already running in this directory.")
        ACTIVE.add(root)
    try:
        if mode == "propose":
            from .patches import propose
            return propose(root, client, task, turns, budget, command, keep, execute, attempts=attempts, fallback=fallback)
        return execute(Session(root, command), client, task, turns, budget, keep, attempts=attempts, fallback=fallback)
    finally:
        with ACTIVE_LOCK:
            ACTIVE.remove(root)


def implement(args):
    started = monotonic()
    result = _implement(args)
    from .ledger import record
    seconds = monotonic() - started
    result["seconds"] = seconds
    warning = record(result, seconds, args.get("mode", "apply"))
    if warning:
        result["ledger_warning"] = warning
    return result
