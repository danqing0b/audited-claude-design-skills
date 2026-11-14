#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
node "$repo_root/scripts/init-project.mjs" "${1:?Usage: init-artifact.sh <new-directory>}"
