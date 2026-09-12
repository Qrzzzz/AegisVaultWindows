using AegisVault.App.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;

namespace AegisVault.App.ViewModels;

public sealed class SettingsViewModel : ObservableObject
{
    private readonly SettingsService service;
    private AppSettings baseline = new();
    private int languageIndex, themeIndex;
    private string outputFolder = "", statusKey = "";
    private bool rememberRecent, overwrite, busy, hasStatus;
    private InfoBarSeverity severity;

    public SettingsViewModel(SettingsService service)
    {
        this.service = service;
        ResetDraft();
        service.Changed += (_, _) =>
        {
            Raise(nameof(RecentFiles)); Raise(nameof(HasRecentFiles)); Raise(nameof(EmptyRecentVisibility));
            Raise(nameof(ThemeOptions)); Raise(nameof(ThemeIndex));
            Raise(nameof(Status)); RefreshDraftState();
        };
    }

    public Localization L => Localization.Instance;
    public string VersionLabel => ProductInfo.DisplayName;
    public int LanguageIndex { get => languageIndex; set { if (!busy && value is >= 0 and <= 1 && Set(ref languageIndex, value)) Edited(); } }
    public int ThemeIndex { get => themeIndex; set { if (!busy && value is >= 0 and <= 2 && Set(ref themeIndex, value)) Edited(); } }
    public string[] ThemeOptions => [L["system"], L["light"], L["dark"]];
    public string OutputFolder { get => outputFolder; set { if (!busy && Set(ref outputFolder, value)) Edited(); } }
    public bool RememberRecent { get => rememberRecent; set { if (!busy && Set(ref rememberRecent, value)) Edited(); } }
    public bool Overwrite { get => overwrite; set { if (!busy && Set(ref overwrite, value)) Edited(); } }
    public bool IsIdle => !busy;
    public string[] RecentFiles => service.Current.RecentFiles;
    public bool HasRecentFiles => RecentFiles.Length > 0;
    public Visibility EmptyRecentVisibility => HasRecentFiles ? Visibility.Collapsed : Visibility.Visible;
    public bool HasChanges => LanguageIndex != (baseline.Language == "zh-CN" ? 0 : 1)
        || ThemeIndex != ThemeToIndex(baseline.Theme) || OutputFolder != baseline.DefaultOutputDir
        || RememberRecent != baseline.RememberRecentFiles || Overwrite != baseline.OverwriteOutputs;
    public string DraftStatus => L[HasChanges ? "unsaved_settings" : "settings_current"];
    public string Status => statusKey.StartsWith("error.", StringComparison.Ordinal) ? L.Error(statusKey[6..])
        : string.IsNullOrEmpty(statusKey) ? "" : L[statusKey];
    public bool HasStatus { get => hasStatus; private set => Set(ref hasStatus, value); }
    public InfoBarSeverity Severity { get => severity; private set => Set(ref severity, value); }

    public async Task SaveAsync()
    {
        if (!HasChanges) return;
        await Perform(async () =>
        {
            await service.SaveAsync(baseline with
            {
                Language = LanguageIndex == 0 ? "zh-CN" : "en-US",
                Theme = ThemeIndex switch { 0 => "system", 1 => "light", _ => "dark" },
                DefaultOutputDir = OutputFolder, RememberRecentFiles = RememberRecent, OverwriteOutputs = Overwrite
            }, baseline);
            ResetDraft();
        }, "settings_saved");
    }
    public Task ClearRecentAsync() => Perform(() => service.ClearRecentAsync(), "recent_cleared");
    public void Discard()
    {
        if (busy) return;
        ResetDraft();
        HasStatus = false;
    }
    private void ResetDraft()
    {
        baseline = service.Current;
        languageIndex = service.Current.Language == "zh-CN" ? 0 : 1;
        themeIndex = ThemeToIndex(service.Current.Theme);
        outputFolder = service.Current.DefaultOutputDir;
        rememberRecent = service.Current.RememberRecentFiles;
        overwrite = service.Current.OverwriteOutputs;
        Raise(nameof(LanguageIndex)); Raise(nameof(ThemeIndex)); Raise(nameof(OutputFolder));
        Raise(nameof(RememberRecent)); Raise(nameof(Overwrite)); RefreshDraftState();
    }
    private static int ThemeToIndex(string theme) => theme switch { "system" => 0, "light" => 1, _ => 2 };
    private void Edited() { HasStatus = false; RefreshDraftState(); }
    private void RefreshDraftState() { Raise(nameof(HasChanges)); Raise(nameof(DraftStatus)); }
    private async Task Perform(Func<Task> action, string successKey)
    {
        if (busy) return;
        busy = true; HasStatus = false; Raise(nameof(IsIdle));
        try { await action(); statusKey = successKey; Severity = InfoBarSeverity.Success; }
        catch (BackendException ex) { statusKey = $"error.{ex.Code}"; Severity = InfoBarSeverity.Error; }
        catch (OperationCanceledException) { statusKey = "error.operation.cancelled"; Severity = InfoBarSeverity.Informational; }
        finally { busy = false; HasStatus = true; Raise(nameof(Status)); Raise(nameof(IsIdle)); RefreshDraftState(); }
    }
    public void Fail(string code)
    {
        statusKey = $"error.{code}"; Raise(nameof(Status)); Severity = InfoBarSeverity.Error; HasStatus = true;
    }
}
