"""Seeded-bug benchmark. Usage: python eval/run_eval.py [--runs N] [--bugs bug1,bug2] [--model M] [--endpoint URL] [--out FILE]

Copies each fixture to a temp git repo, calls the plugin handler directly, then
re-runs the tests independently (status alone is not trusted)."""
import argparse, importlib.util, json, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS = {
    "bug1": "best_score() in scorer.py should return the highest score but returns the wrong value. Fix it.",
    "bug2": "podium() in report.py should list the top three players by points, highest first, but the order is wrong. Fix the bug.",
}


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "patchsmith", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["patchsmith"] = mod
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


def one(plugin, bug, args):
    work = Path(tempfile.mkdtemp(prefix=f"ps-{bug}-"))
    shutil.copytree(ROOT / "tests" / "fixtures" / bug, work, dirs_exist_ok=True)
    git(work, "init", "-q"); git(work, "config", "user.email", "e@e"); git(work, "config", "user.name", "e")
    git(work, "add", "-A"); git(work, "commit", "-qm", "seed")
    cmd = f'"{sys.executable}" -m pytest -x -q -p no:cacheprovider'
    call = {"task": TASKS[bug], "workdir": str(work), "test_command": cmd}
    if args.model: call["model"] = args.model
    if args.endpoint: call["endpoint"] = args.endpoint
    t = time.time()
    res = json.loads(plugin._handle_implement_task(call))
    secs = time.time() - t
    green = subprocess.run(cmd, shell=True, cwd=work, capture_output=True).returncode == 0
    return {"bug": bug, "status": res["status"], "reason": res.get("reason"), "turns": res["turns"],
            "tokens": res["tokens_est"], "secs": round(secs, 1), "green": green, "diff": res["diff"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--bugs", default=",".join(TASKS))
    ap.add_argument("--model"); ap.add_argument("--endpoint"); ap.add_argument("--out")
    args = ap.parse_args()
    plugin = load_plugin()
    rows = []
    for bug in args.bugs.split(","):
        for i in range(args.runs):
            r = one(plugin, bug, args); rows.append(r)
            print(bug, i + 1, r["status"], r["reason"], r["turns"], r["secs"], "green" if r["green"] else "RED", flush=True)
    lines = ["| bug | runs | done | blocked | error | tests green | median turns | median secs |", "|---|---|---|---|---|---|---|---|"]
    for bug in args.bugs.split(","):
        rs = [r for r in rows if r["bug"] == bug]
        c = lambda s: sum(r["status"] == s for r in rs)
        lines.append(f"| {bug} | {len(rs)} | {c('done')} | {c('blocked')} | {c('error')} | {sum(r['green'] for r in rs)}/{len(rs)} | "
                     f"{statistics.median(r['turns'] for r in rs)} | {statistics.median(r['secs'] for r in rs)} |")
    table = "\n".join(lines)
    print(table)
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
        Path(args.out).with_suffix(".table.md").write_text(table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
