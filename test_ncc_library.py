import pytest

from core import ncc_library as library
from core import retriever
from core.reasoning import chunks_to_clauses


@pytest.fixture
def references(tmp_path, monkeypatch):
    root = tmp_path / "ncc"
    root.mkdir()
    monkeypatch.setenv("NCC_DOCUMENT_ROOT", str(root))
    monkeypatch.setattr(library, "DB_PATH", tmp_path / "references.db")
    (root / "fire.txt").write_text("C1.1 Fire resistance\nFire walls must maintain structural stability during a fire.")
    return root


def test_saved_paths_survive_reload_and_are_isolated_by_user(references):
    assert library.save_reference("alice", "fire.txt", "NCC test edition") == 1
    assert library.load_reference("alice")["path"] == "fire.txt"
    assert library.load_reference("bob") is None
    assert library.search_local_references("bob", "NCC fire") == []
    library.clear_reference("alice")
    assert library.load_reference("alice") is None


def test_blocks_path_traversal_and_symlink_escape(references, tmp_path):
    outside = tmp_path / "private.txt"
    outside.write_text("private data")
    (references / "escape.txt").symlink_to(outside)
    for value in ("../private.txt", str(outside), "escape.txt", "."):
        with pytest.raises(library.NCCReferenceError, match="inside"):
            library.save_reference("alice", value, "NCC")


def test_reads_changed_files_and_drops_old_passages(references):
    library.save_reference("alice", "fire.txt", "NCC test")
    hits = library.search_local_references("alice", "NCC fire walls")
    assert hits[0]["metadata"]["source"] == "fire.txt, p. 1"
    assert hits[0]["metadata"]["clause"] == "C1.1"
    (references / "fire.txt").write_text("A1.1 Ventilation\nMechanical ventilation requirements.")
    assert library.search_local_references("alice", "fire walls") == []
    assert library.search_local_references("alice", "ventilation")


def test_regulatory_analysis_reads_saved_path_without_vector_embeddings(references, monkeypatch):
    library.save_reference("alice", ".", "NCC test edition")
    monkeypatch.setattr(retriever, "search_ncc_chunks", lambda *a, **kw: [])
    monkeypatch.setattr(retriever, "retrieve", lambda *a, **kw: [])
    hits = retriever.retrieve_multi("alice", "NCC fire walls")
    context = retriever.retrieve_ncc_context("NCC fire walls", user_id="alice")
    assert hits and context["legal_mode"]
    clauses = chunks_to_clauses(hits)
    assert "NCC test edition; fire.txt, p. 1" in clauses[0]["content"]


def test_pdf_page_citations(references):
    from reportlab.pdfgen.canvas import Canvas
    file = references / "ncc.pdf"
    canvas = Canvas(str(file))
    canvas.drawString(40, 750, "C1.1 Fire wall resistance requirements")
    canvas.showPage()
    canvas.drawString(40, 750, "D1.1 Egress exit travel distance")
    canvas.save()
    library.save_reference("alice", "ncc.pdf", "NCC test")
    hits = library.search_local_references("alice", "NCC egress exit")
    assert hits[0]["metadata"]["page"] == 2
    assert hits[0]["metadata"]["source"] == "ncc.pdf, p. 2"


def test_invalid_or_removed_references_are_explicit(references):
    with pytest.raises(library.NCCReferenceError):
        library.save_reference("alice", "missing.pdf", "NCC")
    with pytest.raises(library.NCCReferenceError, match="edition"):
        library.save_reference("alice", "fire.txt", "")
    library.save_reference("alice", "fire.txt", "NCC")
    (references / "fire.txt").unlink()
    with pytest.raises(library.NCCReferenceError, match="does not exist"):
        library.search_local_references("alice", "NCC fire")


def test_sources_include_edition_file_page_and_clause(references):
    from core.vector_store import format_sources
    library.save_reference("alice", "fire.txt", "NCC test")
    sources = format_sources(library.search_local_references("alice", "NCC fire"))
    assert "NCC test" in sources and "fire.txt, p. 1" in sources and "C1.1" in sources


def test_reference_settings_form_saves_a_path(references):
    import ast
    from pathlib import Path
    from streamlit.testing.v1 import AppTest

    tree = ast.parse(Path("streamlit_app.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "render_ncc_reference_settings")
    source = "import streamlit as st\nfrom core import ncc_library\ndef is_guest_user(): return False\ndef get_current_user_id(): return 'alice'\ndef get_active_project(): return None\n"
    source += ast.unparse(function) + "\nrender_ncc_reference_settings()\n"
    app = AppTest.from_string(source).run()
    assert not app.exception
    app.text_input[0].set_value("fire.txt")
    app.text_input[1].set_value("NCC test edition")
    app.button[0].click().run()
    assert not app.exception
    assert app.success
    assert library.load_reference("alice") == {"path": "fire.txt", "edition": "NCC test edition"}
