"""Sequential, proposal-only comparison of two local models."""

import json


def compare(args):
    if not isinstance(args, dict) or set(args) != {"task", "workdir", "models"}:
        raise ValueError("Provide task, workdir and two model names.")
    models = args["models"]
    if (not isinstance(models, list) or len(models) != 2
            or any(not isinstance(model, str) or not model.strip() for model in models)
            or models[0] == models[1]):
        raise ValueError("models must contain two distinct local model names.")
    from .loop import implement
    results = []
    for model in models:
        result = implement({"task": args["task"], "workdir": args["workdir"],
                            "model": model, "mode": "propose"})
        results.append({"model": model, "result": result})
    return {"status": "done", "comparisons": results,
            "note": "Both runs used isolated proposals. Review each diff and verification result before choosing a patch."}


def compare_tool(args, **kwargs):
    try:
        return json.dumps(compare(args))
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "comparison_failed", "note": str(exc)})
