"""Read-only local inventory and conservative comparisons; no model loading."""
import csv
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, ProxyHandler, build_opener

from .llm import local_url, NoRedirects

GIB = 1024 ** 3


def command(argv):
    """Fixed argument vectors only; failed or missing probes remain unknown."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=8,
                           encoding="utf-8", errors="replace")
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def positive(value):
    try:
        number = int(value)
        return number if number > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def host_inventory():
    system = platform.system()
    result = {"os": system, "os_release": platform.release(), "architecture": platform.machine(),
              "cpu": {"name": platform.processor() or None, "logical_cores": os.cpu_count()},
              "ram_bytes": None, "gpus": [], "warnings": [],
              "backend_commands": {name: shutil.which(name) is not None for name in ("ollama", "llama-server")}}
    if system == "Windows":
        data = command(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
            "$c=Get-CimInstance Win32_Processor | Select-Object -First 1; "
            "$m=Get-CimInstance Win32_ComputerSystem; "
            "$g=@(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }); "
            "@{cpu=$c.Name; ram=$m.TotalPhysicalMemory; gpus=$g} | ConvertTo-Json -Compress"])
        try:
            info = json.loads(data)
            result["cpu"]["name"] = (info.get("cpu") or result["cpu"]["name"] or "").strip() or None
            result["ram_bytes"] = positive(info.get("ram"))
            result["gpus"] = [{"name": n, "total_bytes": None, "free_bytes": None,
                               "source": "Windows display controller"} for n in info.get("gpus", []) if isinstance(n, str)]
        except (ValueError, TypeError, AttributeError):
            result["warnings"].append("Windows hardware probe unavailable.")
    elif system == "Linux":
        try:
            cpu = Path("/proc/cpuinfo").read_text(encoding="utf-8")
            for line in cpu.splitlines():
                if line.startswith("model name"):
                    result["cpu"]["name"] = line.split(":", 1)[1].strip()
                    break
            mem = Path("/proc/meminfo").read_text(encoding="utf-8")
            for line in mem.splitlines():
                if line.startswith("MemTotal:"):
                    result["ram_bytes"] = int(line.split()[1]) * 1024
            for device in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
                vendor = (device / "vendor").read_text(encoding="utf-8").strip()
                total_path = device / "mem_info_vram_total"
                free = None
                total = positive(total_path.read_text()) if total_path.exists() else None
                used_path = device / "mem_info_vram_used"
                if total and used_path.exists():
                    free = max(0, total - int(used_path.read_text()))
                result["gpus"].append({"name": "PCI GPU vendor " + vendor,
                    "total_bytes": total, "free_bytes": free, "source": "Linux DRM"})
        except (OSError, ValueError):
            result["warnings"].append("Some Linux hardware fields are unavailable.")
    elif system == "Darwin":
        result["ram_bytes"] = positive(command(["sysctl", "-n", "hw.memsize"]))
        result["cpu"]["name"] = command(["sysctl", "-n", "machdep.cpu.brand_string"]) or result["cpu"]["name"]
        try:
            displays = json.loads(command(["system_profiler", "SPDisplaysDataType", "-json"]))
            result["gpus"] = [{"name": g.get("sppci_model") or g.get("_name") or "GPU",
                "total_bytes": None, "free_bytes": None, "source": "macOS display inventory"}
                for g in displays.get("SPDisplaysDataType", [])]
        except (ValueError, AttributeError, TypeError):
            pass
        # Unified RAM is never reported as dedicated free VRAM.
        result["warnings"].append("Unified GPU memory is not measured as dedicated VRAM.")
    else:
        result["warnings"].append("This operating system has limited hardware probes.")
    nvidia = shutil.which("nvidia-smi")
    if not nvidia and Path("/usr/lib/wsl/lib/nvidia-smi").is_file():
        nvidia = "/usr/lib/wsl/lib/nvidia-smi"
    if nvidia:
        raw = command([nvidia, "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"])
        found = []
        for row in csv.reader(io.StringIO(raw)):
            if len(row) != 4:
                continue
            total, free = positive(row[1]), positive(row[2])
            found.append({"name": row[0].strip(), "total_bytes": total * 1024 ** 2 if total else None,
                "free_bytes": free * 1024 ** 2 if free else (0 if row[2].strip() == "0" else None),
                "driver_version": row[3].strip(), "source": "nvidia-smi"})
        if found:
            # Avoid counting the same display adapter twice.
            result["gpus"] = [g for g in result["gpus"] if "nvidia" not in g["name"].lower()] + found
    if not result["gpus"]:
        result["warnings"].append("No GPU detected; this does not prove that no GPU is present.")
    return result


def api(endpoint, route):
    parts = urlsplit(local_url(endpoint))
    url = urlunsplit((parts.scheme, parts.netloc, route, "", ""))
    with build_opener(ProxyHandler({}), NoRedirects()).open(Request(url), timeout=4) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("Inventory response exceeds 1 MiB.")
    return json.loads(raw)


def backend_inventory(endpoint):
    # Validate before probing anything, including optional Ollama routes.
    host = urlsplit(local_url(endpoint)).hostname
    result = {"kind": "unknown", "version": None, "reachable": False, "models": [],
              "loaded_models": [], "host_is_loopback": host in {"127.0.0.1", "::1"}, "warnings": []}
    try:
        data = api(endpoint, "/v1/models")
        result["models"] = [{"name": m["id"], "size_bytes": None, "quantization": None}
                            for m in data.get("data", []) if isinstance(m.get("id"), str)]
        result["reachable"] = True
        result["kind"] = "OpenAI-compatible (identity unverified)"
    except Exception:
        result["warnings"].append("Configured local model API is unavailable or does not list models.")
    try:
        version = api(endpoint, "/api/version")
        if not isinstance(version.get("version"), str):
            raise ValueError("Not an Ollama version response")
        result.update(kind="Ollama", version=version["version"], reachable=True)
        tags = api(endpoint, "/api/tags")
        result["models"] = [{"name": m.get("name") or m.get("model"),
            "size_bytes": positive(m.get("size")),
            "quantization": (m.get("details") or {}).get("quantization_level"), "digest": m.get("digest")}
            for m in tags.get("models", []) if isinstance(m.get("name") or m.get("model"), str)]
        loaded = api(endpoint, "/api/ps")
        result["loaded_models"] = [{"name": m.get("name") or m.get("model"),
            "size_bytes": positive(m.get("size")), "vram_bytes": positive(m.get("size_vram"))}
            for m in loaded.get("models", [])]
    except Exception:
        if result["kind"] == "Ollama":
            result["warnings"].append("Some Ollama model metadata is unavailable.")
    if not result["host_is_loopback"]:
        result["warnings"].append("API uses a private-network address: confirm its hardware is this host before comparing it with this inventory.")
    return result


def estimate(model, hardware):
    size = positive(model.get("size_bytes"))
    if not size:
        return {"model": model["name"], "classification": "unknown", "reason": "Model weight size unavailable."}
    # Weight storage is a lower bound. Do not pool cards or count RAM as VRAM.
    reserve = 2 * GIB
    free = max((g.get("free_bytes") or 0 for g in hardware["gpus"]), default=0)
    total = max((g.get("total_bytes") or 0 for g in hardware["gpus"]), default=0)
    required = int(size * 1.2) + reserve
    if free >= required:
        kind = "weights_plus_margin_in_free_vram"
    elif total >= required:
        kind = "weights_plus_margin_in_total_vram_only"
    elif (hardware.get("ram_bytes") or 0) >= required:
        kind = "system_ram_capacity_only"
    else:
        kind = "insufficient_known_capacity"
    return {"model": model["name"], "classification": kind, "weight_bytes": size,
            "heuristic_bytes": required,
            "reason": "Estimate: weight bytes x 1.2 + 2 GiB; excludes context-dependent KV cache and runtime requirements. RAM capacity is not available RAM. No speed or reliability prediction."}


def tested_configurations(hardware, backend):
    records = json.loads((Path(__file__).parent / "benchmarks" / "tested.json").read_text(encoding="utf-8"))
    names = {g["name"].strip().casefold() for g in hardware["gpus"]}
    installed = {m["name"] for m in backend["models"]}
    results = []
    for record in records:
        matches = []
        if record["gpu_name"].strip().casefold() in names:
            matches.append("gpu_name")
        if record["model"] in installed:
            matches.append("installed_model_name")
        if record["backend"] == backend["kind"]:
            matches.append("backend_kind")
        results.append({**record, "matching_fields": matches,
                        "comparison": "Shared fields only; not a reproduced benchmark on this machine."})
    return results


def inspect_hardware(args: dict, **kwargs) -> str:
    try:
        if not isinstance(args, dict) or set(args) - {"endpoint"}:
            raise ValueError("Only optional endpoint is accepted.")
        endpoint = args.get("endpoint", os.environ.get("PS_ENDPOINT", "http://127.0.0.1:11434/v1"))
        if not isinstance(endpoint, str):
            raise ValueError("endpoint must be a string")
        if not endpoint.strip():
            endpoint = os.environ.get("PS_ENDPOINT", "http://127.0.0.1:11434/v1")
        local_url(endpoint)
        host = host_inventory()
        backend = backend_inventory(endpoint)
        return json.dumps({"status": "done", "schema_version": 1, "hardware": host, "backend": backend,
            "estimates": [estimate(m, host) for m in backend["models"]],
            "tested_configurations": tested_configurations(host, backend),
            "limits": ["Read-only; no model loading, downloads, installation or uploads.",
                       "Inventory describes the machine running Hermes, which may be WSL or a container.",
                       "Unknown fields remain unknown; memory fit does not establish speed, coding quality or tool-calling support. Inventory can include embedding models."]})
    except Exception as exc:
        return json.dumps({"status": "error", "reason": "inventory_failed", "note": str(exc)})
