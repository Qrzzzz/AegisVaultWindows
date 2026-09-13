using AegisVault.App.ViewModels;
using AegisVault.App.Services;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Automation.Peers;
using Microsoft.UI.Xaml.Automation;
using Microsoft.UI.Xaml.Data;
using Microsoft.UI.Xaml.Input;
using System.ComponentModel;
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
    private readonly DispatcherTimer announcementTimer = new() { Interval = TimeSpan.FromMilliseconds(400) };
    private string lastAnnouncement = "";
    public WorkflowControl()
    {
        InitializeComponent();
        Loaded += (_, _) => { if (vm is not null) { vm.PropertyChanged -= WorkflowChanged; vm.PropertyChanged += WorkflowChanged; } };
        Unloaded += (_, _) =>
        {
            Password.Password = Confirmation.Password = "";
            announcementTimer.Stop();
            if (vm is not null) vm.PropertyChanged -= WorkflowChanged;
        };
        announcementTimer.Tick += (_, _) => AnnounceQueue();
        WorkflowScroll.SizeChanged += (_, _) => FitTextToViewport();
        ResultHeading.SizeChanged += (_, _) => FitTextToViewport();
    }
    private void FitTextToViewport()
    {
        if (WorkflowScroll.ActualHeight <= 0) return;
        var maximum = Math.Clamp(WorkflowScroll.ActualHeight - 4, 64, 260);
        TextInput.MinHeight = Math.Min(132, maximum);
        TextInput.MaxHeight = maximum;
        FileQueueControl.MaxHeight = Math.Clamp(WorkflowScroll.ActualHeight * 0.65, 120, 400);
        var resultMaximum = Math.Clamp(WorkflowScroll.ActualHeight - ResultHeading.ActualHeight - 12, 32, 260);
        ResultOutput.MinHeight = Math.Min(100, resultMaximum);
        ResultOutput.MaxHeight = resultMaximum;
    }
    public void Attach(WorkflowViewModel value)
    {
        attaching = true;
        if (vm is not null) vm.PropertyChanged -= WorkflowChanged;
        vm = value; DataContext = vm;
        vm.PropertyChanged += WorkflowChanged;
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
    private void WorkflowChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (!IsLoaded || !vm.IsFile || e.PropertyName is not (nameof(vm.QueueSummary) or nameof(vm.Status))) return;
        // Coalesce a batch of row updates; byte progress never interrupts speech.
        announcementTimer.Stop();
        announcementTimer.Start();
    }
    private void AnnounceQueue()
    {
        announcementTimer.Stop();
        if (!IsLoaded) return;
        var message = $"{vm.QueueSummary}. {vm.Status}";
        if (message == lastAnnouncement) return;
        lastAnnouncement = message;
        var peer = FrameworkElementAutomationPeer.FromElement(QueueSummaryText)
            ?? FrameworkElementAutomationPeer.CreatePeerForElement(QueueSummaryText);
        peer?.RaiseNotificationEvent(AutomationNotificationKind.Other,
            AutomationNotificationProcessing.MostRecent, message, "FileQueueStatus");
    }
    private void FocusQueueItem(int index = 0)
    {
        DispatcherQueue.TryEnqueue(Microsoft.UI.Dispatching.DispatcherQueuePriority.Low, () =>
        {
            if (!IsLoaded) return;
            if (vm.VisibleFiles.Count == 0) { FocusInput(PickFilesButton); return; }
            var item = vm.VisibleFiles[Math.Clamp(index, 0, vm.VisibleFiles.Count - 1)];
            FileQueueControl.SelectedItem = item;
            FileQueueControl.ScrollIntoView(item);
            FileQueueControl.UpdateLayout();
            FocusInput(FileQueueControl.ContainerFromItem(item) as Control ?? FileQueueControl);
        });
    }
    private void QueueKeyDown(object sender, KeyRoutedEventArgs e)
    {
        // Delete only on the row itself, never while editing/selecting result text.
        if (e.Key != VirtualKey.Delete || FocusManager.GetFocusedElement(XamlRoot) is not ListViewItem row
            || row.Content is not FileQueueItem item || !item.CanRemove || !vm.CanEditQueue) return;
        var index = vm.VisibleFiles.IndexOf(item);
        vm.RemoveFile(item);
        FocusQueueItem(index);
        e.Handled = true;
    }
    private void QueueGotFocus(object sender, RoutedEventArgs e)
    {
        if (FocusManager.GetFocusedElement(XamlRoot) is FrameworkElement target)
            target.StartBringIntoView(new BringIntoViewOptions { AnimationDesired = false });
    }
    private void QueueContainerChanging(ListViewBase sender, ContainerContentChangingEventArgs e)
    {
        e.ItemContainer.ClearValue(AutomationProperties.NameProperty);
        e.ItemContainer.ClearValue(AutomationProperties.HelpTextProperty);
        if (e.InRecycleQueue || e.Item is not FileQueueItem item) return;
        e.ItemContainer.SetBinding(AutomationProperties.NameProperty,
            new Binding { Source = item, Path = new PropertyPath(nameof(FileQueueItem.AutomationName)), Mode = BindingMode.OneWay });
        e.ItemContainer.SetBinding(AutomationProperties.HelpTextProperty,
            new Binding { Source = item, Path = new PropertyPath(nameof(FileQueueItem.InputPath)), Mode = BindingMode.OneWay });
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
        if (vm.IsBusy)
        {
            Password.Password = Confirmation.Password = "";
            FocusInput(CancelButton);
        }
        var movedDuringRun = false;
        RoutedEventHandler trackFocus = (_, _) =>
        {
            if (vm.IsBusy && !ReferenceEquals(FocusManager.GetFocusedElement(XamlRoot), CancelButton))
                movedDuringRun = true;
        };
        GotFocus += trackFocus;
        try { await task; }
        finally { GotFocus -= trackFocus; }
        if (!IsLoaded) return;
        if (movedDuringRun) return;
        if (vm.IsFile && (vm.HasResult || vm.Files.Any(file => file.State == "failed")) && !vm.LastErrorCode.StartsWith("validation.", StringComparison.Ordinal))
        {
            FocusQueueItem();
            return;
        }
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
        else if (vm.LastErrorCode == "validation.file_required") FocusInput(PickFilesButton);
        else if (vm.IsFile) FocusQueueItem();
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
        FocusInput(vm.IsFile ? PickFilesButton : TextInput);
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
            var result = await picker.PickMultipleFilesAsync();
            if (result is not null) vm.AddFiles(result.Select(file => file.Path));
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
        finally { if (IsLoaded) FocusInput(PickFilesButton); }
    }
    private async void PickFolder(object sender, RoutedEventArgs e)
    {
        try
        {
            var result = await new FolderPicker(App.Window.AppWindow.Id).PickSingleFolderAsync();
            if (result is not null && !vm.IsBusy) vm.OutputDir = result.Path;
        }
        catch (Exception) { vm.Fail("file.output_dir_invalid"); }
        finally { if (IsLoaded && sender is Control control) FocusInput(control); }
    }
    private void SelectRecent(object sender, SelectionChangedEventArgs e)
    {
        if (vm is not null && vm.CanEditQueue && e.AddedItems.FirstOrDefault() is string path)
        {
            vm.AddFiles([path]);
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
        => await RevealPathAsync(vm.ResultPath);
    private async Task RevealPathAsync(string path)
    {
        try
        {
            var folder = await StorageFolder.GetFolderFromPathAsync(Path.GetDirectoryName(path));
            if (!await Launcher.LaunchFolderAsync(folder)) vm.Fail("file.reveal_failed");
        }
        catch (Exception) { vm.Fail("file.reveal_failed"); }
    }
    private void ClearFileQueue(object sender, RoutedEventArgs e)
    {
        vm.ClearQueue();
        FocusInput(PickFilesButton);
    }
    private void RetryFailedFiles(object sender, RoutedEventArgs e)
    {
        vm.RetryFailedFiles();
        FocusInput(vm.IsCrypto ? Password : RunButton);
    }
    private void ClearCompletedFiles(object sender, RoutedEventArgs e)
    {
        vm.ClearCompletedFiles();
        FocusQueueItem();
    }
    private void RemoveQueueItem(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { DataContext: FileQueueItem item } && item.CanRemove && vm.CanEditQueue)
        {
            var index = vm.VisibleFiles.IndexOf(item);
            vm.RemoveFile(item);
            FocusQueueItem(index);
        }
    }
    private void RetryQueueItem(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { DataContext: FileQueueItem item } && vm.CanEditQueue)
        {
            vm.RetryFile(item);
            if (vm.IsBusy) FocusQueueItem(vm.VisibleFiles.IndexOf(item));
            else FocusInput(vm.IsCrypto ? Password : RunButton);
        }
    }
    private async void RevealQueueItem(object sender, RoutedEventArgs e)
    {
        if (sender is FrameworkElement { DataContext: FileQueueItem item } && item.State == "completed")
            await RevealPathAsync(item.ResultPath);
    }
    private void DragOverInput(object sender, DragEventArgs e)
    {
        if (e.DataView.Contains(StandardDataFormats.StorageItems)) return; // Window routes file drops from every page.
        var format = vm.IsFile ? StandardDataFormats.StorageItems : StandardDataFormats.Text;
        e.AcceptedOperation = (vm.IsFile ? vm.CanEditQueue : !vm.IsBusy) && e.DataView.Contains(format)
            ? DataPackageOperation.Copy : DataPackageOperation.None;
        e.Handled = true;
    }
    private async void DropInput(object sender, DragEventArgs e)
    {
        if (e.DataView.Contains(StandardDataFormats.StorageItems)) return;
        if (vm.IsFile ? !vm.CanEditQueue : vm.IsBusy) return;
        var deferral = e.GetDeferral();
        try
        {
            if (!vm.IsFile && e.DataView.Contains(StandardDataFormats.Text))
            {
                var text = await e.DataView.GetTextAsync();
                if (!vm.IsBusy) vm.TrySetExternalInput(text);
            }
        }
        catch (Exception) { vm.Fail("file.read_failed"); }
        finally { e.Handled = true; deferral.Complete(); }
    }
}
