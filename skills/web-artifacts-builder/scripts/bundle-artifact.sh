#!/usr/bin/env bash
set -euo pipefail
if [[ ! -f scripts/offline-build.sh || ! -f package-lock.json ]]; then
  echo "Run this from the root of an initialized audited project." >&2
  exit 1
fi
bash scripts/offline-build.sh
