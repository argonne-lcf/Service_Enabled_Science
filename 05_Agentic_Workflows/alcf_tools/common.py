"""Shared constants, guardrails and helpers for the three tool modules.

Nothing in here is a tool. The IDs, the limits, and the path translation are
the parts that `iri.py`, `globus.py` and `docs.py` all have to agree on, so
they live in one place rather than being restated three times.
"""

import os
import posixpath

import globus_sdk
import requests
from alcf_tokens.auth import ServiceName, get_access_token, get_transfer_authorizer

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
# Everything staged to eagle lands in /eagle/<project>/<user>/. The project is
# the allocation that owns the space; the per-user directory below it is what
# keeps a room full of people staging `train.py` from overwriting each other.
EAGLE_PROJECT = "alcf_training"

# --- Compute-node environment -----------------------------------------------
# Two things every Polaris job needs, and neither is discoverable from the node
# itself. Prompting an agent to remember them works most of the time, which is
# the worst failure rate available: the times it forgets look like a bug in the
# user's script. So `submit_job` prepends them, the same way the limits above
# are enforced instead of requested.
PROXY = "http://proxy.alcf.anl.gov:3128"
# Pinned, not floating. `module load conda` resolves to whatever ALCF has made
# the default that week, so an unpinned preamble silently changes the Python
# under every attendee's job mid-workshop.
CONDA_MODULE = "conda/2026-10-01"
# Where that module's install tree lives, in ALCF's layout. Derived from
# CONDA_MODULE rather than written out a second time: when these were two
# independent constants, bumping one and not the other produced a preamble that
# loaded one version and sourced another. This is only the *fallback* -- the
# preamble prefers the path the loaded module actually reports.
CONDA_ROOT = f"/soft/applications/conda/{CONDA_MODULE.split('/', 1)[-1]}/mconda3"


def job_preamble() -> str:
    """Shell lines prepended to every `submit_job` command block.

    Line by line, because each one is load-bearing:

    * Both proxy variables, with the literal value twice. Compute nodes have no
      direct route off-site, so an unproxied download hangs until walltime with
      no error. Writing it as `export http_proxy=... https_proxy=$http_proxy`
      on one line is a real bug and not a style choice -- bash expands every
      right-hand side before it assigns any of them, so `https_proxy` would get
      whatever `http_proxy` held *before* the line ran, i.e. nothing.

    * `module use /soft/modulefiles` before the load. The conda modules are not
      on the default MODULEPATH; without this line the load simply reports the
      module as unknown.

    * `module load <pinned version> || true`. Lmod on Polaris returns non-zero
      when a module declares a prerequisite that no longer exists, which both
      recent conda modules do. The `|| true` keeps that from being fatal under
      a `set -e` the user may have written into `commands`.

    * `source .../profile.d/conda.sh`, then `conda activate base`. The module
      load on its own does NOT put python on PATH -- a job that skips this
      dies with a bare `/bin/bash: python: command not found`, minutes later,
      looking like a broken script rather than a broken environment. This is
      the whole reason the block exists, and it was briefly dropped on the
      assumption that the module left you in its base environment; it does
      not. `conda activate` is a shell function that `conda init` writes into
      an interactive profile, not a binary, so without sourcing that script it
      is a silent no-op on any account that has not run `conda init`.

      The path is resolved from the module that actually loaded, by asking the
      `conda` on PATH where its base is, and only falls back to CONDA_ROOT if
      that fails. A hard-coded path is a second thing to keep in sync with the
      pinned version, and gets it wrong exactly when the version is bumped.

    * A last check that `python` resolves. If it does not, the preamble says so
      on stderr, naming both candidate causes, instead of letting the job fail
      later with three words that point at the wrong layer.

    Failures here are deliberately non-fatal: nothing in this block is required
    by a job that does no networking and no Python, and it should not be able
    to take one down. Errors land in the job's stderr rather than being
    swallowed, so a genuinely broken conda is still visible.
    """
    return (
        f"export http_proxy={PROXY}\n"
        f"export https_proxy={PROXY}\n"
        "module use /soft/modulefiles || true\n"
        f"module load {CONDA_MODULE} || true\n"
        # Ask the conda that the module put on PATH where its base is, rather
        # than assuming the layout. The trailing `|| true` is load-bearing: an
        # assignment takes the exit status of its command substitution, so
        # under an inherited `set -e` this line -- not the guarded ones below
        # -- is what kills the job, before it reaches its own first command.
        '_ses_conda_base="$(command -v conda >/dev/null 2>&1'
        ' && conda info --base 2>/dev/null)" || true\n'
        f'[ -n "$_ses_conda_base" ] || _ses_conda_base="{CONDA_ROOT}"\n'
        # `|| true` for the same reason as the module load: this line returns
        # non-zero when conda is absent, and a `set -e` inherited from a login
        # profile would turn that into a job that dies before its own first
        # command with no output at all.
        '[ -r "$_ses_conda_base/etc/profile.d/conda.sh" ]'
        ' && . "$_ses_conda_base/etc/profile.d/conda.sh"'
        ' && conda activate base || true\n'
        'command -v python >/dev/null 2>&1 || {\n'
        f'  echo "preamble: python is not on PATH after loading {CONDA_MODULE}." >&2\n'
        '  echo "preamble: tried $_ses_conda_base/etc/profile.d/conda.sh" >&2\n'
        f'  echo "preamble: check \'module avail conda\' on a login node --'
        f' {CONDA_MODULE} may not exist." >&2\n'
        '}\n'
    )


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


