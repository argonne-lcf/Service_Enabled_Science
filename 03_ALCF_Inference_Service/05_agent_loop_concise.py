# /// script
# requires-python = ">=3.10"
# dependencies = ["alcf-ai>=0.13", "httpx"]
# ///
"""The same agent as 04_agent_loop.py, minus the pretty-printing.

    uv run 05_agent_loop_concise.py "Are both Polaris and Crux up?"
"""

import json
import sys

import httpx
from alcf_ai import InferenceClient


def get_system_status(name: str) -> str:
    resources = httpx.get("https://api.alcf.anl.gov/api/v1/status/resources").json()
    status = {r["name"].lower(): r["current_status"] for r in resources}
    return json.dumps({"name": name, "status": status.get(name.lower(), "no such system")})


TOOLS = [{"type": "function", "function": {
    "name": "get_system_status",
    "description": "Get the live status (up/down) of an ALCF system.",
    "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
}}]
TOOL_FUNCTIONS = {"get_system_status": get_system_status}

client = InferenceClient().clusters("metis").openai
question = sys.argv[1] if len(sys.argv) > 1 else "Is Aurora up right now?"
messages = [
    {"role": "system", "content": "You are a helpful ALCF assistant. Be brief."},
    {"role": "user", "content": question},
]
print(f"[user]      {question}")

while True:
    msg = client.chat.completions.create(model="gpt-oss-120b", messages=messages, tools=TOOLS).choices[0].message
    messages.append(msg.model_dump(exclude_none=True))
    if reasoning := getattr(msg, "reasoning", None):
        print(f"[reasoning] {reasoning}")
    if msg.content:
        print(f"[assistant] {msg.content}")
    if not msg.tool_calls:
        break
    for call in msg.tool_calls:
        result = TOOL_FUNCTIONS[call.function.name](**json.loads(call.function.arguments))
        print(f"[tool]      {call.function.name}({call.function.arguments}) -> {result}")
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
