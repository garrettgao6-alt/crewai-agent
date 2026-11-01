"""Guest UI regression checks without browser cookies or external AI calls."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(tmp_path, monkeypatch):
    import project_store
    import prompt_store
    import template_store
    import user_store
    import subscription_store

    for store in (project_store, prompt_store, template_store, user_store, subscription_store):
        monkeypatch.setattr(store, "DB_PATH", tmp_path / f"{store.__name__}.db")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = Path(__file__).with_name("streamlit_app.py").read_text()
    # The cookie component needs a real browser handshake; guest UI does not.
    source = source.replace("auth_cookies = initialize_cookie_manager()", "auth_cookies = {}")
    return AppTest.from_string(source, default_timeout=30).run()


def click_label(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def test_navigation_supports_manual_selection_and_dashboard_shortcuts(app):
    assert not app.exception
    app.selectbox(key="nav_selected").select("Copilot").run()
    assert app.session_state["active_section"] == "Copilot"
    assert app.chat_input[0].placeholder == "Ask Gao Intelligence Hub"
    app.selectbox(key="nav_selected").select("Dashboard").run()
    click_label(app, "Open Copilot")
    assert app.selectbox(key="nav_selected").value == "Copilot"
    app.selectbox(key="nav_selected").select("Dashboard").run()
    assert app.session_state["active_section"] == "Dashboard"


def test_guest_reply_renders_as_html_without_markdown_code_blocks(app):
    from markdown_it import MarkdownIt

    click_label(app, "Open Copilot")
    click_label(app, "NCC check")
    history = next(item.value for item in app.markdown if 'class="chat-container"' in item.value)
    tokens = MarkdownIt("commonmark", {"html": True}).parse(history)
    assert not any(token.type in {"code_block", "fence"} for token in tokens)
    assert "Guest preview response:" in history
    assert 'class="chat-bubble ai-msg"' in history
    assert len(app.session_state["copilot_history"]) == 1


def test_guest_prompt_is_escaped_and_login_form_is_available(app):
    click_label(app, "Open Copilot")
    app.chat_input[0].set_value('<script>alert("x")</script>').run()
    assert not app.exception
    history = next(item.value for item in app.markdown if 'class="chat-container"' in item.value)
    assert "<script>" not in history
    assert "&lt;script&gt;" in history
    click_label(app, "Login / Sign Up")
    assert any(field.label == "Username or Email" for field in app.text_input)
    assert any(field.label == "Password" for field in app.text_input)
