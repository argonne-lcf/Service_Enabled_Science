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

echo "Done. Activate with: source .venv/bin/activate"