def _check_eagle_destination(remote_path: str) -> None:
    """Require an eagle write to land under /eagle/<project>/<user>/.

    `remote_path` is collection-relative, the second half of what
    `_alcf_collection` returns: /eagle/alcf_training/you/run.sh arrives here as
    /alcf_training/you/run.sh.

    Three components are the minimum -- project, username, and something inside
    it -- and the third is the one that is easy to get wrong. Two components
    cannot be checked: `/alcf_training/bob` is a username, `/alcf_training/run.sh`
    is a file sitting in the shared project root, and nothing about the strings
    tells them apart. So the destination has to name a path *inside* a user
    directory, which makes the ambiguous case a rejection rather than a coin
    flip. Eagle's project directory is group writable, so nothing at the
    filesystem layer stops thirty people from overwriting one another's
    `train.py` in the same half hour; only this does.

    This does not verify that <username> is *your* username -- the server has no
    trustworthy way to know it, and guessing wrong would block a legitimate
    transfer mid-workshop. It enforces the layout, not the identity.

    The path is normalised before it is inspected, so `/alcf_training/you/../..`
    is rejected rather than checked in its pre-collapse form. A guard that only
    looks at the prefix is a guard you can walk out of with `..`.
    """
    parts = [p for p in posixpath.normpath(remote_path).split("/") if p and p != "."]
    if not parts or parts[0] != EAGLE_PROJECT:
        raise ValueError(
            f"Writes to eagle must land under /eagle/{EAGLE_PROJECT}/<your-username>/. "
            f"That path resolves outside the {EAGLE_PROJECT} project directory."
        )
    if len(parts) < 3:
        raise ValueError(
            f"Stage to a full path inside your own directory -- "
            f"/eagle/{EAGLE_PROJECT}/<your-username>/<filename> -- not to "
            f"/eagle/{'/'.join(parts)}. A destination one level short is either the "
            f"shared project root or a directory that has to already exist; name the "
            f"file. Create the directory once with: "
            f"ssh <you>@polaris.alcf.anl.gov 'mkdir -p /eagle/{EAGLE_PROJECT}/$USER'"
        )


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


__all__ = [
    "API",
    "RESOURCES",
    "FILESYSTEMS",
    "COLLECTIONS",
    "ALLOWED_ACCOUNTS",
    "MAX_NODES",
    "MAX_WALLTIME_SEC",
    "MAX_STAGE_FILES",
    "MAX_STAGE_BYTES",
    "EAGLE_PROJECT",
    "_check_eagle_destination",
    "_headers",
    "_resource_id",
    "_filesystem_id",
    "_alcf_collection",
    "_local_endpoint_id",
    "_transfer_client",
    "_consent_hint",
    "_measure",
]
