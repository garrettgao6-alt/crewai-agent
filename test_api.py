import importlib
import sys
import types


def import_api_with_fake_gateway(monkeypatch):
    fake_gateway = types.ModuleType("intelligent_gateway")
    fake_gateway.calls = []

    def run_gateway(query):
        fake_gateway.calls.append(query)
        return f"analyzed: {query}"

    fake_gateway.run_gateway = run_gateway
    monkeypatch.setitem(sys.modules, "intelligent_gateway", fake_gateway)
    sys.modules.pop("api", None)

    return importlib.import_module("api"), fake_gateway


def test_health_returns_ok(monkeypatch):
    api, _ = import_api_with_fake_gateway(monkeypatch)

    response = api.health()

    assert response == {"status": "ok"}


def test_analyze_calls_gateway_and_returns_result(monkeypatch):
    api, fake_gateway = import_api_with_fake_gateway(monkeypatch)

    response = api.analyze(api.AnalyzeRequest(query="用户问题"))

    assert response.model_dump() == {"result": "analyzed: 用户问题"}
    assert fake_gateway.calls == ["用户问题"]
