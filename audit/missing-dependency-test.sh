set -eu
cd /app
mv vendor/npm/clsx@2.1.1.tgz vendor/npm/clsx@2.1.1.tgz.missing
if node scripts/verify-vendor.mjs > /tmp/gate.log 2>&1; then
  echo 'ERROR: missing archive passed preflight'; exit 1
fi
task_cache="$(mktemp -d)"
set +e
npm ci --cache="$task_cache" > /tmp/missing-local.log 2>&1
local_status=$?
set -e
if [ "$local_status" -eq 0 ]; then echo 'ERROR: missing archive was repaired'; exit 1; fi
node -e 'const fs=require("node:fs"); const p=JSON.parse(fs.readFileSync("package-lock.json"));p.packages["node_modules/clsx"].resolved="https://registry.npmjs.org/clsx/-/clsx-2.1.1.tgz";fs.writeFileSync("package-lock.json",JSON.stringify(p));'
task_cache_remote="$(mktemp -d)"
set +e
npm ci --cache="$task_cache_remote" > /tmp/missing-remote.log 2>&1
remote_status=$?
set -e
if [ "$remote_status" -eq 0 ]; then echo 'ERROR: remote dependency was fetched'; exit 1; fi
node -e 'const fs=require("node:fs");const gate=fs.readFileSync("/tmp/gate.log","utf8"),local=fs.readFileSync("/tmp/missing-local.log","utf8"),remote=fs.readFileSync("/tmp/missing-remote.log","utf8");if(!gate.includes("ENOENT")||!local.includes("ENOENT")||!remote.includes("ENOTCACHED"))throw new Error(JSON.stringify({gate,local,remote}));console.log(JSON.stringify({missingArchiveRejectedBeforeInstall:true,missingLocalArchiveNotRepaired:true,remoteResolutionBlockedByOfflineConfig:true,missingLocalError:"ENOENT",remoteError:"ENOTCACHED",networkInterfaces:Object.keys(require("node:os").networkInterfaces())}));'
