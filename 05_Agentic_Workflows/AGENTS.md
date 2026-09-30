# Working in this directory

This file is self-contained. Everything needed to work here is in it, in
[`skills/submit-job/SKILL.md`](skills/submit-job/SKILL.md), and in the tool
docstrings themselves.

`README.md` is **not** required reading. It is the tutorial narrative, written
for a person following along: a thousand lines of setup, rationale and worked
examples. Reading it to answer an operational question costs far more context
than it returns, and the parts that matter to you are restated here. Point a
human at it; do not load it yourself.

## The eleven tools — call them, do not import them

One MCP server, `alcf-mcp`.

- **Docs** — `retrieve_alcf_docs`
- **Globus** — `local_endpoint`, `globus_ls`, `stage_to_alcf`, `transfer_status`
- **IRI** — `get_system_status`, `submit_job`, `get_job_state`, `list_jobs`,
  `cancel_job`, `read_file`

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

`submit_job` prepends the HTTP/HTTPS proxy, the pinned conda module, and the
`source` + `conda activate base` that puts `python` on `PATH` — see
`job_preamble()` in [`alcf_tools/common.py`](alcf_tools/common.py). Write
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
