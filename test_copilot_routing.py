import unittest
from unittest.mock import patch
from types import SimpleNamespace

import copilot_core
from core.document_pipeline import chunk_text, process_document, semantic_chunk, split_by_sections
from core.critic import review_output
import core.engine as engine
from core.engine import memory, run_engine
from core.ncc_parser import clauses_to_documents, parse_ncc_clauses
from core.planner import plan_tasks
import core.reasoning as reasoning
import core.planner as planner
from core.report_generator import generate_report
import core.retriever as retriever
import core.router as embedding_router
import core.vector_store as vector_store
from core.router import route_skill, route_skill_chain, route_task
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
                engine,
                "run_construction_agent",
                return_value="construction response with enough detail for critic validation",
            ),
            patch.object(
                engine,
                "run_business_agent",
                return_value="business response with enough detail for critic validation",
            ),
            patch.object(
                engine,
                "run_general_agent",
                return_value="general response with enough detail for critic validation",
            ),
        ):
            self.assertIn("construction response", copilot_core.run_copilot("Analyze this risk"))
            self.assertIn("business response", copilot_core.run_copilot("Improve strategy"))
            self.assertIn("general response", copilot_core.run_copilot("Hello there"))


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

    def test_enterprise_skill_routing_rules(self):
        self.assertEqual(route_skill("Is this NCC compliant?"), "ncc-compliance")
        self.assertEqual(route_skill("Review this contract clause"), "contract-review")
        self.assertEqual(route_skill("Analyze this tender response"), "tender-analysis")
        self.assertEqual(route_skill("Build a business growth plan"), "business-strategy")

    def test_enterprise_skill_chain_adds_quality_and_delivery_skills(self):
        self.assertEqual(
            route_skill_chain("NCC fire compliance", is_rag_response=True),
            ["ncc-compliance", "rag-quality", "critic-review", "report-generator"],
        )

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

        def fake_agent(domain_name):
            def _run(prompt):
                calls.append((domain_name, prompt))
                return f"{domain_name} output with enough detail for critic validation"
            return _run

        with (
            patch.object(engine, "run_construction_agent", fake_agent("construction")),
            patch.object(engine, "run_business_agent", fake_agent("business")),
            patch.object(engine, "run_general_agent", fake_agent("general")),
            patch.object(engine, "retrieve_multi", return_value=[]),
        ):
            result = run_engine("user_engine", "Analyze risk and strategy")

        self.assertEqual([domain for domain, _prompt in calls], ["construction", "construction", "business"])
        for _domain, reasoning_prompt in calls:
            self.assertIn("You are a construction compliance expert.", reasoning_prompt)
            self.assertIn("Analyze risk and strategy", reasoning_prompt)
            self.assertIn("combine multiple clauses", reasoning_prompt)
        self.assertIn("Compliance Summary", result)
        self.assertIn("Assessment", result)
        self.assertIn("construction output", result)
        self.assertIn("business output", result)
        self.assertEqual(memory.get("user_engine", 2)[0]["role"], "user")
        self.assertEqual(memory.get("user_engine", 2)[1]["role"], "assistant")

    def test_memory_persists_across_engine_runs(self):
        def executor(domain, prompt):
            return f"{domain} response with enough detail to avoid short critic warning"

        with (
            patch.object(engine, "agent_executor", lambda _domain, _prompt: "agent response with enough detail"),
            patch.object(engine, "retrieve_multi", return_value=[]),
        ):
            run_engine("memory_user", "Analyze contract risk and give strategy")
            run_engine("memory_user", "How to increase revenue?")

        history = memory.get("memory_user", 4)

        self.assertEqual(history[0]["role"], "user")
        self.assertIn("Analyze contract risk and give strategy", history[0]["content"])
        self.assertEqual(history[2]["role"], "user")
        self.assertIn("How to increase revenue?", history[2]["content"])

    def test_critic_marks_short_outputs(self):
        self.assertEqual(review_output("short"), "short\n\n[Critic]: Response may be too short.")

    def test_report_generator_outputs_required_sections(self):
        report = generate_report(
            {
                "summary": "Summary text",
                "clauses": ["C3.2"],
                "analysis": "Analysis text",
                "risk": "AUTO",
                "recommendations": "AUTO",
            }
        )

        self.assertIn("Compliance Summary", report)
        self.assertIn("* C3.2", report)
        self.assertIn("Assessment", report)
        self.assertIn("Risk Level", report)


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
            results = retriever.retrieve_multi("building exits")

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

        def fake_construction_agent(prompt):
            calls.append(prompt)
            return "Answer\nNCC egress provisions apply.\nSources:\n[1] ncc.txt"

        with (
            patch.object(vector_store, "embed_text", return_value=vector_store.np.array([1.0, 0.0])),
            patch.object(engine, "run_construction_agent", fake_construction_agent),
        ):
            vector_store.add_documents(
                "rag_user",
                ["NCC fire exits must satisfy compliant egress provisions."],
                [{"source": "ncc.txt", "type": "ncc"}],
            )
            result = run_engine("rag_user", "Analyze fire exits")

        self.assertIn("ncc.txt - NCC fire exits must satisfy compliant egress provisions.", calls[0])
        self.assertIn("combine multiple clauses", calls[0])
        self.assertIn("Answer", result)
        self.assertIn("Assessment", result)

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

    def test_ncc_parser_extracts_section_clause_title_and_text(self):
        text = (
            "Section C Fire resistance. "
            "C3.2 Protection of openings Fire doors must protect openings. "
            "C3.3 Fire separation Walls must resist fire spread."
        )

        clauses = parse_ncc_clauses(text)

        self.assertEqual(len(clauses), 2)
        self.assertEqual(clauses[0]["section"], "Section C")
        self.assertEqual(clauses[0]["clause"], "C3.2")
        self.assertIn("Protection of openings", clauses[0]["title"])
        self.assertIn("C3.2", clauses[0]["text"])

    def test_ncc_clauses_store_with_metadata_and_fire_filter(self):
        text = (
            "Section C Fire resistance. "
            "C3.2 Protection of openings Fire doors must protect openings. "
            "C3.3 Fire separation Fire walls must resist fire spread."
        )
        clauses = parse_ncc_clauses(text)
        documents, metadatas = clauses_to_documents(clauses, "ncc-2025.txt")

        with patch.object(vector_store, "embed_text", return_value=vector_store.np.array([1.0, 0.0])):
            vector_store.add_ncc_documents("ncc_user", documents, metadatas)
            results = vector_store.search_ncc_chunks(
                "ncc_user",
                "Is this compliant with NCC fire safety?",
                filter_type="fire",
            )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["metadata"]["code"], "NCC2025")
        self.assertIn(results[0]["metadata"]["clause"], {"C3.2", "C3.3"})
        self.assertEqual(results[0]["metadata"]["type"], "fire")

    def test_ncc_retrieval_uses_housing_collection_separately(self):
        with patch.object(vector_store, "embed_text", return_value=vector_store.np.array([1.0, 0.0])):
            vector_store.add_ncc_documents(
                "housing_user",
                ["C3.2 Fire safety for general NCC buildings."],
                [{"code": "NCC2025", "section": "Section C", "clause": "C3.2", "source": "ncc.txt", "type": "fire"}],
            )
            vector_store.add_ncc_documents(
                "housing_user",
                ["C3.2 Housing fire safety provision."],
                [{"code": "NCC2025", "section": "Section C", "clause": "C3.2", "source": "housing.txt", "type": "fire"}],
                housing=True,
            )

            ncc_results = vector_store.search_ncc_chunks("housing_user", "fire safety", filter_type="fire")
            housing_results = vector_store.search_ncc_chunks(
                "housing_user",
                "housing fire safety",
                filter_type="fire",
                housing=True,
            )

        self.assertEqual(ncc_results[0]["metadata"]["source"], "ncc.txt")
        self.assertEqual(housing_results[0]["metadata"]["source"], "housing.txt")

    def test_engine_uses_ncc_legal_mode_for_compliance_query(self):
        clauses = parse_ncc_clauses(
            "Section C Fire resistance. "
            "C3.2 Protection of openings Fire doors must protect openings."
        )
        documents, metadatas = clauses_to_documents(clauses, "ncc-2025.txt")

        calls = []
        agent_output = (
            "Compliance Summary\nGrounded in C3.2.\n"
            "Relevant Clauses\n* C3.2\n"
            "Assessment\nCompliant if openings are protected.\n"
            "Risk Level\nMedium"
        )

        def fake_agent(domain, prompt):
            calls.append((domain, prompt))
            return agent_output

        with (
            patch.object(vector_store, "embed_text", return_value=vector_store.np.array([1.0, 0.0])),
            patch.object(engine, "agent_executor", fake_agent),
        ):
            vector_store.add_ncc_documents("legal_user", documents, metadatas)
            result = run_engine("legal_user", "Is this compliant with NCC fire safety?")

        self.assertIn("C3.2 - C3.2 Protection of openings", calls[0][1])
        self.assertIn("combine multiple clauses", calls[0][1])
        self.assertIn("Compliance Summary", result)
        self.assertIn("C3.2", result)
        self.assertIn("Assessment", result)

    def test_reasoning_prompt_combines_multiple_clauses(self):
        prompt = reasoning.build_reasoning_prompt(
            "Is this compliant with NCC fire safety?",
            [
                {"clause": "C3.2", "content": "Openings must be protected."},
                {"clause": "C3.3", "content": "Fire separation must resist spread."},
            ],
        )

        self.assertIn("C3.2 - Openings must be protected.", prompt)
        self.assertIn("C3.3 - Fire separation must resist spread.", prompt)
        self.assertIn("combine multiple clauses", prompt)
        self.assertIn("identify conflicts", prompt)


if __name__ == "__main__":
    unittest.main()
