"""All tests use the native proxy over HTTP and a real isolated PostgreSQL."""
import concurrent.futures
import hashlib
import json
import time

import httpx
import psycopg
from jsonschema import validate
from openai import OpenAI
import pytest


def chat(client, headers, model='local-chat', text='hello', **extra):
    return client.post('/v1/chat/completions', headers=headers, json={
        'model': model, 'messages': [{'role': 'user', 'content': text}],
        'max_tokens': 64, **extra})


def test_real_postgres_and_hashed_key(stack, client, admin, issue_key):
    key, _ = issue_key()
    with psycopg.connect(stack.dsn) as db:
        assert 'PostgreSQL' in db.execute('select version()').fetchone()[0]
        row = db.execute('SELECT token FROM "LiteLLM_VerificationToken" WHERE token = %s',
                         (hashlib.sha256(key.encode()).hexdigest(),)).fetchone()
        assert row and row[0] != key


@pytest.mark.parametrize('model,expected', [('local-chat', 'self-hosted'), ('maas-chat', 'MaaS')])
def test_two_protocols(client, issue_key, model, expected):
    _, headers = issue_key()
    response = chat(client, headers, model=model)
    assert response.status_code == 200, response.text[:500]
    body = response.json()
    assert expected in body['choices'][0]['message']['content']
    assert body['usage']['total_tokens'] > 0
    assert response.headers.get('x-litellm-call-id') or response.headers.get('x-request-id')


@pytest.mark.parametrize('model', ['local-chat', 'maas-chat'])
def test_sdk_streaming(stack, issue_key, model):
    key, _ = issue_key()
    with OpenAI(base_url=stack.url + '/v1', api_key=key, max_retries=0,
                http_client=httpx.Client(trust_env=False)) as sdk:
        chunks = list(sdk.chat.completions.create(model=model,
            messages=[{'role': 'user', 'content': 'hello'}], max_tokens=64,
            stream=True, stream_options={'include_usage': True}))
    assert sum(bool(c.choices and c.choices[0].delta.content) for c in chunks) > 1
    assert any(c.choices and c.choices[0].finish_reason == 'stop' for c in chunks)
    assert any(c.usage and c.usage.total_tokens > 0 for c in chunks)


def test_native_anthropic_entry(client, issue_key):
    _, headers = issue_key()
    response = client.post('/v1/messages', headers={**headers, 'anthropic-version': '2023-06-01'},
                           json={'model': 'maas-chat', 'max_tokens': 64,
                                 'messages': [{'role': 'user', 'content': 'hello'}]})
    assert response.status_code == 200, response.text[:500]
    assert response.json()['content'][0]['text'] == 'Hello from internal MaaS.'


def test_model_allowlist_and_filtered_catalog(client, issue_key):
    _, headers = issue_key(models=['local-chat'])
    catalog = client.get('/v1/models', headers=headers)
    assert catalog.status_code == 200
    assert {m['id'] for m in catalog.json()['data']} == {'local-chat'}
    assert chat(client, headers, model='maas-chat').status_code in (401, 403)


def test_invalid_key_and_management_denied(client, issue_key):
    assert chat(client, {'Authorization': 'Bearer sk-invalid-demo'}).status_code == 401
    _, headers = issue_key()
    assert client.post('/model/new', headers=headers, json={'model_name': 'unauthorized', 'litellm_params': {'model': 'openai/nope'}}).status_code in (401, 403)


def test_revocation(client, admin, issue_key):
    key, headers = issue_key()
    assert chat(client, headers).status_code == 200  # Populate auth cache before revoke.
    response = client.post('/key/delete', headers=admin, json={'keys': [key]})
    assert response.status_code == 200, response.text[:500]
    assert chat(client, headers).status_code == 401


def test_expiry(client, issue_key):
    _, headers = issue_key(duration='1s')
    time.sleep(1.2)
    assert chat(client, headers).status_code in (401, 403)


def test_parallel_tool_roundtrip(client, issue_key):
    _, headers = issue_key()
    tools = [{'type': 'function', 'function': {'name': name, 'description': 'Synthetic tool',
        'parameters': {'type': 'object', 'properties': {'city': {'type': 'string'}},
                       'required': ['city']}}} for name in ['weather', 'timezone']]
    first = chat(client, headers, tools=tools)
    assert first.status_code == 200, first.text[:500]
    message = first.json()['choices'][0]['message']
    assert len(message['tool_calls']) == 2
    ids = {c['id'] for c in message['tool_calls']}
    assert len(ids) == 2
    for c in message['tool_calls']:
        assert json.loads(c['function']['arguments']) == {'city': 'Shanghai'}
    response = client.post('/v1/chat/completions', headers=headers, json={
        'model': 'local-chat', 'messages': [{'role': 'user', 'content': 'tools'}, message] + [
            {'role': 'tool', 'tool_call_id': c['id'], 'content': '{"result":"ok"}'}
            for c in message['tool_calls']], 'tools': tools})
    assert response.status_code == 200
    assert response.json()['choices'][0]['message']['content'] == 'Tool results received.'


