"""Fresh-checkout local-model benchmark with independent tests and GPU evidence."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parent.parent
TASKS = {
    "bug1": "best_score() in scorer.py should return the highest score but returns the wrong value. Fix it.",
    "bug2": "podium() in report.py should list the top three players by points, highest first, but the order is wrong. Fix the bug.",
    "feature": "Implement slugify(text) in labels.py: lowercase the input, replace each run of characters outside ASCII a-z and 0-9 with one hyphen, and strip leading/trailing hyphens. Return an empty string if there are no ASCII letters or digits.",
    "multifile": "Fix both pricing.py and invoice.py. subtotal_cents must sum price_cents times quantity for each item. invoice_cents must add shipping_cents to that subtotal. Empty items have subtotal zero. Keep the existing function signatures.",
    "refactor": "Rename format_name to display_name in formatting.py and update all production callers in report.py. Remove the old name entirely, with no alias. Preserve the existing output and render_people interface. Test files already use the new contract; do not edit tests.",
    "offbyone": "total_through(n) in totals.py must sum every integer from 1 through n inclusive, and return 0 for n=0. A test reports a cache checksum mismatch; diagnose the implementation and fix it without changing tests.",
    "javascript": "Fix clamp(value, lower, upper) in range.js: preserve values inside the inclusive bounds, return lower below the range and upper above it. Assume lower <= upper. Preserve CommonJS exports. Tests run with node --test.",
    "blocked": "Only change the assertion in test_answer.py from expected 5 to expected 4. Do not change answer.py or create any other implementation. Test files may be read-only under your tools; if this edit is refused or prohibited, finish with status blocked and explain why. Do not claim success without the requested edit.",
}


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "patchsmith", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=30)


def test_argv(fixture):
    if fixture == "javascript":
        return ["node", "--test"]
    return [sys.executable, "-B", "-m", "unittest", "discover", "-q"]


def command_line(argv):
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def independent_tests(work, fixture):
    started = time.monotonic()
    try:
        proc = subprocess.run(test_argv(fixture), cwd=work, capture_output=True,
                              text=True, timeout=300)
        return {"returncode": proc.returncode, "output": (proc.stdout + proc.stderr)[-12000:],
                "secs": time.monotonic() - started}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "output": "Independent test run timed out after 300 seconds.",
                "secs": time.monotonic() - started}
    except OSError as exc:
        return {"returncode": None, "output": f"Independent test runner failed: {exc}",
                "secs": time.monotonic() - started}


def local_api(endpoint, route, payload=None):
    # Reuse the client's endpoint validation and prohibit proxies and redirects.
    from patchsmith.llm import local_url, NoRedirects
    parts = urlsplit(local_url(endpoint))
    url = urlunsplit((parts.scheme, parts.netloc, route, "", ""))
    body = None if payload is None else json.dumps(payload).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/json"})
    with build_opener(ProxyHandler({}), NoRedirects()).open(req, timeout=180) as res:
        return json.load(res)


def gpu_evidence(endpoint, model):
    status = local_api(endpoint, "/api/ps")
    matches = [entry for entry in status.get("models", [])
               if model in {entry.get("name"), entry.get("model")}]
    loaded = matches[0] if matches else {}
    size, vram = loaded.get("size", 0), loaded.get("size_vram", 0)
    return {"checked_at": datetime.now(timezone.utc).isoformat(),
            "full_gpu": bool(size > 0 and vram >= size), "ollama_model": loaded}


def outcome_ok(row):
    if row["fixture"] == "blocked":
        return row["status"] == "blocked" and not row["green"] and not row["files_changed"]
    return row["status"] == "done" and row["green"]


def one(plugin, fixture, args, run_index):
    with tempfile.TemporaryDirectory(prefix=f"ps-{fixture}-") as name:
        work = Path(name)
        shutil.copytree(ROOT / "tests" / "fixtures" / fixture, work, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        git(work, "init", "-q")
        git(work, "config", "user.email", "eval@example.invalid")
        git(work, "config", "user.name", "Patchsmith Evaluation")
        git(work, "add", "-A")
        git(work, "commit", "-qm", "Seed fixture")
        baseline = independent_tests(work, fixture)
        if baseline["returncode"] in (0, None):
            raise RuntimeError(f"{fixture}: fixture must begin with failing tests")
        call = {"task": TASKS[fixture], "workdir": str(work),
                "model": args.model, "attempts": getattr(args, "attempts", 1)}
        started = time.monotonic()
        saved = {k: os.environ.get(k) for k in ("PS_ENDPOINT", "PS_TEST_COMMAND")}
        test_command = command_line(test_argv(fixture))
        os.environ["PS_ENDPOINT"] = args.endpoint
        os.environ["PS_TEST_COMMAND"] = test_command
        try:
            res = json.loads(plugin._handle_implement_task(call))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        secs = time.monotonic() - started
        try:
            gpu = gpu_evidence(args.endpoint, args.model) if args.require_gpu else None
        except Exception as exc:
            gpu = {"full_gpu": False, "error": str(exc)}
        tests = independent_tests(work, fixture)
        row = {"fixture": fixture, "run": run_index, "status": res["status"],
               "reason": res.get("reason"), "note": res.get("note"),
               "turns": res["turns"], "tokens_est": res["tokens_est"], "secs": secs,
               "green": tests["returncode"] == 0, "independent_tests": tests,
               "baseline_tests": baseline, "files_changed": res["files_changed"],
               "diff": res["diff"], "attempt_history": res.get("attempt_history", []),
               "handback": res.get("handback"), "gpu": gpu, "test_command": test_command}
        if res.get("transcript_path"):
            transcript = Path(res["transcript_path"])
            if args.out:
                target = Path(args.out).parent / (Path(args.out).stem + '.transcripts')
                target.mkdir(parents=True, exist_ok=True)
                saved = target / f"{fixture}-{run_index}.jsonl"
                shutil.copyfile(transcript, saved)
                row["transcript_path"] = saved.as_posix()
        history = res.get("attempt_history", [])
        row["first_attempt_success"] = bool(row["green"] and history and history[0]["status"] == "done"
                                             and history[0].get("test_output", "").startswith("exit 0"))
        row["within_three_success"] = row["status"] == "done" and row["green"]
        row["expected_outcome"] = outcome_ok(row)
        return row


def results_table(rows, fixtures):
    lines = ["| fixture | runs | done | blocked | error | tests green | expected outcome | full GPU | median turns | median secs | first-attempt success | success within three |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for fixture in fixtures:
        selected = [r for r in rows if r["fixture"] == fixture]
        if not selected:
            continue
        count = len(selected)
        statuses = [sum(r["status"] == s for r in selected) for s in ("done", "blocked", "error")]
        gpu_count = sum(bool(r.get("gpu") and r["gpu"]["full_gpu"]) for r in selected)
        lines.append(f"| {fixture} | {count} | {statuses[0]} | {statuses[1]} | {statuses[2]} | "
                     f"{sum(r['green'] for r in selected)}/{count} | "
                     f"{sum(r['expected_outcome'] for r in selected)}/{count} | {gpu_count}/{count} | "
                     f"{statistics.median(r['turns'] for r in selected)} | "
                     f"{statistics.median(r['secs'] for r in selected)} | "
                     f"{sum(r.get('first_attempt_success', False) for r in selected)}/{count} | "
                     f"{sum(r.get('within_three_success', False) for r in selected)}/{count} |")
    return "\n".join(lines) + "\n"


def save(args, metadata, rows, fixtures):
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        path.with_suffix('.table.md').write_text(results_table(rows, fixtures), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--fixtures", "--bugs", dest="fixtures", default=",".join(TASKS))
    parser.add_argument("--fixture-runs", action="append", default=[], metavar="NAME=N")
    parser.add_argument("--model", default=os.environ.get("PS_MODEL", "qwen3.5:9b"))
    parser.add_argument("--endpoint", default=os.environ.get("PS_ENDPOINT", "http://127.0.0.1:11434/v1"))
    parser.add_argument("--require-gpu", action="store_true", help="Require full Ollama GPU residency and record it per run")
    parser.add_argument("--out")
    args = parser.parse_args()
    fixtures = args.fixtures.split(',')
    if args.runs < 1 or len(set(fixtures)) != len(fixtures) or any(f not in TASKS for f in fixtures):
        parser.error("Use positive run counts and unique known fixture names")
    counts = dict.fromkeys(fixtures, args.runs)
    for item in args.fixture_runs:
        try:
            fixture, amount = item.split('=')
            if fixture not in counts or int(amount) < 1:
                raise ValueError
            counts[fixture] = int(amount)
        except ValueError:
            parser.error("--fixture-runs requires a selected fixture and positive count, NAME=N")
    plugin = load_plugin()
    if args.require_gpu:
        local_api(args.endpoint, "/api/generate", {"model": args.model, "prompt": "OK", "stream": False,
                                                  "think": False, "options": {"num_predict": 1}})
        if not gpu_evidence(args.endpoint, args.model)["full_gpu"]:
            raise SystemExit("GPU preflight failed: model is not fully resident in GPU memory; no benchmark runs started")
    metadata = {"started_at": datetime.now(timezone.utc).isoformat(), "command": command_line(sys.argv),
                "attempts": args.attempts, "model": args.model, "endpoint": args.endpoint, "python": sys.version,
                "platform": platform.platform(), "require_gpu": args.require_gpu, "counts": counts,
                "budgets": {"max_turns": os.environ.get("PS_MAX_TURNS", "25"),
                            "context_budget_tokens": os.environ.get("PS_CTX_BUDGET", "24000")}}
    rows = []
    for fixture in fixtures:
        for index in range(1, counts[fixture] + 1):
            row = one(plugin, fixture, args, index)
            rows.append(row)
            save(args, metadata, rows, fixtures)
            print(f"{fixture} {index}/{counts[fixture]} {row['status']} {row['reason']} "
                  f"turns={row['turns']} secs={row['secs']} tests={'green' if row['green'] else 'RED'} "
                  f"expected={row['expected_outcome']}", flush=True)
            if args.require_gpu and not row['gpu']['full_gpu']:
                raise SystemExit("GPU residency changed: partial results saved; benchmark stopped")
    print(results_table(rows, fixtures))


if __name__ == "__main__":
    main()
