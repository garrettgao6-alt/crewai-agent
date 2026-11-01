"""Public demo security boundary and numerical behavior."""
import pytest
from core import public_demo as demo


def test_all_workflows_are_useful_and_require_no_provider(monkeypatch):
    import builtins
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError("Public computation attempted file/network access")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    for case in demo.CASE_NAMES:
        for workflow in demo.WORKFLOWS:
            report = demo.analyze(case, workflow)
            assert report["ai_tokens"] == 0
            assert report["sources"]
            assert "SYNTHETIC DEMO ONLY" in report["result"]
            assert "[" in report["result"]
            assert demo.export_report(report)


def test_scenario_math_and_sample_isolation():
    a = demo.analyze("Riverside sample", "Financial Analysis", 10)
    b = demo.analyze("Hillview sample", "Financial Analysis", 10)
    assert a["calculation"] == {"lead_gap_weeks": 4, "gross_margin": 300000, "delay_exposure": 40000}
    assert b["calculation"] == {"lead_gap_weeks": 0, "gross_margin": 120000, "delay_exposure": 25000}
    a["sources"][0]["text"] = "PRIVATE_INJECTED"
    a["result"] = "PRIVATE_INJECTED"
    assert "PRIVATE_INJECTED" not in demo.export_report(a)
    assert "PRIVATE_INJECTED" not in demo.analyze("Riverside sample", "Contracts")["sources"][0]["text"]


def test_allowlist_and_bounded_inputs():
    with pytest.raises(KeyError):
        demo.documents("/root/crewai-agent/.env")
    with pytest.raises(ValueError):
        demo.analyze("Riverside sample", "read private projects")
    for invalid in (-1, 91, "7", True):
        with pytest.raises(ValueError):
            demo.analyze("Riverside sample", "Contracts", invalid)
    assert demo.search("Riverside sample", "no-such-evidence") == []
    assert len(demo.search("Riverside sample", "payment")) == 1
