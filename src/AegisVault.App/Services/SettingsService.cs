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
    public AppSettings Current { get; private set; } = new();
    public event EventHandler? Changed;
    public event EventHandler? BusyChanged;
    public bool IsBusy { get; private set; }
    public Task ActiveTask { get; private set; } = Task.CompletedTask;
    public Task LoadAsync() => RunAsync("settings.get");
    public Task SaveAsync(AppSettings settings) => RunAsync("settings.update", new
    {
        settings.Language, settings.Theme, settings.DefaultOutputDir, settings.OverwriteOutputs,
        settings.RememberRecentFiles, settings.ShowAdvancedOptions
    });
    public Task ClearRecentAsync() => RunAsync("recent.clear");
    public Task AddRecentAsync(string path) => RunAsync("recent.add", new { input_path = path });
    private Task RunAsync(string operation, object? args = null)
    {
        if (IsBusy) return Task.FromException(new BackendException("ipc.busy"));
        return ActiveTask = ExecuteAsync(operation, args);
    }
    private async Task ExecuteAsync(string operation, object? args)
    {
        IsBusy = true; BusyChanged?.Invoke(this, EventArgs.Empty);
        try { Apply(await backend.CallAsync(operation, args)); }
        finally { IsBusy = false; BusyChanged?.Invoke(this, EventArgs.Empty); }
    }
    private void Apply(JsonElement result)
    {
        Current = result.Deserialize<AppSettings>(BackendClient.JsonOptions) ?? throw new BackendException("ipc.invalid_response");
        Localization.Instance.SetLanguage(Current.Language);
        Changed?.Invoke(this, EventArgs.Empty);
    }
}
