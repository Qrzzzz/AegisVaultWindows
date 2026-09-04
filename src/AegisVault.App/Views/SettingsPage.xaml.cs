using AegisVault.App.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.Windows.Storage.Pickers;
namespace AegisVault.App.Views;
public sealed partial class SettingsPage : Page
{
    private readonly SettingsViewModel vm = new(App.Window.Settings);
    public SettingsPage() { InitializeComponent(); DataContext = vm; UpdateLabels(); }
    private void UpdateLabels()
    { SystemTheme.Content = vm.L["system"]; LightTheme.Content = vm.L["light"]; DarkTheme.Content = vm.L["dark"]; }
    private async void Save(object sender, RoutedEventArgs e) { await vm.SaveAsync(); UpdateLabels(); }
    private async void ClearRecent(object sender, RoutedEventArgs e) => await vm.ClearRecentAsync();
    private async void PickFolder(object sender, RoutedEventArgs e)
    {
        try
        {
            var result = await new FolderPicker(App.Window.AppWindow.Id).PickSingleFolderAsync();
            if (result is not null) vm.OutputFolder = result.Path;
        }
        catch (Exception) { vm.Fail("file.output_dir_invalid"); }
    }
}
