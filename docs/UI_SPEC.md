# UI Specification

Target version: 1.0.0.

## Product Boundary

AegisVault is a local PySide6 encryption utility. The interface may use other
desktop applications as a reference for interaction restraint, but it does not
adopt download workflows, command-line surfaces, network services, or backend
architecture from them.

## Shell

The application uses one native QMainWindow.

- The only persistent workspace entries are **Text**, **File**, and **Base64**.
- Settings, recent files, Exit, and About live in the native menu bar.
- Settings and About open modal dialogs; they are not workspace pages.
- The page header gives one short purpose statement. The bottom status area is
  transient and returns to the localized Ready message after its timeout.
- Ctrl+1, Ctrl+2, and Ctrl+3 select the three workspaces. Ctrl+, opens Settings,
  F1 opens About, and Ctrl+Q exits.

## Workflow Contract

Every workspace follows the same vertical order:

1. mode;
2. input;
3. only the parameters required for that mode;
4. one primary operation;
5. in-place progress, error, and result feedback.

Secondary controls may clear input, copy or clear a result, use a text result as
new input, cancel an active task, or reveal a file output. They must not compete
with the single primary operation. Ctrl+Enter runs the current operation and
Escape requests cancellation.

## Text

- Modes: Encrypt and Decrypt.
- Encrypt shows password and confirmation. A mismatch is rejected before work
  starts.
- Decrypt shows one password field and a visible Legacy / AK recovery entry.
- Supported legacy ciphertext is detected automatically. AK parsing remains
  disabled by default and links to its explicit high-risk setting.
- Results support Copy, Clear result, and Use as new input. Using a result as
  input reverses the operation mode.

## File

- A file can be selected, dropped, or loaded from the Recent files menu.
- Modes: Encrypt and Decrypt.
- Encrypt requires password confirmation; Decrypt requires one password.
- The output directory and exact candidate path are visible before execution.
- Legacy file recovery is explained in Decrypt mode. Ordinary decryption uses
  the modern-only boundary and stops when a legacy file is detected. A
  localized, migration-only confirmation must be accepted before a separate
  legacy recovery task can start; declining writes no output.
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

## Settings

Settings are edited in a modal dialog and applied to existing workspace
instances. Saving must not rebuild the shell or discard current mode, input,
password, result, selected file, or active page.

Normal settings:

- language: Simplified Chinese or English;
- theme: Dark, Light, or System (resolved from the current Qt system color
  scheme);
- default output directory;
- recent-file retention and clearing.

The collapsed **Advanced and recovery options** section contains:

- overwrite existing outputs, with an irreversible-replacement warning;
- AK compatibility parsing, with the embedded-key migration warning.

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
- All visible product copy exists in both locale catalogs.

## Visual Regression

tests/test_ui_visual.py renders all three workspaces with
QT_QPA_PLATFORM=offscreen, verifies dimensions and a tolerant structural pixel
comparison, and uses these committed baselines:

- docs/screenshots/minimal-text-zh-CN.png
- docs/screenshots/minimal-file-zh-CN.png
- docs/screenshots/minimal-base64-zh-CN.png

Regenerate them intentionally with:

    $env:QT_QPA_PLATFORM = "offscreen"
    python tests/test_ui_visual.py --update
