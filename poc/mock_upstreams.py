"""Two authenticated HTTP providers. No LiteLLM calls or database mocks here."""
import asyncio
import json
import os
import secrets
import time
from collections import Counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="POC synthetic MaaS and self-hosted upstreams")
stats = Counter()


def check(value: str | None, expected: str) -> None:
    if not value or not secrets.compare_digest(value, expected):
        raise HTTPException(401, "Invalid synthetic upstream credential")


def sse(payload: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return prefix + "data: " + json.dumps(payload) + "\n\n"


@app.get('/health')
async def health():
    return {'status': 'ok', 'providers': ['anthropic-maas', 'openai-selfhosted']}


@app.get('/stats')
async def counters(request: Request):
    check(request.headers.get('x-poc-admin'), os.environ['POC_STATS_KEY'])
    return dict(stats)


async def prepare(request: Request, provider: str):
    if provider == 'maas':
        check(request.headers.get('x-api-key'), os.environ['POC_UPSTREAM_KEY'])
    else:
        check(request.headers.get('authorization'), 'Bearer ' + os.environ['POC_UPSTREAM_KEY'])
    data = await request.json()
    stats[provider] += 1
    # Never store messages/credentials in our observation endpoint.
    text = json.dumps(data.get('messages', []))
    if '[poc:429]' in text:
        stats[provider + ':429'] += 1
        return JSONResponse(status_code=429, headers={'retry-after': '1'}, content={
            'error': {'type': 'rate_limit_error', 'message': 'Synthetic upstream throttling'}})
    if '[poc:500]' in text:
        stats[provider + ':500'] += 1
        return JSONResponse(status_code=500, content={
            'error': {'type': 'api_error', 'message': 'Synthetic upstream failure'}})
    if '[poc:timeout]' in text:
        await asyncio.sleep(6)
    if '[poc:slow]' in text:
        await asyncio.sleep(1)
    return data


@app.post('/local/v1/chat/completions')
async def local_chat(request: Request):
    data = await prepare(request, 'local')
    if isinstance(data, JSONResponse):
        return data
    ident = 'chatcmpl-poc-' + secrets.token_hex(6)
    content = 'Hello from self-hosted model.'
    message = {'role': 'assistant', 'content': content}
    reason = 'stop'
    if any(m.get('role') == 'tool' for m in data['messages']):
        message['content'] = 'Tool results received.'
    elif data.get('tools'):
        message = {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'call_' + str(i), 'type': 'function', 'function': {
                'name': tool['function']['name'], 'arguments': '{"city":"Shanghai"}'}}
            for i, tool in enumerate(data['tools'])]}
        reason = 'tool_calls'
    elif data.get('response_format'):
        message['content'] = '{"ok":true,"source":"local"}'
    usage = {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20}
    if not data.get('stream'):
        return {'id': ident, 'object': 'chat.completion', 'created': int(time.time()),
                'model': data['model'], 'choices': [{'index': 0, 'message': message,
                'finish_reason': reason}], 'usage': usage}

    async def chunks():
        def chunk(delta, finish=None, usage_value=None):
            result = {'id': ident, 'object': 'chat.completion.chunk', 'created': int(time.time()),
                      'model': data['model'], 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
            if usage_value is not None:
                result['choices'] = []
                result['usage'] = usage_value
            return sse(result)
        yield chunk({'role': 'assistant', 'content': ''})
        if reason == 'tool_calls':
            for i, call in enumerate(message['tool_calls']):
                yield chunk({'tool_calls': [{'index': i, **call}]})
        else:
            for word in message['content'].split(' '):
                yield chunk({'content': word + ' '})
                await asyncio.sleep(0.05)
        yield chunk({}, reason)
        if data.get('stream_options', {}).get('include_usage'):
            yield chunk({}, usage_value=usage)
        yield 'data: [DONE]\n\n'
    return StreamingResponse(chunks(), media_type='text/event-stream')


@app.post('/maas/v1/messages')
async def maas_messages(request: Request):
    data = await prepare(request, 'maas')
    if isinstance(data, JSONResponse):
        return data
    ident = 'msg_poc_' + secrets.token_hex(6)
    content = 'Hello from internal MaaS.'
    result = {'id': ident, 'type': 'message', 'role': 'assistant', 'model': data['model'],
              'content': [{'type': 'text', 'text': content}], 'stop_reason': 'end_turn',
              'stop_sequence': None, 'usage': {'input_tokens': 10, 'output_tokens': 6}}
    if not data.get('stream'):
        return result

    async def events():
        yield sse({'type': 'message_start', 'message': {**result, 'content': [],
                  'stop_reason': None, 'usage': {'input_tokens': 10, 'output_tokens': 0}}}, 'message_start')
        yield sse({'type': 'content_block_start', 'index': 0,
                   'content_block': {'type': 'text', 'text': ''}}, 'content_block_start')
        for word in content.split(' '):
            yield sse({'type': 'content_block_delta', 'index': 0,
                       'delta': {'type': 'text_delta', 'text': word + ' '}}, 'content_block_delta')
            await asyncio.sleep(0.05)
        yield sse({'type': 'content_block_stop', 'index': 0}, 'content_block_stop')
        yield sse({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
                   'usage': {'output_tokens': 6}}, 'message_delta')
        yield sse({'type': 'message_stop'}, 'message_stop')
    return StreamingResponse(events(), media_type='text/event-stream')
