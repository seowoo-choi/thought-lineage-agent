import json

def extract(payload):
    """Accept a schema-shaped dict or recover one JSON object from model text."""
    if isinstance(payload, dict): return payload
    if not isinstance(payload, str): raise ValueError("unsupported Codex payload")
    start, end = payload.find("{"), payload.rfind("}")
    if start < 0 or end < start: raise ValueError("no JSON object")
    return json.loads(payload[start:end+1])
