# UI Specification

AegisVault uses a PySide6 desktop UI with a left navigation rail and stacked pages.

## Pages

- Text Crypto: encrypts and decrypts `AGV1.` text tokens and legacy recovery text.
- File Crypto: encrypts files to `.agv` and decrypts modern or supported legacy files.
- Base64: keeps text and file Base64 workflows separate from encryption.
- Settings: stores language, theme, output directory, overwrite behavior, recent files and legacy compatibility toggles.
- About: states version and security boundaries.

## Visual Style

The default theme is dark, with a light option and a system option. The UI uses layered surfaces, restrained borders, clear spacing, primary/secondary button hierarchy, red error states and blue/green success states.

Base64 copy must clearly state that Base64 is encoding, not encryption.

## Long Tasks

File encryption, file decryption, Base64 file encoding and Base64 file decoding run through worker objects. The UI displays the current stage, progress, cancellation state, output path and readable failure details.

Stages use stable labels:

- Preparing
- Encrypting
- Decrypting
- Encoding
- Decoding
- Writing output
- Done

## Accessibility Baseline

Controls use readable labels, visible disabled states and high-contrast focus/selection colors. Password fields hide input by default and expose a show/hide control.
