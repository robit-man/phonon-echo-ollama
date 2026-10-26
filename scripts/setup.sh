#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
uv venv --python "${PHONON_PYTHON:-3.12}" .venv
# Install the CPU build first; it also satisfies requirements.txt's torch pin.
uv pip install --python .venv/bin/python --index-url https://download.pytorch.org/whl/cpu 'torch==2.12.0'
uv pip install --python .venv/bin/python -r requirements.txt
# OpenVoice's optional demo dependencies are unnecessary for this graph.
uv pip install --python .venv/bin/python --no-deps \
  'git+https://github.com/myshell-ai/OpenVoice.git@74a1d147b17a8c3092dd5430504bd83ef6c7eb23'
uv pip install --python .venv/bin/python --no-deps -e .
