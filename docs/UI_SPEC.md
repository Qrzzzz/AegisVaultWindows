# WinUI 3 desktop contract — 2.0

`Microsoft.UI.Xaml.Window` owns the only production top-level application window. Its content uses native
`TitleBar`, `MicaBackdrop`, `NavigationView`, `Frame` and four Pages. No custom control template, palette,
font size compression, drawn window chrome or simulated Fluent surface is used.

Each workflow is a linear sequence: operation, input, optional password/output location, primary action,
progress/status, result. `WorkflowViewModel` owns state and calls the UI-independent JSON Lines client.
View code only handles platform interactions such as pickers, drag/drop, PasswordBox, clipboard and saving.
Passwords are passed once to the view model and immediately cleared from their input controls.

`InfoBar` reports success and coded errors in place. `ContentDialog` confirms cancellation before closing
a busy window; its default action keeps the task running. While processing, operation/input changes and
navigation are disabled. Cancel remains available and becomes disabled after a cancellation request.

FileOpenPicker, FileSavePicker and FolderPicker come from `Microsoft.Windows.Storage.Pickers` and receive
the actual AppWindow ID. Empty output override delegates to the saved output directory or source folder.
The Core controls automatic naming, collision avoidance and atomic overwrite behavior.

Themes use `RequestedTheme` and `ThemeResource`, including the system high contrast palette. All pages are
vertically scrollable, have stretch layouts and a maximum readable width, and the NavigationView adapts its
pane to available width. Per-monitor V2 DPI awareness is declared. Native labels and automation IDs cover
essential controls; status uses a polite live region. Ctrl+Enter invokes the primary workflow action.

Chinese and English UI/error messages reside in `src/AegisVault.App/Assets`. Language and theme apply after
successful settings persistence. System-provided picker and titlebar strings follow Windows language.
The Settings page keeps a draft so failed writes leave persisted and applied settings unchanged.

The control/API choices follow Microsoft's documentation for the
[native TitleBar](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/title-bar),
[Windows App SDK pickers](https://learn.microsoft.com/en-us/windows/apps/develop/files/pickers-save-file)
and [self-contained unpackaged distribution](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/unpackage-winui-app).
