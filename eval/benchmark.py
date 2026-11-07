"""Run bundled fixtures and export a versioned, path-free community summary."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import run_eval

ROOT = Path(__file__).resolve().parents[1]


def fixture_digest():
    digest = hashlib.sha256()
    for path in sorted((ROOT / "tests" / "fixtures").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def build_report(raw, inventory, requested, exit_code):
    meta = raw["metadata"]
    model = next((m for m in inventory["backend"]["models"] if m["name"] == meta["model"]), {})
    rows = []
    for row in raw["rows"]:
        rows.append({"fixture": row["fixture"], "run": row["run"], "status": row["status"],
            "turns": row["turns"], "seconds": row["secs"], "tokens_est": row["tokens_est"],
            "files_changed_count": len(row["files_changed"]),
            "baseline_exit": row["baseline_tests"]["returncode"],
            "independent_exit": row["independent_tests"]["returncode"],
            "implementation_success": row["fixture"] != "blocked" and row["status"] == "done" and row["green"],
            "expected_outcome": run_eval.outcome_ok(row),
            "full_gpu": bool(row.get("gpu") and row["gpu"]["full_gpu"]) if meta["require_gpu"] else None})
    report = {"schema_version": 1, "provenance": "contributor supplied; not independently reproduced",
        "suite": {"name": "patchsmith-synthetic-v1", "fixtures_sha256": fixture_digest(), "requested_runs": requested},
        "hardware": inventory["hardware"],
        "backend": {"kind": inventory["backend"]["kind"], "version": inventory["backend"]["version"],
                    "host_association": "loopback" if inventory["backend"]["host_is_loopback"] else "unconfirmed private-network host"},
        "model": {"name": meta["model"], "quantization": model.get("quantization"), "weight_bytes": model.get("size_bytes"), "digest": model.get("digest")},
        "budgets": {"attempts": meta["attempts"], "max_turns": int(meta["budgets"]["max_turns"]),
                    "context_budget_tokens": int(meta["budgets"]["context_budget_tokens"])},
        "gpu_required": meta["require_gpu"], "runner_exit": exit_code,
        "complete": exit_code == 0 and len(rows) == sum(requested.values()), "rows": rows,
        "limits": ["No endpoint, task text, source, test output or local paths in this summary.",
                   "Raw results and transcripts are separate: review before publication.",
                   "Unknown quantization or backend versions remain unknown. Non-required GPU offload is unmeasured."]}
    validate_report(report)
    return report


def validate_report(report):
    """Reject inconsistent counts or claims before a result can enter the registry."""
    def need(condition, message):
        if not condition:
            raise ValueError(message)
    def integer(value, low=0):
        return type(value) is int and value >= low
    need(isinstance(report, dict) and report.get("schema_version") == 1, "Expected report schema_version 1")
    need(report.get("provenance") in {"contributor supplied; not independently reproduced", "maintainer reproduced"}, "Invalid provenance")
    suite = report["suite"]
    need(suite["name"] == "patchsmith-synthetic-v1", "Unknown suite")
    need(len(suite["fixtures_sha256"]) == 64 and all(c in "0123456789abcdef" for c in suite["fixtures_sha256"]), "Invalid suite digest")
    requested = suite["requested_runs"]
    need(isinstance(requested, dict) and requested and all(f in run_eval.TASKS and integer(n, 1) for f, n in requested.items()), "Invalid requested runs")
    budgets = report["budgets"]
    need(type(budgets["attempts"]) is int and budgets["attempts"] in (1, 2, 3), "Invalid attempts")
    need(integer(budgets["max_turns"], 1) and budgets["max_turns"] <= 60 and integer(budgets["context_budget_tokens"], 1), "Invalid budgets")
    need(type(report["gpu_required"]) is bool and type(report["complete"]) is bool and integer(report["runner_exit"]), "Invalid completion fields")
    need(isinstance(report["model"]["name"], str) and report["model"]["name"], "Missing model")
    need(isinstance(report["hardware"], dict) and isinstance(report["hardware"]["cpu"], dict) and isinstance(report["hardware"]["gpus"], list), "Missing hardware")
    need(isinstance(report["backend"]["kind"], str), "Missing backend")
    for value in (report["model"].get("quantization"), report["model"].get("digest"), report["backend"].get("version")):
        need(value is None or isinstance(value, str), "Invalid model/backend identity")
    need(report["model"].get("weight_bytes") is None or integer(report["model"]["weight_bytes"], 1), "Invalid model weight bytes")
    hardware = report["hardware"]
    need(hardware.get("ram_bytes") is None or integer(hardware["ram_bytes"], 1), "Invalid RAM size")
    for gpu in hardware["gpus"]:
        need(isinstance(gpu, dict) and isinstance(gpu.get("name"), str), "Invalid GPU identity")
        for field in ("total_bytes", "free_bytes"):
            need(gpu.get(field) is None or integer(gpu[field]), "Invalid GPU memory")
    need(isinstance(report["rows"], list), "Expected rows list")
    seen = set()
    for row in report["rows"]:
        f, n = row["fixture"], row["run"]
        need(f in requested and integer(n, 1) and n <= requested[f] and (f, n) not in seen, "Unknown, duplicate or excess run")
        seen.add((f, n))
        need(row["status"] in {"done", "blocked", "error"}, "Invalid status")
        need(integer(row["turns"]) and integer(row["tokens_est"]), "Invalid work metrics")
        need(type(row["seconds"]) in (int, float) and math.isfinite(row["seconds"]) and row["seconds"] >= 0, "Invalid latency")
        need(integer(row["files_changed_count"]), "Invalid changed file count")
        need(type(row["baseline_exit"]) is int and row["baseline_exit"] != 0, "Fixture baseline must fail")
        need(row["independent_exit"] is None or type(row["independent_exit"]) is int, "Invalid independent exit")
        success = f != "blocked" and row["status"] == "done" and row["independent_exit"] == 0
        need(type(row["implementation_success"]) is bool and row["implementation_success"] == success, "Success must have independent green tests")
        need(type(row["expected_outcome"]) is bool, "Invalid expected outcome")
        if f != "blocked":
            need(row["expected_outcome"] == success, "Expected implementation outcome mismatch")
        elif row["expected_outcome"]:
            need(row["status"] == "blocked" and row["independent_exit"] not in (0, None) and row["files_changed_count"] == 0, "Invalid blocked guardrail outcome")
        need(row["full_gpu"] is None or type(row["full_gpu"]) is bool, "Invalid GPU evidence")
        need(report["gpu_required"] or row["full_gpu"] is None, "GPU offload was not measured")
    complete = report["runner_exit"] == 0 and len(seen) == sum(requested.values())
    need(report["complete"] == complete, "Incomplete runs cannot be marked complete")
    if complete and report["gpu_required"]:
        need(all(row["full_gpu"] is True for row in report["rows"]), "Full GPU gate failed")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path, help="Validate an existing report without running models")
    parser.add_argument("--model", default=os.environ.get("PS_MODEL", "qwen3.5:9b"))
    parser.add_argument("--endpoint", default=os.environ.get("PS_ENDPOINT", "http://127.0.0.1:11434/v1"))
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--attempts", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--fixtures", default=",".join(run_eval.TASKS))
    parser.add_argument("--require-gpu", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.validate:
        try:
            validate_report(json.loads(args.validate.read_text(encoding="utf-8")))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            parser.error("Invalid report: " + str(exc))
        print("Report schema and outcome consistency valid; measurements are not independently reproduced.")
        return
    fixtures = args.fixtures.split(",")
    if args.runs < 1 or len(set(fixtures)) != len(fixtures) or any(f not in run_eval.TASKS for f in fixtures):
        parser.error("Use positive runs and unique bundled fixture names")
    if not args.out or args.out.exists():
        parser.error("--out must name a new directory; prior evidence is never overwritten")
    plugin = run_eval.load_plugin()
    inventory = json.loads(plugin.inspect_hardware({"endpoint": args.endpoint}))
    if inventory["status"] != "done":
        parser.error("Local hardware/backend inventory failed")
    args.out.mkdir(parents=True)
    raw_path = args.out / "raw-results.json"
    cmd = [sys.executable, "-B", str(ROOT / "eval" / "run_eval.py"), "--model", args.model,
           "--endpoint", args.endpoint, "--runs", str(args.runs), "--attempts", str(args.attempts),
           "--fixtures", args.fixtures, "--out", str(raw_path)]
    if args.require_gpu:
        cmd.append("--require-gpu")
    result = subprocess.run(cmd, check=False)
    if raw_path.exists():
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        report = build_report(raw, inventory, dict.fromkeys(fixtures, args.runs), result.returncode)
        (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("Versioned report and raw evidence saved. Review before sharing; no upload performed.")
    else:
        (args.out / "preflight-failure.json").write_text(json.dumps({"schema_version": 1,
            "runner_exit": result.returncode, "note": "Runner stopped before any task results; no benchmark claim."}) + "\n", encoding="utf-8")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
