import unittest
from unittest.mock import patch
from types import SimpleNamespace

import copilot_core
from core.document_pipeline import chunk_text, process_document, semantic_chunk, split_by_sections
from core.critic import review_output
from core.engine import build_task_prompt, ensure_citations, memory, run_engine
from core.planner import plan_tasks
import core.planner as planner
import core.retriever as retriever
import core.router as embedding_router
import core.vector_store as vector_store
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
        vector_store.clear_store()

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

        self.assertEqual([domain for domain, _prompt in calls], ["construction", "construction", "business"])
        self.assertIn("Task: analysis", calls[0][1])
        self.assertIn("Instruction: Perform detailed analysis", calls[0][1])
        self.assertIn("Task: risk", calls[1][1])
        self.assertIn("Instruction: Identify and assess risks", calls[1][1])
        self.assertIn("Task: strategy", calls[2][1])
        self.assertIn("Instruction: Provide strategic recommendations", calls[2][1])
        for _domain, task_prompt in calls:
            self.assertIn("Context:\nInsufficient data", task_prompt)
            self.assertIn("You must ONLY use the provided context.", task_prompt)
            self.assertIn("If not enough information, say 'Insufficient data'.", task_prompt)
            self.assertIn("Sources:\nNo retrieved sources", task_prompt)
            self.assertIn("Analyze risk and strategy", task_prompt)
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
        task_prompt = build_task_prompt("risk", "Analyze risk and strategy")

        self.assertIn("Task: risk", task_prompt)
        self.assertIn("Instruction: Identify and assess risks", task_prompt)
        self.assertIn("Context:\nInsufficient data", task_prompt)
        self.assertIn("User request:\nAnalyze risk and strategy", task_prompt)
        self.assertIn("Conversation history:\n[]", task_prompt)
        self.assertIn("You must ONLY use the provided context.", task_prompt)
        self.assertIn("Sources:\nNo retrieved sources", task_prompt)

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

    def test_engine_enforces_citations_when_sources_exist(self):
        self.assertEqual(
            ensure_citations("Answer\nUse the NCC clause.", "[1] ncc.txt"),
            "Answer\nUse the NCC clause.\n\nSources:\n[1] ncc.txt",
        )


