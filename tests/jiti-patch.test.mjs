import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
test("patched jiti transpiles TypeScript without reading sourceMappingURL files", t => {
  const pkg = require.resolve("jiti/package.json");
  const transform = require(path.join(path.dirname(pkg), "dist/babel.cjs"));
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "jiti-source-map-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const canary = path.join(root, "canary.map");
  fs.writeFileSync(canary, JSON.stringify({ version: 3, sources: [], names: [], mappings: "" }));
  const originalRead = fs.readFileSync;
  let attemptedReads = 0;
  fs.readFileSync = function(file, ...args) {
    if (String(file) === canary) { attemptedReads++; throw new Error("source map read is forbidden"); }
    return originalRead.call(this, file, ...args);
  };
  try {
    const result = transform({ source: `export const value: number = 42;\n//# sourceMappingURL=${canary}`, filename: path.join(root, "input.ts"), ts: true, babel: { filename: path.join(root, "input.ts") } });
    assert.equal(result.error, undefined);
    assert.match(result.code, /value/);
    assert.equal(attemptedReads, 0);
  } finally { fs.readFileSync = originalRead; }
});
