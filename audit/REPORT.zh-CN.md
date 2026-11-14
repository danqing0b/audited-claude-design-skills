# UI 设计 skill 的 npm 全链审计与离线修复

上游基线：`anthropics/skills@2c5958ecac7cee2b583967a2c4981d0f4a75c579`。本衍生库保留 frontend-design、web-artifacts-builder、algorithmic-art、brand-guidelines、canvas-design、theme-factory、webapp-testing 七个相关 skill。

## 结果

交付依赖已固定并下载入库：173 个安装依赖包、143 个从预打包代码识别出的补充对照包、1 个本地嵌入的 p5 包，共 317 个不同包名＋版本。归档约 211 MB，均为普通 Git 文件，不使用需要另行联网下载的 LFS 指针。

安装链包含直接依赖、所有已解析子依赖、可选平台包以及随父包自带的 npm 子包。完整图在 `dependency-graph.json`，没有缺失的必需节点。未安装的可选 peer 不被误算成已安装依赖；使用它们需要另行审计和归档，构建不会自动补全。

317 个原始 npm 发行包的注册表签名全部验证通过。这里的签名/分发比对只验证来源记录与字节一致性，不是大厂背书或安全认证。本地补丁另有自己的哈希，不能冒充 registry 签名过的原始包。

常规静态审查和隔离行为测试未发现额外的隐蔽凭据收集或固定外传行为。已确认问题的修复和非适用公告分别记录在 `advisory-dispositions.json`。原始公告查询保留在 `all-advisories.json`，没有通过删除原始告警来伪造“零漏洞”。

## npm 子包的覆盖

每个安装包都记录了版本、依赖声明、文件归档、SHA-256/SRI、安装脚本、来源、敏感 API 扫描与原生文件清单，见 `packages.json` / `packages.csv`。

内嵌源码不是普通 lockfile 节点时，另外识别它们的版本和所属宿主，见 `embedded-origins.json` / `embedded-packages.json`。对 jiti 还按其发布提交的上游 lockfile 展开了相关运行依赖闭包，进行逐项复核。

Tailwind 的 WASM 可选包内部自带 6 个子包：`@emnapi/core`、`@emnapi/runtime`、`@emnapi/wasi-threads`、`@napi-rs/wasm-runtime`、`@tybys/wasm-util`、`tslib`。前五个是社区生态基础包，不能按“大厂包”自动豁免。六者均纳入审查；父包所带副本中的 71 个 JS/WASM 代码文件与各自 npm 发行包一致，见 `bundled-child-byte-comparison.json`。这项比对不替代源码行为审查。

## 已实施的修复

| 原问题 | 最终处理 |
| --- | --- |
| html-inline 带入旧 minimist 原型污染链 | 完全移除 html-inline、Parcel、parcel-resolver-tspaths 及其相关旧子链。 |
| HTML 内联器根据资源 URL 读取目录外文件 | 改为只内联 bundler 内存输出中的脚本和 CSS，不打开 HTML 提供的文件路径；拒绝外部 URL、越界路径和残留模块导入。 |
| Node 18 分支固定有已知漏洞的 Vite 5.4.11 | 移除遗留分支；使用固定 Node 24 基础镜像、Vite 8.3.8 与匹配的 React 插件。 |
| 运行时脚手架和大量浮动安装 | 改为本地模板；根依赖固定版本、完整 lockfile 与全部本地归档。 |
| 安装或构建可联网补全 | `.npmrc`、安装 CLI 参数、构建环境与 Docker RUN 网络配置多层禁用；缺包立即失败。 |
| jiti 内嵌 Babel 的输入 source map 文件读取漏洞 | 对实际交付的 jiti tarball 做明确标记的本地补丁，删除输入 source map 加载路径；补充 Babel 对照归档也同样修订。 |
| p5 CDN 缺 SRI、Google Fonts 外部请求 | p5 库直接嵌入本地 HTML；字体请求移除，本地字体资源保留。 |
| 固定组件源码与浮动 UI 包版本不匹配 | 更新 Resizable v4 API、DayPicker v10 类名键和 Tailwind v4 主题配置；全部组件通过 TypeScript 检查。 |

## jiti 与 Babel 的具体判断

`jiti@2.7.0` 是 Tailwind 的间接配置加载工具，会转译并执行 JS/TS 模块。它没有普通运行依赖清单，但发行文件中内嵌了 Babel 和模块解析代码。因此仅运行根目录的 npm audit 不足以覆盖该部分。

