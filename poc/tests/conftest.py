from pathlib import Path
import sys
import uuid

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from poc.runtime import Stack


@pytest.fixture(scope='session')
def stack(tmp_path_factory):
    instance = Stack(tmp_path_factory.mktemp('litellm-poc')).start()
    yield instance
    instance.close()


@pytest.fixture
def client(stack):
    with httpx.Client(base_url=stack.url, timeout=15, trust_env=False) as client:
        yield client


@pytest.fixture
def admin(stack):
    return {'Authorization': f'Bearer {stack.master}'}


@pytest.fixture
def issue_key(client, admin):
    def issue(**overrides):
        user_id = 'poc-user-' + uuid.uuid4().hex
        user = client.post('/user/new', headers=admin, json={
            'user_id': user_id, 'user_role': 'internal_user', 'auto_create_key': False})
        assert user.status_code == 200, user.text[:500]
        payload = {'user_id': user_id, 'models': ['maas-chat', 'local-chat'],
                   'metadata': {'project': 'synthetic-demo'}, **overrides}
        response = client.post('/key/generate', headers=admin, json=payload)
        assert response.status_code == 200, response.text[:500]
        key = response.json()['key']
        return key, {'Authorization': f'Bearer {key}'}
    return issue
