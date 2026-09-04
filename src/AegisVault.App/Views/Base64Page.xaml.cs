using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace AegisVault.App.Views;
public sealed partial class Base64Page : Page
{
    private bool ready;
    public Base64Page()
    {
        InitializeComponent(); DataContext = App.Window.Base64TextWorkflow;
        TextKind.Content = App.Window.L["text"]; FileKind.Content = App.Window.L["file"];
        Workflow.Attach(App.Window.Base64InputKind == 0 ? App.Window.Base64TextWorkflow : App.Window.Base64FileWorkflow);
        InputKind.SelectedIndex = App.Window.Base64InputKind;
        ready = true;
        Loaded += (_, _) => { App.Window.Base64TextWorkflow.PropertyChanged += BusyChanged; App.Window.Base64FileWorkflow.PropertyChanged += BusyChanged; };
        Unloaded += (_, _) => { App.Window.Base64TextWorkflow.PropertyChanged -= BusyChanged; App.Window.Base64FileWorkflow.PropertyChanged -= BusyChanged; };
    }
    private void BusyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e) =>
        InputKind.IsEnabled = !App.Window.Workflows.Any(w => w.IsBusy);
    private void ChangeKind(object sender, SelectionChangedEventArgs e)
    {
        if (!ready || App.Window.Workflows.Any(w => w.IsBusy)) return;
        App.Window.Base64InputKind = InputKind.SelectedIndex;
        Workflow.Attach(InputKind.SelectedIndex == 0 ? App.Window.Base64TextWorkflow : App.Window.Base64FileWorkflow);
    }
}
