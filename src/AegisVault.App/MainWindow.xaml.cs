using AegisVault.App.Services;
using AegisVault.App.ViewModels;
using AegisVault.App.Views;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Graphics;
using System.Runtime.InteropServices;

namespace AegisVault.App;

public sealed partial class MainWindow : Window
{
    public Localization L => Localization.Instance;
    public string AppVersion => ProductInfo.Version;
    public BackendClient Backend { get; } = new();
    public SettingsService Settings { get; }
    private SettingsViewModel? settingsDraft;
    public SettingsViewModel SettingsDraft => settingsDraft ??= new(Settings);
    public int Base64InputKind { get; set; }
    public WorkflowViewModel TextWorkflow { get; }
    public WorkflowViewModel FileWorkflow { get; }
    public WorkflowViewModel Base64TextWorkflow { get; }
    public WorkflowViewModel Base64FileWorkflow { get; }
    public IEnumerable<WorkflowViewModel> Workflows => [TextWorkflow, FileWorkflow, Base64TextWorkflow, Base64FileWorkflow];
    private readonly CancellationTokenSource windowLifetime = new();
    private Task initializationTask = Task.CompletedTask;
    private bool initialized, closing;

    public MainWindow()
    {
        Settings = new(Backend);
        TextWorkflow = new("text", Backend, Settings);
        FileWorkflow = new("file", Backend, Settings);
        Base64TextWorkflow = new("base64_text", Backend, Settings);
        Base64FileWorkflow = new("base64_file", Backend, Settings);
        InitializeComponent();
        Root.DataContext = this;
        Title = ProductInfo.DisplayName;
        ExtendsContentIntoTitleBar = true;
        SetTitleBar(AppTitleBar);
        var scale = GetDpiForWindow(WinRT.Interop.WindowNative.GetWindowHandle(this)) / 96.0;
        var area = DisplayArea.GetFromWindowId(AppWindow.Id, DisplayAreaFallback.Primary).WorkArea;
        AppWindow.Resize(new SizeInt32(Math.Min((int)(1080 * scale), area.Width - 80), Math.Min((int)(820 * scale), area.Height - 80)));
        AppWindow.SetIcon(Path.Combine(AppContext.BaseDirectory, "Assets", "app_icon.ico"));
        AppWindow.Closing += OnClosing;
        Settings.Changed += (_, _) => ApplySettings();
        Settings.BusyChanged += (_, _) => UpdateNavigation();
        foreach (var workflow in Workflows)
            workflow.PropertyChanged += (_, e) =>
            {
                if (e.PropertyName == nameof(WorkflowViewModel.IsBusy))
                {
                    // Keep the active page usable for cancellation; lock only navigation items.
                    UpdateNavigation();
                }
            };
        Root.Loaded += InitializeAsync;
        UpdatePageInset();
    }

    private void DisplayModeChanged(NavigationView sender, NavigationViewDisplayModeChangedEventArgs args) => UpdatePageInset();
    private void UpdatePageInset()
    {
        // In minimal mode the native pane toggle occupies the top-left of the content surface.
        if (PageHost is not null)
            PageHost.Margin = Navigation.DisplayMode == NavigationViewDisplayMode.Minimal ? new Thickness(0, 40, 0, 0) : new Thickness(0);
    }

    private void UpdateNavigation()
    {
        foreach (NavigationViewItem item in Navigation.MenuItems.Concat(Navigation.FooterMenuItems))
            item.IsEnabled = !Settings.IsBusy && !Workflows.Any(w => w.IsBusy);
    }

    private async void InitializeAsync(object sender, RoutedEventArgs e)
    {
        if (initialized) return;
        initialized = true;
        initializationTask = InitializeCoreAsync();
        await initializationTask;
    }

    private async Task InitializeCoreAsync()
    {
        try
        {
            var hello = await Backend.CallAsync("hello", cancellationToken: windowLifetime.Token);
            if (BackendResponse.Int32(hello, "protocol") != 1 || BackendResponse.String(hello, "version") != ProductInfo.Version)
                throw new BackendException("ipc.version_mismatch");
            await Settings.LoadAsync(windowLifetime.Token);
        }
        catch (BackendException ex) { StartupError.Message = L.Error(ex.Code); StartupError.IsOpen = true; }
        catch (OperationCanceledException) when (windowLifetime.IsCancellationRequested) { }
        catch (Exception) { StartupError.Message = L.Error("app.error"); StartupError.IsOpen = true; }
        ApplySettings();
        Navigation.SelectedItem = Navigation.MenuItems[0];
    }

    private void ApplySettings()
    {
        Root.Language = Settings.Current.Language;
        Root.RequestedTheme = Settings.Current.Theme switch
        {
            "dark" => ElementTheme.Dark, "light" => ElementTheme.Light, _ => ElementTheme.Default
        };
    }

    private void Navigate(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItem is not NavigationViewItem item) return;
        var type = (item.Tag as string) switch
        {
            "file" => typeof(FilePage), "base64" => typeof(Base64Page), "settings" => typeof(SettingsPage),
            _ => typeof(TextPage)
        };
        ContentFrame.Navigate(type);
        if (Navigation.DisplayMode != NavigationViewDisplayMode.Expanded) Navigation.IsPaneOpen = false;
    }

    private async void OnClosing(AppWindow sender, AppWindowClosingEventArgs args)
    {
        if ((!initializationTask.IsCompleted || Settings.IsBusy) && !Workflows.Any(w => w.IsBusy))
        {
            args.Cancel = true;
            if (closing) return;
            closing = true;
            windowLifetime.Cancel();
            Settings.CancelActive();
            try
            {
                await initializationTask;
                if (Settings.IsBusy) await Settings.CancelAndWaitAsync();
            }
            catch (Exception ex) when (ex is BackendException or OperationCanceledException) { }
            finally { closing = false; }
            Close();
            return;
        }
        if (!Workflows.Any(w => w.IsBusy)) return;
        args.Cancel = true;
        if (closing) return;
        closing = true;
        var dialog = new ContentDialog
        {
            XamlRoot = Root.XamlRoot, RequestedTheme = Root.RequestedTheme,
            Title = L["close_title"], Content = L["close_message"],
            PrimaryButtonText = L["cancel_close"], CloseButtonText = L["keep_open"],
            DefaultButton = ContentDialogButton.Close
        };
        try
        {
            if (await dialog.ShowAsync() == ContentDialogResult.Primary)
            {
                windowLifetime.Cancel();
                Settings.CancelActive();
                await Task.WhenAll(Workflows.Select(w => w.CancelAndWaitAsync()));
                Close();
            }
        }
        finally { closing = false; }
    }

    [DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(IntPtr window);
}
