# UI Specification

Target: AegisVault 1.2.0, the approved modern Windows UI.

## Product Boundary

AegisVault is a local PySide6 encryption utility. The interface may use other
desktop applications as a reference for interaction restraint, but it does not
adopt download workflows, command-line surfaces, network services, or backend
architecture from them.

## Shell

The application uses one QMainWindow with the system title bar and a Fluent-inspired
Qt Widgets interface. It is not a WinUI application. No browser or WebView is used.

- The only persistent workspace entries are **Text**, **File**, and **Base64**.
- The left sidebar contains the three workspaces, Settings, and More. More
  contains the recent-files menu, Settings, Exit and Help/About.
- Settings and About open modal dialogs; they are not workspace pages.
- A QStackedWidget preserves exactly three workspace instances. Sidebar buttons
  have an exclusive selection marker, localized accessible names and tooltips.
- Below 800 logical pixels the sidebar becomes an icon rail. Each workspace has
  a page heading, short description and an exclusive two-button operation switch.
- The native status bar is transient and becomes empty after its timeout.
- Ctrl+1, Ctrl+2, and Ctrl+3 select the three workspaces. Ctrl+, opens Settings,
  F1 opens About, and Ctrl+Q exits.

## Workflow Contract

Every workspace follows the same workflow:

1. mode;
2. input;
3. only the parameters required for that mode;
4. one primary operation;
5. in-place progress, error, and result feedback.

Secondary controls may clear input, copy or clear a result, use a text result as
new input, cancel an active task, or reveal a file output. They must not compete
with the single primary operation. Ctrl+Enter runs the current operation and
Escape requests cancellation.

Page margins are 32 logical pixels (20 in narrow content areas), with 24-pixel
section spacing. Input sections use labels rather than decorative group frames.
Password and confirmation appear side by side where space allows and stack when
narrower or when larger fonts require it. The show/hide icon buttons retain full
localized accessible names. Text editors shorten when results appear or the
window is small. Result actions wrap vertically when translated labels do not fit.

The primary operation and Clear follow the input/options area and remain outside
its scroll viewport. Progress and errors appear immediately below this row only
when needed. Results follow in a separately scrollable area; empty result editors
and result actions are hidden. The input and text result share available vertical
space without changing the system font size. File forms use their natural height
so the operation stays near the options. Both content areas can scroll in small
windows while the operation remains visible. Buttons that clear or reuse results
are disabled during a task; selecting/copying an existing result remains possible.
Starting another task, switching tabs or switching Base64 input types does not
discard a completed result. Explicit Clear / Use as new input retains its
documented clearing behavior.

## Text

- Modes: Encrypt and Decrypt.
- Encrypt shows password and confirmation. A mismatch is rejected before work
  starts.
- Decrypt shows one password field and accepts only an AGV1 token.
- Non-AGV1 input, including retired Base64 ciphertext and AK wrappers, is
  rejected with a clear localized AGV1-only error. There is no recovery
  action, compatibility switch or alternate decryptor.
- Results support Copy, Clear result, and Use as new input. Using a result as
  input reverses the operation mode.

## File

- A file can be selected, dropped, or loaded from the Recent files menu.
- Modes: Encrypt and Decrypt.
- Encrypt requires password confirmation; Decrypt requires one password.
- The output directory and exact candidate path are visible before execution.
- Paths use read-only QLineEdit controls: horizontal text navigation, selection,
  copying and full-path tooltips remain available without widening the window.
- File decryption accepts only AGV1 file contents, regardless of the extension.
  Other contents are rejected inline with protocol.unsupported_format.
  Rejection does not open a recovery dialog or create plaintext/temporary
  output. There is no pending recovery request or second recovery task.
- Progress includes localized stage, percent, processed size, and cancellation.
- A successful result includes output path, size change, format, Clear result,
  and Reveal output.

## Base64

- The warning that Base64 is encoding rather than encryption is always visible.
- Input type is Text or File; operation is Encode or Decode.
- Both input types share one primary operation button.
- Text Decode exposes the optional relaxed ASCII-whitespace mode.
- Text results support Copy, Clear result, and Use as new input.
- File tasks support progress, cancellation, output preview, and Reveal output.
- File mode also shows the output directory and the current overwrite warning.

## Settings

Settings are edited in a modal dialog and applied to existing workspace
instances. Saving must not rebuild the shell or discard current mode, input,
password, result, selected file, or active page.

Normal settings:

- language: Simplified Chinese or English;
- appearance: Light, Dark or Use system setting;
- default output directory;
- recent-file retention and clearing.

The collapsed **Advanced options** section contains:

- overwrite existing outputs, with an irreversible-replacement warning;

No old-format or embedded-key parsing setting is present.

Saving first persists a candidate AppSettings object. Only a successful write
updates the live settings and existing pages. A rejected dialog or failed save
must not mutate live preferences or recent-file history.

## Modern Windows Appearance

An application palette and scoped QSS define muted shell and content surfaces,
subtle control boundaries, a blue primary operation, and visible keyboard focus
and disabled states. The existing system font family is retained; the base size
is at least 10.5 pt and headings scale from it. Monochrome vector icons adapt to
the current palette. There is no simulated glass effect or replacement title bar.

