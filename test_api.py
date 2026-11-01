from fastapi.testclient import TestClient
import pytest
import api
import project_store
import user_store
import subscription_store
import report_store
import core.engine as engine


@pytest.fixture
def secured(tmp_path, monkeypatch):
    monkeypatch.setattr(user_store, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(subscription_store, "DB_PATH", tmp_path / "users.db")
    monkeypatch.setattr(project_store, "DB_PATH", tmp_path / "projects.db")
    monkeypatch.setattr(report_store, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    user_store.initialize_user_store()
    project_store.initialize_project_store()
    a = user_store.create_user("alice", "alice@example.com", "test-password")
    b = user_store.create_user("bob", "bob@example.com", "test-password")
    project = project_store.create_project(a['id'], "Alice project")
    token = user_store.create_session(a['id'])
    other_token = user_store.create_session(b['id'])
    return TestClient(api.app), project, token, other_token


def test_health_returns_ok():
    assert api.health() == {"status": "ok"}


def test_api_requires_session_and_project_ownership(secured, monkeypatch):
    client, project, token, other_token = secured
    monkeypatch.setattr(engine, "run_engine", lambda *a, **kw: pytest.fail("Unauthorized model call"))
    data = {"query": "NCC check", "project_id": project['id']}
    assert client.post('/analyze', json=data).status_code == 401
    assert client.post('/analyze', json=data, headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.post('/analyze', json=data, headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.get(f"/projects/{project['id']}/reports", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    assert client.post('/analyze', json={"query":"x"}, headers={"Authorization": f"Bearer {token}"}).status_code == 422


def test_analyze_saves_and_reloads_only_authorized_report(secured, monkeypatch):
    client, project, token, other_token = secured
    def run(user, query, **kwargs):
        assert kwargs == {"project_id": project['id'], "return_details": True}
        return {"result": "Full verified test result", "sources": [{"text":"C2D2 test evidence", "metadata":{"source":"ncc.pdf"}, "sha256":"test"}], "status":"draft", "version":"2.0"}
    monkeypatch.setattr(engine, "run_engine", run)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post('/analyze', json={"query":"NCC fire", "project_id":project['id']}, headers=headers)
    assert response.status_code == 200, response.text
    saved = response.json()
    url = f"/projects/{project['id']}/reports/{saved['id']}"
    assert client.get(url, headers=headers).json()['sources'] == saved['sources']
    assert client.get(url, headers={"Authorization":f"Bearer {other_token}"}).status_code == 404
    assert len(client.get(f"/projects/{project['id']}/reports", headers=headers).json()) == 1


def test_session_expiry_revocation_and_user_id_forgery(secured):
    _, project, token, _ = secured
    assert user_store.resolve_session(str(project['user_id'])) is None
    expired = user_store.create_session(project['user_id'], lifetime_seconds=-1)
    assert user_store.resolve_session(expired) is None
    assert user_store.resolve_session(token)
    user_store.revoke_session(token)
    assert user_store.resolve_session(token) is None


def test_failed_analysis_does_not_create_a_report(secured, monkeypatch):
    client, project, token, _ = secured
    def failure(*args, **kwargs):
        raise RuntimeError('provider unavailable')
    monkeypatch.setattr(engine,'run_engine',failure)
    response = client.post('/analyze',json={'query':'NCC fire','project_id':project['id']},headers={'Authorization':f'Bearer {token}'})
    assert response.status_code == 502
    assert report_store.list_reports(project['user_id'],project['id']) == []


def test_revoked_and_expired_api_sessions_are_rejected(secured):
    client, project, token, _ = secured
    expired = user_store.create_session(project['user_id'],lifetime_seconds=-1)
    user_store.revoke_session(token)
    for value in (expired,token,str(project['user_id'])):
        response = client.get(f"/projects/{project['id']}/reports",headers={'Authorization':f'Bearer {value}'})
        assert response.status_code == 401
