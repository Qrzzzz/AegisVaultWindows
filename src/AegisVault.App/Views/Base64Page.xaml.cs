using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
namespace AegisVault.App.Views;
public sealed partial class Base64Page : Page
{
    public Base64Page()
    {
        InitializeComponent(); DataContext = App.Window.Base64TextWorkflow;
        TextKind.Content = App.Window.L["text"]; FileKind.Content = App.Window.L["file"];
        TextWorkflow.Attach(App.Window.Base64TextWorkflow); FileWorkflow.Attach(App.Window.Base64FileWorkflow);
        Loaded += (_, _) => { App.Window.Base64TextWorkflow.PropertyChanged += BusyChanged; App.Window.Base64FileWorkflow.PropertyChanged += BusyChanged; };
        Unloaded += (_, _) => { App.Window.Base64TextWorkflow.PropertyChanged -= BusyChanged; App.Window.Base64FileWorkflow.PropertyChanged -= BusyChanged; };
    }
    private void BusyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e) =>
        InputKind.IsEnabled = !App.Window.Workflows.Any(w => w.IsBusy);
    private void ChangeKind(object sender, SelectionChangedEventArgs e)
    {
        if (TextWorkflow is null || FileWorkflow is null) return;
        TextWorkflow.Visibility = InputKind.SelectedIndex == 0 ? Visibility.Visible : Visibility.Collapsed;
        FileWorkflow.Visibility = InputKind.SelectedIndex == 1 ? Visibility.Visible : Visibility.Collapsed;
    }
}
