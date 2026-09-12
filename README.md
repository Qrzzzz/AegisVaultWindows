<div align="center">

# 🛡️ AegisVault Windows

### 面向 Windows 的本地文本与文件加密工具

**WinUI 3 原生界面 · AES-256-GCM · scrypt · AGV1 · 本地运行 · 无账户 / 无云同步 / 无遥测**

<p>
  <strong>语言</strong><br/>
  <strong>简体中文</strong> ·
  <a href="./README.en.md">English</a>
</p>

<p>
  <strong>导航</strong><br/>
  <a href="https://github.com/Qrzzzz/AegisVaultWindows/releases/latest">下载最新版</a> ·
  <a href="./docs/releases/v2.8.md">发布说明</a> ·
  <a href="#主要功能">主要功能</a> ·
  <a href="./docs/SECURITY_MODEL.md">安全模型</a> ·
  <a href="./docs/PROTOCOL.md">AGV1 协议</a> ·
  <a href="#本地开发">本地开发</a> ·
  <a href="./LICENSE">许可证</a>
</p>

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D4)
![UI](https://img.shields.io/badge/UI-WinUI%203-5E5E5E)
![Stack](https://img.shields.io/badge/Stack-C%23%20%2B%20Python-512BD4)
![Crypto](https://img.shields.io/badge/Crypto-AES--256--GCM%20%2B%20scrypt-0F766E)
![Format](https://img.shields.io/badge/Format-AGV1-7C3AED)
![Release](https://img.shields.io/github/v/release/Qrzzzz/AegisVaultWindows)
![License](https://img.shields.io/github/license/Qrzzzz/AegisVaultWindows)

</div>

---

> [!NOTE]
> AegisVault 是一个**密码驱动的文本与文件加密工具**，不是密码管理器。应用不会保存你的加密密码，也不提供账户、云端保险库或密码找回服务。

## 📦 下载与运行

从 [GitHub Releases](https://github.com/Qrzzzz/AegisVaultWindows/releases/latest) 下载最新稳定版本。

当前稳定版为 **AegisVault 2.8**，主要发布文件包括：

| 文件                          | 用途                     |
| --------------------------- | ---------------------- |
| `AegisVault-v2.8-win64.zip` | Windows x64 应用程序       |
| `AegisVault-v2.8.cdx.json`  | CycloneDX 软件物料清单（SBOM） |
| `SHA256SUMS`                | 发布文件 SHA-256 校验值       |

使用方法：

1. 下载并**完整解压** `AegisVault-v2.8-win64.zip`。
2. 保持 `AegisVault.exe`、`backend` 目录及其余运行时文件位于原有目录结构中。
3. 运行 `AegisVault.exe`。

### 系统要求

* Windows 10 Version 2004（Build 19041）或更新版本
* Windows 11
* x64 处理器

发布包已经包含应用运行所需的 Python、.NET 与 Windows App SDK 运行时，无需用户单独安装开发环境。

在受支持的 Windows 11 系统上，AegisVault 会使用 Mica 等原生 Windows 视觉效果。

> [!IMPORTANT]
> 发布流程支持可选代码签名，但“支持签名”并不代表某个具体发布文件一定具有 Authenticode 签名。如需确认，请检查下载文件本身的数字签名及发布校验值。

## ✨ v2.8 更新重点

文件队列分别显示已处理／待处理数量，以及当前文件的百分比和字节进度。处理期间追加或移除待处理文件，会及时更新数量，不再让整体百分比的变化造成误解。

新增仅看失败项、将全部失败项重新加入队列和清除已完成项。成功结果保留在队列中，展开即可查看输出详情；清除记录不会删除磁盘文件。真实 Explorer 多文件拖放、跨页路由、处理中追加和文件夹拒绝均已通过自动化验收。

详情见 [v2.8 发布说明](./docs/releases/v2.8.md) 和 [验收记录](./docs/ACCEPTANCE_2.8.md)。AGV1、文本操作和设置存储保持兼容；早期更新见 [变更记录](./CHANGELOG.md)。

<a id="主要功能"></a>

## ✨ 主要功能

### 🔐 文本加密与解密

* 使用密码加密和解密 UTF-8 文本。
* 新加密文本采用 `AGV1.<base64url-envelope>` 格式。
* 使用 **AES-256-GCM** 提供机密性与完整性验证。
* 使用 **scrypt** 从用户密码派生加密密钥，并为每次加密使用随机 salt。
* 加密时要求再次确认密码，降低输入错误导致数据无法恢复的风险。
* 支持从 UTF-8 文本文件导入内容。
* 加密或解密结果可直接复制、保存，或重新作为下一次操作的输入。
* 对文本输入与 IPC 传输设置明确的资源上限，避免异常大输入破坏桌面端与后端之间的边界。

### 📁 文件加密与解密

* 使用 `.agv` 作为现代加密文件容器。
* 文件采用分块 AES-256-GCM 加密，不需要一次性将整个文件加载进内存。
* 每个数据块都会绑定文件头摘要、块索引及结束标记进行认证。
* 可以检测文件头篡改、数据块篡改、截断、缺失结束块、非法块长度以及异常尾随数据。
* 支持文件选择与拖放。
* 支持选择输出目录。
* 提供操作进度、取消操作、打开结果目录和复制结果路径。
* 写入流程使用临时文件，并在成功后执行原子替换；失败或取消时会尝试清理临时输出。

### 🧾 Base64 工具

AegisVault 同时提供独立的 Base64 文本与文件工作流：

* Base64 文本编码与解码。
* Base64 文件编码与解码。
* 文本解码默认采用严格模式。
* 可显式允许忽略 ASCII 空白字符。
* 文件操作会检查可检测到的输入文件变更，并在输入发生变化时放弃临时输出。

> [!WARNING]
> **Base64 不是加密。**
>
> Base64 只是一种编码方式，不提供机密性、身份验证或防篡改能力。需要保护数据时应使用 AegisVault 的 AGV1 加密功能。

### ⚙️ 设置与本地体验

* 简体中文 / English 两种界面语言。
* 跟随系统 / 浅色 / 深色三种主题模式。
* 可配置默认输出目录。
* 可选择是否允许覆盖已有文件。
* 支持最近文件记录及一键清除。
* 页面草稿在导航过程中保留，直到保存或放弃。
* 设置保存在：

```text
%LOCALAPPDATA%\AegisVault\settings.json
```

* 损坏或非法的设置 JSON 会安全回退到默认值，并可通过重新保存设置完成修复。
* 2.2 及之后的后端使用跨进程设置事务，降低多个 AegisVault 进程同时修改配置时发生竞争的风险。

### 🪟 原生 Windows 界面

AegisVault 当前生产界面完全使用 **C#、WinUI 3 与 Windows App SDK** 构建，不保留旧版桌面前端。

* 原生 Windows NavigationView 与页面结构。
* 支持 Windows 11 Mica。
* 操作按钮与反馈区域在表单滚动时保持可访问。
* 结果命令会适应较窄窗口。
* 文本、文件与 Base64 工作流共享一致的交互模式。
* 桌面端通过受约束的 JSON Lines IPC 与随应用打包的本地 Python 后端通信。

应用本身不提供账户系统、网络服务、云同步或遥测。

## 🔒 加密设计

AegisVault 当前只生成并接受现代 **AGV1** 格式。

### 文本

```text
AGV1.<base64url-envelope>
```

文本信封包含：

* `AGVTEXT\x01` magic
* 规范化 UTF-8 JSON header
* AES-GCM ciphertext 与 authentication tag

协议头本身会作为 AES-GCM AAD 参与认证。

### 文件

`.agv` 文件以 `AGVFILE\x01` 开始，并采用分块加密。

当前默认 scrypt 参数为：

```text
N = 32768
r = 8
p = 1
salt_len = 16
key_len = 32
```

解密器会拒绝不安全或畸形的 KDF 参数。

完整格式定义见 [AGV1 Protocol](./docs/PROTOCOL.md)。

## 🔁 格式兼容性

* AegisVault 1.x 生成的 **AGV1** 数据继续保持兼容。
* 当前版本继续读写 AGV1 version 1。
* 旧 AES 文本 / 文件格式与 AK wrapper 已移除。
* 非 AGV1 数据无法通过修改扩展名转换为 AGV1。
* Base64 工具不会尝试解密旧格式数据。

如从旧版本迁移，请阅读 [Migration Guide](./docs/MIGRATION.md)。

## 🛡️ 安全边界

AegisVault 的目标是保护**已经通过强密码和 AGV1 加密的数据**，但它不是完整的终端安全解决方案。

### AegisVault 会做什么

* 不保存用户密码。
* 使用随机 salt 与 scrypt 派生密钥。
* 使用 AES-256-GCM 验证密文完整性。
* 对文件进行经过认证的分块加密。
* 尽可能通过临时文件和原子写入降低失败操作留下不完整输出的风险。
* 在日志与协议层面对敏感信息处理进行约束。

### AegisVault 无法防御什么

它无法保护你免受以下情况影响：

* 主机已经感染恶意软件。
* 远程控制软件正在监控设备。
* 剪贴板监听。
* 屏幕录制或截图。
* 弱密码或重复使用的密码。
* 明文已经被复制到其他位置。
* 已泄露或不安全的备份。
* 未锁定设备上的物理访问。
* 用户遗失加密密码。

AegisVault **没有经过独立第三方安全审计**。请根据数据敏感程度自行评估使用风险。

另外，加密文件的内容会受到保护，但文件名、路径、时间戳、文件大小等元数据仍可能泄露信息。

完整威胁模型见 [Security Model](./docs/SECURITY_MODEL.md)。安全问题报告方式见 [SECURITY.md](./SECURITY.md)。

## 🧩 技术架构

| 层            | 技术                                           | 职责                                   |
| ------------ | -------------------------------------------- | ------------------------------------ |
| Windows UI   | C# · .NET · WinUI 3 · Windows App SDK        | 原生窗口、导航、工作流与本地化                      |
| IPC          | Versioned JSON Lines                         | 桌面端与本地后端通信                           |
| Backend      | Python 3.11–3.13                             | 工作流、验证、文件与设置服务                       |
| Cryptography | `cryptography` · AES-256-GCM · scrypt        | 加密、认证与密钥派生                           |
| Format       | AGV1                                         | 文本 token 与 `.agv` 文件容器               |
| Packaging    | self-contained x64 ZIP                       | 打包 Python、.NET 与 Windows App SDK 运行时 |
| Validation   | pytest · C# IPC tests · native UI automation | 协议、核心逻辑、发布契约与原生界面验证                  |

## 📚 项目文档

| 文档                                                   | 内容                       |
| ---------------------------------------------------- | ------------------------ |
| [Security Model](./docs/SECURITY_MODEL.md)           | 威胁模型、安全能力与限制             |
| [AGV1 Protocol](./docs/PROTOCOL.md)                  | 文本与文件加密格式                |
| [Backend Protocol](./docs/BACKEND_PROTOCOL.md)       | WinUI 与 Python 后端 IPC 协议 |
| [Migration Guide](./docs/MIGRATION.md)               | 旧版本与格式迁移边界               |
| [QA Checklist](./docs/QA_CHECKLIST.md)               | 发布前质量检查                  |
| [Release Engineering](./docs/RELEASE_ENGINEERING.md) | 构建与发布工程                  |
| [v2.8 Acceptance](./docs/ACCEPTANCE_2.8.md)          | 当前版本执行过的验收项目             |

## AegisVault Web

`web/` 是独立的 Vite + TypeScript + 原生 HTML/CSS 纯静态应用，首版仅支持 **AGV1 文本加密/解密**和**严格 UTF-8 Base64**。不修改 Windows 端逻辑，也不引入新加密格式；Windows 与 Web 生成的 `AGV1.` 文本密文可以互相解密。

所有计算在浏览器本地完成。AES-256-GCM 使用原生 Web Crypto，固定版本并本地打包的 `@noble/hashes` scrypt 在独立 Web Worker 中运行。加密采用随机 16 字节 salt、12 字节 nonce、桌面默认 KDF 参数、canonical JSON header、原始 header 字节 AAD、Big Endian 长度和无填充 Base64URL。解密前验证 header 与 KDF 内存/计算边界，文本上限直接复用 `src/aegisvault/text_limits.json`。

**Base64 不是加密。**严格解码拒绝空白、非法字符、缺失或多余填充以及非 UTF-8 输出，首版不提供宽松模式。编解码保留空文本、Unicode 与 UTF-8 BOM，不规范化或裁剪密码。

网页不使用运行时 CDN、Analytics、远程 API 或字体服务，不上传内容，不向 localStorage、sessionStorage 或应用数据库写入密码、明文或密文。切换工作区或清空会丢弃当前字段，取消会终止 Worker；复制操作由用户主动触发并写入系统剪贴板。JavaScript 无法保证擦除所有内存副本。

**Web 页面的供应链信任模型与已安装的 Windows 应用不同。**每次加载网页都依赖站点维护者、GitHub Pages 分发、浏览器及 JavaScript 构建与依赖链。浏览器本地计算无法抵御被篡改的页面或恶意扩展；**高敏感数据仍优先推荐桌面版**。

安装 Node.js 24 和仓库 Python 开发环境后：

```powershell
cd web
npm ci
npm test
npm run build
npx playwright install chromium
npm run test:browser
npm run preview
```

打开 `http://localhost:4173/AegisVaultWindows/`。需要支持 Web Crypto 与 Worker 的现代浏览器，以及 HTTPS 或 localhost 环境；不支持通过 `file://` 直接打开。

Python 与 Web 测试共同读取 `tests/fixtures/agv1-text.json`，验证固定密文逐字节一致及真实 Python ↔ Web 双向兼容，并覆盖 malformed token、错误密码、Unicode、重复 JSON 键、header/KDF 边界与严格 Base64。`npm test` 优先使用仓库 `.venv`；也可通过 `AEGISVAULT_PYTHON` 指定已安装 `cryptography` 的解释器。浏览器测试覆盖生产构建、Worker、取消、复制、窄屏/深色布局及无外部请求和存储。

独立的 [Web Pages workflow](.github/workflows/web-pages.yml) 在相关 PR 和推送上测试、构建，仅将默认分支的 `web/dist` 部署到 Pages。首次需在仓库 **Settings → Pages → Build and deployment** 中选择 **GitHub Actions**，必要时在默认分支手动运行 **AegisVault Web Pages**。

Vite base 为 `/AegisVaultWindows/`，部署成功后的预期地址为 [AegisVault Web](https://qrzzzz.github.io/AegisVaultWindows/)。本地构建通过不代表站点已发布。参见 [Vite Pages 部署说明](https://vite.dev/guide/static-deploy#github-pages)。

<a id="本地开发"></a>

## 🛠️ 本地开发

开发环境需要：

* Windows
* `global.json` 指定的 .NET SDK
* Python 3.11–3.13
* PowerShell

初始化环境：

```powershell
python -m venv .venv
.\scripts\install_locked_dependencies.ps1
.\scripts\run_dev.ps1
```

`run_dev.ps1` 会启动 WinUI 桌面应用。

如果单独执行：

```powershell
python -m aegisvault.backend
```

启动的是 JSON Lines 本地后端，而不是桌面窗口。

如果使用独立安装的 .NET SDK，可以在运行脚本前设置：

```powershell
$env:AEGISVAULT_DOTNET = "C:\path\to\dotnet.exe"
```

### 验证与构建

```powershell
.\scripts\verify_release.ps1
.\scripts\build_windows.ps1 -Clean -Zip
.\scripts\test_winui.ps1
.\scripts\test_winui.ps1 -Theme dark -Language zh-CN
```

原生 UI 测试需要交互式 Windows 桌面环境。测试会启动实际发布后的 `AegisVault.exe`，使用隔离设置目录和合成测试数据，并将证据截图写入：

```text
build/native-evidence
```

仅通过源码测试或后端 smoke test，不能替代原生 UI 与人工验收。

## 🗂️ 项目结构

```text
src/AegisVault.App/       C# WinUI 窗口、页面、ViewModel、IPC 客户端与本地化资源
src/aegisvault/core/      AGV1、密码学、KDF 与原子文件操作
src/aegisvault/services/  文件命名与工作流服务
src/aegisvault/settings/  配置验证、持久化与跨进程锁
src/aegisvault/backend/   版本化 JSON Lines 本地服务
web/                     浏览器本地 AGV1 文本加密与严格 Base64
tests/                    Core、协议、IPC、发布契约与原生 UI 自动化测试
scripts/                  验证、打包、审计、SBOM 与发布工具
docs/                     协议、安全模型、迁移、QA 与版本验收文档
```

Python 与 NuGet 依赖均通过 lock file 固定。发布流程同时生成软件物料清单与校验值，以提高发布产物的可追溯性。

## 🙏 致谢

感谢构成 AegisVault 技术基础的开源项目与生态，包括：

[Windows App SDK](https://github.com/microsoft/WindowsAppSDK) ·
[.NET](https://github.com/dotnet) ·
[Python](https://www.python.org/) ·
[cryptography](https://github.com/pyca/cryptography) ·
[PyInstaller](https://pyinstaller.org/) ·
[pytest](https://pytest.org/) ·
[CycloneDX](https://cyclonedx.org/)

这些项目分别为原生 Windows 界面、运行时、密码学实现、测试以及发布供应链提供了基础设施。

## 📄 许可证

AegisVault 采用 [MIT License](./LICENSE)。

你可以在 MIT License 条款下使用、复制、修改、合并、发布、分发、再许可或销售本软件的副本。

> 加密软件并不能自动保证使用场景安全。对于高敏感度数据，请结合独立审计的软件、可靠备份、强密码以及安全的终端环境进行风险评估。
