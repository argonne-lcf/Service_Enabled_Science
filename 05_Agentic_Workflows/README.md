# Agentic Workflows

**Huihuo Zheng** — AI/ML Group, Argonne Leadership Computing Facility
· [huihuo.zheng@anl.gov](mailto:huihuo.zheng@anl.gov)  
Service-Enabled Science Workshop, 30 September 2026

A coding agent is only as useful on HPC as what it can *see* and *do* there.
This session connects one to two **MCP servers** — a documentation server ALCF
already runs, and one you write yourself in front of the Facility API from
Session 01 — then teaches it your conventions with a *skill*.

**Goal** — leave with an agent that can answer "is Polaris up?", submit and
monitor a real job under `alcf_training`, and follow your local rules while
doing it, without you writing a REST call.

Session 03 ended with a challenge: *"Add a second tool. Write a new function to
leverage the IRI API, describe it in `TOOLS`, and register it in
`TOOL_FUNCTIONS`."* Session 04 pointed a coding agent at the ALCF Inference
Service so it could write code for you.

This session closes the loop. Instead of hand-registering tools inside one
script, we stand up an **MCP server** in front of the Facility API — and the
coding agent from Session 04 discovers every tool on it at startup.

Nothing new is deployed at the facility. The agent is a new *caller* of
services you already used by hand in `01_Facility_API/`.

The split between the two servers is the point: one that ALCF already runs and
you merely consume, and one you write to reach your own allocation.

```
                 Claude Code / opencode           <-- session 04
                     |              |
   MCP over HTTPS    |              |   MCP over stdio
   (no token)        |              |   ("call submit_job(...)")
                     v              v
  ask.alcf.anl.gov/mcp        alcf_mcp.py  (this session)
   ALCF/OLCF/NERSC docs             |
   -- knowledge                     |  HTTPS + Bearer token from alcf-tokens
                                    v
                            ALCF Facility (IRI) API   <-- session 01
                                    |
                                    v
                             Polaris / Crux
                             -- reach
```

**Knowledge** tells the agent how Polaris works; **reach** lets it act. A skill
supplies the third piece, judgment. Most of the frustration people have with
coding agents on HPC is one of those three being missing.

## Prerequisites

Section 2 needs **none of this** — it is a public endpoint. If your token is
not working yet, start there and sort out credentials while it runs.

- A valid IRI token. Check with `alcf-tokens test-token iri`; if it is not
  ready, run
  `alcf-tokens login --authorize-transfer home --authorize-transfer eagle`.
- A coding agent pointed at the Inference Service, from Session 04. If you
  skipped it, `uvx alcf-ai agent configure opencode` is enough. Check the agent
  launches and that `/models` lists an ALCF provider. **Pick a tool-calling
  model** — this session is nothing but tool calls, and a model without tool
  support will read the tool list and then ignore it.
- Your ALCF username and the reservation queue announced at the start of the
  workshop. The allocation is `alcf_training`.
