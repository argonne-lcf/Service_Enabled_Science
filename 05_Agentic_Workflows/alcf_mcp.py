# /// script
# requires-python = ">=3.10"
# dependencies = ["fastmcp>=2.10,<5", "alcf-tokens", "globus-sdk>=3,<5", "requests"]
# ///
"""
An MCP server that exposes the ALCF Facility (IRI) API as agent tools.

Every tool below is one of the REST calls you already made by hand in
01_Facility_API/ -- the only new thing is the @mcp.tool() decorator, which
turns the function into something an agent can discover and call by name.

    stdio transport (what Claude Code / opencode launch, per .mcp.json and
    opencode.jsonc -- run ./setup.sh first to build .venv):
        .venv/bin/python alcf_mcp.py

    standalone, resolving dependencies from the PEP 723 header above:
        uv run alcf_mcp.py

    poke at it in a browser-based inspector:
        uv run --with fastmcp fastmcp dev alcf_mcp.py
"""

import os
import time

import globus_sdk
import requests
from alcf_tokens.auth import ServiceName, get_access_token, get_transfer_authorizer
from fastmcp import FastMCP

API = "https://api.alcf.anl.gov/api/v1"

RESOURCES = {
    "polaris": "55c1c993-1124-47f9-b823-514ba3849a9a",
    "crux": "8b9b42f7-572a-4909-8472-a0453436304c",
}
FILESYSTEMS = {
    "home": "6115bd2c-957a-4543-abff-5fae52992ff2",
    "eagle": "1c3ad9d4-2e91-42bc-becb-72b1fde1235c",
}
# Globus collection IDs are a *different* namespace from the IRI filesystem IDs
# above -- same two filesystems, different UUIDs, different API. Mixing them up
# produces a 404 that reads like a missing file. These match the aliases
# alcf-tokens uses for `--authorize-transfer home` / `eagle`.
COLLECTIONS = {
    "home": "9032dd3a-e841-4687-a163-2720da731b5b",
    "eagle": "05d2c76a-e867-4f67-aa57-76edeb0beda0",
}

# --- Guardrails -------------------------------------------------------------
# The server is the boundary, not the prompt. An agent cannot talk its way past
# these, because they are ordinary Python running before the request goes out.
ALLOWED_ACCOUNTS = {"alcf_training"}
MAX_NODES = 2
MAX_WALLTIME_SEC = 30 * 60
# Staging limits: enough for a parameter sweep, not enough to push a laptop's
# entire home directory onto eagle by accident.
MAX_STAGE_FILES = 500
MAX_STAGE_BYTES = 1024**3

mcp = FastMCP("alcf-iri")


def _headers() -> dict:
    """A fresh Bearer token on every call -- alcf-tokens handles the refresh."""
    return {
        "Authorization": f"Bearer {get_access_token(ServiceName.iri)}",
        "Content-Type": "application/json",
    }


def _resource_id(system: str) -> str:
    try:
        return RESOURCES[system.lower()]
    except KeyError:
        raise ValueError(f"Unknown system {system!r}. Choose one of: {sorted(RESOURCES)}")


def _filesystem_id(path: str) -> str:
    if path.startswith("/home/"):
        return FILESYSTEMS["home"]
    if path.startswith(("/eagle/", "/lus/eagle/")):
        return FILESYSTEMS["eagle"]
    raise ValueError("Path must be under /home/, /eagle/, or /lus/eagle/.")


def _alcf_collection(path: str) -> tuple[str, str]:
    """Map an ALCF POSIX path to (collection id, collection-relative path).

    Every other tool here speaks absolute POSIX paths (/home/you/run.sh), but a
    Globus collection is rooted at the filesystem it exports, so the same file
    is /you/run.sh on the `home` collection. Translating here keeps one path
    vocabulary across the whole server -- see `_filesystem_id` for the
    IRI-flavoured version of the same question.
    """
    for prefix, name in (("/home/", "home"), ("/eagle/", "eagle"), ("/lus/eagle/", "eagle")):
        if path.startswith(prefix):
            return COLLECTIONS[name], "/" + path[len(prefix) :]
    raise ValueError("Path must be under /home/, /eagle/, or /lus/eagle/.")


def _local_endpoint_id() -> str:
    """The UUID of the Globus Connect Personal collection on this machine.

    Read from ~/.globusonline/lta/client-id.txt, exactly as
    `globus endpoint local-id` does -- never hard-coded, so nothing committed
    to this repo carries one person's endpoint.
    """
    endpoint_id = globus_sdk.LocalGlobusConnectPersonal().endpoint_id
    if not endpoint_id:
        raise ValueError(
            "No Globus Connect Personal collection found on this machine. "
            "Install GCP and run `./globusconnectpersonal -setup <setup-key>`; "
            "see the README section 'Set up a Globus personal endpoint'."
        )
    return endpoint_id


def _transfer_client(collections: list[str]) -> globus_sdk.TransferClient:
    """A TransferClient whose consents cover the ALCF collections in `collections`.

    Only the facility collections get `data_access` asked for up front, because
    those are the ones alcf-tokens already knows need it. Whether a personal
    collection needs its own consent depends on how GCP registered it, so we
    let the first call find out -- `_consent_hint` turns that into the exact
    login command rather than a raw Globus error.
    """
    alcf = [f"{c}:data_access" for c in collections if c in COLLECTIONS.values()]
    return globus_sdk.TransferClient(authorizer=get_transfer_authorizer(authorize_transfer=alcf))


