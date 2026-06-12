import importlib
import os
import sys
import types


class FakeResult:
    def __init__(self, raw):
        self.raw = raw


class FakeAgent:
    def __init__(self, role, goal=None, backstory=None, llm=None, verbose=None):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.llm = llm
        self.verbose = verbose


class FakeChatOpenAI:
    def __init__(self, model, temperature):
        self.model = model
        self.temperature = temperature


class FakeTask:
    def __init__(self, description, expected_output, agent, context=None):
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.context = context or []


class FakeCrew:
    next_raw = "executive report"
    next_exception = None
    last_agents = []
    last_tasks = []

    def __init__(self, agents, tasks, verbose):
        self.agents = agents
        self.tasks = tasks
        self.verbose = verbose
        FakeCrew.last_agents = agents
        FakeCrew.last_tasks = tasks

    def kickoff(self):
        if FakeCrew.next_exception is not None:
            raise FakeCrew.next_exception
        return FakeResult(FakeCrew.next_raw)


def reset_fakes():
    FakeCrew.next_raw = "executive report"
    FakeCrew.next_exception = None
    FakeCrew.last_agents = []
    FakeCrew.last_tasks = []


def install_fake_modules(monkeypatch):
    fake_crewai = types.ModuleType("crewai")
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew

    fake_langchain_openai = types.ModuleType("langchain_openai")
    fake_langchain_openai.ChatOpenAI = FakeChatOpenAI

    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_langchain_openai)


def import_executive_agents(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    install_fake_modules(monkeypatch)

    for module_name in ["executive_agents", "config"]:
        sys.modules.pop(module_name, None)

    return importlib.import_module("executive_agents")


def test_run_executive_agent_team_returns_payload(monkeypatch):
    reset_fakes()
    executive_agents = import_executive_agents(monkeypatch)

    result = executive_agents.run_executive_agent_team(
        "Full Project Review",
        "=== File: contract.pdf ===\nContract text",
    )

    assert result == {
        "category": "executive",
        "confidence": 0.95,
        "result": "executive report",
        "version": "1.0",
    }
    assert len(FakeCrew.last_agents) == 7
    assert len(FakeCrew.last_tasks) == 7
    assert FakeCrew.last_agents[-1].role == "Executive Coordinator Agent"
    assert len(FakeCrew.last_tasks[-1].context) == 6


def test_run_executive_agent_team_failure_returns_friendly_error(monkeypatch):
    reset_fakes()
    FakeCrew.next_exception = RuntimeError("OpenAI unavailable")
    executive_agents = import_executive_agents(monkeypatch)

    result = executive_agents.run_executive_agent_team(
        "Full Project Review",
        "=== File: contract.pdf ===\nContract text",
    )

    assert result == {
        "category": "executive",
        "confidence": 0.0,
        "result": executive_agents.EXECUTIVE_ERROR_MESSAGE,
        "version": "1.0",
    }