- A **Globus personal endpoint** running on your own machine — see
  [below](#set-up-a-globus-personal-endpoint). Set this up before the session;
  it is the one prerequisite you cannot fix in thirty seconds.

| File | Description |
|---|---|
| [`00_ask_alcf_docs.py`](00_ask_alcf_docs.py) | Consume a remote MCP server ALCF already runs — no token required |
| [`ask_alcf_proxy.py`](ask_alcf_proxy.py) | A stdio forwarder to that server, for clients Cloudflare blocks (opencode) |
| [`alcf_mcp.py`](alcf_mcp.py) | The MCP server: six IRI calls and four Globus staging tools, exposed as agent tools |
| [`01_call_tools_directly.py`](01_call_tools_directly.py) | Connect as a client and see the tools the way a model sees them |
| [`skills/polaris-job/SKILL.md`](skills/polaris-job/SKILL.md) | An example skill: the judgment that does not belong in a tool |
| [`.mcp.json`](.mcp.json) | Both servers, pre-registered for Claude Code |
| [`opencode.jsonc`](opencode.jsonc) | The same two servers, for opencode |

## Setup

The repo-root [`setup.sh`](../setup.sh) covers this session too — it installs
`fastmcp`, `requests` and `rich` into the shared `.venv` alongside the ALCF
tooling, then checks both MCP servers import:

```bash
cd ..  && ./setup.sh && cd 05_Agentic_Workflows
```

Then start your agent **from this directory** and the two servers are already
registered:

```bash
claude      # or: opencode
```

> **Why the config points at `../.venv/bin/python` and not `uv run`.** Your
> agent spawns these servers as subprocesses and waits only a few seconds for
> the MCP handshake — opencode's default is 5 s. Measured here: launching from
> the pre-built `.venv` handshakes in **~0.5 s**, while a cold dependency
> resolve takes **~13 s** and blows the budget. That gap is the difference
> between "ten tools" and an unexplained "MCP server failed to start" —
> especially with a roomful of people hitting PyPI at once.

The scripts also carry PEP 723 headers, so `uv run 00_ask_alcf_docs.py` still
works standalone if you have not built the venv. That is fine when *you* are
waiting; it is not fine when an agent is.

Sections 2 and 4 walk through what the config files contain and how you would
have written them by hand — read them even though the wiring is done, because
the next server you add will be yours.

### Set up a Globus personal endpoint

Everything so far acts on things already at the facility. Later exercises go
the other way: the agent **generates input files on your machine and stages
them to ALCF**. For that, your machine has to be a Globus collection — which is
what Globus Connect Personal (GCP) makes it.

`02_Globus_Compute_and_Transfer/` transferred `eagle` → `home`, both facility
collections, so nothing there set this up. Do it now, not during the session:
it involves a browser login.

Download and unpack:

| Platform | Download |
|---|---|
| Linux | [`globusconnectpersonal-latest.tgz`](https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz) |
| macOS | [`globusconnectpersonal-latest.dmg`](https://downloads.globus.org/globus-connect-personal/mac/stable/globusconnectpersonal-latest.dmg) |
| Windows | [`globusconnectpersonal-latest.exe`](https://downloads.globus.org/globus-connect-personal/windows/stable/globusconnectpersonal-latest.exe) |

On Linux:

```bash
curl -LO https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz
tar xzf globusconnectpersonal-latest.tgz
cd globusconnectpersonal-*/
```

Register the collection. Go to
[app.globus.org/collections/gcp](https://app.globus.org/collections/gcp),
choose a name, and Globus hands you a **setup key**:

```bash
./globusconnectpersonal -setup <setup-key>
```

Then start it. GCP has to be **running** for a transfer to move anything — a
registered but stopped endpoint makes the transfer fail, not wait:

```bash
./globusconnectpersonal -start &
```

Verify both halves — the daemon, and what Globus thinks your UUID is:

```bash
./globusconnectpersonal -status      # expect: Globus Online: connected
globus endpoint local-id             # from the tutorial .venv
```

```
Globus Online:   connected
Transfer Status: idle
b8f4ffee-9799-11f1-b623-02ce27bde401
```

**Do not write that UUID down.** The MCP server resolves it the same way
`globus endpoint local-id` does — by reading `~/.globusonline/lta/client-id.txt`
— so nothing you commit ever contains it. A skill with a per-person UUID pasted
into it is a skill nobody else in the room can use, which defeats the point of
§4's "config is per project, and committed."

Finally, confirm your transfer consents cover the ALCF collections. This is the
same command as the first prerequisite, and it is idempotent:

```bash
alcf-tokens login --authorize-transfer home --authorize-transfer eagle
```

#### What your endpoint exposes is a guardrail

Started bare, GCP shares your **entire home directory, read-write**. You can
narrow that to a single staging directory at launch:

```bash
./globusconnectpersonal -start -restrict-paths rw~/ses-staging &
```

Do that once deliberately, because it is §1's argument one layer down: the
agent cannot read or write a path the endpoint does not publish, whatever the
model talks itself into. **The MCP server bounds what the agent can ask for;
the endpoint bounds what your machine will hand over.** Two independent limits,
and neither one is a sentence in a prompt that a model can reason its way past.

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

## 2. Start with a server you did not write

Before building one, consume one. ALCF runs a public MCP server at
**`https://ask.alcf.anl.gov/mcp`** that retrieves documentation across ALCF
(Polaris, Aurora, Sophia), OLCF (Frontier, Summit), NERSC (Perlmutter) and
LLNL, plus PBS, Slurm, CUDA, HIP, oneAPI, SYCL and OpenMP.

It needs no token and no account. The URL is the entire configuration — which
is why the Claude Code entry in [`.mcp.json`](.mcp.json) is four lines:

```json
"ask-alcf": { "type": "http", "url": "https://ask.alcf.anl.gov/mcp" }
```

Had you registered it by hand, it would be one command:

```bash
claude mcp add --transport http ask-alcf https://ask.alcf.anl.gov/mcp
```

Either way, launch the agent **from this directory** and ask:

```bash
claude      # or: opencode
```

```
> Using the ALCF docs, what queues can I submit to on Polaris,
> and what are the node and walltime limits on each?
```

> **Claude Code asks permission the first time.** A checked-in `.mcp.json` is
> executable configuration from a repo you cloned, so Claude Code prompts
> before starting those servers. Answer yes. If you are never prompted *and*
> the tools never appear, see [Troubleshooting](#troubleshooting).

To see the same handshake without an agent in the way:

```bash
../.venv/bin/python 00_ask_alcf_docs.py
../.venv/bin/python 00_ask_alcf_docs.py "How do I request 4 GPUs on Polaris?"
```

### ⚠️ If you are using opencode, use the proxy

The endpoint is behind Cloudflare, which accepts or rejects clients by TLS
fingerprint. As tested on 2026-09-27:

| Client | Direct to the URL |
|---|---|
| Claude Code (`--transport http`) | ✅ connects |
| Python — `fastmcp`, `httpx`, `requests` | ✅ connects |
| `curl` | ✅ connects |
| **opencode** | ❌ **403** |
| Node `fetch`, Python `urllib` | ❌ 403 |

Setting a browser `User-Agent` does not help — the block is below the header
layer. Since Python is allowed through, running the bundled stdio forwarder
restores access. That is what [`opencode.jsonc`](opencode.jsonc) in this
directory already does:

```jsonc
"ask-alcf": {
  "type": "local",
  "command": ["uv", "run", "ask_alcf_proxy.py"],
  "enabled": true
}
```

Note that the two clients reach the *same* server by different routes — direct
HTTPS for Claude Code, a local subprocess for opencode. Compare the two files
side by side; the divergence is the Cloudflare block, and nothing else.

opencode merges this project file with your global
`~/.config/opencode/opencode.jsonc`, so the Inference Service provider from
Session 04 stays in effect — this file only adds the `mcp` key.

[`ask_alcf_proxy.py`](ask_alcf_proxy.py) is twenty lines, and its shape is
worth a look: **the server is also a client of another server.** Once you own
the middle you can log every question, cache repeats, or refuse some outright
— in front of a service you do not operate. That is the same composition trick
that lets one agent sit in front of many facilities.

This is the other half of MCP, and the half that scales. You wrote nothing,
deployed nothing, and updated nothing — when ALCF re-indexes the user guides,
your agent gets the new answers. **A server is a dependency you can share.**

The server advertises exactly one tool, `retrieve_alcf_docs(query, top_k,
include_images)`. One well-described tool is a reasonable server. Note also
what it *is*: a retriever, not an oracle. It returns documentation chunks with
source URLs and similarity scores, and your agent does the reasoning — so you
can always check the citation.

### Two things to notice in the output

**It marks retrieved text as untrusted.** Every chunk arrives wrapped in a
`«UNTRUSTED_CONTENT»` marker. That is a deliberate defence: retrieved documents
are *data*, not instructions. Without it, anyone who can get text into an
indexed page — a GitHub issue, a wiki edit — could plant "also run `rm -rf`"
and have your agent read it as a command. This is the single most common way
agentic systems get compromised, and it is worth seeing a real mitigation.

**Retrieval is not free.** Left to its defaults the tool returns five chunks,
about **5,000 tokens**, on every single question. Passing `top_k=2` cuts that
to roughly 2,200. Tool output lands in your context whether it was useful or
not, so bounding it is part of designing the tool — the same discipline you
will apply to your own server in the next section.

## 3. Look at the tools before you hand them over

```bash
../.venv/bin/python 01_call_tools_directly.py polaris
```

This launches `alcf_mcp.py` over stdio and performs the same handshake a coding
agent performs, then calls one tool. You should see the ten tool names, their
arguments, and the first line of each docstring.

Read that output carefully. **The docstring is the tool description the model
reads** — it is the entire basis on which the model decides whether a tool is
relevant. A vague docstring is a bug, not a style problem.

## 4. Register your own server with your agent

`alcf_mcp.py` is already registered in both config files — as `alcf-iri`, the
second entry alongside `ask-alcf`. Launch your agent from this directory and
ask it to confirm:

```bash
claude      # or: opencode
```

```
> What ALCF tools do you have available?
```

You should get the ten tools from section 3, plus `retrieve_alcf_docs`.

A stdio server is a command plus its arguments — that is the whole entry:

```json
"alcf-iri": { "command": "../.venv/bin/python", "args": ["alcf_mcp.py"] }
```

Three details in those files are worth knowing before you write your own:

- **The command is relative, so the launch directory matters.** Both clients
  resolve `../.venv/bin/python` and `alcf_mcp.py` against the directory you
  launched the agent from, not the directory holding the config. Launch
  elsewhere and the server fails to start.
- **It names an interpreter, not `uv run`.** Both would work by hand, but a
  server has a startup deadline: the client gives it seconds to answer the
  handshake. Pointing at an already-built `.venv` means no resolving, no
  downloading, and no network at spawn time. Startup is a design constraint on
  an MCP server in a way it never is on a script.
- **Config is per project, and committed.** Anyone who clones this repo gets
  the same two servers. That is how a group shares an agent setup — not by
  passing a snippet around for people to paste into a dotfile.

If the tools do not show up, see [Troubleshooting](#troubleshooting) at the
bottom of this page.

## 5. Exercise 1 — explore read-only

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

## 6. Exercise 2 — submit and monitor a real job

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

### Now make it use both servers

With `ask-alcf` and `alcf-iri` both registered, ask a question that needs
knowledge *and* reach:

```
> Look up how Polaris schedules GPU jobs, then submit ~/hello_ses.sh
> accordingly under alcf_training. Cite the doc page you used.
```

A good run reads the documentation, picks `-l select=1:ngpus=4` or the
`filesystems` flag *because the docs said so*, submits, and cites the URL. This
is the smallest complete agentic workflow in the tutorial: retrieve, decide,
act, verify — with a checkable citation at the decision point.

Watch for the failure mode too. If the agent submits without ever calling
`retrieve_alcf_docs`, it is running on training-data memory of how Polaris
worked whenever the model was trained. Ask it which tool it called. Queue names
and limits change; the model's recollection of them does not.

## 7. Exercise 3 — generate locally, stage, then run

Everything so far acted on files already at ALCF. Real work rarely starts
there: you build inputs on your own machine and move them. That is the loop
this exercise adds — **generate → stage → verify → submit**.

Four more tools on `alcf_mcp.py` cover the middle two steps:

| Tool | What it does |
|---|---|
| `local_endpoint` | Returns your GCP collection ID, read from `~/.globusonline/lta/client-id.txt` |
| `globus_ls` | Lists a directory, `location="local"` or `location="alcf"` |
| `stage_to_alcf` | Copies local → `/home/…` or `/eagle/alcf_training/…`, returns a task ID |
| `transfer_status` | Polls that task ID until `SUCCEEDED` |

Make a sweep worth transferring — not one file, or `scp` would be the honest
answer:

```bash
mkdir -p ~/ses-staging/sweep
for t in 300 400 500 600 700 800; do
  printf 'temperature = %s\nsteps = 1000\n' "$t" > ~/ses-staging/sweep/run_$t.in
done
```

Then ask:

```
> Stage ~/ses-staging/sweep to my ALCF home directory, confirm all six
> input files arrived, and then run a job that cats each one.
```

**What you are grading is the verify step.** A correct run calls
`stage_to_alcf`, polls `transfer_status` until `SUCCEEDED`, and only then
submits. Globus returns a task ID the instant it accepts the request — the
bytes have not moved yet. An agent that treats "I got a task ID" as "the files
are there" submits a job against an empty directory, and the failure surfaces
minutes later in a PBS stderr file, looking like a job bug rather than a
staging bug.

To see it, make the sweep big enough that the transfer takes a few seconds, or
stop GCP (`./globusconnectpersonal -stop`) and watch whether the agent notices
the transfer never succeeds — or reports success anyway.

Two other things worth watching:

- **Did it look, or guess?** `globus_ls` exists so the agent can check a
  destination instead of inventing one. If it never calls it, the remote path
  came out of the model's head.
- **Did it discover its own endpoint?** `local_endpoint` resolves your GCP
  UUID at call time. An agent that asks *you* for the UUID has not read the
  tool list carefully.

> **Two path vocabularies, one tool surface.** A Globus collection is rooted at
> the filesystem it exports, so your `/home/you/run.in` is `/you/run.in` on the
> `home` collection — and the Globus collection UUIDs are a different namespace
> from the IRI filesystem UUIDs the other tools use. `alcf_mcp.py` translates
> both internally so every tool takes the same absolute POSIX path. That
> bookkeeping is exactly the kind of thing to put in a server once, rather than
> hope a model gets right on every call.

The staging tools carry their own guardrails, in the same style as
`submit_job`: writes to `eagle` must land under `/eagle/alcf_training/`, and a
transfer is refused above 500 files or 1 GiB. Neither limit is Globus's — both
are workshop policy, expressed as `raise`.

## 8. Exercise 4 — capture the correction as a skill

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

## 9. 🧪 Try it yourself

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

**Put a policy in the middle.** `ask_alcf_proxy.py` forwards to a server you do
not run. Add something to the forwarder: log every query to a file, cache
repeated ones, or prepend your group's local conventions to the result. This is
how you adopt a shared service without accepting it exactly as shipped.

## Troubleshooting

| Symptom | Cause |
|---|---|
| No tools appear, no permission prompt | You have `enabledMcpjsonServers` pinned in `~/.claude/settings.json`; a project `.mcp.json` server not named there is dropped silently. Add it, or set `"enableAllProjectMcpServers": true`. |
| `alcf-iri` fails to start, or times out | Either you never ran `./setup.sh`, or you launched the agent from another directory so `../.venv/bin/python` did not resolve. Run setup, `cd` here, relaunch. |
| `alcf-iri` starts, every tool 401s | Inference and IRI are separate tokens. Run `alcf-tokens test-token iri`. |
| `globus endpoint local-id` prints nothing or errors | GCP setup never completed — `~/.globusonline/lta/client-id.txt` is missing. Re-run `./globusconnectpersonal -setup <setup-key>`. |
| UUID resolves, but transfers fail immediately | The endpoint is registered and **stopped**. `./globusconnectpersonal -status` should say `connected`; if not, `./globusconnectpersonal -start &`. |
| Transfer fails with a consent or permission error | Missing `data_access` consent on the ALCF side. Re-run `alcf-tokens login --authorize-transfer home --authorize-transfer eagle`. |
| Transfer succeeds but the file is not where you expected | GCP paths are relative to what the endpoint publishes, not your shell's `cwd`. Check your `-restrict-paths` value. |
| `stage_to_alcf` returns a task ID, then the job finds no input files | The transfer had not finished. The tool returns when Globus *accepts* the task, not when bytes land — the agent must poll `transfer_status` to `SUCCEEDED` first. This is the failure section 7 is built around. |
| A staging tool raises a long "Globus needs an additional consent" message | Exactly what it says: run the `alcf-tokens login --authorize-transfer …` line in the error. The tool prints the scopes Globus asked for, so paste them into a support question if the login does not clear it. |
| `local_endpoint` raises but `./globusconnectpersonal -status` says connected | The agent's server is running as a different user, or with a different `$HOME`, than the GCP install. Both read `~/.globusonline/lta/client-id.txt`. |
| GCP will not install on ARM Linux | Globus ships no `aarch64` Linux build; the tarball is x86-64 only and needs emulation plus a 64-bit loader. Apple Silicon is fine — the macOS build handles it. |
| `ask-alcf` 403s under opencode | It is reaching the URL directly instead of the proxy — the global config is winning. Check `opencode.jsonc` here is being picked up. |
| Tools are listed but never called | Your model is not tool-capable. Switch with `/models` and pick one the Inference Service advertises tool support for. |

## Where this goes

The same pattern — one MCP server per service, an agent in front, skills for the
judgment — is what Trinity runs as a multi-user platform across ALCF, NERSC, and
OLCF. The architecture on this page does not change when you scale it up; only
the number of servers does.

And because the Inference Service speaks the same APIs as the Genesis Mission
Model Access Gateway (MAG), the same agent runs against AmSC facilities by
swapping the model endpoint. The IRI half is already shared.

## Further reading

- [ask.alcf.anl.gov](https://ask.alcf.anl.gov) — the docs assistant; `/mcp` is the same knowledge base as a tool
- [ALCF IRI API documentation](https://docs.alcf.anl.gov/services/iri-api/)
- [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/)
- [Model Context Protocol specification](https://modelcontextprotocol.io)
- [FastMCP](https://gofastmcp.com)