def _consent_hint(error: globus_sdk.TransferAPIError) -> str:
    """Turn Globus's ConsentRequired into the command that fixes it."""
    if error.info.consent_required:
        return (
            "Globus needs an additional consent before it will touch this "
            "collection. Run, in a terminal where you can open a browser:\n"
            "    alcf-tokens login --authorize-transfer home "
            "--authorize-transfer eagle\n"
            f"Scopes Globus asked for: {error.info.consent_required.required_scopes}"
        )
    return f"Globus Transfer error {error.code}: {error.message}"


def _measure(local_path: str, recursive: bool) -> tuple[int, int]:
    """(file count, total bytes) for what a transfer would move."""
    if not os.path.exists(local_path):
        raise ValueError(f"{local_path} does not exist on this machine.")
    if os.path.isfile(local_path):
        return 1, os.path.getsize(local_path)
    if not recursive:
        raise ValueError(f"{local_path} is a directory -- pass recursive=True to stage it.")
    count = total = 0
    for root, _dirs, files in os.walk(local_path):
        for name in files:
            count += 1
            total += os.path.getsize(os.path.join(root, name))
            if count > MAX_STAGE_FILES:
                raise ValueError(
                    f"{local_path} holds more than {MAX_STAGE_FILES} files. "
                    "Stage a narrower directory, or ask a human to lift the limit."
                )
    return count, total


# --- Tools ------------------------------------------------------------------
# The docstring IS the description the model reads when it decides whether to
# call a tool. Write it for the model, not for a code reviewer.


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


# --- Staging tools ----------------------------------------------------------
# Everything above acts on files that are already at the facility. These four
# move files the other way: generated here, staged there, then run.


@mcp.tool()
def local_endpoint() -> dict:
    """Report this machine's Globus Connect Personal collection.

    Call this first when staging local files -- it confirms GCP is set up and
    returns the collection ID that `stage_to_alcf` will use as the source. If
    it raises, the user has not finished GCP setup and no transfer will work.
    """
    return {
        "collection_id": _local_endpoint_id(),
        "note": (
            "Paths on this collection are ordinary absolute paths on the user's "
            "machine, but only the directories GCP publishes are reachable. Use "
            "globus_ls(location='local') to check before assuming a path exists."
        ),
    }


@mcp.tool()
def globus_ls(path: str, location: str = "alcf") -> dict:
    """List a directory over Globus, on this machine or at ALCF.

    `location="local"` lists `path` on the user's own machine through Globus
    Connect Personal; `location="alcf"` lists an absolute ALCF path such as
    /home/<username>/ or /eagle/alcf_training/.

    Use this to confirm a destination exists before staging, and to verify the
    files actually arrived afterwards. Do not guess remote paths -- look.
    """
    if location == "local":
        collection, target = _local_endpoint_id(), path
    elif location == "alcf":
        collection, target = _alcf_collection(path)
    else:
        raise ValueError('location must be "local" or "alcf".')

    try:
        with _transfer_client([collection]) as tc:
            entries = list(tc.operation_ls(collection, path=target))
    except globus_sdk.TransferAPIError as error:
        raise ValueError(_consent_hint(error)) from error

    return {
        "path": path,
        "entries": [
            {"name": e["name"], "type": e["type"], "size": e.get("size")} for e in entries
        ],
    }


@mcp.tool()
def stage_to_alcf(local_path: str, alcf_path: str, recursive: bool = False) -> dict:
    """Copy a local file or directory to ALCF with Globus, and return a task ID.

    `local_path` is a path on the user's own machine; `alcf_path` is an absolute
    ALCF path under /home/ or /eagle/alcf_training/. Set `recursive=True` for a
    directory.

    This returns as soon as Globus accepts the task -- the bytes have NOT moved
    yet. Poll `transfer_status` until it reports SUCCEEDED before you submit a
    job that reads these files, or the job will start against files that are
    not there.

    Refuses more than 500 files or 1 GiB; ask a human to lift those limits.
    """
    destination, remote_path = _alcf_collection(alcf_path)
    if destination == COLLECTIONS["eagle"] and not remote_path.startswith("/alcf_training/"):
        raise ValueError("Writes to eagle must land under /eagle/alcf_training/.")

    count, total = _measure(local_path, recursive)
    if total > MAX_STAGE_BYTES:
        raise ValueError(
            f"{total} bytes exceeds the {MAX_STAGE_BYTES}-byte staging limit. "
            "Globus can move far more than this; the limit is a workshop guardrail."
        )

    source = _local_endpoint_id()
    try:
        with _transfer_client([source, destination]) as tc:
            request = globus_sdk.TransferData(source, destination, label="ses-agent-stage")
            request.add_item(local_path, remote_path, recursive=recursive)
            task = tc.submit_transfer(request)
    except globus_sdk.TransferAPIError as error:
        raise ValueError(_consent_hint(error)) from error

    return {
        "task_id": task["task_id"],
        "files": count,
        "bytes": total,
        "destination": alcf_path,
        "next_step": "Call transfer_status with this task_id until status is SUCCEEDED.",
    }


@mcp.tool()
def transfer_status(task_id: str) -> dict:
    """Check a Globus transfer. SUCCEEDED means the files are really there.

    ACTIVE means still copying -- wait a few seconds and call again rather than
    assuming it finished. FAILED carries the reason in `nice_status`; quote it
    to the user instead of paraphrasing.
    """
    try:
        with _transfer_client([]) as tc:
            task = tc.get_task(task_id)
    except globus_sdk.TransferAPIError as error:
        raise ValueError(_consent_hint(error)) from error

    return {
        "task_id": task_id,
        "status": task["status"],
        "nice_status": task.get("nice_status"),
        "files_transferred": task.get("files_transferred"),
        "bytes_transferred": task.get("bytes_transferred"),
    }


if __name__ == "__main__":
    mcp.run()
