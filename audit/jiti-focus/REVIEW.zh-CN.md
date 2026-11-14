# jiti@2.7.0 常规安全复核

核对对象为 npm 发行字节、gitHead `fd3bb289b75ed207edfb686d671ed50144f7e90f` 的上游源码、内嵌 Babel 和相关模块解析辅助代码。40 份上游文件按 Git blob 哈希验证后保存；额外保留 MIT 许可。相关 71 个模块/上游闭包记录及逐项判断见 `package-review.json` / CSV，其中 16 项仅属未交付的上游构建对照。

| 入口 | 行为与判断 |
| --- | --- |
| `lib/jiti.cjs` / `.mjs` | 按需加载本地转译器，无安装生命周期脚本。 |
| `src/babel.ts` | 使用内嵌 Babel 进行 AST 转换；默认 `babelrc:false`、`configFile:false`。已知输入 source map 问题在实际 bundle 中修复。 |
| `src/require.ts` / `resolve.ts` | 读取明确解析到的模块和本地 JSON；node/file/data 协议有显式分支，没有自动下载缺失 npm 包的逻辑。 |
| `src/eval.ts` | 使用 VM/原生 import 执行模块；这是加载器的公开功能，不提供恶意配置沙箱。 |
| `src/cache.ts` | 可将转译结果写入本地缓存。交付构建固定 `JITI_FS_CACHE=false`，减少对历史缓存的信任。 |
| `src/options.ts` | 读取 JITI_* 配置变量；未发现固定读取 NPM/GitHub/AWS 凭据的逻辑。 |
| `import-meta-env.ts` | 对 AST 的环境引用做改写，不自动枚举并嵌入全部凭据。 |
| Babel 插件与 helper | 转换语法、装饰器和模块；未发现默认固定上传端点或额外凭据搜集组合。 |
| mlly / get-tsconfig 等 | 本地模块/配置解析；没有发现依赖缺失时主动联网安装的路径。 |

已公开公告：[Babel 官方 GHSA-4x5r-pxfx-6jf8](https://github.com/babel/babel/security/advisories/GHSA-4x5r-pxfx-6jf8)。公告说明、官方缓解策略与实际代码行为一致；没有根据这项功能和漏洞本身认定为蓄意后门。

`regression-control.json` 保存了假数据对照：原包读取一次自建 map 并将假秘密带入输出 map，补丁后两项均为零。`tests/jiti-behavior.test.mjs` 对可信配置加载及转译的 HTTP、socket、DNS、子进程、敏感环境变量和 canary 文件读取做监测；测试运行于无网络容器中。

本复核未发现额外的、预期之外的凭据窃取或外传行为。此判断不能覆盖所有可能的未知漏洞，调用者仍需只加载可信配置。
