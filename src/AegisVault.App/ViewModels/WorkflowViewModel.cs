using AegisVault.App.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace AegisVault.App.ViewModels;

public sealed class WorkflowViewModel : ObservableObject
{
    private readonly BackendClient backend;
    private readonly SettingsService settings;
    private CancellationTokenSource? cancellation;
    private Task? activeTask;
    private bool busy, cancelling, hasStatus, hasResult;
    private int mode;
    private string input = "", inputPath = "", outputDir = "", output = "", status = "", progressText = "";
    private double progress;
    private InfoBarSeverity severity;
    public WorkflowViewModel(string kind, BackendClient backend, SettingsService settings)
    {
        Kind = kind; this.backend = backend; this.settings = settings;
        CancelCommand = new(() => { cancellation?.Cancel(); cancelling = true; Raise(nameof(CanCancel)); CancelCommand!.Refresh(); }, () => CanCancel);
        ClearCommand = new(Clear, () => !IsBusy);
        settings.Changed += (_, _) => { Raise(nameof(OverwriteWarning)); Raise(nameof(RecentFiles)); Raise(nameof(RecentVisibility)); };
    }
    public Localization L => Localization.Instance;
    public string Kind { get; }
    public int Mode { get => mode; set { if (!IsBusy && Set(ref mode, value)) { ClearResult(); Raise(nameof(NeedsConfirmation)); Raise(nameof(ActionLabel)); } } }
    public string Input { get => input; set { if (Set(ref input, value)) ClearResult(); } }
    public string InputPath { get => inputPath; set { if (Set(ref inputPath, value)) ClearResult(); } }
    public string OutputDir { get => outputDir; set => Set(ref outputDir, value); }
    public string Output { get => output; private set => Set(ref output, value); }
    public string ResultPath { get; private set; } = "";
    public bool IgnoreWhitespace { get; set; }
    public bool IsBusy { get => busy; private set { Set(ref busy, value); Raise(nameof(IsIdle)); Raise(nameof(CanCancel)); Raise(nameof(BusyVisibility)); CancelCommand.Refresh(); ClearCommand.Refresh(); } }
    public bool IsIdle => !IsBusy;
    public bool CanCancel => IsBusy && !cancelling;
    public bool HasStatus { get => hasStatus; private set => Set(ref hasStatus, value); }
    public bool HasResult { get => hasResult; private set { Set(ref hasResult, value); Raise(nameof(ResultVisibility)); } }
    public string Status { get => status; private set => Set(ref status, value); }
    public InfoBarSeverity Severity { get => severity; private set => Set(ref severity, value); }
    public double Progress { get => progress; private set => Set(ref progress, value); }
    public string ProgressText { get => progressText; private set => Set(ref progressText, value); }
    public Visibility NeedsConfirmation => Mode == 0 ? Visibility.Visible : Visibility.Collapsed;
    public Visibility OverwriteWarning => settings.Current.OverwriteOutputs ? Visibility.Visible : Visibility.Collapsed;
    public string[] RecentFiles => settings.Current.RecentFiles;
    public Visibility RecentVisibility => RecentFiles.Length > 0 ? Visibility.Visible : Visibility.Collapsed;
    public Visibility BusyVisibility => IsBusy ? Visibility.Visible : Visibility.Collapsed;
    public Visibility ResultVisibility => HasResult ? Visibility.Visible : Visibility.Collapsed;
    public string ActionLabel => L[Kind.StartsWith("base64", StringComparison.Ordinal) ? (Mode == 0 ? "encode" : "decode") : (Mode == 0 ? "encrypt" : "decrypt")];
    public ActionCommand CancelCommand { get; }
    public ActionCommand ClearCommand { get; }
    public void RefreshLabels() => Raise(nameof(ActionLabel));

    public Task RunAsync(string password = "", string confirmation = "")
    {
        if (IsBusy) return activeTask ?? Task.CompletedTask;
        activeTask = ExecuteAsync(password, confirmation);
        return activeTask;
    }

    private async Task ExecuteAsync(string password, string confirmation)
    {
        ClearResult();
        bool file = Kind is "file" or "base64_file";
        bool crypto = Kind is "text" or "file";
        if (file && string.IsNullOrWhiteSpace(InputPath)) { Fail("validation.file_required"); return; }
        if (crypto && password.Length == 0) { Fail("validation.password_required"); return; }
        if (crypto && Mode == 0 && password != confirmation) { Fail("validation.password_mismatch"); return; }
        using var token = new CancellationTokenSource();
        cancellation = token; cancelling = false; IsBusy = true;
        Progress = 0; ProgressText = L["working"];
        try
        {
            var op = Kind switch
            {
                "text" => Mode == 0 ? "text.encrypt" : "text.decrypt",
                "file" => Mode == 0 ? "file.encrypt" : "file.decrypt",
                "base64_file" => Mode == 0 ? "base64.encode_file" : "base64.decode_file",
                _ => Mode == 0 ? "base64.encode_text" : "base64.decode_text"
            };
            var report = new Progress<BackendProgress>(p =>
            {
                Progress = p.Percent * 100;
                ProgressText = p.TotalBytes.HasValue ? $"{Progress:F0}% · {p.ProcessedBytes:N0} / {p.TotalBytes:N0} {L["bytes"]}" : L["working"];
            });
            var result = await backend.CallAsync(op, new { text = Input, password, input_path = InputPath,
                output_dir = OutputDir, strict = !IgnoreWhitespace, ignore_ascii_whitespace = IgnoreWhitespace }, report, token.Token);
            if (file)
            {
                ResultPath = result.GetProperty("output_path").GetString()!;
                Output = $"{ResultPath}\n{result.GetProperty("original_size").GetInt64():N0} → {result.GetProperty("output_size").GetInt64():N0} {L["bytes"]}";
            }
            else Output = result.GetProperty(Kind == "text" ? (Mode == 0 ? "ciphertext" : "plaintext") : "text").GetString()!;
            HasResult = true;
            Show(L["completed"], InfoBarSeverity.Success);
            if (file && settings.Current.RememberRecentFiles)
            {
                try { await settings.AddRecentAsync(InputPath); }
                catch (BackendException) { Show(L["completed_recent_failed"], InfoBarSeverity.Warning); }
            }
        }
        catch (OperationCanceledException) { Show(L["cancelled"], InfoBarSeverity.Informational); }
        catch (BackendException ex) { Fail(ex.Code); }
        catch (Exception) { Fail("app.error"); }
        finally { password = confirmation = ""; cancellation = null; IsBusy = false; ProgressText = ""; }
    }

    public void Fail(string code) => Show(L.Error(code), InfoBarSeverity.Error);
    public void Show(string message, InfoBarSeverity kind = InfoBarSeverity.Informational)
    { Status = message; Severity = kind; HasStatus = true; }
    public void Clear()
    {
        if (IsBusy) return;
        Input = InputPath = OutputDir = ""; ClearResult();
    }
    public void ClearResult() { Output = ""; ResultPath = ""; HasResult = false; HasStatus = false; }
    public async Task CancelAndWaitAsync()
    {
        cancellation?.Cancel();
        if (activeTask is not null) await activeTask;
    }
}
