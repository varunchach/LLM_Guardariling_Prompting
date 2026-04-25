import boto3, json, time

REGION = 'us-east-1'

MODELS = {
    'Claude Sonnet 4.6': 'us.anthropic.claude-sonnet-4-6',
}

PRICE_PER_1M = {
    'us.anthropic.claude-sonnet-4-6': {'input': 3.00, 'output': 15.00},
}

def _client():
    session = boto3.Session(region_name=REGION)
    return session.client('bedrock-runtime')

def calculate_cost(model_id, input_tokens, output_tokens):
    prices = PRICE_PER_1M.get(model_id, {'input': 3.00, 'output': 15.00})
    return round((input_tokens * prices['input'] + output_tokens * prices['output']) / 1_000_000, 6)

def invoke_model(model_id, prompt, system=None, temperature=0.7, max_tokens=512):
    client = _client()
    body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens':        max_tokens,
        'temperature':       temperature,
        'messages':          [{'role': 'user', 'content': prompt}],
    }
    if system:
        body['system'] = system

    start  = time.time()
    resp   = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(resp['body'].read())
    latency_ms = round((time.time() - start) * 1000)

    tokens_in  = result['usage']['input_tokens']
    tokens_out = result['usage']['output_tokens']

    return {
        'text':          result['content'][0]['text'],
        'input_tokens':  tokens_in,
        'output_tokens': tokens_out,
        'latency_ms':    latency_ms,
        'cost_usd':      calculate_cost(model_id, tokens_in, tokens_out),
    }

def stream_response(model_id, prompt, system=None, temperature=0.7, max_tokens=512):
    """Generator — yields text chunks for st.write_stream."""
    client = _client()
    body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens':        max_tokens,
        'temperature':       temperature,
        'messages':          [{'role': 'user', 'content': prompt}],
    }
    if system:
        body['system'] = system

    resp = client.invoke_model_with_response_stream(
        modelId=model_id, body=json.dumps(body)
    )
    for event in resp['body']:
        chunk = json.loads(event['chunk']['bytes'])
        if chunk.get('type') == 'content_block_delta':
            delta = chunk.get('delta', {})
            if delta.get('type') == 'text_delta':
                yield delta.get('text', '')
