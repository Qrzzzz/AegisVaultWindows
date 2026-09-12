using System.Text.Json;

namespace AegisVault.App.Services;

public sealed record AppSettings
{
    public string Language { get; init; } = "zh-CN";
    public string Theme { get; init; } = "light";
    public string DefaultOutputDir { get; init; } = "";
    public bool OverwriteOutputs { get; init; }
    public bool RememberRecentFiles { get; init; } = true;
    public bool ShowAdvancedOptions { get; init; }
    public string[] RecentFiles { get; init; } = [];
}

public sealed class SettingsService(BackendClient backend)
{
    private readonly object sync = new();
    private CancellationTokenSource? activeCancellation;
    public AppSettings Current { get; private set; } = new();
    public event EventHandler? Changed;
    public event EventHandler? BusyChanged;
    public bool IsBusy { get; private set; }
    public Task ActiveTask { get; private set; } = Task.CompletedTask;
    public Task LoadAsync(CancellationToken cancellationToken = default) => RunAsync("settings.get", cancellationToken: cancellationToken);
    public Task SaveAsync(AppSettings settings, CancellationToken cancellationToken = default) =>
        SaveAsync(settings, Current, cancellationToken);
    public Task SaveAsync(AppSettings settings, AppSettings baseline, CancellationToken cancellationToken = default)
    {
        // Merge only the user's edits under the backend lock. For the same field,
        // the last explicit save wins.
        var changes = new Dictionary<string, object>();
        if (settings.Language != baseline.Language) changes["language"] = settings.Language;
        if (settings.Theme != baseline.Theme) changes["theme"] = settings.Theme;
        if (settings.DefaultOutputDir != baseline.DefaultOutputDir) changes["default_output_dir"] = settings.DefaultOutputDir;
        if (settings.OverwriteOutputs != baseline.OverwriteOutputs) changes["overwrite_outputs"] = settings.OverwriteOutputs;
        if (settings.RememberRecentFiles != baseline.RememberRecentFiles) changes["remember_recent_files"] = settings.RememberRecentFiles;
        if (settings.ShowAdvancedOptions != baseline.ShowAdvancedOptions) changes["show_advanced_options"] = settings.ShowAdvancedOptions;
        return changes.Count == 0 ? LoadAsync(cancellationToken) : RunAsync("settings.update", changes, cancellationToken);
    }
    public Task ClearRecentAsync(CancellationToken cancellationToken = default) =>
        RunAsync("recent.clear", cancellationToken: cancellationToken);
    public Task AddRecentAsync(string path, CancellationToken cancellationToken = default) =>
        RunAsync("recent.add", new { input_path = path }, cancellationToken);
    private Task RunAsync(string operation, object? args = null, CancellationToken cancellationToken = default)
    {
        lock (sync)
        {
            if (IsBusy) return Task.FromException(new BackendException("ipc.busy"));
            activeCancellation = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            IsBusy = true; BusyChanged?.Invoke(this, EventArgs.Empty);
            return ActiveTask = ExecuteAsync(operation, args, activeCancellation);
        }
    }
    private async Task ExecuteAsync(string operation, object? args, CancellationTokenSource operationCancellation)
    {
        try { Apply(await backend.CallAsync(operation, args, cancellationToken: operationCancellation.Token)); }
        finally
        {
            lock (sync)
            {
                if (ReferenceEquals(activeCancellation, operationCancellation)) activeCancellation = null;
                IsBusy = false;
            }
            operationCancellation.Dispose();
            BusyChanged?.Invoke(this, EventArgs.Empty);
        }
    }
    public void CancelActive()
    {
        lock (sync) activeCancellation?.Cancel();
    }
    public async Task CancelAndWaitAsync()
    {
        Task task;
        lock (sync) { activeCancellation?.Cancel(); task = ActiveTask; }
        await task;
    }
    private void Apply(JsonElement result)
    {
        AppSettings candidate;
        try { candidate = result.Deserialize<AppSettings>(BackendClient.JsonOptions) ?? throw BackendResponse.Invalid(); }
        catch (Exception ex) when (ex is JsonException or NotSupportedException or InvalidOperationException)
        {
            throw BackendResponse.Invalid();
        }
        if (candidate.Language is not ("zh-CN" or "en-US") || candidate.Theme is not ("system" or "light" or "dark")
            || candidate.DefaultOutputDir is null || candidate.RecentFiles is null || candidate.RecentFiles.Any(path => path is null))
            throw BackendResponse.Invalid();
        Current = candidate;
        Localization.Instance.SetLanguage(Current.Language);
        Changed?.Invoke(this, EventArgs.Empty);
    }
}
