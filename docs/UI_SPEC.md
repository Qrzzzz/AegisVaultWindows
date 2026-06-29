# UI Specification

Target version: `1.0.0`.

## Shell

- `AppShell` owns the left `Sidebar`, right `Workspace`, top `PageHeader` and bottom `StatusArea`.
- Pages do not own their title block. Page title and description are controlled by the shell.
- The default visual style is a restrained dark Windows tool surface: flat dark panels, 8 px cards, consistent borders, no full-page gradients and no one-card control dumps.

## Design System

- Tokens live in `src/aegisvault/ui/design/tokens.py`.
- Spacing lives in `src/aegisvault/ui/design/spacing.py`.
- Stylesheet generation lives in `src/aegisvault/ui/design/theme.py`.
- Reusable widgets live under `src/aegisvault/ui/components/`.

Standard components:

- `AppShell`, `Sidebar`, `PageHeader`
- `Card`, `FormRow`, `SegmentedControl`
- `PasswordInput`, `FilePickerCard`, `OutputPreview`
- `InlineAlert`, `TaskProgress`, `ResultSummary`, `ActionBar`

## Text Crypto

- Uses an Encrypt / Decrypt segmented control.
- Input is on the left, output is on the right.
- Password controls are isolated above the text workspace.
- Encrypt mode shows password and confirm password.
- Decrypt mode shows only password.
- Output supports Copy, Clear and Swap.
- Normal validation and operation errors appear in `InlineAlert`.

## File Crypto

- Step 1: select file.
- Step 2: choose Encrypt or Decrypt.
- Step 3: enter password and review output directory/path preview.
- Step 4: execute, cancel and review result.
- File metadata includes path, size, type and output previews.
- Progress displays stage, percent and processed size when available.

## Base64

- Header copy states: Base64 is encoding, not encryption.
- Text Base64 and File Base64 are separate tabs.
- Text supports encode, decode, copy, clear and swap.
- Strict text decode rejects whitespace unless relaxed decode is enabled.
- File supports encode, decode, progress, cancel and open output.

## Settings

Settings are grouped into General, Output, Legacy recovery and Recent files:

- Theme
- Language
- Output directory
- Overwrite behavior
- Recent files
- Legacy recovery visibility
- AK compatibility, default off, with risk warning
