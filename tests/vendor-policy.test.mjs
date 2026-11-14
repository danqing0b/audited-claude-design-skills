import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { verifyVendor } from "../scripts/verify-vendor.mjs";

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "offline-policy-"));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, "audit")); fs.mkdirSync(path.join(root, "vendor/npm"), { recursive: true });
  const manifest = { dependencies: { parent: "1.0.0" } };
  const packages = { "": manifest }; const records = [];
  for (const name of ["parent", "child"]) {
    const archive = `vendor/npm/${name}.tgz`; const bytes = Buffer.from(`fixture-${name}`);
    fs.writeFileSync(path.join(root, archive), bytes);
    const integrity = "sha512-" + crypto.createHash("sha512").update(bytes).digest("base64");
    packages[`node_modules/${name}`] = { version: "1.0.0", resolved: "file:" + archive, integrity, ...(name === "parent" ? { dependencies: { child: "1.0.0" } } : {}) };
    records.push({ name, version: "1.0.0", archive, integrity, sha256: crypto.createHash("sha256").update(bytes).digest("hex"), lock_paths: [`node_modules/${name}`] });
  }
  const write = (p, value) => fs.writeFileSync(path.join(root, p), JSON.stringify(value));
  write("package.json", manifest); write("package-lock.json", { lockfileVersion: 3, packages }); write("audit/packages.json", records);
  fs.writeFileSync(path.join(root, ".npmrc"), "offline=true\nignore-scripts=true\naudit=false\nfetch-retries=0\nregistry=http://127.0.0.1:9/\n");
  return { root, packages, records, write };
}
test("checks children as well as root packages", t => {
  const { root } = fixture(t);
  assert.equal(verifyVendor(root, { requireReview: false }).packages, 2);
});
test("missing transitive archive fails before any npm operation", t => {
  const { root } = fixture(t); fs.unlinkSync(path.join(root, "vendor/npm/child.tgz"));
  assert.throws(() => verifyVendor(root, { requireReview: false }));
});
test("tampered transitive archive fails integrity validation", t => {
  const { root } = fixture(t); fs.appendFileSync(path.join(root, "vendor/npm/child.tgz"), "tampered");
  assert.throws(() => verifyVendor(root, { requireReview: false }), /SHA-256 mismatch/);
});
test("remote lockfile resolution is rejected even when archive exists", t => {
  const { root, packages, write } = fixture(t); packages["node_modules/child"].resolved = "https://registry.npmjs.org/child/-/child-1.0.0.tgz";
  write("package-lock.json", { lockfileVersion: 3, packages });
  assert.throws(() => verifyVendor(root, { requireReview: false }), /checked-in archive/);
});
test("unreviewed or absent child package is rejected", t => {
  const { root, records, write } = fixture(t); write("audit/packages.json", records.filter(p => p.name !== "child"));
  assert.throws(() => verifyVendor(root, { requireReview: false }), /unreviewed transitive/);
});
test("network-capable npm config is rejected", t => {
  const { root } = fixture(t); fs.writeFileSync(path.join(root, ".npmrc"), "offline=false\n");
  assert.throws(() => verifyVendor(root, { requireReview: false }), /offline=true/);
});
test("project lockfile and root dependencies must agree", t => {
  const { root, write } = fixture(t); write("package.json", { dependencies: { parent: "2.0.0" } });
  assert.throws(() => verifyVendor(root, { requireReview: false }), /disagree/);
});
