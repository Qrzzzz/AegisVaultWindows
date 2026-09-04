using AegisVault.App.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace AegisVault.App.ViewModels;

public sealed class WorkflowViewModel : ObservableObject
{
    public const int MaxTextLength = 2097152;
    private readonly BackendClient backend;
    private readonly SettingsService settings;
    private CancellationTokenSource? cancellation;
    private Task? activeTask;
    private bool busy, cancelling, hasStatus, hasResult, ignoreWhitespace;
    private int mode;
    private string input = "", inputPath = "", outputDir = "", output = "", statusKey = "", progressText = "";
    private double progress;
    private long originalSize, outputSize;
    private InfoBarSeverity severity;

    public WorkflowViewModel(string kind, BackendClient backend, SettingsService settings)
    {
        Kind = kind;
        this.backend = backend;
        this.settings = settings;
        CancelCommand = new(RequestCancellation, () => CanCancel);
        ClearCommand = new(Clear, () => !IsBusy);
        settings.Changed += (_, _) => RefreshLabels();
    }

    public Localization L => Localization.Instance;
    public string Kind { get; }
    public bool IsFile => Kind is "file" or "base64_file";
    public bool IsCrypto => Kind is "text" or "file";
    public int Mode
    {
        get => mode;
        set
        {
            if (IsBusy || value is < 0 or > 1 || !Set(ref mode, value)) return;
            ClearResult();
            Raise(nameof(NeedsConfirmation));
            Raise(nameof(DecodeOptionsVisibility));
            Raise(nameof(ActionLabel));
        }
    }
    public string Input { get => input; set { if (!IsBusy && Set(ref input, value)) ClearResult(); } }
    public string InputPath { get => inputPath; set { if (!IsBusy && Set(ref inputPath, value)) ClearResult(); } }
    public string OutputDir { get => outputDir; set { if (!IsBusy && Set(ref outputDir, value)) ClearResult(); } }
    public bool IgnoreWhitespace { get => ignoreWhitespace; set { if (!IsBusy && Set(ref ignoreWhitespace, value)) ClearResult(); } }
    public string Output { get => output; private set => Set(ref output, value); }
    public string ResultPath { get; private set; } = "";
    public string CopyContent => IsFile ? ResultPath : Output;
    public string CopyLabel => L[IsFile ? "copy_path" : "copy"];
    public string LastErrorCode { get; private set; } = "";
    public bool IsBusy
    {
        get => busy;
        private set
        {
            Set(ref busy, value);
            Raise(nameof(IsIdle)); Raise(nameof(CanCancel)); Raise(nameof(BusyVisibility)); Raise(nameof(IdleVisibility));
            Raise(nameof(IsIndeterminate)); Raise(nameof(CancelLabel));
            CancelCommand.Refresh(); ClearCommand.Refresh();
        }
    }
    public bool IsIdle => !IsBusy;
    public bool CanCancel => IsBusy && !cancelling;
    public bool IsIndeterminate => IsBusy && (Progress == 0 || cancelling);
    public string CancelLabel => L[cancelling ? "cancelling" : "cancel"];
    public bool HasStatus { get => hasStatus; private set => Set(ref hasStatus, value); }
    public bool HasResult
    {
        get => hasResult;
        private set
        {
            Set(ref hasResult, value); Raise(nameof(ResultVisibility));
            Raise(nameof(TextResultVisibility)); Raise(nameof(FileResultVisibility));
        }
    }
    public string Status => statusKey.StartsWith("error.", StringComparison.Ordinal) ? L.Error(statusKey[6..])
        : string.IsNullOrEmpty(statusKey) ? "" : L[statusKey];
    public InfoBarSeverity Severity { get => severity; private set => Set(ref severity, value); }
    public double Progress { get => progress; private set { Set(ref progress, value); Raise(nameof(IsIndeterminate)); } }
    public string ProgressText { get => progressText; private set => Set(ref progressText, value); }
    public Visibility NeedsConfirmation => Mode == 0 ? Visibility.Visible : Visibility.Collapsed;
    public Visibility DecodeOptionsVisibility => Kind == "base64_text" && Mode == 1 ? Visibility.Visible : Visibility.Collapsed;
    public Visibility OverwriteWarning => settings.Current.OverwriteOutputs ? Visibility.Visible : Visibility.Collapsed;
    public string[] RecentFiles => settings.Current.RecentFiles;
    public Visibility RecentVisibility => RecentFiles.Length > 0 ? Visibility.Visible : Visibility.Collapsed;
    public Visibility BusyVisibility => IsBusy ? Visibility.Visible : Visibility.Collapsed;
    public Visibility IdleVisibility => IsBusy ? Visibility.Collapsed : Visibility.Visible;
    public Visibility ResultVisibility => HasResult ? Visibility.Visible : Visibility.Collapsed;
    public Visibility TextResultVisibility => HasResult && !IsFile ? Visibility.Visible : Visibility.Collapsed;
    public Visibility FileResultVisibility => HasResult && IsFile ? Visibility.Visible : Visibility.Collapsed;
    public string OutputFolderPlaceholder => string.IsNullOrWhiteSpace(settings.Current.DefaultOutputDir) ? L["same_folder"] : settings.Current.DefaultOutputDir;
    public string ActionLabel => L[IsCrypto ? (Mode == 0 ? "encrypt" : "decrypt") : (Mode == 0 ? "encode" : "decode")];
    public ActionCommand CancelCommand { get; }
    public ActionCommand ClearCommand { get; }

