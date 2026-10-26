#!/usr/bin/env bash
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_dir"
export OLLAMA_PHONON_HYBRID_PYTHON="$repo_dir/.venv/bin/python"
export OLLAMA_PHONON_HYBRID_ROOT="$repo_dir"
export OLLAMA_HOST=${OLLAMA_HOST:-127.0.0.1:11471}
export OLLAMA_NOPRUNE=1
export CUDA_VISIBLE_DEVICES=-1
export HIP_VISIBLE_DEVICES=-1
export ROCR_VISIBLE_DEVICES=-1
export OLLAMA_VULKAN=0
export GGML_VK_VISIBLE_DEVICES=-1
exec "$repo_dir/bin/ollama" serve
