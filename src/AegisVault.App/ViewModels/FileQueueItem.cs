using AegisVault.App.Services;
using Microsoft.UI.Xaml;

namespace AegisVault.App.ViewModels;

public sealed class FileQueueItem(string inputPath) : ObservableObject
{
    private string state = "pending", errorCode = "", resultPath = "";
    private long originalSize, outputSize;
    public string InputPath { get; } = inputPath;
    public string Name => Path.GetFileName(InputPath);
    public Localization L => Localization.Instance;
    public string State => state;
    public string ResultPath => resultPath;
    public string ErrorCode => errorCode;
    public string Status => state == "failed" ? L.Error(errorCode) : L["queue_" + state];
    public string ResultText => $"{ResultPath}\n{originalSize:N0} → {outputSize:N0} {L["bytes"]}";
    public bool CanRemove => state != "running";
    public string RemoveLabel => $"{L["remove_file"]}: {Name}";
    public string RetryLabel => $"{L["retry_file"]}: {Name}";
    public string RevealLabel => $"{L["open_folder"]}: {Name}";
    public Visibility RetryVisibility => state is "failed" or "cancelled" ? Visibility.Visible : Visibility.Collapsed;
    public Visibility ResultVisibility => state == "completed" ? Visibility.Visible : Visibility.Collapsed;
    internal void ChangeState(string value, string code = "")
    {
        state = value; errorCode = code;
        if (value != "completed") resultPath = "";
        RefreshLabels();
    }
    internal void Complete(string path, long sourceBytes, long resultBytes)
    {
        resultPath = path; originalSize = sourceBytes; outputSize = resultBytes;
        ChangeState("completed");
    }
    internal void RefreshLabels()
    {
        Raise(nameof(State)); Raise(nameof(Status)); Raise(nameof(ResultPath)); Raise(nameof(ResultText));
        Raise(nameof(CanRemove)); Raise(nameof(RetryVisibility)); Raise(nameof(ResultVisibility));
        Raise(nameof(RemoveLabel)); Raise(nameof(RetryLabel)); Raise(nameof(RevealLabel)); Raise(nameof(L));
    }
}
