"""diagnostics.py — startup self-test that catches the most common Windows pain points.

Each check returns (ok: bool, label: str, detail: str). The diagnose() helper runs
all of them and returns a structured report the UI can render.
"""
from __future__ import annotations

import importlib
import logging
import socket
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("voice2ai.diagnostics")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


# ── individual checks ────────────────────────────────────────────────

def check_dependencies() -> list[CheckResult]:
    """Each runtime dep is import-tested separately so we can pinpoint which one is missing."""
    needed = ["numpy", "sounddevice", "soundfile", "requests", "pyperclip", "pynput", "dotenv"]
    results = []
    for mod in needed:
        try:
            importlib.import_module(mod)
            results.append(CheckResult(f"dependency:{mod}", True, "installed"))
        except Exception as e:
            results.append(CheckResult(f"dependency:{mod}", False, f"{type(e).__name__}: {e}"))
    # tray icon is optional
    try:
        importlib.import_module("pystray")
        importlib.import_module("PIL")
        results.append(CheckResult("dependency:pystray", True, "installed"))
    except Exception as e:
        results.append(CheckResult(
            "dependency:pystray",
            False,
            f"optional — tray icon disabled ({type(e).__name__})",
        ))
    return results


def check_microphone() -> CheckResult:
    """Open and close an InputStream to verify the mic + driver are usable."""
    try:
        import sounddevice as sd
        info = sd.query_devices(kind="input")
        name = info.get("name", "?") if isinstance(info, dict) else "?"
        # try opening at 16000Hz mono — sounddevice will negotiate or raise
        with sd.InputStream(samplerate=16000, channels=1, dtype="float32"):
            pass
        return CheckResult("microphone", True, f"{name}")
    except Exception as e:
        return CheckResult("microphone", False, f"{type(e).__name__}: {e}")


def check_network(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> CheckResult:
    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        ms = int((time.time() - t0) * 1000)
        return CheckResult("network", True, f"{ms}ms to {host}:{port}")
    except Exception as e:
        return CheckResult("network", False, f"{type(e).__name__}: {e}")


def check_provider_reachable(provider_name: str, host_override: Optional[str] = None) -> CheckResult:
    """TCP-reach the provider's API host. Doesn't validate the API key — that's check_api()."""
    hosts = {
        "siliconflow": "api.siliconflow.cn",
        "openai": "api.openai.com",
        "groq": "api.groq.com",
        "azure": "openai.azure.com",
    }
    host = host_override or hosts.get(provider_name)
    if not host:
        return CheckResult(f"reach:{provider_name}", False, f"unknown provider")
    t0 = time.time()
    try:
        sock = socket.create_connection((host, 443), timeout=5.0)
        sock.close()
        ms = int((time.time() - t0) * 1000)
        return CheckResult(f"reach:{provider_name}", True, f"{ms}ms")
    except Exception as e:
        return CheckResult(f"reach:{provider_name}", False, f"{host}: {e}")


def check_api(provider_obj) -> CheckResult:
    """Send a 0.5s synthetic tone and confirm 200 OK."""
    try:
        result = provider_obj.health_check()
        if result.ok:
            return CheckResult("api", True, f"{result.latency_ms}ms")
        return CheckResult("api", False, result.error or "unknown")
    except Exception as e:
        return CheckResult("api", False, f"{type(e).__name__}: {e}")


# ── orchestrator ─────────────────────────────────────────────────────

def diagnose(settings, provider_obj=None) -> list[CheckResult]:
    """Run all checks. Provider checks are skipped if provider_obj is None."""
    results: list[CheckResult] = []
    results.extend(check_dependencies())
    results.append(check_microphone())
    results.append(check_network())
    if provider_obj is not None:
        results.append(check_provider_reachable(settings.provider))
        results.append(check_api(provider_obj))
    return results


def format_report(results: list[CheckResult]) -> str:
    lines = []
    for r in results:
        icon = "✓" if r.ok else "✗"
        lines.append(f"  {icon} {r.name}: {r.detail}")
    return "\n".join(lines)
