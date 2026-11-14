import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import http from "node:http";
import https from "node:https";
import net from "node:net";
import tls from "node:tls";
import dns from "node:dns";
import childProcess from "node:child_process";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
test("jiti trusted loading and transform make no network, process, or canary credential accesses", async t => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "jiti-behavior-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const config = path.join(root, "config.ts");
  const canary = path.join(root, ".credential-canary.map");
  const secret = "AUDIT_FAKE_SECRET_9b8f2";
  fs.writeFileSync(config, 'export default { title: "offline", count: 42 }');
  fs.writeFileSync(canary, JSON.stringify({ version: 3, sources: ["private.ts"], names: [], mappings: "AAAA", sourcesContent: [secret] }));
  const events = []; const restores = [];
  function block(object, name, kind) {
    const original = object[name];
    object[name] = function(...args) { events.push({ kind, method: name }); throw new Error(`Unexpected ${kind} in jiti audit`); };
    restores.push(() => { object[name] = original; });
  }
  for (const [object, names, kind] of [
    [http, ["request", "get"], "http"], [https, ["request", "get"], "https"],
    [net, ["connect", "createConnection"], "socket"], [tls, ["connect"], "tls"],
    [dns, ["lookup", "resolve"], "dns"], [globalThis, ["fetch"], "fetch"],
    [childProcess, ["exec", "execSync", "execFile", "execFileSync", "spawn", "spawnSync"], "subprocess"],
  ]) for (const name of names) block(object, name, kind);
  const oldRead = fs.readFileSync;
  fs.readFileSync = function(file, ...args) {
    if (String(file) === canary) { events.push({ kind: "canary-read" }); throw new Error("Unexpected sensitive file read"); }
    return oldRead.call(this, file, ...args);
  };
  restores.push(() => { fs.readFileSync = oldRead; });
  const previousEnv = process.env;
  process.env = new Proxy(previousEnv, { get(target, key) {
    if (["NPM_TOKEN", "GITHUB_TOKEN", "AWS_SECRET_ACCESS_KEY", "AUDIT_FAKE_CREDENTIAL"].includes(String(key))) { events.push({ kind: "credential-env", key: String(key) }); throw new Error("Unexpected credential environment access"); }
    return Reflect.get(target, key);
  } });
  restores.push(() => { process.env = previousEnv; });
  try {
    const { createJiti } = require("jiti");
    const jiti = createJiti(config, { fsCache: false, moduleCache: false, sourceMaps: false, debug: false });
    const loaded = await jiti.import(config, { default: true });
    assert.deepEqual(loaded, { title: "offline", count: 42 });
    for (const annotation of [`//# sourceMappingURL=${canary}`, `/*# sourceMappingURL=${canary} */`, "//# sourceMappingURL=../.credential-canary.map"]) {
      const output = jiti.transform({ source: `export const answer: number = 42;\n${annotation}`, filename: config, ts: true, babel: { filename: config, inputSourceMap: true, sourceMaps: "inline" } });
      assert.match(output, /answer/); assert.ok(!output.includes(secret));
    }
    assert.deepEqual(events, []);
  } finally { for (const restore of restores.reverse()) restore(); }
});
