# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=2.10,<5", "rich"]
# ///
"""
Step 0: Use an MCP server somebody else runs.

ask.alcf.anl.gov/mcp is a public, remote MCP server that retrieves ALCF, OLCF,
NERSC and LLNL documentation. No token, no install, no account -- the URL is
the whole configuration. Run this before writing a server of your own, to see
what the protocol looks like from the consuming side.

    uv run 00_ask_alcf_docs.py
    uv run 00_ask_alcf_docs.py "How do I request 4 GPUs on Polaris?"
"""

import asyncio
import re
import sys

from fastmcp import Client
from rich import print
from rich.table import Table

ASK_ALCF = "https://ask.alcf.anl.gov/mcp"

DEFAULT_QUESTION = "What is the max walltime for the Polaris debug queue?"


async def main(question: str) -> None:
    # A URL instead of a script path: fastmcp speaks streamable HTTP to a server
    # running somewhere else. Nothing is launched locally.
    async with Client(ASK_ALCF) as client:

        tools = await client.list_tools()
        table = Table(title=f"Tools advertised by {ASK_ALCF}", title_justify="left")
        table.add_column("name", style="cyan")
        table.add_column("arguments")
        table.add_column("description")
        for tool in tools:
            args = ", ".join(tool.inputSchema.get("properties", {}))
            first_line = (tool.description or "").strip().splitlines()[0]
            table.add_row(tool.name, args, first_line)
        print(table)

        # top_k is not optional in practice. Left unset the server returns five
        # chunks -- roughly 5k tokens -- into your context on every question.
        print(f"\n[bold]retrieve_alcf_docs({question!r}, top_k=2)[/bold]\n")
        result = await client.call_tool(
            "retrieve_alcf_docs",
            {"query": question, "top_k": 2, "include_images": False},
        )

        total = 0
        for block in result.content:
            text = getattr(block, "text", "") or ""
            total += len(text)
            score = re.search(r"score: ([\d.]+)", text)
            source = re.search(r"Source: (\S+)", text)
            print(f"[cyan]score[/cyan] {score.group(1) if score else '?'}   "
                  f"[cyan]source[/cyan] {source.group(1) if source else '?'}")
            print(text[:400].strip().replace("\n", " ") + " ...\n")

        print(f"[dim]{len(result.content)} chunks, {total} chars "
              f"(~{total // 4} tokens) added to context[/dim]")

        # Note the «UNTRUSTED_CONTENT» marker in each chunk. Retrieved text is
        # data, not instructions -- see README section 2.


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    asyncio.run(main(question))
