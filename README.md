# Audited Claude Design Skills

这是基于 [anthropics/skills](https://github.com/anthropics/skills) 提交 `2c5958ecac7cee2b583967a2c4981d0f4a75c579` 的私有衍生仓库，包含与 UI/视觉设计直接相关的七个 skill，以及修复后的离线 UI 模板。

## 从本地依赖构建

预先安装 Node 24 和 npm 11，然后在仓库根目录运行：

```bash
bash scripts/offline-build.sh
```

所有安装依赖都通过 Git 保存为普通 npm tarball，包括直接依赖、间接子包和可选平台包；不使用 Git LFS，也不依赖本机预热缓存。`package-lock.json` 的可安装记录只引用 `file:vendor/...`。随父包打包的子包另有清单和归档。

`.npmrc` 强制 `offline=true`、`ignore-scripts=true`，registry 指向无服务的本机端口。构建入口还通过命令参数固定这些设置。缺包、哈希变化、lockfile 变化或未完成审计都会先失败，普通构建不会联网补全。

安装忽略全部生命周期脚本。支持的平台依赖必须预先归档；不能用现场 node-gyp 编译或下载缺失的原生绑定作为兜底。

## 操作系统级断网构建

先在有网络的准备阶段获取已经固定 digest 的 Node 基础镜像：

```bash
docker pull node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c
```

然后执行：

```bash
docker build --pull=false --network=none --no-cache --output type=local,dest=./.cache/offline-output .
```

Dockerfile 的安装/检查/测试/构建层也显式设置 `RUN --network=none`。镜像不存在时应在准备阶段获取；断网构建阶段不会补全它。GitHub 拉取和基础镜像准备需要网络，与 npm 的断网安装/构建阶段分开。

输出位于 `.cache/offline-output/dist/index.html` 和 `.cache/offline-output/bundle.html`。本次实际验证的平台见 `audit/validation.json`；保存其他平台包不代表已在其他平台运行测试。

## 使用 skill 与模板

核心设计指引是 `skills/frontend-design/SKILL.md`，它不安装 npm 包。复杂交互页面使用修订后的 `skills/web-artifacts-builder/SKILL.md`。

创建独立项目：

```bash
bash skills/web-artifacts-builder/scripts/init-artifact.sh /absolute/path/to/new-project
```

初始化器只复制本仓库已有的模板、配置和归档，不运行联网脚手架。目标必须是新目录。

web-artifacts-builder 需要保留完整仓库克隆，不能只复制单个 SKILL.md 后期待它从网络补全模板和依赖。

本地 UI 源码在 `src/components/ui/`，主题在 `src/index.css`。已迁移至 Tailwind CSS 4 并修正 Resizable 的 v4 API。打包时不再使用 Parcel、parcel-resolver-tspaths、html-inline 及其旧 minimist 子链。

算法艺术模板的 p5 库已嵌入 HTML；不再请求 CDN 或 Google Fonts。原始字体和主题 PDF 作为本地静态资源保留。

## jiti 专项修复

`jiti@2.7.0` 是 Tailwind 配置加载链的间接依赖。它内嵌的 Babel 7.29.0 命中 [CVE-2026-49356 / GHSA-4x5r-pxfx-6jf8](https://github.com/babel/babel/security/advisories/GHSA-4x5r-pxfx-6jf8)。这是调试 source map 处理的已知文件读取漏洞；没有据此认定它为蓄意后门。

本仓库使用明确标记的本地修订版 tarball，移除了 Babel 输入 source map 的加载路径，并记录修改前后的哈希和被删除的代码。补充审计所保存的 Babel 源码归档也做同等修订。补丁不冒充官方新版本，原始版本号保留用于溯源；registry 签名验证的是官方原始包，不是本地补丁。

构建额外禁用 jiti 的磁盘缓存、source map 输出和调试输出。jiti 仍然是会执行 JS/TS 配置的工具，不是运行不可信代码的沙箱；无网络 Docker 环境不挂载主机凭据。

完整调用链、逐包记录和隔离测试见 `audit/jiti-focus/`。审计证据与边界见 `audit/REPORT.zh-CN.md`。

## 更新依赖

普通使用者不需要运行 `tools/`。这些脚本用于维护者明确授权的联网取证、重新解析、下载、签名检查和归档；不会由 install/build 自动调用。

依赖更新后必须重新完成全链静态审查、处理公告、审查内嵌模块、重建本地补丁、更新 `audit/review.json`，并重复空缓存断网测试。没有新的审计批准时，构建校验应拒绝运行。

许可保留在各 skill 目录和 `THIRD_PARTY_NOTICES.txt`。npm 依赖许可证随 tarball 保存，p5 的许可证另存于 `vendor/runtime/`。
