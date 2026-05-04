"""tests/test_diagnostics.py — pure-function checks (no GUI / no network needed)."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from voice2cc.diagnostics import (
    CheckResult, check_dependencies, check_provider_reachable,
    check_api, format_report,
)


def test_check_dependencies_returns_list_of_results():
    results = check_dependencies()
    assert all(isinstance(r, CheckResult) for r in results)
    # at least one of each must be there (numpy / sounddevice / etc.)
    names = {r.name for r in results}
    assert "dependency:numpy" in names
    assert "dependency:requests" in names


def test_check_provider_reachable_unknown():
    r = check_provider_reachable("nonsense_provider_xyz")
    assert r.ok is False


def test_format_report_renders_check_marks():
    results = [
        CheckResult("a", True, "ok"),
        CheckResult("b", False, "boom"),
    ]
    out = format_report(results)
    assert "✓" in out
    assert "✗" in out
    assert "boom" in out


def test_check_api_with_failing_provider():
    fake_provider = MagicMock()
    fake_provider.health_check.return_value = MagicMock(ok=False, error="HTTP 401: bad key")
    r = check_api(fake_provider)
    assert r.ok is False
    assert "401" in r.detail
