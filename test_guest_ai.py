from concurrent.futures import ThreadPoolExecutor
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from core import guest_ai, public_demo


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(guest_ai, 'DB_PATH', tmp_path / 'guest.db')
    for name in guest_ai.LIMITS:
        monkeypatch.delenv('GUEST_AI_' + name.upper(), raising=False)
    monkeypatch.delenv('GUEST_AI_ENABLED', raising=False)


def test_concurrent_requests_cannot_exceed_shared_daily_budget(monkeypatch):
    monkeypatch.setenv('GUEST_AI_GLOBAL_REQUESTS', '4')
    def attempt(_):
        try:
            return guest_ai.reserve(uuid4().hex, 1000)
        except guest_ai.GuestAIError:
            return None
    with ThreadPoolExecutor(max_workers=12) as executor:
        results = list(executor.map(attempt, range(30)))
    assert sum(result is not None for result in results) == 4
    assert guest_ai.usage(uuid4().hex)['global'][:2] == (4, 4000)


def test_atomic_session_and_token_rejection_survives_reconnect(monkeypatch):
    session = uuid4().hex
    monkeypatch.setenv('GUEST_AI_GLOBAL_TOKENS', '2500')
    guest_ai.reserve(session, 2000)
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.reserve(uuid4().hex, 1000)
    assert guest_ai.usage(session)['global'][:2] == (1, 2000)
    monkeypatch.setenv('GUEST_AI_SESSION_REQUESTS', '1')
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.reserve(session, 1)
    assert guest_ai.usage(session)['global'][:2] == (1, 2000)
    monkeypatch.setattr(guest_ai, 'budget_day', lambda: '2100-01-01')
    assert guest_ai.usage(session)['global'][:2] == (0, 0)


def test_live_request_has_only_public_evidence_and_bounded_provider_options():
    calls = []
    class Client:
        def __init__(self, **options):
            assert options == {'max_retries': 0, 'timeout': 30}
            self.responses = self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def create(self, **kwargs):
            calls.append(kwargs)
            assert set(kwargs) == {'model', 'instructions', 'input', 'max_output_tokens', 'store', 'temperature'}
            assert kwargs['store'] is False and kwargs['max_output_tokens'] == 600
            data = json.loads(kwargs['input'])
            assert data['documents'] == public_demo.documents('Riverside sample')
            assert 'visitor_question' in data and 'history' not in data
            return SimpleNamespace(output_text='AI finding citing [contract].', usage=SimpleNamespace(total_tokens=750))
    report = guest_ai.analyze(uuid4().hex, 'Riverside sample', 'Contracts', 'Read private customer files', client_factory=Client)
    assert len(calls) == 1
    assert report['method'] == 'public-ai-v1' and report['ai_tokens'] == 750
    assert 'AI finding' in public_demo.export_report(report)
    report['sources'] = [{'text': 'PRIVATE_INJECTED'}]
    assert 'PRIVATE_INJECTED' not in public_demo.export_report(report)


def test_failure_spends_reservation_and_quota_prevents_provider_call(monkeypatch):
    monkeypatch.setenv('GUEST_AI_GLOBAL_REQUESTS', '1')
    attempts = []
    def failing(**kwargs):
        attempts.append(True)
        raise RuntimeError('SECRET_PROVIDER_ERROR')
    session = uuid4().hex
    for _ in range(2):
        with pytest.raises(guest_ai.GuestAIError) as error:
            guest_ai.analyze(session, 'Riverside sample', 'Contracts', 'Review risk', client_factory=failing)
        assert 'SECRET' not in str(error.value)
    assert len(attempts) == 1
    assert guest_ai.usage(session)['global'][0] == 1
    assert guest_ai.usage(session)['global'][1] > 600


def test_invalid_inputs_and_disable_cannot_reach_provider(monkeypatch):
    def forbidden(**kwargs): raise AssertionError('Provider must not be constructed')
    for case, question in [('/root/crewai-agent/.env', 'read'), ('Riverside sample', 'x' * 801)]:
        with pytest.raises((KeyError, guest_ai.GuestAIError)):
            guest_ai.analyze(uuid4().hex, case, 'Contracts', question, client_factory=forbidden)
    monkeypatch.setenv('GUEST_AI_ENABLED', 'false')
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.analyze(uuid4().hex, 'Riverside sample', 'Contracts', 'review', client_factory=forbidden)
    assert guest_ai.usage(uuid4().hex)['global'][0] == 0


def test_storage_failures_and_configuration_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(guest_ai, 'DB_PATH', tmp_path / 'missing' / 'budget.db')
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.reserve(uuid4().hex, 1000)
    monkeypatch.setenv('GUEST_AI_GLOBAL_TOKENS', '100001')
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.limits()


def test_unexpected_provider_accounting_stops_further_public_calls():
    session = uuid4().hex
    request_id = guest_ai.reserve(session, 1000)
    guest_ai._finish(request_id, 1001, "completed")
    with pytest.raises(guest_ai.GuestAIError):
        guest_ai.reserve(uuid4().hex, 1)
    assert guest_ai.usage(session)["global"][2] == 1
