import importlib
import sys
import types


def import_api_with_fake_gateway(monkeypatch):
    fake_gateway = types.ModuleType("intelligent_gateway")
    fake_gateway.calls = []

    def run_gateway_v1(query):
        fake_gateway.calls.append(query)
        return {
            "category": "writing",
            "confidence": 0.9,
            "result": f"analyzed: {query}",
            "version": "1.0",
        }

    fake_gateway.run_gateway_v1 = run_gateway_v1
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

    assert response.model_dump() == {
        "category": "writing",
        "confidence": 0.9,
        "result": "analyzed: 用户问题",
        "version": "1.0",
    }
    assert fake_gateway.calls == ["用户问题"]


def test_analyze_openapi_response_schema(monkeypatch):
    api, _ = import_api_with_fake_gateway(monkeypatch)

    schema = api.app.openapi()["components"]["schemas"]["AnalyzeResponse"]

    assert schema["required"] == ["category", "confidence", "result", "version"]
    assert schema["properties"]["category"]["type"] == "string"
    assert schema["properties"]["confidence"]["type"] == "number"
    assert schema["properties"]["result"]["type"] == "string"
    assert schema["properties"]["version"]["type"] == "string"
