---
name: submit-job
description: Generate inputs, stage them to ALCF over Globus, submit through the IRI API, then monitor and report back. Use whenever the user asks to run something on an ALCF system.
---

# Running a workload on an ALCF system

Five stages. Do them in order, and tell the user where you are.

## 1. Generate the input

Write the input deck, script or config **locally** first, and show it to the
user before you move anything. A file staged by mistake still costs a transfer
and still has to be cleaned up.

## 2. Stage it with Globus

Call `stage_to_alcf(local_path, alcf_path)`. Eagle writes must land under
`/eagle/<project>/`; for the workshop that project is `alcf_training`.

Then poll `transfer_status(task_id)` until it reports `SUCCEEDED`. **A task ID
is not a delivery.** If you submit before the transfer lands, the job runs
against an empty directory and the failure shows up minutes later in PBS
stderr, looking like a job bug rather than a staging bug.

## 3. Submit

Call `get_system_status(system)` first. If the system is down, say so and stop.

Then `submit_job`. Its signature is:

```python
submit_job(system, commands, stdout_path, nodes=1, queue="debug",
           account="alcf_training", walltime_sec=600, setup_env=True)
```

`stdout_path` is required and must be an absolute path under `/home/` or
`/eagle/` that you can write to. Ask for the username if you do not know it.

`commands` is a shell string, not a script file — the tool runs it as
`/bin/bash -lc "<commands>"`. Do not write a `#!/bin/bash -l` shebang; there is
no file for it to be the first line of, so it would just be a comment.

**The environment is already set up. Write `commands` as the work only.**
`setup_env=True` (the default) prepends the proxy exports and the pinned conda
module load to your command block before it is submitted — see `job_preamble()`
in `alcf_tools/common.py` for the exact lines and why each one is there. So:

```python
commands="python train.py"          # correct — that is the whole job
```

Not this:

```python
commands="export http_proxy=...\nmodule load conda\n..."   # already done
```

Restating them is not harmful, but it is noise you then have to keep correct,
and it is how the one-line `export http_proxy=... https_proxy=$http_proxy` bug
gets reintroduced. Leave it to the server.

Only pass `setup_env=False` if the user has asked for a different environment —
a personal conda env, a container, a non-default module set. That job gets no
proxy and no conda and must arrange both itself; say so when you do it.

**Do not take the `queue` default on faith.** `debug` is only the fallback. If
the user names a reservation, pass it as `queue=` — in PBS a reservation *is* a
queue name, so there is no separate flag for it. If the request does not say
which queue to use and the job is more than a few minutes long, ask rather than
silently landing in `debug`, where it may sit behind everyone else or exceed
the queue's walltime limit.

Report the job ID as soon as you have it, **before** you start polling — the
user should be able to find the job even if this session dies.

## 4. Monitor

Poll `get_job_state(system, job_id)` with backoff: every 10 s for the first
minute, then every 30 s. Do not poll in a tight loop.

## 5. Report

On success, read the output with `read_file(path)` and quote the part the user
actually asked for.

On failure, fetch the job's stderr and quote **the specific line** that
explains it. Do not summarise as "the job failed" — name the cause. Then
*propose* a fix and wait for approval. Never resubmit on your own; a silent
retry loop burns the user's allocation.

## Workshop guardrails

These are enforced in `alcf_tools/common.py`, not by prompting. Do not try to
work around them — ask a human to lift them.

| Limit | Value |
|---|---|
| Allowed account | `alcf_training` |
| Max nodes | 2 |
| Max walltime | 30 minutes |
| Max staged files | 500 |
| Max staged bytes | 1 GiB |

`job_preamble()` lives in the same file for the same reason. An environment
that depends on the agent remembering it is an environment that works in
rehearsal and fails in the room.

## Common causes of failure

| Symptom | Cause |
|---|---|
| Job never starts | Wrong queue, or the reservation is not active |
| `Permission denied` on stdout | `stdout_path` is outside `/home/` and `/eagle/` |
| File not found on the compute node | The transfer had not finished — you skipped stage 2's poll |
| Killed at the walltime boundary | `walltime_sec` too short; do not silently raise it |
| `ModuleNotFoundError` / wrong Python | Conda did not come up. Read **stderr**, not stdout — `job_preamble()` is deliberately non-fatal, so a missing module says so there and the job carries on under the system Python |
| Download hangs on the compute node | No direct internet. The preamble exports both proxy variables, so this means either `setup_env=False` or a tool that ignores `http_proxy` |
| Either of the above, with `setup_env=False` | You opted out of the preamble; the job has to set up its own environment |

## Multi-node

Allocating N nodes does not use N nodes. `hostname` on its own runs once, on
the head node. Use `mpiexec -n <ranks> --ppn <ranks-per-node> <cmd>` when the
user asks for work on every node.
