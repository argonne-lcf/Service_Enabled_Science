# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=2.10", "alcf-tokens", "requests", "rich"]
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

from fastmcp import Client
from rich import print
from rich.table import Table


async def main(system: str) -> None:
    # Pointing a Client at the script path launches it over stdio, the same way
    # a coding agent does.
    async with Client("alcf_mcp.py") as client:

        tools = await client.list_tools()
        table = Table(title="Tools this server advertises", title_justify="left")
        table.add_column("name", style="cyan")
        table.add_column("arguments")
        table.add_column("description")
        for tool in tools:
            args = ", ".join(tool.inputSchema.get("properties", {}))
            first_line = (tool.description or "").strip().splitlines()[0]
            table.add_row(tool.name, args, first_line)
        print(table)

        print(f"\n[bold]Calling get_system_status({system!r})[/bold]")
        result = await client.call_tool("get_system_status", {"system": system})
        print(result.data)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else ""))
