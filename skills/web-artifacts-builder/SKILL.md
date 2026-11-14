---
name: web-artifacts-builder
description: Build React UI artifacts from a pinned, vendored offline template, with local shadcn components and a verified single-file output.
license: Complete terms in LICENSE.txt; third-party components retain their original notices.
---

# Web Artifacts Builder — audited offline derivative

This derivative replaces upstream runtime dependency installation and Parcel/html-inline bundling. The repository root is the complete application template. Do not run npm/pnpm create, npx, npm add, online installs, or CDN loaders.

## Initialize

From the repository root, run:

```bash
bash skills/web-artifacts-builder/scripts/init-artifact.sh /absolute/path/to/new-project
```

The initializer verifies all vendored dependency archives before copying the template, audit manifest, configuration, and archives into a new directory. It refuses to overwrite an existing directory. A supported Node 24/npm 11 installation must already exist.

## Develop

Edit `src/`. The template contains React, TypeScript, Tailwind CSS 4, and 43 local UI components. Imports use `@/components/ui/...`. Resizable components use the v4 Group/Separator API. Preserve accessible focus and reduced-motion support.

Use CSS theme variables in `src/index.css`; do not introduce executable Tailwind configuration, remote plugins, downloaded fonts, or unreviewed packages. Existing npm packages and all installed child packages are fixed in `package-lock.json` and `vendor/npm/`.

## Build

```bash
bash scripts/offline-build.sh
```

This verifies archive hashes and audit approval, runs `npm ci --offline --ignore-scripts` with an empty temporary cache and a disabled registry, then runs TypeScript checking, regression tests, and the build. A missing or changed dependency fails; it is never fetched automatically.

For OS-level network isolation use the repository Dockerfile and the command in README.md. Both Docker's build network and the dependency installation are disabled. Bootstrap the pinned Node image separately if it is not already local.

## Output

The outputs are `dist/index.html` and `bundle.html`. JavaScript and CSS are taken only from the bundler's in-memory output map. The inliner does not open resource paths supplied by HTML. The artifact uses a CSP that disables network connections.

## Security maintenance

Changes to dependencies require an explicit maintainer refresh, complete child-package review, vendoring, updated approval hashes, and a fresh empty-cache/no-network build. Do not disable the offline configuration to make an ordinary build pass.

This is a static audit with documented limits, not proof that third-party code is free of every vulnerability. See the repository's audit report and jiti-focused review before changing its security controls.