def test_structured_output(client, issue_key):
    _, headers = issue_key()
    schema = {'type': 'object', 'properties': {'ok': {'type': 'boolean'},
        'source': {'type': 'string'}}, 'required': ['ok', 'source'], 'additionalProperties': False}
    response = chat(client, headers, response_format={'type': 'json_schema',
        'json_schema': {'name': 'result', 'strict': True, 'schema': schema}})
    assert response.status_code == 200, response.text[:500]
    validate(json.loads(response.json()['choices'][0]['message']['content']), schema)


@pytest.mark.parametrize('marker,status', [('[poc:429]', 429), ('[poc:500]', 500)])
def test_error_no_retry_no_fallback(stack, client, issue_key, marker, status):
    _, headers = issue_key()
    before = stack.stats()
    response = chat(client, headers, text=marker)
    assert response.status_code == status, response.text[:500]
    after = stack.stats()
    assert after.get('local', 0) - before.get('local', 0) == 1
    assert after.get('maas', 0) == before.get('maas', 0)


def test_timeout(client, issue_key):
    _, headers = issue_key()
    start = time.monotonic()
    response = chat(client, headers, text='[poc:timeout]')
    assert response.status_code in (408, 504), response.text[:500]
    assert time.monotonic() - start < 5.5


def test_rpm_limit(client, issue_key):
    _, headers = issue_key(rpm_limit=1)
    assert chat(client, headers).status_code == 200
    assert chat(client, headers).status_code == 429


def test_concurrency_limit(stack, client, issue_key):
    _, headers = issue_key(max_parallel_requests=1)
    before = stack.stats().get('local', 0)
    with concurrent.futures.ThreadPoolExecutor() as pool:
        first = pool.submit(chat, client, headers, text='[poc:slow]')
        deadline = time.monotonic() + 3
        while stack.stats().get('local', 0) == before and time.monotonic() < deadline:
            time.sleep(0.02)
        second = chat(client, headers)
        assert second.status_code == 429, second.text[:500]
        assert first.result().status_code == 200
    assert chat(client, headers).status_code == 200  # Slot released.


def test_spend_persisted_without_prompt(stack, client, issue_key):
    key, headers = issue_key()
    secret_prompt = 'synthetic-private-prompt-do-not-log'
    assert chat(client, headers, text=secret_prompt).status_code == 200
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    deadline = time.monotonic() + 30
    row = None
    while time.monotonic() < deadline:
        with psycopg.connect(stack.dsn) as db:
            row = db.execute('SELECT row_to_json(s) FROM "LiteLLM_SpendLogs" s WHERE api_key = %s',
                             (key_hash,)).fetchone()
        if row:
            break
        time.sleep(0.5)
    assert row, 'Spend log not flushed to PostgreSQL'
    assert row[0]['total_tokens'] == 20
    assert row[0]['spend'] > 0
    assert secret_prompt not in json.dumps(row[0])
    assert key not in json.dumps(row[0])


def test_other_key_details_denied(client, issue_key):
    key_a, _ = issue_key()
    _, headers_b = issue_key()
    response = client.get('/key/info', headers=headers_b, params={'key': hashlib.sha256(key_a.encode()).hexdigest()})
    assert response.status_code in (401, 403), response.text[:500]


def test_z_restart_preserves_key_and_data(stack, client, issue_key):
    key, headers = issue_key()
    assert chat(client, headers).status_code == 200
    stack.restart_proxy()
    assert chat(client, headers).status_code == 200
    with psycopg.connect(stack.dsn) as db:
        assert db.execute('SELECT count(*) FROM "LiteLLM_VerificationToken" WHERE token = %s',
                          (hashlib.sha256(key.encode()).hexdigest(),)).fetchone()[0] == 1


def test_budget_after_spend_settlement(client, admin, issue_key):
    key, headers = issue_key(max_budget=0.000001)
    assert chat(client, headers).status_code == 200
    deadline = time.monotonic() + 30
    spent = 0
    while time.monotonic() < deadline:
        info = client.get('/key/info', headers=admin, params={'key': hashlib.sha256(key.encode()).hexdigest()})
        assert info.status_code == 200
        spent = info.json()['info']['spend']
        if spent > 0.000001:
            break
        time.sleep(0.5)
    assert spent > 0.000001
    response = chat(client, headers)
    assert response.status_code == 422, response.text[:500]
    assert response.json()['error']['type'] == 'budget_exceeded'
    assert 'budget' in response.text.lower()


def test_ui_and_openapi_available(client):
    # Asset delivery only; no claim of a browser interaction test.
    response = client.get('/ui/', follow_redirects=True)
    assert response.status_code == 200
    assert 'html' in response.headers.get('content-type', '')
    spec = client.get('/openapi.json')
    assert spec.status_code == 200
    assert '/key/generate' in spec.json()['paths']
