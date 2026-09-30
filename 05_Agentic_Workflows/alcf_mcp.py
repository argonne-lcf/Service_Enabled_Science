# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=2.10,<5", "alcf-tokens", "globus-sdk>=3,<5", "requests"]
# ///
"""
One MCP server exposing the three ALCF services this session uses.

    ALCF Knowledge base     alcf_tools/docs.py       1 tool    (no token)
    Globus data transfer    alcf_tools/globus.py     4 tools
    ALCF IRI for compute    alcf_tools/iri.py        6 tools

Each group is its own module with its own FastMCP instance; this file mounts
all three. Mounting without a namespace keeps the tool names plain, so an
agent sees `submit_job`, not `iri_submit_job`, and the split is invisible from
the outside. The guardrails and facility IDs the groups share live in
alcf_tools/common.py.

Why one server and not three: every server you register is another entry to
configure, another process to launch, and another thing that can fail on an
unfamiliar network. One server, eleven tools.

    stdio transport (what Claude Code / opencode launch, per .mcp.json and
    opencode.jsonc -- run ./setup.sh first to build .venv):
        .venv/bin/python alcf_mcp.py

    standalone, resolving dependencies from the PEP 723 header above:
        uv run alcf_mcp.py

    poke at it in a browser-based inspector:
        uv run --with fastmcp fastmcp dev alcf_mcp.py
"""

from fastmcp import FastMCP

from alcf_tools import docs, globus, iri

mcp = FastMCP("alcf-mcp")

# No namespace argument: tool names pass through unchanged.
mcp.mount(docs.mcp)
mcp.mount(globus.mcp)
mcp.mount(iri.mcp)


if __name__ == "__main__":
    mcp.run()
