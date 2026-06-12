import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ["TAVILY_API_KEY"] = ""
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import intelligent_gateway as gateway


class FakeResult:
    def __init__(self, raw):
        self.raw = raw


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


class NamedAgent:
    def __init__(self, name):
        self.name = name


def reset_fakes():
    FakeCrew.next_raw = '{"category": "writing", "confidence": 0.5}'
    FakeCrew.next_exception = None
    FakeCrew.kickoff_agents = []


def install_fakes():
    gateway.Task = FakeTask
    gateway.Crew = FakeCrew
    gateway.router_agent = NamedAgent("router")
    gateway.market_agent = NamedAgent("market")
    gateway.tech_agent = NamedAgent("technical")
    gateway.writer_agent = NamedAgent("writing")


def test_select_agent_routes():
    assert gateway.select_agent("market").name == "market"
    assert gateway.select_agent("technical").name == "technical"
    assert gateway.select_agent("writing").name == "writing"
    assert gateway.select_agent("unknown").name == "writing"


def test_classify_request_valid_json():
    reset_fakes()
    FakeCrew.next_raw = '{"category": "market", "confidence": 0.91}'

    category, confidence = gateway.classify_request("Analyze the market")

    assert category == "market"
    assert confidence == 0.91
    assert FakeCrew.kickoff_agents == [gateway.router_agent]


def test_classify_request_invalid_json_fallback():
    reset_fakes()
    FakeCrew.next_raw = "not json"

    category, confidence = gateway.classify_request("Broken router output")

    assert category == "writing"
    assert confidence == 0.5


def test_classify_request_kickoff_failure_fallback():
    reset_fakes()
    FakeCrew.next_exception = RuntimeError("OpenAI unavailable")

    category, confidence = gateway.classify_request("Router provider failure")

    assert category == "writing"
    assert confidence == 0.0
    assert FakeCrew.kickoff_agents == [gateway.router_agent]


def test_classify_request_unknown_category_fallback():
    reset_fakes()
    FakeCrew.next_raw = '{"category": "finance", "confidence": 0.88}'

    category, confidence = gateway.classify_request("Unsupported category")

    assert category == "writing"
    assert confidence == 0.88


def assert_run_gateway_routes(category, expected_agent):
    reset_fakes()
    original_classifier = gateway.classify_request
    gateway.classify_request = lambda user_input: (category, 0.99)

    try:
        FakeCrew.next_raw = f"{expected_agent} response"
        result = gateway.run_gateway(f"Route to {category}")
    finally:
        gateway.classify_request = original_classifier

    assert result == f"{expected_agent} response"
    assert FakeCrew.kickoff_agents == [getattr(gateway, f"{expected_agent}_agent")]


def test_run_gateway_market_route():
    assert_run_gateway_routes("market", "market")


def test_run_gateway_technical_route():
    assert_run_gateway_routes("technical", "tech")


def test_run_gateway_writing_route():
    assert_run_gateway_routes("writing", "writer")


def test_run_gateway_specialist_failure_returns_friendly_error():
    reset_fakes()
    original_classifier = gateway.classify_request
    gateway.classify_request = lambda user_input: ("technical", 0.99)
    FakeCrew.next_exception = RuntimeError("OpenAI unavailable")

    try:
        result = gateway.run_gateway("Route to technical")
    finally:
        gateway.classify_request = original_classifier

    assert result == "Gateway execution failed: unable to reach the LLM provider. Please try again later."
    assert FakeCrew.kickoff_agents == [gateway.tech_agent]


def main():
    install_fakes()
    test_select_agent_routes()
    test_classify_request_valid_json()
    test_classify_request_invalid_json_fallback()
    test_classify_request_kickoff_failure_fallback()
    test_classify_request_unknown_category_fallback()
    test_run_gateway_market_route()
    test_run_gateway_technical_route()
    test_run_gateway_writing_route()
    test_run_gateway_specialist_failure_returns_friendly_error()
    print("All mock gateway routing tests passed.", flush=True)


if __name__ == "__main__":
    main()
    os._exit(0)
