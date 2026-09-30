# Agentic Workflows

**Huihuo Zheng** — AI/ML Group, Argonne Leadership Computing Facility
· [huihuo.zheng@anl.gov](mailto:huihuo.zheng@anl.gov)  
Service-Enabled Science Workshop, 30 September 2026

**Slides** — [`slides.pdf`](slides.pdf)

A coding agent is only as useful on HPC as what it can *see* and *do* there.
This session connects one to a single **MCP server** carrying three groups of
tools — facility documentation, Globus data transfer, and the IRI compute API
from Session 01 — then teaches it your conventions with a *skill*.

**Goal** — leave with an agent that can answer "is Polaris up?", stage a file
from your laptop to `/eagle`, submit and monitor a real job under
`alcf_training`, and follow your local rules while doing it, without you
writing a REST call.

Session 03 ended with a challenge: *"Add a second tool. Write a new function to
leverage the IRI API, describe it in `TOOLS`, and register it in
`TOOL_FUNCTIONS`."* Session 04 pointed a coding agent at the ALCF Inference
Service so it could write code for you.

This session closes the loop. Instead of hand-registering tools inside one
script, we stand up an **MCP server** in front of those services — and the
coding agent from Session 04 discovers every tool on it at startup.

Nothing new is deployed at the facility. The agent is a new *caller* of
services you already used by hand in `01_Facility_API/` and
`02_Globus_Compute_and_Transfer/`.

```
              Claude Code / opencode              <-- session 04
                          |
                          |  MCP over stdio  ("call submit_job(...)")
                          v
                    alcf_mcp.py                   <-- this session
                          |
          +---------------+---------------+
          |               |               |
      docs.py         globus.py         iri.py
      1 tool          4 tools           6 tools
          |               |               |
          v               v               v
  ask.alcf.anl.gov   Globus Transfer   ALCF Facility (IRI) API
   -- knowledge       -- data           -- reach          <-- session 01
                          |               |
                          +-------+-------+
                                  v
                           Polaris / Crux
```

**Knowledge** tells the agent how Polaris works; **data** gets your inputs
there; **reach** lets it act. A skill supplies the fourth piece, judgment. Most
of the frustration people have with coding agents on HPC is one of those four
being missing.

| File | Description |
|---|---|
| [`alcf_mcp.py`](alcf_mcp.py) | The MCP server — mounts all three tool groups into one |
| [`alcf_tools/docs.py`](alcf_tools/docs.py) | ALCF Knowledge base: `retrieve_alcf_docs` (1 tool, no token) |
| [`alcf_tools/globus.py`](alcf_tools/globus.py) | Globus data transfer: staging local → ALCF (4 tools) |
| [`alcf_tools/iri.py`](alcf_tools/iri.py) | ALCF IRI: PBS submit / poll / read (6 tools) |
| [`alcf_tools/common.py`](alcf_tools/common.py) | Facility IDs, path translation, and the guardrails |
| [`00_ask_alcf_docs.py`](00_ask_alcf_docs.py) | Consume the remote MCP server ALCF already runs — no token required |
| [`01_call_tools_directly.py`](01_call_tools_directly.py) | Connect as a client and see the tools the way a model sees them |
| [`skills/submit-job/SKILL.md`](skills/submit-job/SKILL.md) | The skill: the judgment that does not belong in a tool |
| [`mnist_pytorch.py`](mnist_pytorch.py) | The training script for Example 3 |
| [`.mcp.json`](.mcp.json) | The server, pre-registered for Claude Code |
| [`opencode.jsonc`](opencode.jsonc) | The same server, for opencode |
| [`AGENTS.md`](AGENTS.md) | Always-loaded rules for whichever agent you run here |
| [`CLAUDE.md`](CLAUDE.md) | Imports `AGENTS.md`, so Claude Code and opencode cannot drift |

---

## Step 1 — Agent core and credentials

One clone, one login, one configure. Run these in order:

```bash
git clone https://github.com/argonne-lcf/Service_Enabled_Science.git
cd Service_Enabled_Science
./setup.sh
source .venv/bin/activate

alcf-tokens login \
  --authorize-transfer home \
  --authorize-transfer eagle
alcf-tokens test-token inference
# {"ready": true, "error": null}

uvx alcf-ai agent configure claude    # ...or: configure opencode
```

What each line buys you:

- **`./setup.sh`** installs `uv`, builds the shared `.venv` with `fastmcp`,
  `alcf-tokens`, `globus-sdk`, `requests` and `rich`, and checks the MCP server
  imports.
- **`alcf-tokens login`** opens a browser. Pick the **Argonne LCF** provider
  and paste the code back. The two `--authorize-transfer` flags are what let
  the agent write to `/home/` and `/eagle/` later — grant them now, not in
  Step 2.
- **`alcf-tokens test-token`** is the only proof a token works. Do it before
  anything else fails confusingly. The IRI half is a separate token:
  `alcf-tokens test-token iri`.