Light remains the default. Valid persisted light/dark/system values are respected;
invalid values fall back to light. Theme and language changes apply only after
settings are successfully saved and never rebuild pages or discard work. System
notifications update system appearance; an explicit Light or Dark choice remains
pinned. Dialogs inherit the application appearance.

The default client size is 1024 x 760 logical pixels, with a 600 x 440 minimum.
The operation stays outside the input viewport and remains reachable. Small
windows and larger fonts use vertical scrolling without horizontal overflow.
File selection starts with a compact drop area, then shows the selectable full
path and short size/type metadata. The exact output path remains visible before
execution. QFileDialog uses the platform-native file/folder picker, which follows
Windows appearance independently of an explicitly selected application theme.

## Task and Window State

- Each run receives a monotonically increasing task id.
- Worker progress and terminal callbacks are accepted only for the active id.
- A new run cannot begin until the prior worker thread has stopped.
- Cancellation is idempotent.
- While a task runs, all controls that could replace its captured input,
  including drag-and-drop, are disabled or rejected.
- Closing with active work asks for confirmation, requests cancellation, and
  waits for each worker thread to reach a stopped terminal state. If a worker
  does not stop within the safety wait, the window remains open.
- Settings cannot be changed while a task is active.

## Accessibility and Feedback

- Editors, password fields, mode controls, file pickers, result actions, and
  menu actions have localized accessible names.
- Validation and operational errors are localized and shown inline; the alert
  is keyboard-focusable.
- Page switches move focus to the primary input.
- Tab traverses the form fields, main operation and result actions; it does not
  insert indentation in the text editors. Ctrl+Enter still starts work.
- All visible product copy exists in both locale catalogs.

## Visual Regression

tests/test_ui_visual.py renders 1024 x 760 light workspaces with
QT_QPA_PLATFORM=offscreen, verifies dimensions and a structural pixel comparison,
and uses these committed baselines (replacing the former dark images):

- docs/screenshots/minimal-text-zh-CN.png
- docs/screenshots/minimal-file-zh-CN.png
- docs/screenshots/minimal-base64-zh-CN.png

The general offscreen documentation samples also include text result and
settings. The obsolete recovery-confirmation screenshot is removed.
Additional English, error, file-result, file-decrypt,
advanced, 640 x 480 and 150% scaling samples go to an explicit QA directory.
Every render uses isolated APPDATA / LOCALAPPDATA and generated display
fixtures, never real configuration, network data or user secrets. Screenshot
fixtures are visual evidence, not cryptographic round-trip evidence.

Offscreen Windows font registration is confined to the QA process
(segoeui.ttf and msyh.ttc). Production uses the Qt/system font unchanged.

Regenerate baselines intentionally with the hash-locked environment:

    $env:QT_QPA_PLATFORM = "offscreen"
    $env:QT_SCALE_FACTOR = "1"
    .venv/Scripts/python.exe tests/test_ui_visual.py --update --qa-dir <outside-repo-QA-directory>

For high-DPI samples use a separate process with QT_SCALE_FACTOR=1.5 and the
same --qa-dir. It does not replace the 100% committed baselines.

Generate temporary Windows validation captures outside the source tree with
the real `windows` platform at the system DPI. Runtime JSON records the exact
Qt version, style, available styles, font and device-pixel ratio. The capture
exercises real synthetic AGV1 and Base64 round trips, authentication failure
and settings persistence; these are not injected results. Temporary captures
are separate from the maintained regression baselines above.

    .venv/Scripts/python.exe scripts/capture_windows_ui.py --output <QA-directory> --exercise

The capture command uses isolated temporary configuration and data. For
interaction checks, set QT_QPA_PLATFORM=windows before running the UI tests.
Additional QT_SCALE_FACTOR values multiply the system DPI; record the observed
device-pixel ratio instead of assuming that 1.5 always means physical 150%.

tests/test_ui_basic_light.py exercises Qt input, shortcuts, phase
visibility, theme persistence and platform notifications, compact
layout reachability, real Base64 file round trips, recent files, output reveal
dispatch and guarded drops. tests/test_ui_behavior.py retains real encryption,
rejection of static retired-format samples without output or a dialog, settings
failure, stale callback, cancellation and
close/wait contracts. `test_ui_v11_workflows.py` adds form Tab order, translated
translated operation widths, long paths, real file round trips and cancellation/close cleanup
through the actual services. Its cancellation tests hold progress delivery until
the UI cancels, and simulate the confirmation answer for close testing.

## Integration Boundary

The UI calls the AGV1-only CryptoService text/file methods. It has no
allow_legacy argument, recovery API call, AK settings field or compatibility
result fields. All non-AGV1 format errors use protocol.unsupported_format,
localized as "Only AGV1 is supported. Older formats are not supported." and
"仅支持 AGV1，不支持旧格式。". The UI must not suggest enabling a removed switch.

TaskController lifecycle, settings candidate-before-live persistence,
cancellation, output overwrite protection and modern/Base64 workflows remain
unchanged. Retired-format backend code remains removed.

Unused runtime skin modules and old card/navigation components are removed.
The two historical resources/qss files remain solely because the unchanged
release artifact audit explicitly requires them. The UI does not load them.
Removing those packaged placeholders later requires a coordinated manifest /
artifact-audit update, outside this UI task.
