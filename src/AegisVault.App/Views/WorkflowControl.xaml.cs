using AegisVault.App.ViewModels;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.Windows.Storage.Pickers;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage;
using Windows.System;

namespace AegisVault.App.Views;

public sealed partial class WorkflowControl : UserControl
{
    private WorkflowViewModel vm = null!;
    private bool attaching;
    public WorkflowControl() => InitializeComponent();
    public void Attach(WorkflowViewModel value)
    {
        attaching = true;
        vm = value; DataContext = vm;
        bool file = vm.Kind is "file" or "base64_file", crypto = vm.Kind is "text" or "file";
        TextInput.Visibility = ImportButton.Visibility = SaveButton.Visibility = file ? Visibility.Collapsed : Visibility.Visible;
        FileInputs.Visibility = RevealButton.Visibility = file ? Visibility.Visible : Visibility.Collapsed;
        Passwords.Visibility = crypto ? Visibility.Visible : Visibility.Collapsed;
        DecodeOptions.Visibility = vm.Kind == "base64_text" ? Visibility.Visible : Visibility.Collapsed;
        ModePicker.Items.Clear();
        ModePicker.Items.Add(vm.L[crypto ? "encrypt" : "encode"]);
        ModePicker.Items.Add(vm.L[crypto ? "decrypt" : "decode"]);
        ModePicker.SelectedIndex = vm.Mode;
        attaching = false;
        vm.RefreshLabels();
    }
    private void ModeChanged(object sender, SelectionChangedEventArgs e)
    { if (!attaching && vm is not null && ModePicker.SelectedIndex >= 0) vm.Mode = ModePicker.SelectedIndex; }
    private async void Run(object sender, RoutedEventArgs e)
    {
        var task = vm.RunAsync(Password.Password, Confirmation.Password);
        Password.Password = Confirmation.Password = "";
        await task;
        if (vm.HasResult) ResultOutput.StartBringIntoView();
    }
    private void ClearPasswords(object sender, RoutedEventArgs e) => Password.Password = Confirmation.Password = "";
    private async void PickFile(object sender, RoutedEventArgs e)
    {
        try
        {
            var picker = new FileOpenPicker(App.Window.AppWindow.Id);
            picker.FileTypeFilter.Add("*");
            var result = await picker.PickSingleFileAsync();
            if (result is not null) vm.InputPath = result.Path;
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
    }
    private async void PickFolder(object sender, RoutedEventArgs e)
    {
        try
        {
            var result = await new FolderPicker(App.Window.AppWindow.Id).PickSingleFolderAsync();
            if (result is not null) vm.OutputDir = result.Path;
        }
        catch (Exception) { vm.Fail("file.output_dir_invalid"); }
    }
    private void SelectRecent(object sender, SelectionChangedEventArgs e)
    { if (!vm.IsBusy && e.AddedItems.FirstOrDefault() is string path) vm.InputPath = path; }
    private async void ImportText(object sender, RoutedEventArgs e)
    {
        try
        {
            var picker = new FileOpenPicker(App.Window.AppWindow.Id);
            picker.FileTypeFilter.Add("*");
            var result = await picker.PickSingleFileAsync();
            if (result is null) return;
            if (new FileInfo(result.Path).Length > 2 * 1024 * 1024) { vm.Fail("resource.limit_exceeded"); return; }
            using var stream = File.OpenRead(result.Path);
            var bytes = new byte[2 * 1024 * 1024 + 1];
            var count = await stream.ReadAtLeastAsync(bytes, bytes.Length, throwOnEndOfStream: false);
            if (count == bytes.Length) { vm.Fail("resource.limit_exceeded"); return; }
            vm.Input = new System.Text.UTF8Encoding(false, true).GetString(bytes, 0, count).TrimStart('\uFEFF');
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
    }
    private void Copy(object sender, RoutedEventArgs e)
    {
        try { var data = new DataPackage(); data.SetText(vm.Output); Clipboard.SetContent(data); vm.Show(vm.L["copied"]); }
        catch (Exception) { vm.Fail("clipboard.unavailable"); }
    }
    private async void SaveText(object sender, RoutedEventArgs e)
    {
        try
        {
            var picker = new FileSavePicker(App.Window.AppWindow.Id) { SuggestedFileName = "AegisVault-result" };
            picker.FileTypeChoices.Add(vm.L["text"], new List<string> { ".txt" });
            var result = await picker.PickSaveFileAsync();
            if (result is null) return;
            var temporary = Path.Combine(Path.GetDirectoryName(result.Path)!, $".{Guid.NewGuid():N}.tmp");
            try
            {
                await File.WriteAllTextAsync(temporary, vm.Output, new System.Text.UTF8Encoding(false));
                File.Move(temporary, result.Path, overwrite: true); // The native save picker confirms replacement.
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
            vm.Show(vm.L["saved"]);
        }
        catch (Exception) { vm.Fail("file.io_error"); }
    }
    private async void Reveal(object sender, RoutedEventArgs e)
    {
        try
        {
            var folder = await StorageFolder.GetFolderFromPathAsync(Path.GetDirectoryName(vm.ResultPath));
            if (!await Launcher.LaunchFolderAsync(folder)) vm.Fail("file.reveal_failed");
        }
        catch (Exception) { vm.Fail("file.reveal_failed"); }
    }
    private void DragOverInput(object sender, DragEventArgs e)
    {
        e.AcceptedOperation = !vm.IsBusy && (e.DataView.Contains(StandardDataFormats.StorageItems) ||
            e.DataView.Contains(StandardDataFormats.Text)) ? DataPackageOperation.Copy : DataPackageOperation.None;
    }
    private async void DropInput(object sender, DragEventArgs e)
    {
        if (vm.IsBusy) return;
        var deferral = e.GetDeferral();
        try
        {
            if (vm.Kind is "file" or "base64_file")
            {
                if (e.DataView.Contains(StandardDataFormats.StorageItems))
                {
                    var items = await e.DataView.GetStorageItemsAsync();
                    if (!vm.IsBusy && items.Count == 1 && items[0] is StorageFile file) vm.InputPath = file.Path;
                }
            }
            else if (e.DataView.Contains(StandardDataFormats.Text))
            {
                var text = await e.DataView.GetTextAsync();
                if (text.Length > 2097152) vm.Fail("resource.limit_exceeded");
                else if (!vm.IsBusy) vm.Input = text;
            }
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
        finally { deferral.Complete(); }
    }
}