class RagSystemTests(unittest.TestCase):
    def setUp(self):
        memory.clear()
        vector_store.clear_store()

    def test_split_by_sections_detects_clause_and_section_titles(self):
        text = (
            "Intro text. Section 1 Fire safety requirements. "
            "Clause 2.1 Egress paths must be maintained. "
            "Section 3 Energy efficiency requirements."
        )

        chunks = split_by_sections(text)

        self.assertEqual(len(chunks), 3)
        self.assertTrue(chunks[0].startswith("Section 1"))
        self.assertTrue(chunks[1].startswith("Clause 2.1"))

    def test_semantic_chunk_uses_sentence_boundaries(self):
        text = ". ".join(
            " ".join(f"word{sentence}_{index}" for index in range(20))
            for sentence in range(40)
        )

        chunks = semantic_chunk(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 850 for chunk in chunks))

    def test_chunk_text_prefers_structured_sections(self):
        text = "\n".join(
            [
                "Section 1 Fire safety requirements.",
                "Clause 1.1 Exits must remain clear.",
                "Section 2 Waterproofing requirements.",
                "Clause 2.1 Membranes must be compliant.",
            ]
        )

        chunks = chunk_text(text)

        self.assertEqual(len(chunks), 4)
        self.assertTrue(chunks[0].startswith("Section 1"))

    def test_process_txt_document_preserves_metadata(self):
        text = ("National Construction Code fire safety compliance " * 30).encode("utf-8")

        chunks = process_document("ncc-guide.txt", text)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["source"], "ncc-guide.txt")
        self.assertEqual(chunks[0]["metadata"]["type"], "ncc")

    def test_retrieve_filters_by_metadata_and_formats_sources(self):
        chunks = [
            {
                "text": "NCC compliance requires fire safety provisions for exits.",
                "metadata": {"source": "ncc.txt", "type": "ncc"},
            },
            {
                "text": "Revenue growth strategy includes pricing and retention.",
                "metadata": {"source": "business.txt", "type": "business"},
            },
        ]

        with patch.object(
            vector_store,
            "embed_text",
            side_effect=[
                vector_store.np.array([1.0, 0.0]),
                vector_store.np.array([0.0, 1.0]),
                vector_store.np.array([1.0, 0.0]),
            ],
        ):
            vector_store.add_chunks(chunks)
            retrieved = vector_store.retrieve("NCC fire exits", filter_type="ncc")

        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["metadata"]["source"], "ncc.txt")
        self.assertIn("NCC compliance", vector_store.build_context(retrieved))
        self.assertEqual(vector_store.format_sources(retrieved), "[1] ncc.txt")

    def test_rerank_can_use_gpt_ranked_indexes(self):
        chunks = [
            {"text": "Less relevant", "metadata": {"source": "a.txt", "type": "business"}},
            {"text": "Most relevant revenue strategy", "metadata": {"source": "b.txt", "type": "business"}},
        ]
        fake_response = SimpleNamespace(output_text='{"ranked_indexes": [1, 0]}')
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **_kwargs: fake_response,
            ),
        )

        with patch.object(retriever, "_get_client", return_value=fake_client):
            ranked = retriever.rerank("revenue strategy", chunks)

        self.assertEqual(ranked[0]["metadata"]["source"], "b.txt")

    def test_generate_queries_uses_gpt_list_output(self):
        fake_response = SimpleNamespace(output_text="['egress compliance', 'fire exits NCC', 'building exits']")
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **_kwargs: fake_response,
            ),
        )

        with patch.object(retriever, "_get_client", return_value=fake_client):
            self.assertEqual(
                retriever.generate_queries("NCC exits"),
                ["egress compliance", "fire exits NCC", "building exits"],
            )

    def test_retrieve_multi_dedupes_expanded_query_results(self):
        chunk = {
            "text": "NCC egress provisions for fire exits.",
            "metadata": {"source": "ncc.txt", "type": "ncc"},
            "score": 0.9,
        }

        with (
            patch.object(retriever, "generate_queries", return_value=["egress", "fire exits"]),
            patch.object(retriever, "retrieve", side_effect=[[chunk], [chunk], [chunk]]),
        ):
            results = retriever.retrieve_multi("NCC exits")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["source"], "ncc.txt")

    def test_advanced_rerank_uses_sorted_indices(self):
        chunks = [
            {"text": "General growth", "metadata": {"source": "a.txt", "type": "business"}},
            {"text": "Precise pricing retention strategy", "metadata": {"source": "b.txt", "type": "business"}},
        ]
        fake_response = SimpleNamespace(output_text="[1, 0]")
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=lambda **_kwargs: fake_response,
            ),
        )

        with patch.object(retriever, "_get_client", return_value=fake_client):
            ranked = retriever.rerank("pricing retention", chunks)

        self.assertEqual(ranked[0]["metadata"]["source"], "b.txt")

    def test_engine_includes_retrieved_context_and_sources(self):
        calls = []

        def executor(domain, prompt):
            calls.append((domain, prompt))
            return "Answer\nNCC egress provisions apply.\nSources:\n[1] ncc.txt"

        with patch.object(vector_store, "embed_text", return_value=vector_store.np.array([1.0, 0.0])):
            vector_store.add_documents(
                "default",
                ["NCC fire exits must satisfy compliant egress provisions."],
                [{"source": "ncc.txt", "type": "ncc"}],
            )
            result = run_engine("Analyze NCC fire exits", executor)

        self.assertIn("Context:\nNCC fire exits must satisfy compliant egress provisions.", calls[0][1])
        self.assertIn("Sources:\n[1] ncc.txt", calls[0][1])
        self.assertIn("Answer", result)
        self.assertIn("[1] ncc.txt", result)

    def test_chroma_collections_isolate_users(self):
        with patch.object(
            vector_store,
            "embed_text",
            side_effect=[
                vector_store.np.array([1.0, 0.0]),
                vector_store.np.array([0.0, 1.0]),
                vector_store.np.array([1.0, 0.0]),
                vector_store.np.array([1.0, 0.0]),
            ],
        ):
            vector_store.add_documents(
                "user_a",
                ["NCC user A fire exit compliance content."],
                [{"source": "a-ncc.txt", "type": "ncc"}],
            )
            vector_store.add_documents(
                "user_b",
                ["Business user B revenue strategy content."],
                [{"source": "b-business.txt", "type": "business"}],
            )

            user_a_results = vector_store.search("user_a", "fire exit compliance")
            user_b_results = vector_store.search("user_b", "fire exit compliance")

        self.assertEqual(user_a_results, ["NCC user A fire exit compliance content."])
        self.assertEqual(user_b_results, ["Business user B revenue strategy content."])


if __name__ == "__main__":
    unittest.main()
