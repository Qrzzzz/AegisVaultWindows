using AegisVault.App.Services;
using System.Collections.ObjectModel;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace AegisVault.App.ViewModels;

public sealed class WorkflowViewModel : ObservableObject
{
    public static int MaxTextLength => TextLimits.Contract.MaxEncodedTextUtf16CodeUnits;
    private readonly BackendClient backend;
    private readonly SettingsService settings;
    private CancellationTokenSource? cancellation;
    private Task? activeTask;
    private bool busy, cancelling, hasStatus, hasResult, ignoreWhitespace;
    private int mode;
    private string input = "", inputPath = "", outputDir = "", output = "", statusKey = "", progressText = "";
    private double progress;
    private InfoBarSeverity severity;
    private readonly ObservableCollection<FileQueueItem> files = [];

    public WorkflowViewModel(string kind, BackendClient backend, SettingsService settings)
    {
        Kind = kind;
        this.backend = backend;
        this.settings = settings;
        Files = new(files);
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
            ResetFileResults();
            Raise(nameof(NeedsConfirmation));
            Raise(nameof(DecodeOptionsVisibility));
            Raise(nameof(ActionLabel));
            Raise(nameof(InputCodeUnitLimit));
            Raise(nameof(InputUtf8ByteLimit));
        }
    }
    public string Input { get => input; set { if (!IsBusy && Set(ref input, value)) ClearResult(); } }
    public string InputPath
    {
        get => inputPath;
        set
        {
            if (IsBusy) return;
            files.Clear(); inputPath = "";
            if (!string.IsNullOrWhiteSpace(value)) AddFiles([value]);
            RefreshQueue(); ClearResult(); Raise();
        }
    }
    public string OutputDir { get => outputDir; set { if (!IsBusy && Set(ref outputDir, value)) { ClearResult(); ResetFileResults(); } } }
    public bool IgnoreWhitespace { get => ignoreWhitespace; set { if (!IsBusy && Set(ref ignoreWhitespace, value)) ClearResult(); } }
    public string Output { get => output; private set => Set(ref output, value); }
    public string ResultPath { get; private set; } = "";
    public string CopyContent => IsFile ? string.Join(Environment.NewLine, files.Where(f => f.State == "completed").Select(f => f.ResultPath)) : Output;
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
            Raise(nameof(CanEditQueue)); Raise(nameof(CanRun));
            Raise(nameof(ResultActionsVisibility)); Raise(nameof(TextResultVisibility)); Raise(nameof(FileResultVisibility));
            CancelCommand.Refresh(); ClearCommand.Refresh();
        }
    }
    public bool IsIdle => !IsBusy;
    public bool CanEditQueue => !cancelling;
    public bool CanRun => !IsBusy && (!IsFile || files.Any(f => f.State is "pending" or "cancelled"));
    public ReadOnlyObservableCollection<FileQueueItem> Files { get; }
    public string QueueSummary => string.Format(L["queue_summary"], files.Count,
        files.Count(f => f.State == "completed"), files.Count(f => f.State == "failed"),
        files.Count(f => f.State is "pending" or "cancelled"));
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
            Raise(nameof(ResultActionsVisibility));
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
    public Visibility ResultActionsVisibility => HasResult && !IsBusy ? Visibility.Visible : Visibility.Collapsed;
    public Visibility TextResultVisibility => HasResult && !IsBusy && !IsFile ? Visibility.Visible : Visibility.Collapsed;
    public Visibility FileResultVisibility => HasResult && !IsBusy && IsFile ? Visibility.Visible : Visibility.Collapsed;
    public string OutputFolderPlaceholder => string.IsNullOrWhiteSpace(settings.Current.DefaultOutputDir) ? L["same_folder"] : settings.Current.DefaultOutputDir;
    public string ActionLabel => L[IsCrypto ? (Mode == 0 ? "encrypt" : "decrypt") : (Mode == 0 ? "encode" : "decode")];
    public int InputCodeUnitLimit => TextLimits.Utf16CodeUnitLimit(Kind, Mode);
    public int InputUtf8ByteLimit => TextLimits.Utf8ByteLimit(Kind, Mode);
    public ActionCommand CancelCommand { get; }
    public ActionCommand ClearCommand { get; }

    public void RefreshLabels()
    {
        Raise(nameof(ActionLabel)); Raise(nameof(CopyLabel)); Raise(nameof(Status)); Raise(nameof(CancelLabel));
        Raise(nameof(OverwriteWarning)); Raise(nameof(RecentFiles)); Raise(nameof(RecentVisibility));
        Raise(nameof(OutputFolderPlaceholder));
        foreach (var file in files) file.RefreshLabels();
        Raise(nameof(QueueSummary));
        if (IsFile && HasResult) FormatFileResult();
    }

    public void AddFiles(IEnumerable<string> paths)
    {
        if (!IsFile || !CanEditQueue) return;
        var rejected = false;
        foreach (var value in paths)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(value) || value.Length > 32767 || !TextLimits.HasValidUnicode(value))
                { rejected = true; continue; }
                var path = Path.GetFullPath(value);
                if (Directory.Exists(path)) { rejected = true; continue; }
                if (files.Any(f => string.Equals(f.InputPath, path, StringComparison.OrdinalIgnoreCase))) continue;
                if (files.Count >= BatchResponse.MaxFiles) { Fail("resource.limit_exceeded"); break; }
                files.Add(new(path)); inputPath = path; Raise(nameof(InputPath));
            }
            catch (Exception ex) when (ex is ArgumentException or NotSupportedException or PathTooLongException)
            { rejected = true; }
        }
        if (rejected) Show("queue_files_only", InfoBarSeverity.Warning);
        RefreshQueue();
    }

    public void RemoveFile(FileQueueItem file)
    {
        if (!CanEditQueue || !file.CanRemove) return;
        files.Remove(file); RefreshQueue(); FormatFileResult();
    }

    public void RetryFile(FileQueueItem file)
    {
        if (!CanEditQueue || !files.Contains(file) || file.State is not ("failed" or "cancelled")) return;
        file.ChangeState("pending"); RefreshQueue();
    }

    public void ClearQueue()
    {
        if (IsBusy) return;
        files.Clear(); inputPath = ""; Raise(nameof(InputPath));
        ClearResult(); RefreshQueue();
    }

    private void RefreshQueue() { Raise(nameof(QueueSummary)); Raise(nameof(CanRun)); }
    private void ResetFileResults()
    {
        foreach (var file in files) file.ChangeState("pending");
        RefreshQueue();
    }

    public Task RunAsync(string password = "", string confirmation = "")
    {
        if (IsBusy) return activeTask ?? Task.CompletedTask;
        activeTask = ExecuteAsync(password, confirmation);
        return activeTask;
    }

    private async Task ExecuteAsync(string password, string confirmation)
    {
        if (!IsFile) ClearResult();
        if (IsFile && files.Count == 0) { Fail("validation.file_required"); return; }
        if (IsCrypto && password.Length == 0) { Fail("validation.password_required"); return; }
        if (IsCrypto && Mode == 0 && password != confirmation) { Fail("validation.password_mismatch"); return; }
        if (!IsFile && !TextLimits.HasValidUnicode(Input)) { Fail("ipc.invalid_request"); return; }
        if (!IsFile && !TextLimits.Fits(Kind, Mode, Input)) { Fail("resource.limit_exceeded"); return; }
        if (IsFile && !CanRun) return;
        using var token = new CancellationTokenSource();
        cancellation = token; cancelling = false; IsBusy = true;
        Progress = 0; ProgressText = L["working"];
        try
        {
            if (IsFile)
            {
                await ExecuteFilesAsync(password, token);
                return;
            }
            var op = Kind switch
            {
                "text" => Mode == 0 ? "text.encrypt" : "text.decrypt",
                _ => Mode == 0 ? "base64.encode_text" : "base64.decode_text"
            };
            var report = new Progress<BackendProgress>(p =>
            {
                if (!ReferenceEquals(cancellation, token) || !IsBusy || cancelling) return;
                Progress = Math.Clamp(p.Percent * 100, 0, 100);
                ProgressText = p.TotalBytes.HasValue ? $"{Progress:F0}% · {p.ProcessedBytes:N0} / {p.TotalBytes:N0} {L["bytes"]}" : L["working"];
            });
            var result = await backend.CallAsync(op, new { text = Input, password,
                strict = !IgnoreWhitespace, ignore_ascii_whitespace = IgnoreWhitespace }, report, token.Token);
            Output = BackendResponse.String(result, Kind == "text" ? (Mode == 0 ? "ciphertext" : "plaintext") : "text");
            HasResult = true;
            Show("completed", InfoBarSeverity.Success);
        }
        catch (OperationCanceledException) { Show("cancelled"); }
        catch (BackendException ex) { Fail(ex.Code); }
        catch (Exception) { Fail("app.error"); }
        finally { password = confirmation = ""; cancellation = null; cancelling = false; IsBusy = false; ProgressText = ""; }
    }

    private async Task ExecuteFilesAsync(string password, CancellationTokenSource token)
    {
        foreach (var item in files.Where(f => f.State == "cancelled")) item.ChangeState("pending");
        Show("working");
        var operation = Kind == "file" ? (Mode == 0 ? "file.encrypt" : "file.decrypt")
            : Mode == 0 ? "base64.encode_file" : "base64.decode_file";
        // Freeze options for this run. Queue contents stay editable between items.
        var destination = string.IsNullOrWhiteSpace(OutputDir) ? settings.Current.DefaultOutputDir : OutputDir;
        var finished = 0;
        var historyFailed = false;
        while (!token.IsCancellationRequested && files.FirstOrDefault(f => f.State == "pending") is { } item)
        {
            item.ChangeState("running"); RefreshQueue();
            var current = item;
            var report = new Progress<BackendProgress>(p =>
            {
                if (!ReferenceEquals(cancellation, token) || current.State != "running" || cancelling) return;
                var total = finished + 1 + files.Count(f => f.State == "pending");
                Progress = (finished + p.Percent) * 100 / total;
                ProgressText = $"{finished + 1}/{total} · {current.Name} · {p.Percent:P0}";
            });
            ProgressText = $"{finished + 1}/{finished + 1 + files.Count(f => f.State == "pending")} · {item.Name}";
            try
            {
                // Submit just the selected item to the batch endpoint so pending
                // additions/removals take effect before the next backend request.
                var response = await backend.CallAsync("file.batch", new { operation, input_paths = new[] { item.InputPath },
                    password, output_dir = string.IsNullOrWhiteSpace(destination) ? Path.GetDirectoryName(item.InputPath)! : destination }, report, token.Token);
                var results = BatchResponse.Read(response);
                if (results.Count != 1 || results[0].InputPath != item.InputPath) throw BackendResponse.Invalid();
                var result = results[0];
                if (result.Status == "completed")
                    item.Complete(result.OutputPath, result.OriginalSize, result.OutputSize);
                else item.ChangeState(result.Status, result.Code);
                FormatFileResult(); RefreshQueue();
                if (result.Status is "cancelled" or "pending") break;
                if (result.Status == "completed" && settings.Current.RememberRecentFiles)
                {
                    try { await settings.AddRecentAsync(item.InputPath, token.Token); }
                    catch (Exception ex) when (ex is BackendException or OperationCanceledException) { historyFailed = true; }
                }
            }
            catch (OperationCanceledException) { item.ChangeState("cancelled"); break; }
            catch (BackendException ex)
            {
                item.ChangeState("failed", ex.Code); RefreshQueue();
                // A broken transport leaves the outcome uncertain; do not start
                // more files. Already committed results remain available.
                Fail(ex.Code); return;
            }
            catch (Exception) { item.ChangeState("failed", "app.error"); RefreshQueue(); Fail("app.error"); return; }
            finished++;
        }
        FormatFileResult(); RefreshQueue();
        if (historyFailed && files.All(f => f.State == "completed")) Show("completed_recent_failed", InfoBarSeverity.Warning);
        else if (token.IsCancellationRequested || files.Any(f => f.State == "cancelled")) Show("cancelled");
        else if (files.Any(f => f.State == "failed"))
        {
            if (files.Count == 1) Fail(files[0].ErrorCode);
            else Show("queue_partial", InfoBarSeverity.Warning);
        }
        else Show(historyFailed ? "completed_recent_failed" : "completed", historyFailed ? InfoBarSeverity.Warning : InfoBarSeverity.Success);
        if (!token.IsCancellationRequested) Progress = 100;
    }

    private void FormatFileResult()
    {
        var completed = files.Where(f => f.State == "completed").ToArray();
        ResultPath = completed.LastOrDefault()?.ResultPath ?? "";
        Output = string.Join("\n\n", completed.Select(f => f.ResultText));
        HasResult = completed.Length > 0;
    }
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
        var value = Output;
        var nextMode = 1 - Mode;
        if (!TextLimits.HasValidUnicode(value)) { Fail("ipc.invalid_response"); return false; }
        if (!TextLimits.Fits(Kind, nextMode, value)) { Fail("resource.limit_exceeded"); return false; }
        Mode = nextMode;
        Input = value;
        return true;
    }
    public bool TrySetExternalInput(string value)
    {
        if (IsBusy) return false;
        if (!TextLimits.HasValidUnicode(value)) { Fail("ipc.invalid_request"); return false; }
        if (!TextLimits.Fits(Kind, Mode, value)) { Fail("resource.limit_exceeded"); return false; }
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
        Raise(nameof(CanEditQueue));
        CancelCommand.Refresh();
        cancellation?.Cancel();
    }
    public async Task CancelAndWaitAsync()
    {
        RequestCancellation();
        if (activeTask is not null) await activeTask;
    }
}
