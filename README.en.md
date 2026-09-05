<div align="center">

# 🛡️ AegisVault

### Local text and file encryption for Windows

**Native WinUI 3 · AES-256-GCM · scrypt · AGV1 · Local operation · No accounts / cloud sync / telemetry**

<p>
  <strong>Language</strong><br/>
  <a href="./README.md">简体中文</a> ·
  <strong>English</strong>
</p>

<p>
  <strong>Navigation</strong><br/>
  <a href="https://github.com/Qrzzzz/AegisVaultWindows/releases/latest">Download</a> ·
  <a href="./docs/releases/v2.5.md">Release Notes</a> ·
  <a href="#features">Features</a> ·
  <a href="./docs/SECURITY_MODEL.md">Security Model</a> ·
  <a href="./docs/PROTOCOL.md">AGV1 Protocol</a> ·
  <a href="#development">Development</a> ·
  <a href="./LICENSE">License</a>
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
> AegisVault is a **password-based text and file encryption utility**, not a password manager. It does not store encryption passwords and does not provide accounts, a cloud vault, or password recovery.

## 📦 Download and run

Download the latest stable build from [GitHub Releases](https://github.com/Qrzzzz/AegisVaultWindows/releases/latest).

The current stable release is **AegisVault 2.5**. Its primary release artifacts are:

| File                        | Purpose                                 |
| --------------------------- | --------------------------------------- |
| `AegisVault-v2.5-win64.zip` | Windows x64 application                 |
| `AegisVault-v2.5.cdx.json`  | CycloneDX software bill of materials    |
| `SHA256SUMS`                | SHA-256 checksums for release artifacts |

To run AegisVault:

1. Download and **fully extract** `AegisVault-v2.5-win64.zip`.
2. Keep `AegisVault.exe`, the `backend` directory, and the bundled runtime files in their original directory structure.
3. Run `AegisVault.exe`.

### System requirements

* Windows 10 Version 2004 / Build 19041 or newer
* Windows 11
* x64 processor

The release package includes the Python, .NET, and Windows App SDK runtimes required by the application. End users do not need to install a development environment.

On supported Windows 11 systems, AegisVault uses native Windows effects such as Mica.

> [!IMPORTANT]
> The release pipeline supports optional signing, but signing support does not mean that a particular artifact necessarily carries an Authenticode signature. Verify the downloaded binary itself and the published checksums when signature status matters.

## ✨ What's new in v2.5

AegisVault 2.5 primarily tightens error handling between the native desktop client and its local backend:

* Malformed or truncated UTF-8 from a faulty backend is consistently mapped to `ipc.invalid_response` instead of exposing a raw `DecoderFallbackException`.
* Valid non-BMP Unicode characters remain intact even when split across transport reads.
* Existing repairs for Base64 source-mutation rollback, malformed settings recovery, and process-shared settings transactions are retained and revalidated.
* AGV1, scrypt, AES-256-GCM, the settings schema, and the WinUI interface remain compatible. Legacy decryption formats have not been restored.

See the full [v2.5 release notes](./docs/releases/v2.5.md) and [v2.5 acceptance record](./docs/ACCEPTANCE_2.5.md).

<a id="features"></a>

## ✨ Features

### 🔐 Text encryption and decryption

* Encrypt and decrypt UTF-8 text using a user-supplied password.
* Newly encrypted text uses the `AGV1.<base64url-envelope>` format.
* Uses **AES-256-GCM** for authenticated encryption.
* Uses **scrypt** with a random salt to derive encryption keys from passwords.
* Requires password confirmation when encrypting to reduce accidental unrecoverable input mistakes.
* Import text from UTF-8 files.
* Copy, save, or immediately reuse generated results as the input of another operation.
* Applies explicit text and IPC resource limits to keep the desktop/backend boundary bounded and predictable.

### 📁 File encryption and decryption

* Uses `.agv` as the modern encrypted file container.
* Encrypts files with chunked AES-256-GCM instead of loading an entire file into memory.
* Each encrypted chunk authenticates the header hash, chunk index, and final-chunk flag.
* Detects header tampering, chunk tampering, truncation, missing final chunks, invalid chunk lengths, and unexpected trailing data.
* Select or drag and drop input files.
* Choose the destination directory.
* View progress and cancel long-running operations.
* Open the result directory or copy the result path after completion.
* Write workflows use temporary files and atomic replacement on success, with cleanup attempted after failures or cancellation.

### 🧾 Base64 tools

AegisVault also provides independent Base64 workflows for text and files:

* Base64 text encoding and decoding.
* Base64 file encoding and decoding.
* Strict text decoding by default.
* Optional explicit handling of ASCII whitespace.
* File operations detect observable changes to the opened input and discard temporary output when the input changes.

> [!WARNING]
> **Base64 is not encryption.**
>
> Base64 is an encoding format. It provides no confidentiality, authentication, or tamper resistance. Use AGV1 encryption when the data needs protection.

### ⚙️ Settings and local experience

* Simplified Chinese / English interface.
* System / light / dark appearance modes.
* Configurable default output directory.
* Optional overwrite behavior.
* Recent-file history and one-click clearing.
* Unsaved page drafts survive navigation until explicitly saved or discarded.
* Configuration is stored at:

```text
%LOCALAPPDATA%\AegisVault\settings.json
```

* Invalid or malformed settings JSON safely falls back to defaults and can be repaired by saving settings again.
* The 2.2+ backend serializes cooperating settings mutations across processes to reduce configuration races.

### 🪟 Native Windows interface

The production AegisVault interface is implemented entirely with **C#, WinUI 3, and Windows App SDK**. No legacy desktop frontend remains.

* Native Windows NavigationView and page structure.
* Mica on supported Windows 11 systems.
* Workflow actions and feedback remain accessible while forms scroll.
* Result commands adapt to narrower windows.
* Text, file, and Base64 workflows use a consistent interaction model.
* The native client communicates with the bundled local Python backend through a bounded, versioned JSON Lines protocol.

AegisVault does not add an account system, network service, telemetry, or cloud synchronization.

## 🔒 Cryptographic design

AegisVault currently generates and accepts the modern **AGV1** format.

### Text

```text
AGV1.<base64url-envelope>
```

A text envelope contains:

* `AGVTEXT\x01` magic
* Canonical UTF-8 JSON header
* AES-GCM ciphertext and authentication tag

The protocol header is authenticated as AES-GCM additional authenticated data.

### Files

`.agv` files begin with `AGVFILE\x01` and use authenticated chunked encryption.

The current default scrypt parameters are:

```text
N = 32768
r = 8
p = 1
salt_len = 16
key_len = 32
```

Decryptors reject unsafe or malformed KDF parameters.

See the complete [AGV1 Protocol](./docs/PROTOCOL.md) for the wire-format specification.

## 🔁 Format compatibility

* **AGV1** data created by AegisVault 1.x remains compatible.
* AegisVault 2.5 continues to read and write AGV1 version 1.
* Legacy AES text/file formats and AK wrappers have been removed.
* Renaming a non-AGV1 file does not convert it to AGV1.
* Base64 tools do not decrypt legacy encrypted formats.

See the [Migration Guide](./docs/MIGRATION.md) when moving from older versions.

## 🛡️ Security boundaries

AegisVault is designed to protect data **after it has been encrypted with a strong password and AGV1**. It is not a complete endpoint-security solution.

### What AegisVault does

* Does not store user passwords.
* Derives keys using scrypt with random salts.
* Uses AES-256-GCM for authenticated encryption.
* Authenticates individual file chunks.
* Uses temporary files and atomic writes where applicable to reduce incomplete output after failed operations.
* Constrains sensitive information across its logging and protocol boundaries.

### What AegisVault cannot protect against

AegisVault cannot protect data from:

* Malware already running on the host.
* Remote-control software monitoring the machine.
* Clipboard monitoring.
* Screen recording or screenshots.
* Weak or reused passwords.
* Plaintext already copied elsewhere.
* Compromised or insecure backups.
* Physical access to an unlocked computer.
* A lost encryption password.

AegisVault **has not been independently security audited**. Evaluate that limitation according to the sensitivity of your data.

Encrypted file contents are protected, but metadata such as filenames, paths, timestamps, and file sizes may still reveal information.

See the complete [Security Model](./docs/SECURITY_MODEL.md). For vulnerability reporting, see [SECURITY.md](./SECURITY.md).

## 🧩 Architecture

| Layer        | Technology                                   | Responsibility                                             |
| ------------ | -------------------------------------------- | ---------------------------------------------------------- |
| Windows UI   | C# · .NET · WinUI 3 · Windows App SDK        | Native windows, navigation, workflows, localization        |
| IPC          | Versioned JSON Lines                         | Communication between the desktop client and local backend |
| Backend      | Python 3.11–3.13                             | Workflows, validation, file and settings services          |
| Cryptography | `cryptography` · AES-256-GCM · scrypt        | Encryption, authentication, key derivation                 |
| Format       | AGV1                                         | Text tokens and `.agv` file containers                     |
| Packaging    | Self-contained x64 ZIP                       | Bundled Python, .NET, and Windows App SDK runtimes         |
| Validation   | pytest · C# IPC tests · native UI automation | Core, protocol, release-contract and native UI validation  |

## 📚 Documentation

| Document                                             | Contents                                    |
| ---------------------------------------------------- | ------------------------------------------- |
| [Security Model](./docs/SECURITY_MODEL.md)           | Threat model, guarantees, and limitations   |
| [AGV1 Protocol](./docs/PROTOCOL.md)                  | Text and file encryption formats            |
| [Backend Protocol](./docs/BACKEND_PROTOCOL.md)       | WinUI ↔ Python IPC protocol                 |
| [Migration Guide](./docs/MIGRATION.md)               | Compatibility and migration boundaries      |
| [QA Checklist](./docs/QA_CHECKLIST.md)               | Pre-release quality checks                  |
| [Release Engineering](./docs/RELEASE_ENGINEERING.md) | Build and release engineering               |
| [v2.5 Acceptance](./docs/ACCEPTANCE_2.5.md)          | Executed validation for the current release |

<a id="development"></a>

## 🛠️ Development

Development requires:

* Windows
* The .NET SDK specified by `global.json`
* Python 3.11–3.13
* PowerShell

Set up the environment with:

```powershell
python -m venv .venv
.\scripts\install_locked_dependencies.ps1
.\scripts\run_dev.ps1
```

`run_dev.ps1` launches the WinUI desktop application.

Running:

```powershell
python -m aegisvault.backend
```

starts the JSON Lines backend only. It does not open a desktop window.

For an isolated .NET SDK installation, set:

```powershell
$env:AEGISVAULT_DOTNET = "C:\path\to\dotnet.exe"
```

before invoking the repository scripts.

### Build and validation

```powershell
.\scripts\verify_release.ps1
.\scripts\build_windows.ps1 -Clean -Zip
.\scripts\test_winui.ps1
.\scripts\test_winui.ps1 -Theme dark -Language en-US
```

Native UI tests require an interactive Windows desktop. They launch the actual published `AegisVault.exe` with synthetic data, an isolated settings directory, and a constrained environment, then write evidence screenshots to:

```text
build/native-evidence
```

Source tests and backend smoke tests do not substitute for native UI or manual acceptance.

## 🗂️ Repository structure

```text
src/AegisVault.App/       C# WinUI windows, pages, view models, IPC client, localization
src/aegisvault/core/      AGV1, cryptography, KDF, atomic file operations
src/aegisvault/services/  File naming and workflow services
src/aegisvault/settings/  Validated configuration persistence and cross-process locking
src/aegisvault/backend/   Versioned JSON Lines local service
tests/                    Core, protocol, IPC, release-contract and native UI tests
scripts/                  Validation, packaging, audits, SBOM and release tooling
docs/                     Protocol, security, migration, QA and acceptance documentation
```

Python and NuGet dependencies are locked. The release pipeline also produces a software bill of materials and checksums to improve artifact traceability.

## 🙏 Acknowledgements

AegisVault is built on open-source projects and ecosystems including:

[Windows App SDK](https://github.com/microsoft/WindowsAppSDK) ·
[.NET](https://github.com/dotnet) ·
[Python](https://www.python.org/) ·
[cryptography](https://github.com/pyca/cryptography) ·
[PyInstaller](https://pyinstaller.org/) ·
[pytest](https://pytest.org/) ·
[CycloneDX](https://cyclonedx.org/)

They provide the foundations for the native Windows interface, runtimes, cryptographic implementation, testing, and release supply chain.

## 📄 License

AegisVault is licensed under the [MIT License](./LICENSE).

You may use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software under the terms of the MIT License.

> Encryption software does not automatically make an environment secure. For highly sensitive data, evaluate AegisVault together with independently audited software, reliable backups, strong passwords, and a trusted endpoint.
