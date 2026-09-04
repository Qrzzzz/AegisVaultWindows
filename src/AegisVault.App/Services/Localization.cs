using System.ComponentModel;
using System.Text.Json;

namespace AegisVault.App.Services;

public sealed class Localization : INotifyPropertyChanged
{
    public static Localization Instance { get; } = new();
    private Dictionary<string, string> messages = [];
    public string Language { get; private set; } = "zh-CN";
    public event PropertyChangedEventHandler? PropertyChanged;
    private Localization() => SetLanguage(Language);
    public string this[string key] => messages.GetValueOrDefault(key, key);
    public void SetLanguage(string language)
    {
        Language = language == "en-US" ? "en-US" : "zh-CN";
        messages = JsonSerializer.Deserialize<Dictionary<string, string>>(
            File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Assets", $"{Language}.json")))!;
        PropertyChanged?.Invoke(this, new("Item[]"));
    }
    public string Error(string code) => messages.GetValueOrDefault($"error.{code}", this["error.app.error"]);
}
