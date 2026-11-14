// Maintainer-only online provenance check; never imported by installation/build.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
if (!process.argv.includes("--allow-network-refresh")) throw new Error("Explicit --allow-network-refresh is required");
// Node honors the inherited proxy/CA settings when NODE_USE_ENV_PROXY=1 is set.
async function json(url) { const response = await fetch(url); if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`); return response.json(); }
const keys = await json("https://registry.npmjs.org/-/npm/v1/keys");
fs.writeFileSync(path.join(root,"audit/npm-registry-signing-keys.json"),JSON.stringify(keys,null,2)+"\n");
const packages = JSON.parse(fs.readFileSync(path.join(root,"audit/packages.json")))
  .concat(JSON.parse(fs.readFileSync(path.join(root,"audit/embedded-packages.json"))))
  .concat(JSON.parse(fs.readFileSync(path.join(root,"audit/runtime-assets.json"))));
const results = [];
for (let offset=0;offset<packages.length;offset+=12) {
  const batch = await Promise.all(packages.slice(offset,offset+12).map(async record => {
    const meta = await json(`https://registry.npmjs.org/${encodeURIComponent(record.name)}/${record.version}`);
    const message = `${record.name}@${record.version}:${meta.dist.integrity}`;
    const signatures = (meta.dist.signatures ?? []).map(signature => {
      const key = keys.keys.find(k=>k.keyid===signature.keyid);
      if (!key) return { keyid: signature.keyid, verified: false, reason: "key not in current registry key set" };
      const publicKey = crypto.createPublicKey({ key: Buffer.from(key.key,"base64"), format:"der", type:"spki" });
      return { keyid:signature.keyid, verified:crypto.verify("sha256",Buffer.from(message),publicKey,Buffer.from(signature.sig,"base64")), keyExpires:key.expires };
    });
    return { name:record.name,version:record.version,upstreamIntegrity:meta.dist.integrity,localIntegrity:record.integrity,locallyPatched:!!record.local_patch,signatures,gitHead:meta.gitHead,attestations:meta.dist.attestations ?? null };
  }));
  results.push(...batch);
}
fs.writeFileSync(path.join(root,"audit/origin-signatures.json"),JSON.stringify(results,null,2)+"\n");
const failed = results.filter(r=>!r.signatures.some(s=>s.verified));
console.log(JSON.stringify({ packages:results.length,validRegistrySignatures:results.length-failed.length,withoutVerifiedSignature:failed.map(r=>r.name+"@"+r.version),limitation:"Registry key verification authenticates the upstream metadata integrity, not absence of malicious code or local patches. Expiry fields are retained; signing timestamps/Sigstore attestations are not independently validated." }));
if (failed.length) process.exitCode=1;
