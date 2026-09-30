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
submit_job(system, commands, stdout_path,
           nodes=1, queue="debug", account="alcf_training", walltime_sec=600)
```

`stdout_path` is required and must be an absolute path under `/home/` or
`/eagle/` that you can write to. Ask for the username if you do not know it.

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

## Common causes of failure

| Symptom | Cause |
|---|---|
| Job never starts | Wrong queue, or the reservation is not active |
| `Permission denied` on stdout | `stdout_path` is outside `/home/` and `/eagle/` |
| File not found on the compute node | The transfer had not finished — you skipped stage 2's poll |
| Killed at the walltime boundary | `walltime_sec` too short; do not silently raise it |
| `module load` aborts the job | Non-zero return from a missing prereq plus `set -e`; drop `set -e` around the module block |
| `conda activate` does nothing | It is a shell function — source `profile.d/conda.sh` first |
| Download hangs on the compute node | No direct internet; export `http_proxy=http://proxy.alcf.anl.gov:3128` |

## Multi-node

Allocating N nodes does not use N nodes. `hostname` on its own runs once, on
the head node. Use `mpiexec -n <ranks> --ppn <ranks-per-node> <cmd>` when the
user asks for work on every node.