- **`alcf-ai agent configure`** points the agent at the ALCF Inference Service.
  **Pick a tool-calling model** — this session is nothing but tool calls, and a
  model without tool support will read the tool list and then ignore it. Check
  with `/model` (`/models` on opencode) once the agent is up — see
  [Step 3](#step-3--first-contact-with-your-agent).

You also need your ALCF username and the reservation queue announced at the
start of the workshop. The allocation is `alcf_training`.

Then start your agent **from this directory** and the server is already
registered:

```bash
cd 05_Agentic_Workflows
claude      # or: opencode
```

> **Why the config points at `../.venv/bin/python` and not `uv run`.** Your
> agent spawns the server as a subprocess and waits only a few seconds for the
> MCP handshake — opencode's default is 5 s. Measured here: launching from the
> pre-built `.venv` handshakes in **~0.5 s**, while a cold dependency resolve
> took **~4 s** and pulled **104 MB** — inside the 5 s budget on a good link,
> but with no margin, and that 104 MB is per person. With a roomful of people
> hitting PyPI at once it is the difference between "eleven tools" and an
> unexplained "MCP server failed to start".

The scripts also carry PEP 723 headers, so `uv run 00_ask_alcf_docs.py` still
works standalone if you have not built the venv. That is fine when *you* are
waiting; it is not fine when an agent is.

## Step 2 — Globus data transfer

Sessions 01–04 only ever acted on things already at the facility. This session
goes the other way: the agent **generates input files on your machine and
stages them to ALCF**. For that, your machine has to be a Globus collection —
which is what Globus Connect Personal (GCP) makes it.

`02_Globus_Compute_and_Transfer/` transferred `eagle` → `home`, both facility
collections, so nothing there set this up. Do it before the session, not
during: it involves a browser login.

### Set up a Globus personal endpoint

Three commands on Linux. On macOS and Windows, GCP ships as a GUI application
that does the same three steps itself. All three builds come from the same base
URL, `https://downloads.globus.org/globus-connect-personal/<os>/stable/`:

| OS | File | How you set it up |
|---|---|---|
| Linux | [`.tgz`](https://downloads.globus.org/globus-connect-personal/linux/stable/globusconnectpersonal-latest.tgz) (132 MB) | run `./globusconnectpersonal`; text prompts if there is no display |
| macOS | [`.dmg`](https://downloads.globus.org/globus-connect-personal/mac/stable/globusconnectpersonal-latest.dmg) (57 MB) | drag to Applications, launch, click **Log In** |
| Windows | [`.exe`](https://downloads.globus.org/globus-connect-personal/windows/stable/globusconnectpersonal-latest.exe) (84 MB) | run the installer; GCP launches, click **Log In** |

**1. Download and unpack.**

```bash
GCP=https://downloads.globus.org/globus-connect-personal/linux/stable
wget $GCP/globusconnectpersonal-latest.tgz    # 132 MB
tar xzf globusconnectpersonal-latest.tgz && cd globusconnectpersonal-*/
```

**2. Run the guided setup.** The first launch *is* setup, not the application:

```bash
./globusconnectpersonal        # prompts for login, then a collection name
```

It prints a URL, takes an auth code back, and asks what to call the collection.
There is no separate `globus login` and no setup key to paste — GCP does its
own registration. (`globus gcp create mapped` is an alternative that *produces*
a setup key for `-setup <key>`; it exists for scripted installs, and you do not
need it here.)

**3. Start it.**

```bash
./globusconnectpersonal -start &
```

GCP has to be **running** for a transfer to move anything — a registered but
stopped endpoint makes the transfer fail, not wait. On macOS and Windows it is
a menu-bar / tray application, so launching it is starting it. Everything after
this — the test below, and every tool call in the session — is identical on all
three.

### Test it before you trust it

Registered, installed and started are three different things, and each can
succeed while the next has not:

```bash
./globusconnectpersonal -status
```

```
Globus Online: connected
```

`connected` means the endpoint is registered *and* the local process is
reaching the Globus service. Anything else maps to a row in
[Troubleshooting](#troubleshooting):

| What you get | What it means |
|---|---|
| `Globus Online: disconnected` | The process is up but cannot reach Globus — check egress or proxy |
| Nothing, or a "not set up" message | The guided setup in step 2 never completed |
| `command not found` | You are not inside the unpacked `globusconnectpersonal-*/` directory |

That checks the endpoint, not any particular directory. If you want an
end-to-end check that a path is actually published, authenticate the `globus`
CLI once — it keeps its own tokens, separate from `alcf-tokens` — and list it:

```bash
globus login --no-local-server                  # prints a URL; paste the code
globus ls "$(globus endpoint local-id):/~/"
```

**Do not write that UUID down.** The `local_endpoint` tool resolves it the same
way `globus endpoint local-id` does — by reading
`~/.globusonline/lta/client-id.txt` — so nothing you commit ever contains it,
and you never paste a collection UUID into the chat. A skill with a per-person
UUID in it is a skill nobody else in the room can use, which defeats the point
of ["config is per project, and
committed"](#register-the-server-with-your-agent).

The ALCF side was already granted in Step 1. If you skipped those flags, the
command is idempotent — run it now:

```bash
alcf-tokens login --authorize-transfer home --authorize-transfer eagle
```

### Make somewhere to put the files

The endpoint is one half of a transfer; the other half is a destination that
exists. `/eagle/alcf_training/` is the workshop project directory, but your
personal subdirectory under it is not created for you, and a transfer into a
path that does not exist fails at delivery rather than at submission — minutes
later, in a Globus task error rather than in your terminal. Create it once:

```bash
ssh <you>@polaris.alcf.anl.gov 'mkdir -p /eagle/alcf_training/$USER'
```

Single quotes matter: `$USER` has to expand on Polaris, not on your laptop,
where it is very likely a different name. This is the only time in the session
you log into Polaris by hand — everything after it goes through the agent.

That per-user directory is not a convention you can skip. Everything staged to
eagle has to land under `/eagle/<project>/<user>/`, and `stage_to_alcf` refuses
anything shallower — see `_check_eagle_destination` in
[`alcf_tools/common.py`](alcf_tools/common.py). The project directory is group
writable, so without it a room of thirty people staging `train.py` in the same
half hour overwrite each other, and the filesystem is perfectly happy to let
them. Pass the full destination path including the filename
(`…/<you>/mnist_pytorch.py`), not the directory it goes in.

What that check does *not* do is confirm `<user>` is you. The server has no
trustworthy way to know your ALCF username — it is often not your laptop
username — and guessing wrong would block a real transfer in the middle of the
session. It enforces the layout; the filesystem's own permissions are what
enforce identity.

### What your endpoint exposes is a guardrail

Started bare — `./globusconnectpersonal -start &`, with no other flag — GCP
shares your **entire home directory, read-write**. That is the default, and it
is what the three commands above leave you with. Know it rather than discover
it.

To narrow the share, put one path per line in
`~/.globusonline/lta/config-paths` with its read/write flags and restart GCP;
`./globusconnectpersonal -start -restrict-paths rw~/ses-staging &` does the
same thing from the command line. Worth doing on a machine that holds anything
you would not hand to a transfer service.

Set it deliberately, because it is [the next
section's](#what-mcp-actually-buys-you) argument one layer down: the agent
cannot read or write a path the endpoint does not publish, whatever the model
talks itself into. **The MCP server bounds what the agent can ask for; the
endpoint bounds what your machine will hand over.** Two independent limits, and
neither one is a sentence in a prompt that a model can reason its way past.

---

## What MCP actually buys you

You could paste the IRI docs into a prompt and ask the model to write `requests`
calls. People do. It works until it doesn't. MCP is worth the extra file for
three reasons:

- **Discovered, not hard-coded.** The agent asks the server what it can do. Add
  a tool to `alcf_tools/` and the agent can use it on the next launch — no
  prompt edit, no code change on the agent side.
- **Typed.** Each tool carries a JSON schema, so arguments are validated before
  anything leaves your laptop.
- **Scoped.** The server is a real boundary. `submit_job` refuses any account
  other than `alcf_training`, more than 2 nodes, and walltimes over 30 minutes;
  `stage_to_alcf` refuses more than 500 files or 1 GiB, and refuses eagle
  writes outside `/eagle/<project>/<user>/`. Those are ordinary Python `raise`
  statements running before the HTTP request — the model cannot argue its way
  past them the way it can past an instruction in a prompt. They all live in
  one place, [`alcf_tools/common.py`](alcf_tools/common.py).

That last point is the one worth internalizing: **what you do not expose, the
agent cannot do.** The MCP server is where your judgment about blast radius
lives.

## One server, three tool groups

Every server you register is another entry to configure, another process to
launch, and another thing that can fail on an unfamiliar network. So this
session ships **one** server with eleven tools, split into three modules that
[`alcf_mcp.py`](alcf_mcp.py) mounts:

```
alcf_mcp.py    mounts all three
alcf_tools/
  __init__.py  the tool map
  common.py    IDs, paths, guardrails
  docs.py      1 tool   ALCF Knowledge base
  globus.py    4 tools  data transfer
  iri.py       6 tools  compute
skills/
  submit-job/SKILL.md   the chain
```

Mounting without a namespace keeps the tool names plain: the agent sees
`submit_job`, not `iri_submit_job`, and the split is invisible from the
outside.

### Group 1 — ALCF Knowledge base (no token)

ALCF runs a public MCP server at **`https://ask.alcf.anl.gov/mcp`** that
retrieves documentation across ALCF (Polaris, Aurora, Sophia), OLCF (Frontier,
Summit), NERSC (Perlmutter) and LLNL, plus PBS, Slurm, CUDA, HIP, oneAPI, SYCL
and OpenMP. It needs no token and no account — the URL is the entire
configuration.

[`alcf_tools/docs.py`](alcf_tools/docs.py) does not register it as a second
server. It is a **client** of that server and re-exposes its one tool here:

```python
@mcp.tool()
async def retrieve_alcf_docs(query: str, top_k: int = 3) -> str:
    """Search ALCF, OLCF, NERSC and LLNL documentation, plus PBS, Slurm,
    CUDA, HIP, oneAPI, SYCL and OpenMP. ..."""
    async with Client(ASK_ALCF) as upstream:
        result = await upstream.call_tool("retrieve_alcf_docs", {...})
```

**The server is also a client of another server.** That is the composition
trick worth keeping. Once you own the middle you can log every question, cache
repeats, or refuse some outright — in front of a service you do not operate.
It is the same move that lets one agent sit in front of many facilities.

It also buys three concrete things here:

- **One entry in `.mcp.json` instead of two.**
- **No token for this tool**, even though its neighbours all need one. Nothing
  in `docs.py` touches `alcf-tokens`, so it answers before you have logged in.
- **It routes around Cloudflare.** See below.

To see the upstream handshake without an agent or this server in the way:

```bash
../.venv/bin/python 00_ask_alcf_docs.py
../.venv/bin/python 00_ask_alcf_docs.py "How do I request 4 GPUs on Polaris?"
```

#### ⚠️ Why going through Python matters: the Cloudflare edge

`ask.alcf.anl.gov` sits behind Cloudflare, which accepts or rejects clients by
**TLS fingerprint** rather than by anything in the request. Measured from one
network on 2026-09-28:

| Client | Direct to the URL |
|---|---|
| Claude Code (`--transport http`) | ✅ connects |
| opencode 1.18.18 | ✅ connects |
| `curl` | ✅ 200 |
| Python — `fastmcp`, `httpx`, `requests` | ✅ 200 |
| Node `fetch` | ❌ 403 |
| Python `urllib` | ❌ 403 |
| `curl` **with a browser `User-Agent`** | ❌ 403 |

Two things worth drawing out, because both are counter-intuitive:

- **A browser `User-Agent` makes things worse, not better.** Plain `curl` gets
  200; the same `curl` with a Chrome UA gets 403, reproducibly. The edge is
  comparing the claimed header against the TLS handshake, and a mismatch is
  more suspicious than an honest CLI.
- **You cannot infer a client from its runtime.** opencode is Bun-compiled, so
  the Node `fetch` result above does *not* predict it — opencode connects fine.
  Test the client you will actually run.

Both supported agents *can* reach the server directly, and an earlier version
of this session registered it as a second `http` entry. Reaching it through
`docs.py` instead means the Cloudflare edge only ever sees Python's HTTP stack,
which it accepts — for **every** client, including ones that would be 403'd.
When a remote MCP endpoint is unreachable from your client but reachable from
*some* runtime you have, wrapping it in a server you already run recovers it
without touching the server.

#### Two things to notice in the output

**It marks retrieved text as untrusted.** Every chunk arrives wrapped in a
`«UNTRUSTED_CONTENT»` marker. That is a deliberate defence: retrieved documents
are *data*, not instructions. Without it, anyone who can get text into an
indexed page — a GitHub issue, a wiki edit — could plant "also run `rm -rf`"
and have your agent read it as a command. This is the single most common way
agentic systems get compromised, and it is worth seeing a real mitigation.

**Retrieval is not free.** Left to its defaults the upstream tool returns five
chunks, about **5,000 tokens**, on every single question. `docs.py` defaults
`top_k=3` and caps it at 5 for exactly that reason. Tool output lands in your
context whether it was useful or not, so bounding it is part of designing the
tool.

Note also what this is: a **retriever, not an oracle.** It returns
documentation chunks with source URLs and similarity scores, and your agent
does the reasoning — so you can always check the citation.

### Group 2 — Globus data transfer (4 tools)

| Tool | What it does |
|---|---|
| `local_endpoint` | Returns your GCP collection ID, read from `~/.globusonline/lta/client-id.txt` |
| `globus_ls` | Lists a directory, `location="local"` or `location="alcf"` |
| `stage_to_alcf` | Copies local → `/home/…` or `/eagle/alcf_training/<you>/…`, returns a task ID |
| `transfer_status` | Polls that task ID until `SUCCEEDED` |

The docstring on `stage_to_alcf` is doing real work:

```python
@mcp.tool()
def stage_to_alcf(local_path: str, alcf_path: str, recursive=False) -> dict:
    """Copy a local file to ALCF.

    Returns as soon as Globus accepts the task -- the bytes have NOT moved
    yet. Poll transfer_status until SUCCEEDED before submitting.
    """
```

That warning is the failure this group exists to teach. Globus returns a task
ID the instant it *accepts* the request. An agent that treats "I got a task ID"
as "the files are there" submits a job against an empty directory, and the
failure surfaces minutes later in a PBS stderr file, looking like a job bug
rather than a staging bug.

> **Two path vocabularies, one tool surface.** A Globus collection is rooted at
> the filesystem it exports, so your `/home/you/run.in` is `/you/run.in` on the
> `home` collection — and the Globus collection UUIDs are a different namespace
> from the IRI filesystem UUIDs the compute tools use. `common.py` translates
> both internally so every tool takes the same absolute POSIX path. That
> bookkeeping is exactly the kind of thing to put in a server once, rather than
> hope a model gets right on every call.

### Group 3 — ALCF IRI for compute (6 tools)

These wrap the same Session-01 REST calls you made by hand.

| Tool | What it does |
|---|---|
| `get_system_status` | Polaris / Crux up? Current reservations |
| `submit_job` | Submit a PBS job via IRI, return its ID. Prepends the proxy + conda preamble unless `setup_env=False` |
| `get_job_state` | Poll one job |
| `list_jobs` | Filter by state, queue, owner; `historical=True` for finished jobs |
| `cancel_job` | Stop a run |
| `read_file` | Fetch stdout / stderr |

```python
@mcp.tool()
def submit_job(system: str, commands: str, stdout_path: str, nodes=1,
               queue="debug", account="alcf_training",
               walltime_sec=600) -> dict:
    """Submit a PBS job, return its ID.

    Refuses accounts outside the workshop allocation, >2 nodes, or
    walltimes over 30 minutes.
    """
```

**The docstring *is* the tool description the model reads** — it is the entire
basis on which the model decides whether a tool is relevant. A vague docstring
is a bug, not a style problem.

## Look at the tools before you hand them over

```bash
../.venv/bin/python 01_call_tools_directly.py polaris
```

This launches `alcf_mcp.py` over stdio and performs the same handshake a coding
agent performs, then calls one tool. You should see all **eleven** tool names,
their arguments, and the first line of each docstring.

Read that output carefully. It is what the model sees, and nothing else.

## Register the server with your agent

`alcf_mcp.py` is already registered in both config files, as `alcf-mcp`. Launch
your agent from this directory and ask it to confirm:

```bash
claude      # or: opencode
```

```
> What ALCF tools do you have available?
```

You should get all eleven. A stdio server is a command plus its arguments —
that is the whole entry:

```json
"alcf-mcp": {
  "type": "stdio",
  "command": "../.venv/bin/python",
  "args": ["alcf_mcp.py"]
}
```

> **Claude Code asks permission the first time.** A checked-in `.mcp.json` is
> executable configuration from a repo you cloned, so Claude Code prompts
> before starting the server. Answer yes. If you are never prompted *and* the
> tools never appear, see [Troubleshooting](#troubleshooting).

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
  the same server. That is how a group shares an agent setup — not by passing a
  snippet around for people to paste into a dotfile.

[`opencode.jsonc`](opencode.jsonc) is the same server for opencode, with one
extra key: `"timeout": 30000`. opencode's default is 5 s, and a documentation
call still has to reach `ask.alcf.anl.gov`. opencode merges this project file
with your global `~/.config/opencode/opencode.jsonc`, so the Inference Service
provider from Session 04 stays in effect — this file only adds the `mcp` key.

If the tools do not show up, see [Troubleshooting](#troubleshooting) at the
bottom of this page.

## Capture the chain: the `submit-job` skill

The tools exist. Something has to say in what *order* to use them — and by the
third job you will have corrected the agent about the same thing two or three
times: poll the transfer before submitting, put stdout somewhere writable, do
not resubmit without asking. Retyping that every session is the actual cost of
working this way.

A **skill** is where it goes instead.

- **A repeatable workflow, written down** — the steps you would otherwise
  retype every session.
- **Just a markdown file** — it diffs, reviews and ships like any other
  artifact.
- **The `description:` routes it** — the agent reads *only* that line when
  deciding whether to load the skill at all. A description that does not name
  the situation will never fire.

[`skills/submit-job/SKILL.md`](skills/submit-job/SKILL.md) spans the whole
chain in five stages:

```yaml
---
name: submit-job
description: Generate, stage over Globus, submit via IRI, monitor, report back.
---
1. Generate the input locally; show it.
2. stage_to_alcf -> /eagle/<project>/<user>/
   Wait for SUCCEEDED. Never assume.
3. get_system_status, then submit_job.
4. Poll with backoff: 10s, then 30s.
5. Quote the stderr line, propose a fix, never resubmit on your own.
```

Claude Code picks it up from this directory automatically. To make it available
everywhere:

```bash
mkdir -p ~/.claude/skills
cp -r skills/submit-job ~/.claude/skills/
```

Open the file and note what is in it: a polling cadence, an escalation rule, a
table of common failures, the multi-node `mpiexec` gotcha. None of that belongs
in the MCP server — it is judgment, not plumbing.

### Tools vs. skills

| | Tools (`alcf_tools/`) | Skills (`SKILL.md`) |
|---|---|---|
| What it is | Code the agent can run | Instructions the agent reads |
| Enforced? | Yes — Python, before the call | No — guidance the model can ignore |
| Put here | Capability and hard limits | Judgment, conventions, gotchas |
| Fails how | Raises an exception | Model decides not to follow it |

Put anything you actually need enforced in the tool, not the skill.

---

## Step 3 — First contact with your agent

Everything up to here was setup and reading. Launch the agent and look around
before you spend a single tool call:

```bash
source .venv/bin/activate
claude                       # or: opencode
# [shift + tab] -> auto mode
```

Then, in the session:

```
> What model are you?

/model    # what is actually configured
/mcp      # the server and its tools
```

On opencode the equivalents are `/models` and `/mcp`.

Then ask it something it cannot answer on its own:

```
> How many nodes does Polaris have? What queues can I use?
```

Four things to notice:

- **Its answer is a guess.** A model names itself from training data — often
  confidently, sometimes wrongly, and never from your config. `/model` reads
  the configuration. *Ask the system, not the model* is the same discipline
  every example below is built on.
- **`/mcp` is the real check.** If `alcf-mcp` is not listed there with its
  eleven tools, nothing after this section will work — go to
  [Troubleshooting](#troubleshooting) before continuing.
- **The Polaris question calls a tool.** It should be answered by
  `retrieve_alcf_docs`, reading ALCF's live documentation. If no tool call
  appears and you just get a number, you got training data — and the node
  count, the queue names and the walltime limits have all changed since then.
  A confident, sourceless answer here is the failure mode this whole session
  is about.
- **Auto mode stops asking.** Shift+Tab cycles Claude Code's permission mode,
  and turning the confirmation prompt off is exactly why the limits that
  matter live in the server rather than in your reflexes. This is the same
  argument as ["what you do not expose, the agent cannot
  do"](#what-mcp-actually-buys-you), now with the safety net removed.

## Example 1 — check system status

Read-only. Nothing here costs node-hours, which is the point: this is how you
find out what the model assumes *before* one of those assumptions bills your
allocation.

```
> What's the status of Polaris and Crux right now? How many jobs are
> queued on Polaris, and what were the last five jobs to finish on Crux?
```

The calls it should make — watch which, and in what order:

```python
get_system_status(system="polaris")      # up / down, current reservations
get_system_status(system="crux")
list_jobs(system="polaris", states=["queued"])
list_jobs(system="crux", limit=5, historical=True)
```

**What to watch for.** It should *list* resources before naming one. An
invented resource ID is the first failure mode. Ask it to show you the tool
calls if your agent does not display them by default.

**Try to break it.** Ask about a system that does not exist. Ask for someone
else's jobs. Ask for a number the API never returns. A good answer is "I can't
tell you that."

## Example 2 — a two-node smoke test

The smallest job that proves the whole chain works.

```
> Run a 2-node smoke test on Polaris under alcf_training, in reservation
> R7645913, that prints the hostname of every node, then show me the output
> when it lands.
```

The chain it runs:

```python
submit_job(system="polaris", nodes=2,
           commands="mpiexec -n 2 --ppn 1 hostname",
           queue="R7645913",              # the workshop reservation
           account="alcf_training",
           walltime_sec=600,
           stdout_path="/home/<you>/smoke.out")
get_job_state(system="polaris", job_id=...)   # poll
read_file(path="/home/<you>/smoke.out")
```

**On how short `commands` is.** It is the work and nothing else. ALCF compute
nodes have no direct route off-site and `python` needs conda brought up, but
neither of those belongs in a prompt: `submit_job` prepends both before the
job goes out — see [`job_preamble()`](alcf_tools/common.py), and
[Example 3](#example-3--train-mnist-on-polaris) for what it contains and why.
`hostname` needs none of it; the point is that you get the same environment
whether or not the agent thought to ask for one.

**On the reservation.** In PBS a reservation *is* a queue name, so `R7645913`
goes in `queue=` — there is no separate flag for it. During the workshop this
is what gets your job onto a node without waiting behind the general queue.
Outside the reservation window it will not run; fall back to `queue="debug"`.

No script to stage — the commands travel in the job spec. And plain `hostname`
prints the head node *once*: two nodes allocated is not two nodes used.
`mpiexec -n 2 --ppn 1` is what makes the second one answer. If the agent
submits bare `hostname` and then reports "both nodes responded", it is reading
one line and telling you about two.

**Then make it fail on purpose.** Point `stdout_path` at `/tmp`, ask for 3
nodes, or set the walltime to 5 seconds. What you are grading:

- Does it quote the actual error, or paraphrase it as "the job failed"?
- Does it name the specific line of stderr it read?
- Does it ask before resubmitting — or does it silently retry?

An agent that retries silently is not being helpful; it is spending your
allocation without telling you.

Ask for three nodes and the *server* says no, not the model: `MAX_NODES = 2`
lives in [`common.py`](alcf_tools/common.py), not in your prompt.

### Now make it use the knowledge base too

Ask a question that needs knowledge *and* reach:

```
> Look up how Polaris schedules GPU jobs, then run the smoke test
> accordingly under alcf_training. Cite the doc page you used.
```

A good run reads the documentation, picks the queue or `filesystems` flag
*because the docs said so*, submits, and cites the URL. This is the smallest
complete agentic workflow in the tutorial: retrieve, decide, act, verify — with
a checkable citation at the decision point.

Watch for the failure mode too. If the agent submits without ever calling
`retrieve_alcf_docs`, it is running on training-data memory of how Polaris
worked whenever the model was trained. Ask it which tool it called. Queue names
and limits change; the model's recollection of them does not.

## Example 3 — train MNIST on Polaris

The first example where the file does not already exist at ALCF. One prompt,
all three tool groups.

```
> Stage mnist_pytorch.py to my eagle space, train on one Polaris node in
> reservation R7645913, and report the test accuracy.
```

The chain it runs:

```python
stage_to_alcf(
  local_path="~/mnist_pytorch.py",
  alcf_path="/eagle/alcf_training/<you>/mnist_pytorch.py")
transfer_status(task_id=...)      # poll to SUCCEEDED before submitting
submit_job(system="polaris", nodes=1,
           commands="python /eagle/alcf_training/<you>/mnist_pytorch.py",
           walltime_sec=1800,
           queue="R7645913",      # the workshop reservation
           stdout_path="/eagle/alcf_training/<you>/mnist.out")
get_job_state(...)                # poll to completion
read_file("/eagle/alcf_training/<you>/mnist.out")
```

At 30 minutes of walltime this is the longest job in the session, so it is the
one that most needs the reservation — see
[Example 2](#example-2--a-two-node-smoke-test) for why `R7645913` goes in
`queue=` rather than a flag of its own. Outside the window, `queue="debug"`.

[`mnist_pytorch.py`](mnist_pytorch.py) is a plain single-GPU PyTorch script —
three epochs by default, well inside the 30-minute walltime ceiling.

Notice how little `commands` contains. The interesting part is the block you
*don't* write: `submit_job` prepends this to every job, from
[`job_preamble()`](alcf_tools/common.py):

```bash
export http_proxy=http://proxy.alcf.anl.gov:3128
export https_proxy=http://proxy.alcf.anl.gov:3128
module use /soft/modulefiles || true
module load conda/2026-10-01 || true
_ses_conda_base="$(command -v conda >/dev/null 2>&1 && conda info --base 2>/dev/null)" || true
[ -n "$_ses_conda_base" ] || _ses_conda_base="/soft/applications/conda/2026-10-01/mconda3"
[ -r "$_ses_conda_base/etc/profile.d/conda.sh" ] \
  && . "$_ses_conda_base/etc/profile.d/conda.sh" && conda activate base || true
command -v python >/dev/null 2>&1 || {
  echo "preamble: python is not on PATH after loading conda/2026-10-01." >&2
  ...
}
```

Every line exists because of something that fails *quietly*. That is also the
reason they live in the *server* rather than in the skill: a prompt that has to
be remembered is a prompt that will eventually be forgotten.

- **Compute nodes have no direct internet.** The first run downloads MNIST, and
  that hangs until the walltime kills it — no error, no output — without the
  proxy exports. Note the literal value twice: writing
  `export http_proxy=... https_proxy=$http_proxy` on one line is a real bug,
  because bash expands every right-hand side before it assigns any of them.
- **The conda modules are not on the default `MODULEPATH`.** Without
  `module use /soft/modulefiles`, the load just reports an unknown module.
- **The version is pinned.** Bare `module load conda` resolves to whatever ALCF
  has made the default that week, which is not something you want changing
  under a room full of people midway through a workshop.

- **The module load does not put `python` on `PATH`.** This is the one that
  bites. `module load conda/...` on its own leaves you with no `python` at all,
  and the job dies at its first line with `/bin/bash: python: command not
  found` — three words, minutes later, in PBS stderr, pointing at your script
  instead of at the environment. You have to source conda's `profile.d` script
  and then `conda activate base`. `conda activate` is a shell *function* that
  `conda init` writes into an interactive profile, not a binary, so without
  that `source` it is a silent no-op on any account that has never run `conda
  init` — a nasty way for the presenter's laptop to differ from yours.
- **The base path is resolved, not hard-coded.** The preamble asks the `conda`
  that the module actually put on `PATH` where its base is, and only falls back
  to `/soft/applications/conda/<version>/mconda3` if that fails. A written-out
  path is a second thing to keep in step with the pinned version, and it goes
  stale exactly when the version is bumped.
- **Every line is `|| true`, and that is deliberate.** None of this is needed
  by a job that does no networking and no Python, so none of it should be able
  to kill one. The subtle case is the `_ses_conda_base=` assignment: a variable
  assignment takes the exit status of its command substitution, so under a
  `set -e` inherited from a login profile *that* line — not the guarded ones
  after it — is what would kill the job before it reached its own first
  command.
- **If it still fails, the preamble says so itself.** The closing `command -v
  python` check prints which `conda.sh` it tried and suggests `module avail
  conda`, so a wrong pin reports itself at the top of stderr rather than as a
  missing interpreter further down.

This block was briefly shortened to just the `module load`, on the assumption
that the module leaves you in its base environment. It does not, and the
symptom was exactly the `python: command not found` above. The assumption is
recorded here because the failure is silent in both directions: the shortened
version looks correct, and Trinity's own Polaris notes had already written the
fix down under `conda-activate-requires-source`.

Since `commands` is a string passed to `bash -lc`, there is no script file and
no shebang: a `#!/bin/bash -l` line would just be a comment.

Nothing in the preamble is fatal if it fails. A job that needs neither Python
nor the network should not die because `/soft` moved. The cost is that a failed
`module load` is reported in **stderr** while the job keeps going under the
system Python, so read the stderr file, not just stdout, when a run comes back
with an import error.

If you want a different environment — your own conda env, a container, a
different module set — pass `setup_env=False` and set it up yourself. That is
the supported way out; editing `commands` to re-export the proxy is not,
because it leaves two copies to keep in step.

**What you are grading is the verify step.** A correct run calls
`stage_to_alcf`, polls `transfer_status` until `SUCCEEDED`, and only then
submits. To see the failure, stop GCP mid-run (`./globusconnectpersonal -stop`)
and watch whether the agent notices the transfer never succeeded — or reports
success anyway.

Two other things worth watching:

- **Did it look, or guess?** `globus_ls` exists so the agent can check a
  destination instead of inventing one. If it never calls it, the remote path
  came out of the model's head.
- **Did it discover its own endpoint?** `local_endpoint` resolves your GCP UUID
  at call time. An agent that asks *you* for the UUID has not read the tool list
  carefully.

## Example 4 — running your own workload

This is the one you take home. Point the agent at your code:

```
> Stage ~/mycode to my eagle space, build it on a Polaris compute node,
> and run the 2-node test case.
```

Or, if you do not have the code yet, ask it to build the software:

```
> Build LAMMPS (or QE, or CP2K) on Polaris with GPU support, then run
> its 2-node benchmark.
```

Nothing here is LAMMPS-specific. Quantum ESPRESSO, CP2K, NAMD, GROMACS, your
group's own code — the prompt changes by a noun and the five stages do not move
at all. If swapping the application changes anything beyond that noun, the
thing you built is a LAMMPS script, not a skill.

What changes, and what does not:

- **Same chain as before** — generate, stage, submit, monitor, report. Only the
  payload is yours. That is what the skill is for.
- **A build is just a job.** Make it show you the compiler line it chose and
  the log it read, not a summary of them.
- **The guardrails do not move.** Two nodes, 30 minutes, the training account —
  a build that needs more of any of those needs a human, and the server will
  say so.

The workload changes; the skill does not.

## 🧪 Try it yourself

**Add a tool for your own workload.** Pick one thing you do by hand on Polaris
every week. Write it as a function in `alcf_tools/iri.py`, decorate it with
`@mcp.tool()`, write the docstring for the model, and relaunch. The agent finds
it with no other change.

**Add a guardrail and try to talk past it.** Restrict `submit_job` to a single
queue in `common.py`, then spend five minutes trying to convince the agent to
use another one. Then move the same restriction into `SKILL.md` instead and try
again. The difference between those two experiments is the whole argument for
putting limits in code.

**Chain two facilities.** `02_Globus_Compute_and_Transfer/` gives you a second
execution path. Expose a Globus Compute function as a fourth tool group
alongside the IRI tools and ask the agent to choose between them.

**Put a policy in the middle.** `docs.py` already forwards to a server you do
not run. Add something to the forwarder: log every query to a file, cache
repeated ones, or prepend your group's local conventions to the result. This is
how you adopt a shared service without accepting it exactly as shipped.

## Troubleshooting

| Symptom | Cause |
|---|---|
| No tools appear, no permission prompt | You have `enabledMcpjsonServers` pinned in `~/.claude/settings.json`; a project `.mcp.json` server not named there is dropped silently. Add it, or set `"enableAllProjectMcpServers": true`. |
| `/mcp` lists an `ask-alcf` server as `tools fetch failed · connected` | An old clone. There is no separate `ask-alcf` server any more. Claude Code's built-in `"type": "http"` client is Node, and Cloudflare 403s Node's TLS fingerprint at `tools/list` — "connected" is only the handshake. `git pull`: the current `.mcp.json` has one server, and documentation goes out over Python inside it. |
| `/mcp` shows `alcf-mcp` with **10** tools, not 11 | Same cause — a pre-consolidation clone, without `retrieve_alcf_docs`. The missing eleventh tool is the knowledge base. |
| `alcf-mcp` fails to start, or times out | Either you never ran `./setup.sh`, or you launched the agent from another directory so `../.venv/bin/python` did not resolve. Run setup, `cd` here, relaunch. |
| `alcf-mcp` starts, `retrieve_alcf_docs` works, every other tool 401s | Inference and IRI are separate tokens. Run `alcf-tokens test-token iri`. |
| `retrieve_alcf_docs` 403s | Cloudflare is rejecting your network's TLS fingerprint. The tool already goes out over Python's HTTP stack, which is the path most likely to be allowed; if it still fails, you are behind a proxy that re-terminates TLS. |
| `globus endpoint local-id` prints nothing or errors | GCP setup never completed — `~/.globusonline/lta/client-id.txt` is missing. Re-run `./globusconnectpersonal` and complete the guided setup. |
| UUID resolves, but transfers fail immediately | The endpoint is registered and **stopped**. `./globusconnectpersonal -status` should say `connected`; if not, `./globusconnectpersonal -start &`. |
| Transfer fails with a consent or permission error | Missing `data_access` consent on the ALCF side. Re-run `alcf-tokens login --authorize-transfer home --authorize-transfer eagle`. |
| `stage_to_alcf` refuses the destination before Globus sees it | The eagle path is a level too shallow. It must be `/eagle/alcf_training/<your-username>/<filename>` — the project root is shared, and a destination naming only a directory is rejected rather than guessed at. |
| Transfer succeeds but the file is not where you expected | GCP paths are relative to what the endpoint publishes, not your shell's `cwd`. By default that is your whole home directory; check `~/.globusonline/lta/config-paths` if you narrowed it. |
| `stage_to_alcf` returns a task ID, then the job finds no input files | The transfer had not finished. The tool returns when Globus *accepts* the task, not when bytes land — the agent must poll `transfer_status` to `SUCCEEDED` first. This is the failure [Example 3](#example-3--train-mnist-on-polaris) is built around. |
| A staging tool raises a long "Globus needs an additional consent" message | Exactly what it says: run the `alcf-tokens login --authorize-transfer …` line in the error. The tool prints the scopes Globus asked for, so paste them into a support question if the login does not clear it. |
| `local_endpoint` raises but `./globusconnectpersonal -status` says connected | The agent's server is running as a different user, or with a different `$HOME`, than the GCP install. Both read `~/.globusonline/lta/client-id.txt`. |
| GCP will not install on ARM Linux | Globus ships no `aarch64` Linux build; the tarball is x86-64 only and needs emulation plus a 64-bit loader. Apple Silicon is fine — the macOS build handles it. |
| The job dies with a `conda` or `import torch` error | The preamble's conda step failed and was non-fatal by design, so the job ran under the system Python. The reason is in **stderr**, not stdout — read the `.err` file beside `stdout_path`. If you passed `setup_env=False`, there was no preamble at all. |
| Tools are listed but never called | Your model is not tool-capable. Check with `/model` (`/models` on opencode) and pick one the Inference Service advertises tool support for. |

## Where this goes

The same pattern — one MCP server per facility, an agent in front, skills for
the judgment — is what Trinity runs as a multi-user platform across ALCF, NERSC
and OLCF. The architecture on this page does not change when you scale it up;
only the number of tool groups does. One conversation, shared by a researcher
and an agent, fans out to Polaris and Aurora at ALCF, Frontier at OLCF, and
Perlmutter at NERSC — and outlives the session, which is the part a chat window
cannot do.

Three things are added on the way from this directory to that platform, and
none of them are new tools:

- **Sessions that stay up.** The agent's memory of a campaign is not the chat
  scrollback; it survives the browser tab closing and the job finishing
  overnight.
- **More than one person in front of it.** Concurrent users and agents share
  the same platform rather than each running a private copy of the server on a
  laptop.
- **Skills and K-atoms per domain.** The judgment this session puts in
  `skills/submit-job/SKILL.md` becomes a library, so the DFT convention and the
  MD convention can disagree without either one being hard-coded into a tool.

Introducing Trinity: <https://trinityscience.org>.

And because the Inference Service speaks the same APIs as the Genesis Mission
Model Access Gateway (MAG), the same agent runs against AmSC facilities by
swapping the model endpoint. The IRI half is already shared.

## Further reading

- [ask.alcf.anl.gov](https://ask.alcf.anl.gov) — the docs assistant; `/mcp` is the same knowledge base as a tool
- [ALCF IRI API documentation](https://docs.alcf.anl.gov/services/iri-api/)
- [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/)
- [Model Context Protocol specification](https://modelcontextprotocol.io)
- [FastMCP](https://gofastmcp.com)
