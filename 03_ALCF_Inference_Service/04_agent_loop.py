# /// script
# requires-python = ">=3.10"
# dependencies = ["alcf-ai>=0.13", "httpx", "rich"]
# ///
"""
Step 4: A tiny agent from scratch

Watch the context window grow as we go around the agent loop:

    conversation + tools ──► LLM asks for a tool call ──► we run the tool
         ▲                                                      │
         └────────── send the result back ◄─────────────────────┘
                     ...until the LLM answers in plain text.

    uv run 04_agent_loop.py
    uv run 04_agent_loop.py "Are both Polaris and Crux up?"   # ask your own question
    uv run 04_agent_loop.py --step                            # pause between steps
"""

import json
import sys

import httpx
from alcf_ai import InferenceClient
from rich import print
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

MODEL = "gpt-oss-120b"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
QUESTION = args[0] if args else "Is Aurora up right now?"
STEP_MODE = "--step" in sys.argv


# ════════════════════════════════════════════════════════════════════════
# 1. THE TOOL: an ordinary Python function that runs on your machine...
# ════════════════════════════════════════════════════════════════════════
def get_system_status(name: str) -> str:
    """Look up a system in the public ALCF status API."""
    resources = httpx.get("https://api.alcf.anl.gov/api/v1/status/resources").json()
    for r in resources:
        if r["name"].lower() == name.lower():
            return json.dumps({"name": r["name"], "status": r["current_status"]})
    return json.dumps({"error": f"No ALCF system named {name!r}"})


# ...plus a description the LLM can read. This is ALL the LLM ever sees of
# the tool: a name, a description, and a JSON Schema for the arguments.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get the live status (up/down) of an ALCF system.",
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
TOOL_FUNCTIONS = {"get_system_status": get_system_status}


# ════════════════════════════════════════════════════════════════════════
# Pretty-printing helpers (skip these on a first read!)
# ════════════════════════════════════════════════════════════════════════
ROLE_STYLE = {
    "tools": ("🧰 tools", "magenta"),
    "system": ("⚙️  system", "white"),
    "user": ("👤 user", "cyan"),
    "assistant": ("🤖 assistant", "green"),
    "tool": ("🔧 tool", "yellow"),
}
already_shown = 0


def clip(text: str, width: int = 120) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def describe(msg: dict) -> str:
    """One or two lines summarising a message in the context window."""
    if msg["role"] == "assistant":
        lines = []
        if msg.get("reasoning"):
            lines.append(f"[dim italic]🧠 {clip(msg['reasoning'])}[/dim italic]")
        for call in msg.get("tool_calls") or []:
            fn = call["function"]
            lines.append(f"[bold]🔧 call {fn['name']}({fn['arguments']})[/bold]")
        if msg.get("content"):
            lines.append(f"💬 {clip(msg['content'])}")
        return "\n".join(lines)
    return clip(msg["content"])


def show_context(messages: list[dict], title: str) -> None:
    """Draw the whole context window, marking what's new since last time."""
    global already_shown
    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column(no_wrap=True)
    table.add_column()
    table.add_column(no_wrap=True)

    name, style = ROLE_STYLE["tools"]
    table.add_row(f"[{style}]{name}[/{style}]", "get_system_status(name)", "")
    for i, msg in enumerate(messages):
        name, style = ROLE_STYLE[msg["role"]]
        new = "[bold yellow]✨ NEW[/bold yellow]" if i >= already_shown else ""
        table.add_row(f"[{style}]{name}[/{style}]", describe(msg), new)

    print(Panel(table, title=title, title_align="left", border_style="blue"))
    already_shown = len(messages)


def narrate(text: str) -> None:
    if STEP_MODE:
        input("\n[press Enter] ")
    print()
    print(Rule(f"[bold]{text}[/bold]", align="left"))


# ════════════════════════════════════════════════════════════════════════
# 2. THE CONTEXT: a plain list of messages. This is the agent's memory.
# ════════════════════════════════════════════════════════════════════════
messages: list[dict] = [
    {"role": "system", "content": "You are a helpful ALCF assistant. Be brief."},
    {"role": "user", "content": QUESTION},
]

# ════════════════════════════════════════════════════════════════════════
# 3. THE AGENT LOOP (the "harness")
# ════════════════════════════════════════════════════════════════════════
prompt_tokens_per_request = []

narrate("The conversation begins")
show_context(messages, "Context window")

openai_client = InferenceClient().clusters("metis").openai

for request_number in range(1, 20):  # a safety cap on the number of turns
    # The LLM is stateless: it remembers nothing between requests, so every
    # request carries everything.
    narrate(f"📤 Request #{request_number}: harness sends the whole context to the LLM")
    response = openai_client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS
    )
    prompt_tokens_per_request.append(response.usage.prompt_tokens)
    message = response.choices[0].message

    # Whatever the LLM says gets appended to the conversation.
    messages.append(message.model_dump(exclude_none=True))
    print(
        f"📥 The LLM read {response.usage.prompt_tokens} tokens and replied with "
        f"finish_reason=[bold]{response.choices[0].finish_reason!r}[/bold]"
    )
    show_context(messages, "Context window")

    # No tool calls: we have our answer
    if not message.tool_calls:
        break

    # Otherwise, it's the harness's job to actually run each tool...
    narrate("🔧 Harness runs the requested tool(s) on your machine")
    for call in message.tool_calls:
        func = TOOL_FUNCTIONS[call.function.name]
        kwargs = json.loads(call.function.arguments)
        result = func(**kwargs)
        print(f"   {call.function.name}(**{kwargs}) → {result}")

        # ...and append the result, tagged with the matching tool_call_id.
        messages.append(
            {"role": "tool", "tool_call_id": call.id, "content": result}
        )
    show_context(messages, "Context window")


# ════════════════════════════════════════════════════════════════════════
# 4. THE ANSWER, and how much the context grew along the way
# ════════════════════════════════════════════════════════════════════════
narrate("✅ Final answer")
answer = (message.content or "").strip()
body = Markdown(answer) if "\n" in answer else Text(answer)
print(Panel(body, border_style="green"))

print("\n[bold]Context size sent on each request[/bold] (prompt tokens)")
biggest = max(prompt_tokens_per_request)
for n, tokens in enumerate(prompt_tokens_per_request, start=1):
    bar = "█" * round(40 * tokens / biggest)
    print(f"  request #{n}  [blue]{bar}[/blue] {tokens}")
print(f"  ...and the conversation is now {len(messages)} messages long.")
