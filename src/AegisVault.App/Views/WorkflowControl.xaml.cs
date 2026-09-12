using AegisVault.App.ViewModels;
using AegisVault.App.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.Windows.Storage.Pickers;
using Windows.ApplicationModel.DataTransfer;
using Windows.Storage;
using Windows.System;

namespace AegisVault.App.Views;

public sealed partial class WorkflowControl : UserControl
{
    public static readonly DependencyProperty HeaderProperty = DependencyProperty.Register(
        nameof(Header), typeof(object), typeof(WorkflowControl), new PropertyMetadata(null));
    public object Header { get => GetValue(HeaderProperty); set => SetValue(HeaderProperty, value); }
    private WorkflowViewModel vm = null!;
    private bool attaching;
    public WorkflowControl()
    {
        InitializeComponent();
        Unloaded += (_, _) => Password.Password = Confirmation.Password = "";
        WorkflowScroll.SizeChanged += (_, _) => FitTextToViewport();
        ResultHeading.SizeChanged += (_, _) => FitTextToViewport();
    }
    private void FitTextToViewport()
    {
        if (WorkflowScroll.ActualHeight <= 0) return;
        var maximum = Math.Clamp(WorkflowScroll.ActualHeight - 4, 64, 260);
        TextInput.MinHeight = Math.Min(132, maximum);
        TextInput.MaxHeight = maximum;
        var resultMaximum = Math.Clamp(WorkflowScroll.ActualHeight - ResultHeading.ActualHeight - 12, 32, 260);
        ResultOutput.MinHeight = Math.Min(100, resultMaximum);
        ResultOutput.MaxHeight = resultMaximum;
    }
    public void Attach(WorkflowViewModel value)
    {
        attaching = true;
        vm = value; DataContext = vm;
        bool file = vm.Kind is "file" or "base64_file", crypto = vm.Kind is "text" or "file";
        TextInputs.Visibility = file ? Visibility.Collapsed : Visibility.Visible;
        FileInputs.Visibility = file ? Visibility.Visible : Visibility.Collapsed;
        Passwords.Visibility = crypto ? Visibility.Visible : Visibility.Collapsed;
        ModePicker.Items.Clear();
        ModePicker.Items.Add(vm.L[crypto ? "encrypt" : "encode"]);
        ModePicker.Items.Add(vm.L[crypto ? "decrypt" : "decode"]);
        ModePicker.SelectedIndex = vm.Mode;
        attaching = false;
        vm.RefreshLabels();
    }
    private void ModeChanged(object sender, SelectionChangedEventArgs e)
    {
        if (attaching || vm is null || vm.IsBusy || ModePicker.SelectedIndex < 0) return;
        vm.Mode = ModePicker.SelectedIndex;
        Password.Password = Confirmation.Password = "";
    }
    private async void Run(object sender, RoutedEventArgs e)
    {
        if (vm.IsBusy) return;
        var task = vm.RunAsync(Password.Password, Confirmation.Password);
        if (vm.IsBusy) Password.Password = Confirmation.Password = "";
        await task;
        if (vm.HasResult)
            DispatcherQueue.TryEnqueue(Microsoft.UI.Dispatching.DispatcherQueuePriority.Low, () =>
            {
                if (!IsLoaded || !vm.HasResult) return;
                UpdateLayout();
                FitTextToViewport();
                UpdateLayout();
                ResultOutput.Focus(FocusState.Programmatic);
                // Finish native focus scrolling before revealing the complete final result block.
                DispatcherQueue.TryEnqueue(Microsoft.UI.Dispatching.DispatcherQueuePriority.Low, () =>
                {
                    if (!IsLoaded || !vm.HasResult) return;
                    UpdateLayout();
                    WorkflowScroll.ChangeView(null, WorkflowScroll.ScrollableHeight, null, disableAnimation: true);
                });
            });
        else if (vm.LastErrorCode == "validation.password_mismatch") FocusInput(Confirmation);
        else if (vm.LastErrorCode == "validation.password_required") FocusInput(Password);
        else if (vm.LastErrorCode == "validation.file_required") FocusInput(FileInput);
    }
    private static void FocusInput(Control control)
    {
        control.Focus(FocusState.Programmatic);
        control.StartBringIntoView();
    }
    private void ClearPasswords(object sender, RoutedEventArgs e)
    {
        Password.Password = Confirmation.Password = "";
        RecentPicker.SelectedIndex = -1;
        FocusInput(vm.IsFile ? FileInput : TextInput);
    }
    private void UseResult(object sender, RoutedEventArgs e)
    {
        if (!vm.UseResult()) return;
        ModePicker.SelectedIndex = vm.Mode;
        Password.Password = Confirmation.Password = "";
        FocusInput(TextInput);
    }
    private async void PickFile(object sender, RoutedEventArgs e)
    {
        try
        {
            var picker = new FileOpenPicker(App.Window.AppWindow.Id);
            picker.FileTypeFilter.Add("*");
            var result = await picker.PickSingleFileAsync();
            if (result is not null && !vm.IsBusy) vm.InputPath = result.Path;
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
    }
    private async void PickFolder(object sender, RoutedEventArgs e)
    {
        try
        {
            var result = await new FolderPicker(App.Window.AppWindow.Id).PickSingleFolderAsync();
            if (result is not null && !vm.IsBusy) vm.OutputDir = result.Path;
        }
        catch (Exception) { vm.Fail("file.output_dir_invalid"); }
    }
    private void SelectRecent(object sender, SelectionChangedEventArgs e)
    {
        if (vm is not null && !vm.IsBusy && e.AddedItems.FirstOrDefault() is string path)
        {
            vm.InputPath = path;
            RecentPicker.SelectedIndex = -1;
        }
    }
    private async void ImportText(object sender, RoutedEventArgs e)
    {
        try
        {
            var picker = new FileOpenPicker(App.Window.AppWindow.Id);
            picker.FileTypeFilter.Add("*");
            var result = await picker.PickSingleFileAsync();
            if (result is null) return;
            var value = await TextImport.ReadAsync(result.Path, vm.InputUtf8ByteLimit);
            if (!vm.IsBusy)
            {
                vm.TrySetExternalInput(value);
            }
        }
        catch (BackendException ex) { vm.Fail(ex.Code); }
        catch (Exception) { vm.Fail("file.read_failed"); }
    }
    private void Copy(object sender, RoutedEventArgs e)
    {
        if (!vm.HasResult || vm.IsBusy) return;
        try { var data = new DataPackage(); data.SetText(vm.CopyContent); Clipboard.SetContent(data); vm.Show("copied"); }
        catch (Exception) { vm.Fail("clipboard.unavailable"); }
    }
    private async void SaveText(object sender, RoutedEventArgs e)
    {
        if (!vm.HasResult || vm.IsBusy) return;
        var output = vm.Output;
        try
        {
            var picker = new FileSavePicker(App.Window.AppWindow.Id) { SuggestedFileName = "AegisVault-result" };
            picker.FileTypeChoices.Add(vm.L["text"], new List<string> { ".txt" });
            var result = await picker.PickSaveFileAsync();
            if (result is null) return;
            var temporary = Path.Combine(Path.GetDirectoryName(result.Path)!, $".{Guid.NewGuid():N}.tmp");
            try
            {
                await File.WriteAllTextAsync(temporary, output, new System.Text.UTF8Encoding(false));
                File.Move(temporary, result.Path, overwrite: true); // The native save picker confirms replacement.
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
            if (vm.HasResult && vm.Output == output && !vm.IsBusy) vm.Show("saved");
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
        var format = vm.IsFile ? StandardDataFormats.StorageItems : StandardDataFormats.Text;
        e.AcceptedOperation = !vm.IsBusy && e.DataView.Contains(format) ? DataPackageOperation.Copy : DataPackageOperation.None;
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
                if (!vm.IsBusy) vm.TrySetExternalInput(text);
            }
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
        finally { deferral.Complete(); }
    }
}
