# Service Enabled Science at ALCF

Demo materials for ALCF Service-Enabled Science Workshop

## Start Here

`setup.sh` installs uv, the Python environment for the exercises, opencode, and Claude Code, then configures opencode for the [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/):

```bash
./setup.sh
```

## ALCF Tokens

To gain access to services covered in this hackathon, we recommend using [alcf-tokens](https://pypi.org/project/alcf-tokens/).  After just one interactive login step, this CLI tool automatically refreshes and retrieves Globus access tokens for the following services:

| Service | service-name |
|---|---|
| [ALCF Inference Service](https://docs.alcf.anl.gov/services/inference-endpoints/) | `inference` |
| [ALCF IRI API](https://docs.alcf.anl.gov/services/iri-api/) | `iri` |
| [Globus Compute](https://www.globus.org/compute) | `globus-compute` |
| [Globus Transfer](https://www.globus.org/data-transfer) | `globus-transfer` |


### Authentication

To properly gain access to all ALCF services, **make sure you authenticate with your ALCF credentials**.

```bash
alcf-tokens login --authorize-transfer home --authorize-transfer eagle
```

### Troubleshooting

If you have issues with your tokens, please logout from Globus by visiting [https://app.globus.org/logout](https://app.globus.org/logout), open a new incognito browser, and restart a new authentication flow. 

## Coding Agents

Run `./setup.sh` for the quick setup above, or install and configure the agents manually.

Install the agents:

```bash
curl -fsSL https://opencode.ai/install | bash   # opencode
curl -fsSL https://claude.ai/install.sh | bash  # Claude Code
```

The [Inference Endpoints guide](https://docs.alcf.anl.gov/services/inference-endpoints/#agents) also covers Codex, pi, and other harnesses.

After [authenticating](#authentication), configure opencode:

```bash
uvx alcf-ai agent configure opencode
```

Configuring Claude Code is optional and works the same way:

```bash
uvx alcf-ai agent configure claude
```

The commands write the service endpoints and an API key to `~/.config/opencode/opencode.jsonc` and `~/.claude/settings.json`. Re-run them to refresh the key.

## Alternative Environment Setups

You will need a Python 3.10+ environment with the [`alcf-tokens`](https://pypi.org/project/alcf-tokens/) and [`alcf-ai`](https://pypi.org/project/alcf-ai/) packages installed.  

We recommend one of the following methods.

### Option 1:  uv

[uv](https://docs.astral.sh/uv/getting-started/installation/) is useful, as it can quickly bootstrap missing Python versions and manage per-tool environments:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12

uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```


### Option 2:  venv

This assumes you already have a Python3.10+ installation:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 3: conda

This assumes you have an Anaconda distribution installed, such as [Miniconda](https://www.anaconda.com/download):

```bash
conda create -n alcf-ses python=3.12 -y
conda activate alcf-ses
pip install -r requirements.txt
```

## Automatic tool environments with uv

Beyond manually-managed virtual environments, `uv` can manage tool-scoped virtual environments which is often convenient:

```bash
# Install CLI tools with self-contained venvs:
uv tool install alcf-tokens
uv tool install alcf-ai

alcf-tokens --help

# If you'd rather not add tools to your PATH:
uvx alcf-tokens --help
```

You can remove installed tools with `uv tool uninstall`.  

## More on alcf-tokens

With a terminal, you can obtain access tokens with:

```bash
inference_token=$(alcf-tokens get-token inference)
iri_token=$(alcf-tokens get-token iri)
globus_compute_token=$(alcf-tokens get-token globus-compute)
globus_transfer_token=$(alcf-tokens get-token globus-transfer)
```

With python, you can obtain them with:

```python
from alcf_tokens.auth import get_access_token, ServiceName

inference_token = get_access_token(ServiceName.inference)
iri_token = get_access_token(ServiceName.iri)
globus_compute_token = get_access_token(ServiceName.globus_compute)
globus_transfer_token = get_access_token(ServiceName.globus_transfer)
```
