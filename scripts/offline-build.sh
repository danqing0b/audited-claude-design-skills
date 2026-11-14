#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
node scripts/verify-vendor.mjs
export npm_config_offline=true npm_config_ignore_scripts=true npm_config_registry=http://127.0.0.1:9/ COREPACK_ENABLE_NETWORK=0
export JITI_FS_CACHE=false JITI_SOURCE_MAPS=false JITI_DEBUG=false
task_cache="$(mktemp -d)"
trap 'rm -rf -- "$task_cache"' EXIT
# CLI flags override inherited npm configuration. No registry fallback is allowed.
npm ci --offline --ignore-scripts --no-audit --no-fund --strict-peer-deps \
  --registry=http://127.0.0.1:9/ --fetch-retries=0 --cache="$task_cache"
npm run typecheck
npm test
npm run build
