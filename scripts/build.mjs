import { verifyVendor } from "./verify-vendor.mjs";
import { copyFile } from "node:fs/promises";
// Verification is completed before importing any third-party build-time code.
verifyVendor();
Object.assign(process.env, { npm_config_offline: "true", npm_config_ignore_scripts: "true", npm_config_registry: "http://127.0.0.1:9/", COREPACK_ENABLE_NETWORK: "0", JITI_FS_CACHE: "false", JITI_SOURCE_MAPS: "false", JITI_DEBUG: "false" });
const { build } = await import("vite");
await build();
await copyFile("dist/index.html", "bundle.html");
console.log("Built dist/index.html and bundle.html entirely from local dependencies.");
