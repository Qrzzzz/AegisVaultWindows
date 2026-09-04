using AegisVault.App.Services;
using Microsoft.UI.Xaml.Controls;

namespace AegisVault.App.ViewModels;

public sealed class SettingsViewModel(SettingsService service) : ObservableObject
{
    public Localization L => Localization.Instance;
    public string VersionLabel => ProductInfo.DisplayName;
    public int LanguageIndex { get; set; } = service.Current.Language == "zh-CN" ? 0 : 1;
    public int ThemeIndex { get; set; } = service.Current.Theme switch { "system" => 0, "light" => 1, _ => 2 };
    private string outputFolder = service.Current.DefaultOutputDir;
    private bool busy, hasStatus;
    private string status = "";
    private InfoBarSeverity severity;
    public string OutputFolder { get => outputFolder; set => Set(ref outputFolder, value); }
    public bool RememberRecent { get; set; } = service.Current.RememberRecentFiles;
    public bool Overwrite { get; set; } = service.Current.OverwriteOutputs;
    public bool IsIdle => !busy;
    public string[] RecentFiles => service.Current.RecentFiles;
    public string Status { get => status; private set => Set(ref status, value); }
    public bool HasStatus { get => hasStatus; private set => Set(ref hasStatus, value); }
    public InfoBarSeverity Severity { get => severity; private set => Set(ref severity, value); }
    public async Task SaveAsync() => await Perform(async () =>
        await service.SaveAsync(service.Current with
        {
            Language = LanguageIndex == 0 ? "zh-CN" : "en-US",
            Theme = ThemeIndex switch { 0 => "system", 1 => "light", _ => "dark" },
            DefaultOutputDir = OutputFolder, RememberRecentFiles = RememberRecent, OverwriteOutputs = Overwrite
        }));
    public async Task ClearRecentAsync() => await Perform(service.ClearRecentAsync);
    private async Task Perform(Func<Task> action)
    {
        if (busy) return;
        busy = true; Raise(nameof(IsIdle));
        try { await action(); Status = L["saved"]; Severity = InfoBarSeverity.Success; Raise(nameof(RecentFiles)); }
        catch (BackendException ex) { Status = L.Error(ex.Code); Severity = InfoBarSeverity.Error; }
        finally { busy = false; HasStatus = true; Raise(nameof(IsIdle)); }
    }
    public void Fail(string code) { Status = L.Error(code); Severity = InfoBarSeverity.Error; HasStatus = true; }
}
