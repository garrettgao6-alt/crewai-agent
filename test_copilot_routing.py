import unittest
from unittest.mock import patch

import copilot_core
from core.critic import review_output
from core.engine import memory, run_engine
from core.planner import plan_tasks
from core.router import route_task
from router import detect_intent


class IntentRouterTests(unittest.TestCase):
    def test_keyword_routes_construction_prompts(self):
        self.assertEqual(detect_intent("Review this tender risk"), "construction")

    def test_keyword_routes_business_prompts(self):
        self.assertEqual(detect_intent("Create a growth strategy"), "business")

    @patch("router._classify_with_llm", return_value="general")
    def test_llm_fallback_defaults_to_general(self, _mock_classifier):
        self.assertEqual(detect_intent("Tell me a joke"), "general")


class CopilotDispatcherTests(unittest.TestCase):
    def test_dispatches_to_distinct_agents(self):
        with (
            patch.object(
                copilot_core,
                "run_construction_agent",
                return_value="construction response with enough detail for critic validation",
            ),
            patch.object(
                copilot_core,
                "run_business_agent",
                return_value="business response with enough detail for critic validation",
            ),
            patch.object(
                copilot_core,
                "run_general_agent",
                return_value="general response with enough detail for critic validation",
            ),
        ):
            self.assertEqual(
                copilot_core.run_copilot("Analyze this risk"),
                (
                    "construction response with enough detail for critic validation\n\n"
                    "construction response with enough detail for critic validation"
                ),
            )
            self.assertEqual(
                copilot_core.run_copilot("Improve strategy"),
                "business response with enough detail for critic validation",
            )
            self.assertEqual(
                copilot_core.run_copilot("Hello there"),
                "general response with enough detail for critic validation",
            )


class CoreEngineTests(unittest.TestCase):
    def setUp(self):
        memory.clear()

    def test_planner_breaks_prompt_into_tasks(self):
        self.assertEqual(plan_tasks("Analyze risk and strategy"), ["analysis", "risk", "strategy"])

    def test_router_maps_tasks_to_domains(self):
        self.assertEqual(route_task("analysis"), "construction")
        self.assertEqual(route_task("risk"), "construction")
        self.assertEqual(route_task("strategy"), "business")
        self.assertEqual(route_task("finance"), "business")
        self.assertEqual(route_task("unknown"), "general")

    def test_engine_combines_multiple_task_outputs_and_stores_memory(self):
        calls = []

        def executor(domain, prompt):
            calls.append((domain, prompt))
            return f"{domain} output for {prompt}"

        result = run_engine("Analyze risk and strategy", executor)

        self.assertEqual(
            calls,
            [
                ("construction", "Analyze risk and strategy"),
                ("construction", "Analyze risk and strategy"),
                ("business", "Analyze risk and strategy"),
            ],
        )
        self.assertIn("construction output", result)
        self.assertIn("business output", result)
        self.assertEqual(memory.get(2)[0]["role"], "user")
        self.assertEqual(memory.get(2)[1]["role"], "assistant")

    def test_critic_marks_short_outputs(self):
        self.assertEqual(review_output("short"), "short\n\n[Critic]: Response may be too short.")


if __name__ == "__main__":
    unittest.main()
