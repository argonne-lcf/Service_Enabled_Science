# /// script
# requires-python = ">=3.10"
# dependencies = ["alcf-ai>=0.13", "rich"]
# ///
"""
Step 3: Dissect a ChatCompletion response.

    uv run 03_response_anatomy.py          # annotated tree view of each response
    uv run 03_response_anatomy.py --raw    # the full raw JSON instead of the tree
"""

import sys

from alcf_ai import InferenceClient
from openai.types.chat import ChatCompletion
from rich import print
from rich.json import JSON
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.tree import Tree

MODEL = "gpt-oss-120b"
openai_client = InferenceClient().clusters("metis").openai


def note(text: str) -> str:
    return f"  [yellow]← {text}[/yellow]"


def add_text(node: Tree, label: str, text: str | None, annotation: str, style: str) -> None:
    """Add a labelled field, with its full (word-wrapped) text as a child."""
    if text is None:
        node.add(f"{label} = [dim]None[/dim]" + note(annotation))
    else:
        node.add(label + note(annotation)).add(Text(text.strip(), style=style))


def show_request(request: dict) -> None:
    print(Panel(
        JSON.from_data(request),
        title="request",
        title_align="left",
        border_style="cyan",
    ))


def show_response(response: ChatCompletion) -> None:
    if "--raw" in sys.argv:
        body = JSON(response.model_dump_json())
        body.text.no_wrap = False  # wrap long strings instead of cropping them
    else:
        body = response_tree(response)
    print(Panel(body, border_style="green"))


def response_tree(response: ChatCompletion) -> Tree:
    choice = response.choices[0]
    message = choice.message
    reasoning = getattr(message, "reasoning", None)

    tree = Tree("[bold]response[/bold]")
    tree.add(f"model = {response.model!r}")

    c = tree.add("choices[0]")
    c.add(f"finish_reason = [bold]{choice.finish_reason!r}[/bold]" + note("why generation stopped"))

    m = c.add("message")
    m.add(f"role = {message.role!r}")
    add_text(m, "reasoning", reasoning, "🧠 thinking", style="dim italic")
    add_text(m, "content", message.content, "💬 the answer", style="bold")

    if message.tool_calls:
        tc_node = m.add("tool_calls" + note("🔧 the model wants YOU to run this"))
        for i, call in enumerate(message.tool_calls):
            t = tc_node.add(f"[{i}]")
            t.add(f"id                 = {call.id!r}" + note("echo it back later"))
            t.add(f"function.name      = {call.function.name!r}")
            t.add(f"function.arguments = {call.function.arguments!r}" + note("JSON string"))
    else:
        m.add("tool_calls = [dim]None[/dim]")

    u = tree.add("usage")
    u.add(f"prompt_tokens     = {response.usage.prompt_tokens}" + note("everything you sent"))
    ct = u.add(f"completion_tokens = {response.usage.completion_tokens}" + note("everything it generated"))
    details = response.usage.completion_tokens_details
    if details and details.reasoning_tokens:
        ct.add(f"reasoning_tokens = {details.reasoning_tokens}" + note("spent thinking"))

    return tree


# Simple question / answer
print(Rule("[bold]A) Plain answer[/bold]"))
messages = [{"role": "user", "content": "In one sentence: why is the sky blue?"}]

request = {"model": MODEL, "messages": messages}
show_request(request)

response = openai_client.chat.completions.create(**request)
show_response(response)

# Same API, but now we offer the model a tool
# A tool is just a JSON Schema describing a function. The model never runs
# anything itself: it can only *ask* for a tool call in its response.
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get the current status (up/down) of an ALCF system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "e.g. 'Aurora'"}
                },
                "required": ["name"],
            },
        },
    }
]

print("\n\n", Rule("[bold]B) Tool call[/bold]"))
request = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Is Aurora up right now?"}],
    "tools": tools,
}
show_request(request)

response = openai_client.chat.completions.create(**request)
show_response(response)
