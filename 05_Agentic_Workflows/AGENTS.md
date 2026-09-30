# Working in this directory

Read alongside [`README.md`](README.md); this file is only the things an agent
gets wrong unprompted. Anything explained at length there is not repeated here.

## Call the tools, do not import them

There is one MCP server, `alcf-mcp`, with eleven tools. Call them as tools.

Do **not** reach for Bash to do the same job — `python -c "from alcf_mcp import
get_job_state, read_file, ..."` runs the same code with none of the guardrails,
produces no tool-call record the user can see, and re-implements polling badly.
If a tool appears to be missing, say so and stop; do not route around it.

`retrieve_alcf_docs` is the AskALCF knowledge base. There is no separate
`ask-alcf` server — it is mounted into `alcf-mcp` like everything else, so its
absence from `/mcp` as its own entry is correct.

## Use the skill for anything that runs

Requests to run, stage, submit or monitor work go through
[`skills/submit-job/SKILL.md`](skills/submit-job/SKILL.md). Follow its five
stages in order rather than improvising a shorter path.

## `commands` is the work only

`submit_job` prepends the HTTP/HTTPS proxy and the pinned conda module itself —
see `job_preamble()` in [`alcf_tools/common.py`](alcf_tools/common.py). Write
`commands="python train.py"`, not a block that re-exports the proxy. Pass
`setup_env=False` only when the user has asked for a different environment.

## The limits are in the server, not in the conversation

`alcf_training` only, 2 nodes, 30 minutes, 500 staged files, 1 GiB, and eagle
writes only under `/eagle/<project>/<user>/` with the filename spelled out.
These are Python `raise`s in `common.py`. Do not try to talk past them or work
around them — report the limit and ask a human to lift it.

## Facility facts come from the facility

Queue names, node counts, filesystem layout and module versions change. Use
`retrieve_alcf_docs` or `get_system_status` rather than answering from memory,
and cite what you used.
