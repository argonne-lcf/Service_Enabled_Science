---
name: polaris-job
description: Submit and monitor a PBS job on Polaris or Crux through the ALCF IRI API. Use whenever the user asks to run something on an ALCF system.
---

# Running a job on Polaris or Crux

## Before submitting

1. Call `get_system_status` first. If the system is not up, say so and stop.
2. The workshop allocation is `alcf_training`. Never substitute another account.
3. `stdout_path` must be an absolute path under `/home/<username>/` or
   `/eagle/`. Ask for the username if you do not already know it.

## Submitting

Use `submit_job`. Default to 1 node and a 10-minute walltime unless the user
asks for more. Report the job ID as soon as you have it, before you start
polling -- the user should be able to find the job even if this session dies.

## Monitoring

Poll `get_job_state` with backoff: every 10 s for the first minute, then every
30 s. Do not poll in a tight loop.

## When it fails

Fetch the job's stderr with `read_file` and quote the specific line that
explains the failure. Do not summarize it as "the job failed" -- name the
cause.

Then **propose** a fix and wait for approval. Never resubmit on your own; a
silent retry loop burns the user's allocation.

## Common causes

| Symptom | Cause |
|---|---|
| Job never starts | Wrong queue, or the reservation is not active |
| `Permission denied` on stdout | `stdout_path` is outside `/home/` and `/eagle/` |
| File not found on the compute node | Missing `filesystems` attribute for that mount |
| Killed at the walltime boundary | `walltime_sec` too short; do not silently raise it |
