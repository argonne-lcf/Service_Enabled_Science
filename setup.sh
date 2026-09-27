#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# uv
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.opencode/bin:$HOME/.local/bin:$PATH"

# Python environment for the exercise scripts
[ -d .venv ] || uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Coding agents
command -v opencode >/dev/null || curl -fsSL https://opencode.ai/install | bash
command -v claude >/dev/null || curl -fsSL https://claude.ai/install.sh | bash

# Point opencode at the ALCF Inference Service
uvx alcf-ai agent configure opencode

# Session 05's MCP servers run from this same .venv. Check they import now,
# rather than surfacing later as an opaque "MCP server failed to start".
(cd 05_Agentic_Workflows && ../.venv/bin/python - <<'EOF'
import importlib.util, sys

for mod in ("fastmcp", "requests", "rich", "alcf_tokens", "globus_sdk"):
    if importlib.util.find_spec(mod) is None:
        sys.exit(f"FAILED: {mod} did not install")

for script in ("alcf_mcp.py", "ask_alcf_proxy.py"):
    spec = importlib.util.spec_from_file_location(script[:-3], script)
    spec.loader.exec_module(importlib.util.module_from_spec(spec))

import fastmcp
print(f"OK  fastmcp {fastmcp.__version__}; session 05 MCP servers import cleanly.")
EOF
)

# Session 05 stages files from this machine, which needs a Globus Connect
# Personal collection. Nothing here can install it -- registration needs a
# setup key from a browser -- so warn rather than fail, and let sessions 1-4
# proceed either way.
.venv/bin/python - <<'EOF' || true
from globus_sdk import LocalGlobusConnectPersonal

endpoint_id = LocalGlobusConnectPersonal().endpoint_id
if endpoint_id:
    print(f"OK  Globus personal collection {endpoint_id}")
else:
    print(
        "WARNING  No Globus Connect Personal collection on this machine.\n"
        "         Session 05's staging exercise needs one. Set it up before the\n"
        "         workshop -- it involves a browser login:\n"
        "           https://app.globus.org/collections/gcp\n"
        "         See 05_Agentic_Workflows/README.md, 'Set up a Globus personal endpoint'."
    )
EOF

echo "Done. Activate with: source .venv/bin/activate"
