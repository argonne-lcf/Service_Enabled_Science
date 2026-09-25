# Agentic Workflows

Session 03 ended with a challenge: *"Add a second tool. Write a new function to
leverage the IRI API, describe it in `TOOLS`, and register it in
`TOOL_FUNCTIONS`."* Session 04 pointed a coding agent at the ALCF Inference
Service so it could write code for you.

This session closes the loop. Instead of hand-registering tools inside one
script, we stand up an **MCP server** in front of the Facility API — and the
coding agent from Session 04 discovers every tool on it at startup.

Nothing new is deployed at the facility. The agent is a new *caller* of
services you already used by hand in `01_Facility_API/`.

```
    Claude Code / opencode           <-- session 04
            |
            |  MCP: "what tools do you have?"  /  "call submit_job(...)"
            v
      alcf_mcp.py  (this session)
            |
            |  HTTPS + Bearer token from alcf-tokens
            v
      ALCF Facility (IRI) API        <-- session 01
            |
            v
      Polaris / Crux
```

## Prerequisites

- A valid IRI token. Check with `alcf-tokens test-token iri`; if it is not
  ready, run
  `alcf-tokens login --authorize-transfer home --authorize-transfer eagle`.
- A coding agent installed and configured against the Inference Service, from
  Session 04:
  ```bash
  uvx alcf-ai agent configure claude     # or: configure opencode
  ```
- Your ALCF username and the reservation queue announced at the start of the
  workshop. The allocation is `alcf_training`.

| Script | Description |
|---|---|
| [`alcf_mcp.py`](alcf_mcp.py) | The MCP server: six IRI calls, exposed as agent tools |
| [`01_call_tools_directly.py`](01_call_tools_directly.py) | Connect as a client and see the tools the way a model sees them |
| [`skills/polaris-job/SKILL.md`](skills/polaris-job/SKILL.md) | An example skill: the judgment that does not belong in a tool |

---

## 1. What MCP actually buys you

You could paste the IRI docs into a prompt and ask the model to write `requests`
calls. People do. It works until it doesn't. MCP is worth the extra file for
three reasons:

- **Discovered, not hard-coded.** The agent asks the server what it can do. Add
  a tool to `alcf_mcp.py` and the agent can use it on the next launch — no
  prompt edit, no code change on the agent side.
- **Typed.** Each tool carries a JSON schema, so arguments are validated before
  anything leaves your laptop.
- **Scoped.** The server is a real boundary. `alcf_mcp.py` refuses any account
  other than `alcf_training`, more than 2 nodes, and walltimes over 30 minutes.
  Those are ordinary Python `raise` statements running before the HTTP request —
  the model cannot argue its way past them the way it can past an instruction in
  a prompt.

That last point is the one worth internalizing: **what you do not expose, the
agent cannot do.** The MCP server is where your judgment about blast radius
lives.

## 2. Look at the tools before you hand them over

```bash
uv run 01_call_tools_directly.py polaris
```

This launches `alcf_mcp.py` over stdio and performs the same handshake a coding
agent performs, then calls one tool. You should see the six tool names, their
arguments, and the first line of each docstring.

Read that output carefully. **The docstring is the tool description the model
reads** — it is the entire basis on which the model decides whether a tool is
relevant. A vague docstring is a bug, not a style problem.

## 3. Register the server with your agent

For Claude Code, from inside this directory:

```bash
claude mcp add alcf-iri -- uv run alcf_mcp.py
claude
```

Then ask the agent to confirm it can see the tools:

```
> What ALCF tools do you have available?
```

For opencode, add the equivalent block to `~/.config/opencode/opencode.jsonc`:

```jsonc
{
  "mcp": {
    "alcf-iri": {
      "type": "local",
      "command": ["uv", "run", "alcf_mcp.py"],
      "enabled": true
    }
  }
}
```

## 4. Exercise 1 — explore read-only

Start with questions that cannot cost you anything:

```
> What's the status of Polaris and Crux right now?
> How many jobs are queued under alcf_training on Polaris?
> Show me the last five completed jobs on Crux.
```

Watch what the agent actually does, not just what it answers:

- Which tool did it pick? Was it the cheapest one that could answer?
- Did it invent a resource ID, or call `get_system_status` and read one off?
- When you ask something the tools genuinely cannot answer, does it say so — or
  does it produce a confident, fluent, wrong answer?