    public void RefreshLabels()
    {
        Raise(nameof(ActionLabel)); Raise(nameof(CopyLabel)); Raise(nameof(Status)); Raise(nameof(CancelLabel));
        Raise(nameof(OverwriteWarning)); Raise(nameof(RecentFiles)); Raise(nameof(RecentVisibility));
        Raise(nameof(OutputFolderPlaceholder));
        if (IsFile && HasResult) FormatFileResult();
    }

    public Task RunAsync(string password = "", string confirmation = "")
    {
        if (IsBusy) return activeTask ?? Task.CompletedTask;
        activeTask = ExecuteAsync(password, confirmation);
        return activeTask;
    }

    private async Task ExecuteAsync(string password, string confirmation)
    {
        ClearResult();
        if (IsFile && string.IsNullOrWhiteSpace(InputPath)) { Fail("validation.file_required"); return; }
        if (IsCrypto && password.Length == 0) { Fail("validation.password_required"); return; }
        if (IsCrypto && Mode == 0 && password != confirmation) { Fail("validation.password_mismatch"); return; }
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
                if (!ReferenceEquals(cancellation, token) || !IsBusy || cancelling) return;
                Progress = Math.Clamp(p.Percent * 100, 0, 100);
                ProgressText = p.TotalBytes.HasValue ? $"{Progress:F0}% · {p.ProcessedBytes:N0} / {p.TotalBytes:N0} {L["bytes"]}" : L["working"];
            });
            var result = await backend.CallAsync(op, new { text = Input, password, input_path = InputPath,
                output_dir = OutputDir, strict = !IgnoreWhitespace, ignore_ascii_whitespace = IgnoreWhitespace }, report, token.Token);
            if (IsFile)
            {
                ResultPath = BackendResponse.String(result, "output_path");
                originalSize = BackendResponse.Int64(result, "original_size");
                outputSize = BackendResponse.Int64(result, "output_size");
                FormatFileResult();
            }
            else Output = BackendResponse.String(result, Kind == "text" ? (Mode == 0 ? "ciphertext" : "plaintext") : "text");
            HasResult = true;
            Show("completed", InfoBarSeverity.Success);
            if (IsFile && settings.Current.RememberRecentFiles)
            {
                try { await settings.AddRecentAsync(InputPath, token.Token); }
                catch (Exception ex) when (ex is BackendException or OperationCanceledException)
                {
                    Show("completed_recent_failed", InfoBarSeverity.Warning);
                }
            }
        }
        catch (OperationCanceledException) { Show("cancelled"); }
        catch (BackendException ex) { Fail(ex.Code); }
        catch (Exception) { Fail("app.error"); }
        finally { password = confirmation = ""; cancellation = null; IsBusy = false; ProgressText = ""; }
    }

    private void FormatFileResult() => Output = $"{ResultPath}\n{originalSize:N0} → {outputSize:N0} {L["bytes"]}";
    public void Fail(string code)
    {
        Show($"error.{code}", InfoBarSeverity.Error);
        LastErrorCode = code;
    }
    public void Show(string key, InfoBarSeverity kind = InfoBarSeverity.Informational)
    {
        LastErrorCode = "";
        statusKey = key; Raise(nameof(Status)); Severity = kind; HasStatus = true;
    }
    public void Clear()
    {
        if (IsBusy) return;
        Input = InputPath = OutputDir = ""; IgnoreWhitespace = false; ClearResult();
    }
    public bool UseResult()
    {
        if (IsBusy || IsFile || !HasResult) return false;
        if (Output.Length > MaxTextLength) { Fail("resource.limit_exceeded"); return false; }
        var value = Output;
        Mode = 1 - Mode;
        Input = value;
        return true;
    }
    public void ClearResult()
    {
        Output = ""; ResultPath = ""; HasResult = false; HasStatus = false; LastErrorCode = "";
    }
    private void RequestCancellation()
    {
        if (!CanCancel) return;
        cancelling = true;
        ProgressText = L["cancelling_note"];
        Raise(nameof(CanCancel)); Raise(nameof(CancelLabel)); Raise(nameof(IsIndeterminate));
        CancelCommand.Refresh();
        cancellation?.Cancel();
    }
    public async Task CancelAndWaitAsync()
    {
        RequestCancellation();
        if (activeTask is not null) await activeTask;
    }
}
