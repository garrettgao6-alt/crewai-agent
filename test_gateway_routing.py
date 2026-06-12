import importlib
import os
import sys
import types

import pytest


class FakeResult:
    def __init__(self, raw):
        self.raw = raw


class FakeAgent:
    def __init__(self, role, goal=None, backstory=None, tools=None, llm=None, verbose=None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools or []
        self.llm = llm
        self.verbose = verbose


class FakeChatOpenAI:
    def __init__(self, model, temperature):
        self.model = model
        self.temperature = temperature


class FakeTask:
    def __init__(self, description, expected_output, agent):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent


class FakeCrew:
    next_raw = '{"category": "writing", "confidence": 0.5}'
    next_exception = None
    kickoff_agents = []

    def __init__(self, agents, tasks, verbose):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose

    def kickoff(self):
        FakeCrew.kickoff_agents.append(self.agents[0])
        if FakeCrew.next_exception is not None:
            raise FakeCrew.next_exception
        return FakeResult(FakeCrew.next_raw)


def reset_fakes():
    FakeCrew.next_raw = '{"category": "writing", "confidence": 0.5}'
    FakeCrew.next_exception = None
    FakeCrew.kickoff_agents = []


def install_fake_modules(monkeypatch):
    fake_crewai = types.ModuleType("crewai")
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew

    fake_langchain_openai = types.ModuleType("langchain_openai")
    fake_langchain_openai.ChatOpenAI = FakeChatOpenAI

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_langchain_openai)


def import_gateway(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ["TAVILY_API_KEY"] = ""
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")

    install_fake_modules(monkeypatch)

    for module_name in ["intelligent_gateway", "agents", "config"]:
        sys.modules.pop(module_name, None)

    return importlib.import_module("intelligent_gateway")


@pytest.fixture
def gateway(monkeypatch):
    reset_fakes()
    return import_gateway(monkeypatch)


def test_select_agent_routes(gateway):
    assert gateway.select_agent("market").role == "Market Analyst"
    assert gateway.select_agent("technical").role == "Technical Architect"
    assert gateway.select_agent("writing").role == "Professional Writer"
    assert gateway.select_agent("unknown").role == "Professional Writer"


def test_classify_request_valid_json(gateway):
    reset_fakes()
    FakeCrew.next_raw = '{"category": "market", "confidence": 0.91}'

    category, confidence = gateway.classify_request("Analyze the market")

    assert category == "market"
    assert confidence == 0.91
    assert FakeCrew.kickoff_agents == [gateway.router_agent]


def test_classify_request_invalid_json_fallback(gateway):
    reset_fakes()
    FakeCrew.next_raw = "not json"

    category, confidence = gateway.classify_request("Broken router output")

    assert category == "writing"
    assert confidence == 0.5


def test_classify_request_kickoff_failure_fallback(gateway):
    reset_fakes()
    FakeCrew.next_exception = RuntimeError("OpenAI unavailable")

    category, confidence = gateway.classify_request("Router provider failure")

    assert category == "writing"
    assert confidence == 0.0
    assert FakeCrew.kickoff_agents == [gateway.router_agent]


def test_classify_request_unknown_category_fallback(gateway):
    reset_fakes()
    FakeCrew.next_raw = '{"category": "finance", "confidence": 0.88}'

    category, confidence = gateway.classify_request("Unsupported category")

    assert category == "writing"
    assert confidence == 0.88


def assert_run_gateway_routes(monkeypatch, gateway, category, expected_agent_name, expected_role):
    reset_fakes()
    monkeypatch.setattr(gateway, "classify_request", lambda user_input: (category, 0.99))

    FakeCrew.next_raw = f"{expected_agent_name} response"
    result = gateway.run_gateway(f"Route to {category}")

    assert result == f"{expected_agent_name} response"
    assert FakeCrew.kickoff_agents == [getattr(gateway, f"{expected_agent_name}_agent")]
    assert FakeCrew.kickoff_agents[0].role == expected_role


def test_run_gateway_market_route(monkeypatch, gateway):
    assert_run_gateway_routes(monkeypatch, gateway, "market", "market", "Market Analyst")


def test_run_gateway_technical_route(monkeypatch, gateway):
    assert_run_gateway_routes(monkeypatch, gateway, "technical", "tech", "Technical Architect")


def test_run_gateway_writing_route(monkeypatch, gateway):
    assert_run_gateway_routes(monkeypatch, gateway, "writing", "writer", "Professional Writer")


def test_run_gateway_specialist_failure_returns_friendly_error(monkeypatch, gateway):
    reset_fakes()
    monkeypatch.setattr(gateway, "classify_request", lambda user_input: ("technical", 0.99))
    FakeCrew.next_exception = RuntimeError("OpenAI unavailable")

    result = gateway.run_gateway("Route to technical")

    assert result == "Gateway execution failed: unable to reach the LLM provider. Please try again later."
    assert FakeCrew.kickoff_agents == [gateway.tech_agent]
