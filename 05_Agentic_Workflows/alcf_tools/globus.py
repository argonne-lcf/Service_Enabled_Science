"""Globus data transfer: four staging tools, exposed as agent tools.

The IRI tools in `iri.py` all act on files that are already at the facility.
These four move files the other way: generated here, staged there, then run.
"""

import globus_sdk
from fastmcp import FastMCP

from .common import (
    COLLECTIONS,
    MAX_STAGE_BYTES,
    _alcf_collection,
    _consent_hint,
    _local_endpoint_id,
    _measure,
    _transfer_client,
)

mcp = FastMCP("alcf-globus-data")


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
