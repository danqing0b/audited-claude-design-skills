import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const json = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const sorted = (o) => JSON.stringify(Object.entries(o ?? {}).sort(([a], [b]) => a.localeCompare(b)));
function fail(message) { throw new Error(`Offline dependency verification failed: ${message}`); }
function inside(root, relative) {
  if (typeof relative !== "string" || relative.includes("\\") || path.isAbsolute(relative)) fail(`unsafe archive path: ${relative}`);
  const absolute = path.resolve(root, relative);
  if (!absolute.startsWith(path.resolve(root, "vendor") + path.sep)) fail(`archive outside vendor/: ${relative}`);
  if (fs.realpathSync(absolute) !== absolute) fail(`symlinked archive: ${relative}`);
  return absolute;
}
function resolveDependency(packages, from, name) {
  let folder = from;
  while (true) {
    const candidate = `${folder ? folder + "/" : ""}node_modules/${name}`;
    if (packages[candidate]) return candidate;
    if (!folder) return undefined;
    folder = folder.includes("/") ? folder.slice(0, folder.lastIndexOf("/")) : "";
  }
}
export function verifyVendor(root = projectRoot, { requireReview = true } = {}) {
  const manifest = json(path.join(root, "package.json"));
  const lock = json(path.join(root, "package-lock.json"));
  const records = json(path.join(root, "audit/packages.json"));
  const policy = Object.fromEntries(fs.readFileSync(path.join(root, ".npmrc"), "utf8").split(/\r?\n/).filter(l => l.trim() && !l.startsWith("#")).map(l => { const at=l.indexOf("=");return [l.slice(0,at).trim(),l.slice(at+1).trim()]; }));
  for (const [key, expected] of Object.entries({ offline: "true", "ignore-scripts": "true", audit: "false", "fetch-retries": "0", registry: "http://127.0.0.1:9/" })) {
    if (policy[key] !== expected) fail(`.npmrc must set ${key}=${expected}`);
  }
  if (lock.lockfileVersion !== 3) fail("unsupported lockfile format");
  for (const kind of ["dependencies", "devDependencies", "optionalDependencies"]) {
    if (sorted(manifest[kind]) !== sorted(lock.packages[""][kind])) fail(`package.json and lockfile disagree: ${kind}`);
    for (const [name, version] of Object.entries(manifest[kind] ?? {})) {
      if (!/^\d+\.\d+\.\d+(?:-[\w.-]+)?$/.test(version)) fail(`root dependency is not pinned: ${name}`);
    }
  }
  const indexed = new Map();
  const hashes = new Map();
  for (const record of records) {
    const key = `${record.name}@${record.version}`;
    if (indexed.has(key)) fail(`duplicate package record: ${key}`);
    indexed.set(key, record);
    const file = inside(root, record.archive);
    const bytes = fs.readFileSync(file);
    const sha = crypto.createHash("sha256").update(bytes).digest("hex");
    if (sha !== record.sha256) fail(`SHA-256 mismatch: ${key}`);
    const integrity = "sha512-" + crypto.createHash("sha512").update(bytes).digest("base64");
    if (integrity !== record.integrity) fail(`SRI mismatch: ${key}`);
    hashes.set(key, integrity);
  }
  const used = new Set();
  let edges = 0;
  for (const [location, pkg] of Object.entries(lock.packages)) {
    if (!location) continue;
    if (pkg.link) fail(`unapproved linked dependency: ${location}`);
    const name = location.split("node_modules/").at(-1);
    const key = `${name}@${pkg.version}`;
    const record = indexed.get(key);
    if (!record) fail(`unreviewed transitive package: ${key}`);
    used.add(key);
    if (!record.lock_paths.includes(location)) fail(`unexpected package location: ${location}`);
    if (pkg.inBundle) {
      const parent = location.slice(0, location.lastIndexOf("/node_modules/"));
      if (!lock.packages[parent]?.resolved?.startsWith("file:vendor/")) fail(`untracked bundled parent: ${location}`);
    } else if (pkg.resolved !== "file:" + record.archive || pkg.integrity !== hashes.get(key)) {
      fail(`dependency must resolve to its checked-in archive: ${key}`);
    }
    for (const kind of ["dependencies", "optionalDependencies"]) {
      for (const dependency of Object.keys(pkg[kind] ?? {})) {
        if (!resolveDependency(lock.packages, location, dependency)) fail(`missing ${kind} child ${dependency} of ${key}`);
        edges++;
      }
    }
  }
  if (used.size !== indexed.size) fail("inventory contains unreferenced install archives");
  if (requireReview) {
    const review = json(path.join(root, "audit/review.json"));
    if (review.status !== "accepted-static-audit" || review.blockers?.length !== 0) fail("audit has open blockers");
    for (const [key, integrity] of hashes) if (review.approvedIntegrities[key] !== integrity) fail(`not approved after audit: ${key}`);
    if (review.packageLockSha256 !== crypto.createHash("sha256").update(fs.readFileSync(path.join(root, "package-lock.json"))).digest("hex")) fail("lockfile changed after review");
    for (const file of review.extraFiles ?? []) {
      const target = path.resolve(root, file.path);
      if (!target.startsWith(path.resolve(root) + path.sep)) fail("invalid supplemental evidence path");
      if (crypto.createHash("sha256").update(fs.readFileSync(target)).digest("hex") !== file.sha256) fail(`changed supplemental evidence: ${file.path}`);
    }
  }
  return { packages: indexed.size, dependencyEdges: edges, policy: "offline; local archives only; lifecycle scripts disabled" };
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { console.log(JSON.stringify(verifyVendor())); }
  catch (error) { console.error(error.message); process.exitCode = 1; }
}