其 Babel 7.29.0 命中 [CVE-2026-49356 / GHSA-4x5r-pxfx-6jf8](https://github.com/babel/babel/security/advisories/GHSA-4x5r-pxfx-6jf8)。官方公告描述的是：攻击者控制输入代码、能读取编译输出、并知道目标 source map 路径时，可能读取该 map。不能从此直接推断程序会搜索私钥并主动上传。官方提供的缓解方法包括关闭 `inputSourceMap`；官方修复版包括 Babel 7.29.6。

本地修改直接去掉内嵌 Babel 的输入 source map 处理块，防止调用者再次开启该路径；同时通过构建配置关闭 jiti 的磁盘缓存、source map 输出和调试输出。改动前后文件/归档哈希及删除的代码保存在 `jiti-local-patch.json`。包版本仍标为上游 2.7.0，以 `x-audited-local-patch` 标记衍生修改；版本扫描器仍可能报告原版本命中，应查看补丁和回归证据。

使用自建 source map 中的假秘密做对照，未使用真实凭据：

| 检查 | 原始发行代码 | 本地补丁后 |
| --- | --- | --- |
| 读取自建 canary map 的次数 | 1 | 0 |
| 输出 map 含假秘密 | 是 | 否 |

该测试在 UID 1000、只读容器根文件系统、仅回环接口、无网络条件下运行，见 `jiti-focus/regression-control.json`。可信模块加载与不同 sourceMappingURL 写法还经过 HTTP/DNS/socket/子进程/敏感环境变量访问监测，测试未记录额外访问。

jiti 上游源码中的 `import.meta.env` 插件是把 AST 引用改写为 `process.env`，不是在转译时自动提取所有环境变量。jiti 的模块执行和动态编译是其公开功能；它不应被当成执行恶意配置的沙箱。

上游构建闭包还命中 Browserslist / baseline-browser-mapping 的公告，但实际 jiti 将 helper-compilation-targets 替换为固定 stub，这些实现未交付。16 个仅上游构建对照项记录在 `excluded-upstream-build-packages.json`；其原始 npm tarball 没有作为交付依赖入库。

## 离线构建的强制控制

- `package-lock.json` 的可安装 tarball 记录只引用 `file:vendor/...`，随包附带的子包则由已校验父包提供。
- `.npmrc` 强制离线、禁用所有安装脚本、关闭 audit/update 检查与重试，registry 为无服务的回环端口。
- `scripts/offline-build.sh` 显式固定离线参数，并为每次安装创建空缓存，验证不依赖本机缓存。
- `scripts/verify-vendor.mjs` 先检查每个子包的归档、哈希、路径和审计批准，再允许引入第三方构建代码。
- Docker 使用固定 digest 的 Node 镜像，以非 root 用户构建；所有 RUN 层显式无网络。
- 交付 HTML 内联全部默认脚本/CSS，CSP 禁用连接、远程脚本和外部字体。

真实缺包负向测试证明：预检查拒绝缺失子包；即使直接绕过预检查执行 npm ci，缺失本地归档也不会被修复；把子包解析地址改为 registry 后，在空缓存下以 `ENOTCACHED` 失败，见 `offline-negative-result.json`。

GitHub 克隆和 Node/Docker 基础环境准备本身不是 npm 依赖补全。基础镜像必须预先存在；断网阶段不能从外部下载它。

## 验证记录

最终平台、测试数量、构建及浏览器交互结果记录在 `validation.json`，详细构建日志为 `offline-build.log`。构建执行完整 TypeScript 检查、单元回归和实际 Vite 单文件打包。浏览器测试只允许回环地址导航，随后切换离线，记录所有非回环请求与页面异常。

## 审计边界

这是完整解析链的静态安全审查与受控行为验证，不是对未知漏洞不存在的证明。按照用户允许的范围，对知名核心工具保留了深入源码审查豁免，但没有在这些父依赖处截断对子包的枚举；jiti 重点链没有沿用该豁免。

原生/WASM 字节已下载、校验并入清单，未独立反汇编或重现其构建。签名验证采用当前 registry 公钥集，未独立验证每份 Sigstore attestation 和历史签名时间。字体/PDF 为本地数据资源，未做字体/PDF 引擎漏洞研究。其他平台的包虽已保存，实际运行测试以 validation.json 为准。

未纳入与 UI 设计无直接关系的 Office 文档、Claude API、MCP 等独立 skill，也未涵盖后续使用者自行添加的依赖。修改依赖必须重新审计和批准，不应关闭离线控制来临时安装。
