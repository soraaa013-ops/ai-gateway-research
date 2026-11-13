"""Seed and exercise a running POC without printing API keys."""
import argparse
import json
import uuid
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('credentials', type=Path)
    args = parser.parse_args()
    config = json.loads(args.credentials.read_text())
    with httpx.Client(base_url=config['base_url'], timeout=15, trust_env=False) as client:
        admin = {'Authorization': 'Bearer ' + config['master_key']}
        user_id = 'poc-developer-' + uuid.uuid4().hex
        user = client.post('/user/new', headers=admin, json={
            'user_id': user_id, 'user_role': 'internal_user', 'auto_create_key': False})
        user.raise_for_status()
        result = client.post('/key/generate', headers=admin, json={
            'user_id': user_id, 'key_alias': user_id, 'models': ['maas-chat', 'local-chat'],
            'max_budget': 1, 'rpm_limit': 30,
            'metadata': {'project': 'synthetic-demo', 'owner': 'demo-developer'}})
        result.raise_for_status()
        key = result.json()['key']
        output = args.credentials.parent / 'developer.json'
        output.touch(mode=0o600)
        output.chmod(0o600)
        output.write_text(json.dumps({'api_key': key, 'base_url': config['base_url'] + '/v1'}, indent=2))
        for model in ['maas-chat', 'local-chat']:
            response = client.post('/v1/chat/completions', headers={'Authorization': 'Bearer ' + key},
                json={'model': model, 'messages': [{'role': 'user', 'content': 'hello'}], 'max_tokens': 64})
            response.raise_for_status()
            data = response.json()
            print(json.dumps({'model': model, 'content': data['choices'][0]['message']['content'],
                              'usage': data['usage']}, ensure_ascii=False))
        print(f'Developer credential saved locally: {output}')


if __name__ == '__main__':
    main()
