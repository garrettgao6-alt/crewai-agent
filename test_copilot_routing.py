import unittest
from unittest.mock import patch

import copilot_core
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
            patch.object(copilot_core, "run_construction_agent", return_value="construction response"),
            patch.object(copilot_core, "run_business_agent", return_value="business response"),
            patch.object(copilot_core, "run_general_agent", return_value="general response"),
        ):
            self.assertEqual(copilot_core.run_copilot("Review this contract"), "construction response")
            self.assertEqual(copilot_core.run_copilot("Improve revenue growth"), "business response")
            self.assertEqual(copilot_core.run_copilot("Hello there"), "general response")


if __name__ == "__main__":
    unittest.main()
