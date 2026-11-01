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
    from core import guest_ai
    monkeypatch.setattr(guest_ai, "DB_PATH", tmp_path / "guest_ai.db")

    for store in (project_store, prompt_store, template_store, user_store, subscription_store):
        monkeypatch.setattr(store, "DB_PATH", tmp_path / f"{store.__name__}.db")
    monkeypatch.setattr(subscription_store, "DB_PATH", user_store.DB_PATH)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import core.router
    provider_attempts = []
    def forbid_guest_provider(*args, **kwargs):
        provider_attempts.append(True)
        raise AssertionError("Guest startup attempted an AI request")
    monkeypatch.setattr(core.router, "_get_client", forbid_guest_provider)
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
    yield AppTest.from_string(source, default_timeout=30).run()
    assert not provider_attempts, "Guest page attempted an AI provider call"


def click_label(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def test_navigation_supports_manual_selection_and_dashboard_shortcuts(app):
    assert not app.exception
    app.selectbox(key="nav_selected").select("Copilot").run()
    assert app.session_state["active_section"] == "Copilot"
    assert app.selectbox(key="public_demo_workflow").value == "NCC Compliance"
    app.selectbox(key="nav_selected").select("Dashboard").run()
    click_label(app, "Open Copilot")
    assert app.selectbox(key="nav_selected").value == "Copilot"
    click_label(app, "Gao Intelligence")
    assert app.session_state["active_section"] == "Dashboard"
    assert app.selectbox(key="nav_selected").value == "Dashboard"
    click_label(app, "Open Copilot")
    app.selectbox(key="nav_selected").select("Dashboard").run()
    assert app.session_state["active_section"] == "Dashboard"


def test_guest_review_save_and_project_isolation(app, monkeypatch):
    import core.engine
    def forbid(*args, **kwargs):
        raise AssertionError("Guest demo called private AI engine")
    monkeypatch.setattr(core.engine, "run_engine", forbid)
    click_label(app, "Open Copilot")
    click_label(app, "Run sample review")
    assert app.session_state["public_demo_result"]["ai_tokens"] == 0
    assert "NOT DETERMINED" in app.session_state["public_demo_result"]["result"]
    click_label(app, "Save sample report to this session")
    app.selectbox(key="nav_selected").select("Reports").run()
    assert any("SYNTHETIC DEMO" in item.value for item in app.text)
    assert any(button.label == "Download Report PDF" for button in app.get("download_button"))
    app.selectbox(key="public_demo_case").select("Hillview sample").run()
    assert not app.exception
    assert any("No sample reports" in item.value for item in app.info)
    app.selectbox(key="public_demo_case").select("Riverside sample").run()
    assert any("SYNTHETIC DEMO" in item.value for item in app.text)


def test_guest_document_search_and_login(app):
    app.selectbox(key="nav_selected").select("Documents").run()
    assert not app.exception
    app.text_input[0].set_value("no-such-evidence").run()
    assert any("0 sample documents" in item.value for item in app.caption)
    app.text_input[0].set_value("payment").run()
    assert any("Payment due" in item.value for item in app.text)
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
    click_label(app, "Login / Sign Up")
    click_label(app, "Close sign-in")
    assert app.session_state["active_section"] == "Dashboard"
    assert not any(field.key == "auth_sign_in_identifier" for field in app.text_input)


def test_unavailable_cookie_component_does_not_block_public_demo(app, monkeypatch):
    import sys
    cookies = sys.modules["ui_test_cookies"].cookies
    monkeypatch.setattr(cookies, "ready", lambda: False, raising=False)
    def unreadable(*args, **kwargs):
        raise AssertionError("Unready browser cookie storage accessed")
    monkeypatch.setattr(cookies, "get", unreadable)
    app.run()
    assert not app.exception
    click_label(app, "Open Copilot")
    click_label(app, "Run sample review")
    assert app.session_state["public_demo_result"]["ai_tokens"] == 0
    click_label(app, "Login / Sign Up")
    assert any("Secure sign-in is waiting" in item.value for item in app.warning)
    assert not any(field.label == "Password" for field in app.text_input)
    click_label(app, "Close sign-in")
    assert app.session_state["active_section"] == "Dashboard"


def test_guest_real_ai_uses_isolated_path_and_saves_actual_output(app, monkeypatch):
    from core import guest_ai, public_demo
    def isolated(session, case, workflow, question, delay_days):
        report = public_demo.analyze(case, workflow, delay_days)
        report.update(method="public-ai-v1", result="Real isolated AI test output [contract]", ai_tokens=100)
        return report
    monkeypatch.setattr(guest_ai, "analyze", isolated)
    click_label(app, "Open Copilot")
    click_label(app, "Run real AI analysis")
    assert app.session_state["public_demo_result"]["method"] == "public-ai-v1"
    click_label(app, "Save sample report to this session")
    app.selectbox(key="nav_selected").select("Reports").run()
    assert any("Real isolated AI test output" in item.value for item in app.text)


def test_public_registration_requires_email_activation_before_login(app,monkeypatch):
    import account_recovery,user_store
    sent=[]
    monkeypatch.setattr(account_recovery,'delivery_ready',lambda:True)
    monkeypatch.setattr(account_recovery,'_send',lambda email,code,**kwargs:sent.append(code))
    click_label(app,'Login / Sign Up')
    app.text_input(key='auth_create_username').set_value('verified_signup')
    app.text_input(key='auth_create_email').set_value('signup@example.test')
    app.text_input(key='auth_create_password').set_value('Signup-test-password')
    app.text_input(key='auth_create_confirm_password').set_value('Signup-test-password')
    click_label(app,'Register')
    assert not app.session_state['is_logged_in'] and len(sent)==1
    assert user_store.authenticate_user('verified_signup','Signup-test-password') is None
    next(field for field in app.text_input if field.label=='Registration email').set_value('signup@example.test')
    next(field for field in app.text_input if field.label=='Account activation code').set_value(sent[0])
    click_label(app,'Verify account email')
    app.text_input(key='auth_sign_in_identifier').set_value('verified_signup')
    app.text_input(key='auth_sign_in_password').set_value('Signup-test-password')
    click_label(app,'Sign In')
    assert app.session_state['is_logged_in']
