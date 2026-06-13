import unittest
from unittest.mock import patch
from types import SimpleNamespace

import copilot_core
from core.critic import review_output
from core.engine import build_task_prompt, memory, run_engine
from core.planner import plan_tasks
import core.planner as planner
import core.router as embedding_router
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
                    "--- Analysis ---\n"
                    "[Task: analysis]\n"
                    "construction response with enough detail for critic validation\n\n"
                    "--- Risk ---\n"
                    "[Task: risk]\n"
                    "construction response with enough detail for critic validation"
                ),
            )
            self.assertEqual(
                copilot_core.run_copilot("Improve strategy"),
                (
                    "--- Strategy ---\n"
                    "[Task: strategy]\n"
                    "business response with enough detail for critic validation"
                ),
            )
            self.assertEqual(
                copilot_core.run_copilot("Hello there"),
                (
                    "--- General ---\n"
                    "[Task: general]\n"
                    "general response with enough detail for critic validation"
                ),
            )


class CoreEngineTests(unittest.TestCase):
    def setUp(self):
        memory.clear()

    def test_planner_breaks_prompt_into_tasks(self):
        with patch.object(planner, "_get_client", side_effect=RuntimeError("offline")):
            self.assertEqual(plan_tasks("Analyze risk and strategy"), ["analysis", "risk", "strategy"])

    def test_gpt_planner_parses_multiple_tasks(self):
        fake_response = SimpleNamespace(output_text='{"tasks": ["analysis", "risk", "strategy"]}')
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **_kwargs: fake_response,
            ),
        )

        with patch.object(planner, "_get_client", return_value=fake_client):
            self.assertEqual(plan_tasks("Analyze contract risk and give strategy"), ["analysis", "risk", "strategy"])

    def test_revenue_prompt_falls_back_to_finance_task(self):
        with patch.object(planner, "_get_client", side_effect=RuntimeError("offline")):
            self.assertEqual(plan_tasks("How to increase revenue?"), ["finance"])

    def test_router_maps_tasks_to_domains(self):
        with patch.object(embedding_router, "init_vectors", return_value=False):
            self.assertEqual(route_task("analysis"), "construction")
            self.assertEqual(route_task("risk"), "construction")
            self.assertEqual(route_task("strategy"), "business")
            self.assertEqual(route_task("finance"), "business")
            self.assertEqual(route_task("unknown"), "general")

    def test_embedding_router_picks_best_domain(self):
        embedding_router.DOMAIN_VECTORS["construction"] = embedding_router.np.array([1.0, 0.0])
        embedding_router.DOMAIN_VECTORS["business"] = embedding_router.np.array([0.0, 1.0])
        embedding_router.DOMAIN_VECTORS["general"] = embedding_router.np.array([0.1, 0.1])

        fake_embedding = SimpleNamespace(data=[SimpleNamespace(embedding=[0.0, 0.9])])
        fake_client = SimpleNamespace(
            embeddings=SimpleNamespace(
                create=lambda **_kwargs: fake_embedding,
            ),
        )

        with (
            patch.object(embedding_router, "init_vectors", return_value=True),
            patch.object(embedding_router, "_get_client", return_value=fake_client),
        ):
            self.assertEqual(route_task("strategy"), "business")

    def test_engine_combines_multiple_task_outputs_and_stores_memory(self):
        calls = []

        def executor(domain, prompt):
            calls.append((domain, prompt))
            return f"{domain} output for {prompt.splitlines()[0]}"

        result = run_engine("Analyze risk and strategy", executor)

        self.assertEqual(
            calls,
            [
                (
                    "construction",
                    "Task: analysis\n"
                    "Instruction: Perform detailed analysis\n\n"
                    "User request:\n"
                    "Analyze risk and strategy\n\n"
                    "Conversation history:\n"
                    "[{'role': 'user', 'content': 'Analyze risk and strategy'}]\n",
                ),
                (
                    "construction",
                    "Task: risk\n"
                    "Instruction: Identify and assess risks\n\n"
                    "User request:\n"
                    "Analyze risk and strategy\n\n"
                    "Conversation history:\n"
                    "[{'role': 'user', 'content': 'Analyze risk and strategy'}]\n",
                ),
                (
                    "business",
                    "Task: strategy\n"
                    "Instruction: Provide strategic recommendations\n\n"
                    "User request:\n"
                    "Analyze risk and strategy\n\n"
                    "Conversation history:\n"
                    "[{'role': 'user', 'content': 'Analyze risk and strategy'}]\n",
                ),
            ],
        )
        self.assertIn("--- Analysis ---\n[Task: analysis]", result)
        self.assertIn("--- Risk ---\n[Task: risk]", result)
        self.assertIn("--- Strategy ---\n[Task: strategy]", result)
        self.assertIn("construction output for Task: analysis", result)
        self.assertIn("construction output for Task: risk", result)
        self.assertIn("business output for Task: strategy", result)
        self.assertNotIn("construction output for Task: strategy", result)
        self.assertIn("construction output", result)
        self.assertIn("business output", result)
        self.assertEqual(memory.get(2)[0]["role"], "user")
        self.assertEqual(memory.get(2)[1]["role"], "assistant")

    def test_build_task_prompt_uses_focused_task_context(self):
        self.assertEqual(
            build_task_prompt("risk", "Analyze risk and strategy"),
            "Task: risk\n"
            "Instruction: Identify and assess risks\n\n"
            "User request:\n"
            "Analyze risk and strategy\n\n"
            "Conversation history:\n"
            "[]\n",
        )

    def test_memory_persists_across_engine_runs(self):
        def executor(domain, prompt):
            return f"{domain} response with enough detail to avoid short critic warning"

        run_engine("Analyze contract risk and give strategy", executor)
        run_engine("How to increase revenue?", executor)

        history = memory.get(4)

        self.assertEqual(history[0]["role"], "user")
        self.assertIn("Analyze contract risk and give strategy", history[0]["content"])
        self.assertEqual(history[2]["role"], "user")
        self.assertIn("How to increase revenue?", history[2]["content"])

    def test_critic_marks_short_outputs(self):
        self.assertEqual(review_output("short"), "short\n\n[Critic]: Response may be too short.")


if __name__ == "__main__":
    unittest.main()