Now try to break it. Ask about a system that does not exist. Ask for someone
else's jobs. Ask for a number the API never returns.

> **Why read-only first?** Not caution theatre. This is how you find out what
> the model assumes *before* one of those assumptions costs node-hours.

## 5. Exercise 2 — submit and monitor a real job

Write a trivial script somewhere on `/home/<your-username>/`:

```bash
cat > ~/hello_ses.sh <<'EOF'
echo "Running on $(hostname) at $(date)"
nvidia-smi --query-gpu=name --format=csv,noheader
EOF
```

Then ask, in plain language:

```
> Run ~/hello_ses.sh on 1 Polaris node under alcf_training in the
> reservation queue, write stdout to ~/hello_ses.out, and tell me when
> it's done.
```

The agent should resolve the account and queue, call `submit_job`, report the
job ID, poll `get_job_state`, and then `read_file` the output. Ask it to show
you the tool calls if your agent does not display them by default.

**Then make it fail on purpose.** Point `stdout_path` at `/tmp`, or ask for 8
nodes, or set the walltime to 5 seconds. What you are grading:

- Does it quote the actual error, or paraphrase it as "the job failed"?
- Does it name the specific line of stderr it read?
- Does it ask before resubmitting — or does it silently retry?

An agent that retries silently is not being helpful; it is spending your
allocation without telling you.

## 6. Exercise 3 — capture the correction as a skill

By now you have probably corrected the agent about the same thing two or three
times: use `alcf_training`, put stdout under `/home/`, do not resubmit without
asking. Retyping that every session is the actual cost of working this way.

A **skill** is a markdown file the agent loads on demand:

```
~/.claude/skills/
└── polaris-job/
    └── SKILL.md
```

Copy the example in and restart your agent:

```bash
mkdir -p ~/.claude/skills
cp -r skills/polaris-job ~/.claude/skills/
```

Open [`skills/polaris-job/SKILL.md`](skills/polaris-job/SKILL.md) and note what
is in it: a polling cadence, an escalation rule, a table of common failures.
None of that belongs in the MCP server — it is judgment, not plumbing.

The `description:` line in the frontmatter matters more than it looks. It is the
routing signal — the agent reads *only* the description when deciding whether to
load the skill at all. A description that does not name the situation will never
fire.

### Tools vs. skills

| | Tools (`alcf_mcp.py`) | Skills (`SKILL.md`) |
|---|---|---|
| What it is | Code the agent can run | Instructions the agent reads |
| Enforced? | Yes — Python, before the call | No — guidance the model can ignore |
| Put here | Capability and hard limits | Judgment, conventions, gotchas |
| Fails how | Raises an exception | Model decides not to follow it |

Put anything you actually need enforced in the tool, not the skill.

## 7. 🧪 Try it yourself

**Add a tool for your own workload.** Pick one thing you do by hand on Polaris
every week. Write it as a function in `alcf_mcp.py`, decorate it with
`@mcp.tool()`, write the docstring for the model, and relaunch. The agent finds
it with no other change.

**Add a guardrail and try to talk past it.** Restrict `submit_job` to a single
queue, then spend five minutes trying to convince the agent to use another one.
Then move the same restriction into `SKILL.md` instead and try again. The
difference between those two experiments is the whole argument for putting
limits in code.

**Chain two facilities.** `02_Globus_Compute_and_Transfer/` gives you a second
execution path. Expose a Globus Compute function as a tool alongside the IRI
tools and ask the agent to choose between them.

## Where this goes

The same pattern — one MCP server per service, an agent in front, skills for the
judgment — is what Trinity runs as a multi-user platform across ALCF, NERSC, and
OLCF. The architecture on this page does not change when you scale it up; only
the number of servers does.

And because the Inference Service speaks the same APIs as the Genesis Mission
Model Access Gateway (MAG), the same agent runs against AmSC facilities by
swapping the model endpoint. The IRI half is already shared.

## Further reading

- [ALCF IRI API documentation](https://docs.alcf.anl.gov/services/iri-api/)
- [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/)
- [Model Context Protocol specification](https://modelcontextprotocol.io)
- [FastMCP](https://gofastmcp.com)
