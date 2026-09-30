"""ALCF IRI for compute: six PBS calls, exposed as agent tools.

Every tool here is one of the REST calls you already made by hand in
01_Facility_API/ -- the only new thing is the @mcp.tool() decorator, which
turns the function into something an agent can discover and call by name.

The docstring IS the description the model reads when it decides whether to
call a tool. Write it for the model, not for a code reviewer.
"""

import time

import requests
from fastmcp import FastMCP

from .common import (
    ALLOWED_ACCOUNTS,
    API,
    MAX_NODES,
    MAX_WALLTIME_SEC,
    _filesystem_id,
    _headers,
    _resource_id,
)

mcp = FastMCP("alcf-iri-compute")


@mcp.tool()
def get_system_status(system: str = "") -> list:
    """Report whether ALCF systems are up.

    Pass a system name (e.g. "Polaris") to filter, or leave it empty to list
    every resource the facility knows about. Needs no authentication.
    """
    resources = requests.get(f"{API}/status/resources", timeout=30).json()
    if system:
        resources = [r for r in resources if r["name"].lower() == system.lower()]
    return [
        {"name": r["name"], "status": r.get("current_status"), "id": r["id"]}
        for r in resources
    ]


@mcp.tool()
def submit_job(
    system: str,
    commands: str,
    stdout_path: str,
    nodes: int = 1,
    queue: str = "debug",
    account: str = "alcf_training",
    walltime_sec: int = 600,
) -> dict:
    """Submit a PBS job and return its job ID.

    `commands` is run under `bash -lc` on the compute node. `stdout_path` must
    be an absolute path under /home/ or /eagle/ that you can write to.
    Refuses accounts outside the workshop allocation, more than 2 nodes, or
    walltimes over 30 minutes -- ask a human to lift those limits.
    """
    if account not in ALLOWED_ACCOUNTS:
        raise ValueError(f"Account {account!r} is not allowed here. Use alcf_training.")
    if nodes > MAX_NODES:
        raise ValueError(f"{nodes} nodes exceeds the {MAX_NODES}-node workshop limit.")
    if walltime_sec > MAX_WALLTIME_SEC:
        raise ValueError(f"Walltime exceeds the {MAX_WALLTIME_SEC}s workshop limit.")
    _filesystem_id(stdout_path)  # raises if the path is somewhere we can't write
    stderr_path = (
        stdout_path[: -len(".out")] + ".err"
        if stdout_path.endswith(".out")
        else stdout_path + ".err"
    )

    response = requests.post(
        f"{API}/compute/job/{_resource_id(system)}",
        json={
            "executable": "/bin/bash",
            "arguments": ["-lc", commands],
            "name": "ses-agent-job",
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "resources": {"node_count": nodes},
            "attributes": {
                "duration": walltime_sec,
                "queue_name": queue,
                "account": account,
                "custom_attributes": {"filesystems": "home:eagle"},
            },
        },
        headers=_headers(),
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_job_state(system: str, job_id: str) -> dict:
    """Look up the current state of one PBS job by its ID."""
    response = requests.get(
        f"{API}/compute/status/{_resource_id(system)}/{job_id}",
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def list_jobs(
    system: str,
    states: list[str] | None = None,
    queue: str = "",
    owner: str = "",
    limit: int = 10,
    historical: bool = False,
) -> dict:
    """List PBS jobs on a system, newest first.

    `states` filters on e.g. ["active"] or ["active", "queued"]. Set
    `historical=True` to include jobs that have already finished.
    """
    filters: dict = {}
    if states:
        filters["states"] = states
    if queue:
        filters["queue"] = queue
    if owner:
        filters["owner"] = owner

    response = requests.post(
        f"{API}/compute/status/{_resource_id(system)}",
        params={"historical": str(historical).lower(), "limit": limit, "offset": 0},
        json=filters,
        headers=_headers(),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def cancel_job(system: str, job_id: str) -> str:
    """Cancel a queued or running PBS job. Confirm with the user before calling."""
    response = requests.delete(
        f"{API}/compute/cancel/{_resource_id(system)}/{job_id}",
        headers=_headers(),
        timeout=30,
    )
    if response.status_code == 204:
        return f"Cancellation submitted for job {job_id}."
    return response.text


@mcp.tool()
def read_file(path: str, size: int = 4000, offset: int = 0) -> str:
    """Read up to `size` bytes of a file on /home/ or /eagle/.

    Use this to fetch a job's stdout or stderr after it finishes. The facility
    runs this as an async task, so it may take a few seconds to return.
    """
    submit = requests.get(
        f"{API}/filesystem/view/{_filesystem_id(path)}",
        params={"path": path, "size": size, "offset": offset},
        headers=_headers(),
        timeout=30,
    )
    submit.raise_for_status()
    task_id = submit.json()["task_id"]

    for _ in range(30):  # ~60 s ceiling, then give up rather than hang the agent
        time.sleep(2)
        task = requests.get(f"{API}/task/{task_id}", headers=_headers(), timeout=30).json()
        if task.get("status") not in ("pending", "active"):
            break
    else:
        return f"Filesystem task {task_id} did not finish in 60 s."

    if task.get("status") == "failed":
        return f"Read failed: {task.get('result')}"
    return task["result"]["output"]["content"]
