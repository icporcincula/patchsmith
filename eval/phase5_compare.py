"""Compare complete Phase 5 cohorts without dropping failed outcomes."""

import argparse
import json
from pathlib import Path
from statistics import median


def compare(before, after):
    for field in ("attempts", "model", "endpoint", "python", "platform", "require_gpu", "counts", "budgets"):
        if before["metadata"][field] != after["metadata"][field]:
            raise ValueError("Cohort metadata differs: " + field)
    counts = before["metadata"]["counts"]
    if len(counts) != 8 or any(value != 5 for value in counts.values()):
        raise ValueError("Expected eight fixtures with five runs each")
    wanted = {(fixture, run) for fixture in counts for run in range(1, 6)}
    for cohort in (before, after):
        rows = cohort["rows"]
        if len(rows) != len(wanted) or {(row["fixture"], row["run"]) for row in rows} != wanted:
            raise ValueError("Incomplete or duplicate runs")
        if not all(row.get("gpu", {}).get("full_gpu") is True for row in rows):
            raise ValueError("Missing full GPU evidence")
        for row in rows:
            code = row["independent_tests"]["returncode"]
            expected = (row["status"] == "blocked" and code not in (0, None) and not row["files_changed"]
                        if row["fixture"] == "blocked" else row["status"] == "done" and code == 0)
            if row["expected_outcome"] != expected or row["green"] != (code == 0):
                raise ValueError("Outcome disagrees with independent tests")
    identities = []
    for cohort in (before, after):
        values = {(row["gpu"]["ollama_model"].get("digest"),
                   row["gpu"]["ollama_model"].get("context_length"),
                   row["gpu"]["ollama_model"].get("details", {}).get("quantization_level"))
                  for row in cohort["rows"]}
        if len(values) != 1 or not next(iter(values))[0]:
            raise ValueError("Model identity or context changed within cohort")
        identities.append(values)
    if identities[0] != identities[1]:
        raise ValueError("Model identity differs between cohorts")
    rows_b, rows_a = before["rows"], after["rows"]
    fixtures = []
    for fixture in counts:
        b = [row for row in rows_b if row["fixture"] == fixture]
        a = [row for row in rows_a if row["fixture"] == fixture]
        fixtures.append({"fixture": fixture,
                         "before_expected": sum(row["expected_outcome"] for row in b),
                         "after_expected": sum(row["expected_outcome"] for row in a),
                         "before_median_turns": median(row["turns"] for row in b),
                         "after_median_turns": median(row["turns"] for row in a),
                         "before_median_secs": median(row["secs"] for row in b),
                         "after_median_secs": median(row["secs"] for row in a)})
    summary = {}
    for label, rows in (("before", rows_b), ("after", rows_a)):
        implementation = [row for row in rows if row["fixture"] != "blocked"]
        summary[label] = {"expected_outcomes": sum(row["expected_outcome"] for row in rows),
                          "implementation_successes": sum(row["expected_outcome"] for row in implementation),
                          "median_turns": median(row["turns"] for row in rows),
                          "median_secs": median(row["secs"] for row in rows),
                          "implementation_median_turns": median(row["turns"] for row in implementation),
                          "implementation_median_secs": median(row["secs"] for row in implementation)}
    no_regression = all(row["after_expected"] >= row["before_expected"] for row in fixtures)
    faster = (summary["after"]["median_turns"] < summary["before"]["median_turns"] or
              summary["after"]["median_secs"] < summary["before"]["median_secs"])
    summary.update(no_fixture_success_regression=no_regression, median_improved=faster,
                   keep_candidate=no_regression and faster, fixtures=fixtures)
    return summary


def table(result):
    lines = ["| fixture | expected before | expected after | median turns before | median turns after | median secs before | median secs after |",
             "|---|---|---|---|---|---|---|"]
    for row in result["fixtures"]:
        lines.append("| " + " | ".join(str(row[key]) for key in (
            "fixture", "before_expected", "after_expected", "before_median_turns", "after_median_turns",
            "before_median_secs", "after_median_secs")) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(json.loads(args.before.read_text(encoding="utf-8")),
                     json.loads(args.after.read_text(encoding="utf-8")))
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.out.with_suffix(".table.md").write_text(table(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "fixtures"}, indent=2))


if __name__ == "__main__":
    main()
