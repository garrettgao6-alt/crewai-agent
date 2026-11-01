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
    monkeypatch.setattr(subscription_store, "DB_PATH", user_store.DB_PATH)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    source = Path(__file__).with_name("streamlit_app.py").read_text()
    # The cookie component needs a real browser handshake; guest UI does not.
    import sys
    import types
    class CookieJar(dict):
        def save(self):
            pass
    module = types.ModuleType("ui_test_cookies")
    module.cookies = CookieJar()
    monkeypatch.setitem(sys.modules, module.__name__, module)
    source = source.replace("auth_cookies = initialize_cookie_manager()", "from ui_test_cookies import cookies as auth_cookies")
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
    click_label(app, "Gao Intelligence")
    assert app.session_state["active_section"] == "Dashboard"
    assert app.selectbox(key="nav_selected").value == "Dashboard"
    click_label(app, "Open Copilot")
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


def test_login_form_submission_survives_full_script_rerun(app):
    import user_store
    user_store.create_user("ui_login_check", "ui-login@example.test", "UiLoginTest-12345")
    click_label(app, "Login / Sign Up")
    app.text_input(key="auth_sign_in_identifier").set_value("ui_login_check")
    app.text_input(key="auth_sign_in_password").set_value("UiLoginTest-12345")
    click_label(app, "Sign In")
    assert app.session_state["is_logged_in"]
    token = app.session_state["auth_session_token"]
    assert user_store.resolve_session(token)["username"] == "ui_login_check"
    click_label(app, "Sign Out")
    assert not app.session_state["is_logged_in"]
    assert user_store.resolve_session(token) is None


def test_close_protected_page_sign_in_returns_to_dashboard(app):
    app.selectbox(key="nav_selected").select("Reports").run()
    click_label(app, "Close sign-in")
    assert app.session_state["active_section"] == "Dashboard"
    assert not any(field.key == "auth_sign_in_identifier" for field in app.text_input)
