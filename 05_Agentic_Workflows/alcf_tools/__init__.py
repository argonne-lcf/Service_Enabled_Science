"""The three tool groups that `alcf_mcp.py` mounts into one MCP server.

    docs.py     ALCF Knowledge base    -- retrieve_alcf_docs          (1 tool)
    globus.py   Globus data transfer   -- staging, local -> ALCF      (4 tools)
    iri.py      ALCF IRI for compute   -- PBS submit / poll / read    (6 tools)

Each module owns a FastMCP instance so the groups stay readable separately;
`alcf_mcp.py` mounts all three without a namespace, so an agent sees eleven
tools under their plain names and never has to know about this split.

`common.py` holds what all three agree on: facility IDs, path translation, and
the guardrails.
"""
