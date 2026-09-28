# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=2.10,<5", "alcf-tokens", "requests", "rich"]
# ///
"""
Step 1: Call the MCP server without an agent in the way.

Before handing these tools to a model, see what the model will see. This
connects to alcf_mcp.py as a client, lists the tools it advertises, and calls
one of them -- exactly the handshake Claude Code performs at startup.

    uv run 01_call_tools_directly.py
    uv run 01_call_tools_directly.py polaris
"""

import asyncio
import sys
from pathlib import Path

from fastmcp import Client
from rich import print
from rich.table import Table

SERVER = Path(__file__).parent / "alcf_mcp.py"


async def main(system: str) -> None:
    # Pointing a Client at the script path launches it over stdio, the same way
    # a coding agent does.
    async with Client(SERVER) as client:

        tools = await client.list_tools()
        table = Table(title="Tools this server advertises", title_justify="left")
        table.add_column("name", style="cyan")
        table.add_column("arguments")
        table.add_column("description")
        for tool in tools:
            # MCP SDK v2 (fastmcp 4) renamed .inputSchema to .input_schema.
            schema = getattr(tool, "input_schema", None) or tool.inputSchema
            args = ", ".join(schema.get("properties", {}))
            first_line = (tool.description or "").strip().splitlines()[0]
            table.add_row(tool.name, args, first_line)
        print(table)

        print(f"\n[bold]Calling get_system_status({system!r})[/bold]")
        result = await client.call_tool("get_system_status", {"system": system})

        # .data is the deserialized return value, but it is only populated when
        # the server advertises an output schema -- these tools do not, so on
        # fastmcp 4 it is None and the payload arrives as text content blocks.
        # A model reads the same blocks.
        print(result.data if result.data is not None else
              "\n".join(b.text for b in result.content if hasattr(b, "text")))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else ""))
