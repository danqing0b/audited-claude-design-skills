import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { verifyVendor } from "./verify-vendor.mjs";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
verifyVendor(root);
if (!process.argv[2]) throw new Error("Usage: node scripts/init-project.mjs <new-directory>");
const target = path.resolve(process.argv[2]);
if (target === root || fs.existsSync(target)) throw new Error("Target must be a new directory; existing files are never overwritten");
fs.mkdirSync(target);
for (const name of ["package.json", "package-lock.json", ".npmrc", ".gitignore", ".gitattributes", ".dockerignore", "tsconfig.json", "vite.config.mjs", "index.html", "Dockerfile", "LICENSE", "THIRD_PARTY_NOTICES.txt", "README.md", "src", "scripts", "tests", "vendor", "audit", "skills", "tools"]) {
  fs.cpSync(path.join(root, name), path.join(target, name), { recursive: true, errorOnExist: true });
}
console.log(`Created local project at ${target}. Run bash scripts/offline-build.sh in that directory.`);
