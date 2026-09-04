# WinUI 3 desktop contract — 2.1

`Microsoft.UI.Xaml.Window` owns the only production top-level application window. Its content uses native
`TitleBar`, `MicaBackdrop`, `NavigationView`, `Frame` and four Pages. No custom control template, palette,
font size compression, drawn window chrome or simulated Fluent surface is used.

Each workflow is a linear sequence: operation, input, optional password/output location and result.
The page title and form share a bounded scroll area. Primary action, cancellation and status remain in
a separate footer, including in narrow windows. `WorkflowViewModel` owns state and calls the UI-independent JSON Lines client.
View code only handles platform interactions such as pickers, drag/drop, PasswordBox, clipboard and saving.
Passwords are passed once to the view model and cleared from their input controls when processing starts.
Local validation preserves entries for correction and focuses the failing field. Mode changes and page exit
clear password controls. Secrets never appear in command-line arguments or application logs.

`InfoBar` reports success and coded errors in place. `ContentDialog` confirms cancellation before closing
a busy window; its default action keeps the task running. While processing, operation/input changes and
navigation are disabled at both the control and view-model boundary. Cancel is visible only during processing,
remains in the footer and becomes disabled after a cancellation request. Late progress callbacks cannot modify a later task.

Completed results receive focus after layout and scroll into view. Native `CommandBar` overflow keeps copy,
save and result reuse available at narrow widths. File copy puts only the exact output path on the clipboard.
Text reuse switches to the reverse operation and clears the old result. Editing input, destination or decoding
options invalidates old feedback. Base64 retains the input type and the separate text/file workflow state across navigation.

FileOpenPicker, FileSavePicker and FolderPicker come from `Microsoft.Windows.Storage.Pickers` and receive
the actual AppWindow ID. Empty output override delegates to the saved output directory or source folder.
The Core controls automatic naming, collision avoidance and atomic overwrite behavior.

Themes use `RequestedTheme` and `ThemeResource`, including the system high contrast palette. All pages are
vertically scrollable, have stretch layouts and a maximum readable width, and the NavigationView adapts its
pane to available width. Per-monitor V2 DPI awareness is declared. Native labels and automation IDs cover
essential controls; status uses a polite live region. Ctrl+Enter invokes the primary workflow action.

Chinese and English UI/error messages reside in `src/AegisVault.App/Assets`. Language and theme apply after
successful settings persistence. System-provided picker and titlebar strings follow Windows language.
The Settings page keeps its draft across navigation and exposes Save/Discard with pending-change feedback.
Failed writes leave persisted and applied settings unchanged while preserving the draft for retry.
Retained workflow status and file-size metadata retranslate when language changes.

The control/API choices follow Microsoft's documentation for the
[native TitleBar](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/title-bar),
[Windows App SDK pickers](https://learn.microsoft.com/en-us/windows/apps/develop/files/pickers-save-file)
and [self-contained unpackaged distribution](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/unpackage-winui-app).
