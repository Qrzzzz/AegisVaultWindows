using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows.Automation;

internal static class Program
{
    private static AutomationElement window = null!;
    private static Process process = null!;
    private static string evidence = "";
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length < 2) throw new ArgumentException("Usage: NativeTests <AegisVault.exe> <evidence-directory> [theme] [language]");
        evidence = Path.GetFullPath(args[1]); Directory.CreateDirectory(evidence);
        var profile = Path.Combine(evidence, Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path.Combine(profile, "AegisVault"));
        var theme = args.Length > 2 ? args[2] : "light";
        var language = args.Length > 3 ? args[3] : "en-US";
        var labels = Messages(args[0], language);
        var previousClipboard = System.Windows.Forms.Clipboard.GetDataObject();
        File.WriteAllText(Path.Combine(profile, "AegisVault", "settings.json"),
            JsonSerializer.Serialize(new { language, theme, remember_recent_files = false }));
        var info = new ProcessStartInfo(Path.GetFullPath(args[0])) { UseShellExecute = false, WorkingDirectory = profile };
        info.Environment["LOCALAPPDATA"] = profile;
        info.Environment["APPDATA"] = profile;
        info.Environment["PATH"] = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "System32");
        process = Process.Start(info)!;
        try
        {
            window = Wait(() => AutomationElement.RootElement.FindFirst(TreeScope.Children,
                new AndCondition(new PropertyCondition(AutomationElement.ProcessIdProperty, process.Id),
                    new PropertyCondition(AutomationElement.ClassNameProperty, "WinUIDesktopWin32WindowClass"))), "WinUI window");
            Wait(() => Find("TextInput"), "Text page");
            Console.WriteLine($"Window class: {window.Current.ClassName}; framework: {window.Current.FrameworkId}");
            Console.WriteLine($"DPI: {GetDpiForWindow(new IntPtr(window.Current.NativeWindowHandle))}; High Contrast: {System.Windows.SystemParameters.HighContrast}");
            var originalBounds = window.Current.BoundingRectangle;
            var transform = (TransformPattern)window.GetCurrentPattern(TransformPattern.Pattern);
            Capture($"text-idle-{theme}-{language}.png");
            transform.Resize(680, 640);
            WaitVisible("Run");
            AssertNavigationClear("WorkflowScroll");
            if (Find("Cancel") is { } idleCancel && !idleCancel.Current.IsOffscreen) throw new Exception("Idle Cancel is visible");
            Set("TextInput", "WinUI AGV1 roundtrip");
            Set("Password", "native-test-password"); Set("ConfirmPassword", "wrong-confirmation");
            Invoke("Run");
            WaitMessage("Status", labels["error.validation.password_mismatch"]);
            Wait(() => AutomationElement.FocusedElement.Current.AutomationId == "ConfirmPassword" ? Find("ConfirmPassword") : null, "Validation focus");
            WaitVisible("Run");
            Capture($"narrow-validation-{theme}-{language}.png");
            Set("ConfirmPassword", "native-test-password"); // The original password must survive validation.
            Find("Password")!.SetFocus();
            System.Windows.Forms.SendKeys.SendWait("^{ENTER}");
            var token = WaitText("Result", value => value.StartsWith("AGV1.", StringComparison.Ordinal));
            WaitVisible("Result"); WaitVisible("Run");
            Capture($"narrow-text-result-{theme}-{language}.png");
            InvokeResult("UseResult");
            WaitText("TextInput", value => value == token);
            transform.Resize(originalBounds.Width, originalBounds.Height);
            Invoke("Run");
            WaitMessage("Status", labels["error.validation.password_required"]);
            Set("Password", "native-test-password"); Invoke("Run");
            WaitText("Result", value => value == "WinUI AGV1 roundtrip");
            WaitVisible("Result");
            Capture($"text-{theme}-{language}.png");
            InvokeResult("CopyResult");
            if (System.Windows.Forms.Clipboard.GetText() != "WinUI AGV1 roundtrip") throw new Exception("Text clipboard differs");
            var savedText = Path.Combine(profile, "saved-result.txt");
            InvokeResult("SaveText"); PickNativePath(savedText);
            WaitMessage("Status", labels["saved"]);
            if (File.ReadAllText(savedText) != "WinUI AGV1 roundtrip") throw new Exception("Saved text differs");
            Console.WriteLine("PASS: native Text correction, focus, reverse-input reuse, password clearing, clipboard and save picker");
            SelectNav("NavFile"); Wait(() => Find("InputFile"), "File page");
            var input = Path.Combine(profile, "fixture.bin");
            File.WriteAllBytes(input, Enumerable.Range(0, 256).Select(i => (byte)i).ToArray());
            Invoke("PickFile");
            PickNativePath(input);
            WaitText("InputFile", value => value == input);
            Console.WriteLine("PASS: Windows App SDK native file picker");
            Set("Password", "native-file-password"); Set("ConfirmPassword", "native-file-password");
            Invoke("Run");
            var fileResult = WaitText("Result", value => value.Contains(".agv", StringComparison.Ordinal));
            var encryptedPath = fileResult.Split(['\r', '\n'])[0].Trim();
            if (!File.Exists(encryptedPath)) throw new Exception("Native file operation did not produce its result");
            WaitVisible("Result"); InvokeResult("CopyResult");
            if (System.Windows.Forms.Clipboard.GetText() != encryptedPath) throw new Exception("File clipboard contains more than its path");
            Capture($"file-{theme}-{language}.png");
            Set("OutputFolder", profile);
            if (Find("Result") is not null) throw new Exception("Changing output folder retained a stale result");
            Set("OutputFolder", "");
            ChooseMode(1); Set("InputFile", encryptedPath); Set("Password", "native-file-password"); Invoke("Run");
            var restoredPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            if (!File.ReadAllBytes(input).SequenceEqual(File.ReadAllBytes(restoredPath))) throw new Exception("Native file roundtrip differs");
            Console.WriteLine("PASS: native File encrypt/decrypt");
            var large = Path.Combine(profile, "cancel.bin");
            using (var stream = File.Create(large)) stream.SetLength(512L * 1024 * 1024);
            ChooseMode(0); Set("InputFile", large); Set("Password", "cancel-password"); Set("ConfirmPassword", "cancel-password");
            transform.Resize(680, 640);
            Invoke("Run"); WaitVisible("Cancel");
            if (Find("InputFile")!.Current.IsEnabled || Find("NavText") is { } navText && navText.Current.IsEnabled)
                throw new Exception("Task inputs or navigation stayed enabled");
            Invoke("Cancel");
            Wait(() => Find("Message") is { } message && (message.Current.Name.Contains("cancelled", StringComparison.OrdinalIgnoreCase) || message.Current.Name.Contains("已取消", StringComparison.Ordinal)) ? message : null, "Cancellation terminal");
            if (File.Exists(large + ".agv") || Directory.GetFiles(profile, ".*.tmp").Length != 0) throw new Exception("Cancellation left partial output");
            WaitVisible("Run"); Capture($"narrow-cancelled-{theme}-{language}.png");
            transform.Resize(originalBounds.Width, originalBounds.Height);
            Console.WriteLine("PASS: native cooperative cancellation and partial-output cleanup");
            SelectNav("NavBase64"); Wait(() => Find("TextInput"), "Base64 page");
            if (Find("IgnoreWhitespace") is not null) throw new Exception("Decode option is exposed while encoding");
            Set("TextInput", "hello"); Invoke("Run"); WaitText("Result", value => value == "aGVsbG8=");
            ChooseMode(1); Set("TextInput", "aGVsbG8="); Invoke("Run"); WaitText("Result", value => value == "hello");
            ((TogglePattern)Find("IgnoreWhitespace")!.GetCurrentPattern(TogglePattern.Pattern)).Toggle();
            Set("TextInput", "aG Vs bG8=\r\n"); Invoke("Run"); WaitText("Result", value => value == "hello");
            Capture($"base64-{theme}-{language}.png");
            Invoke("Clear");
            if (((TogglePattern)Find("IgnoreWhitespace")!.GetCurrentPattern(TogglePattern.Pattern)).Current.ToggleState != ToggleState.Off)
                throw new Exception("Clear did not reset whitespace mode");
            Console.WriteLine("PASS: native Base64 encode/decode");
            Choose("InputKind", 1); Wait(() => Find("InputFile"), "Base64 file page");
            Set("InputFile", input); Invoke("Run");
            var encodedPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            ChooseMode(1); Set("InputFile", encodedPath); Invoke("Run");
            var decodedPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            if (!File.ReadAllBytes(input).SequenceEqual(File.ReadAllBytes(decodedPath))) throw new Exception("Native Base64 file roundtrip differs");
            Console.WriteLine("PASS: native Base64 file encode/decode");
            SelectNav("NavSettings"); Wait(() => Find("SaveSettings"), "Settings page");
            if (Find("SaveSettings")!.Current.IsEnabled) throw new Exception("Unchanged settings can be saved");
            var alternateLanguage = language == "en-US" ? "zh-CN" : "en-US";
            var alternateTheme = theme == "dark" ? "light" : "dark";
            Choose("Language", alternateLanguage == "zh-CN" ? 0 : 1);
            Choose("Theme", alternateTheme == "dark" ? 2 : 1);
            Set("SettingsOutputFolder", profile);
            SelectNav("NavBase64"); Wait(() => Find("InputFile"), "Retained Base64 file mode");
            SelectNav("NavSettings"); WaitText("SettingsOutputFolder", value => value == profile);
            if (!Find("SaveSettings")!.Current.IsEnabled) throw new Exception("Settings draft lost on navigation");
            Invoke("DiscardSettings");
            WaitText("SettingsOutputFolder", value => value == "");
            if (Find("SaveSettings")!.Current.IsEnabled) throw new Exception("Discard left a dirty draft");
            Choose("Language", alternateLanguage == "zh-CN" ? 0 : 1);
            Choose("Theme", alternateTheme == "dark" ? 2 : 1);
            Set("SettingsOutputFolder", profile);
            var settingsPath = Path.Combine(profile, "AegisVault", "settings.json");
            var oldSettings = File.ReadAllBytes(settingsPath);
            using (var lockedSettings = File.Open(settingsPath, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                Invoke("SaveSettings");
                WaitMessage("SettingsStatus", labels["error.file.write_failed"]);
                if (!File.ReadAllBytes(settingsPath).SequenceEqual(oldSettings)) throw new Exception("Failed save changed persisted settings");
                WaitText("SettingsOutputFolder", value => value == profile);
                if (Find("NavText")!.Current.Name != labels["text"]) throw new Exception("Failed save applied the language");
                Capture($"settings-save-failure-{theme}-{language}.png");
            }
            Invoke("SaveSettings");
            var alternateLabels = Messages(args[0], alternateLanguage);
            WaitMessage("SettingsStatus", alternateLabels["settings_saved"]);
            AssertSelectedName("Theme", alternateLabels[alternateTheme]);
            if (Find("SaveSettings")!.Current.IsEnabled) throw new Exception("Saved settings still dirty");
            Capture($"settings-switched-{theme}-{language}.png");
            SelectNav("NavBase64"); Wait(() => Find("InputFile"), "Retained Base64 file mode after language change");
            WaitMessage("Status", alternateLabels["completed"]);
            SelectNav("NavSettings");
            Choose("Language", language == "zh-CN" ? 0 : 1);
            Choose("Theme", theme == "dark" ? 2 : 1);
            Set("SettingsOutputFolder", ""); Invoke("SaveSettings");
            WaitMessage("SettingsStatus", labels["settings_saved"]);
            AssertSelectedName("Theme", labels[theme]);
            Capture($"settings-{theme}-{language}.png");
            Console.WriteLine("PASS: retained drafts, discard, locked-file save failure, retry, applied theme/language and retranslated results");
            var nativeWindows = AutomationElement.RootElement.FindAll(TreeScope.Children,
                new PropertyCondition(AutomationElement.ProcessIdProperty, process.Id));
            if (nativeWindows.Count != 1) throw new Exception($"Expected one top-level window; found {nativeWindows.Count}");
            transform.Resize(680, 640);
            Thread.Sleep(300);
            WaitVisible("SaveSettings"); WaitVisible("DiscardSettings");
            AssertNavigationClear("SettingsScroll");
            Capture($"narrow-settings-{theme}-{language}.png");
            Console.WriteLine("PASS: Settings, 680 x 640 resize, one top-level window");
            var controls = window.FindAll(TreeScope.Descendants, new PropertyCondition(AutomationElement.IsKeyboardFocusableProperty, true));
            var unnamed = controls.Cast<AutomationElement>().Where(e => string.IsNullOrWhiteSpace(e.Current.Name) &&
                e.Current.ControlType is var type && type != ControlType.Pane && type != ControlType.Window).Select(e => e.Current.ControlType.ProgrammaticName).ToArray();
            if (unnamed.Length != 0) throw new Exception("Unnamed focusable controls: " + string.Join(", ", unnamed));
            Console.WriteLine($"PASS: {controls.Count} focusable settings elements have accessible names");
            SelectNav("NavFile"); Wait(() => Find("InputFile"), "File page for close");
            ChooseMode(0); Set("InputFile", large); Set("Password", "close-password"); Set("ConfirmPassword", "close-password");
            Invoke("Run");
            Wait(() => Find("Cancel") is { } cancel && cancel.Current.IsEnabled ? cancel : null, "Busy before close");
            ((WindowPattern)window.GetCurrentPattern(WindowPattern.Pattern)).Close();
            var confirm = Wait(() => window.FindAll(TreeScope.Descendants,
                new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button)).Cast<AutomationElement>()
                .FirstOrDefault(e => e.Current.Name is "Cancel task and close" or "取消任务并关闭"), "Close confirmation");
            Capture($"close-dialog-{theme}-{language}.png");
            ((InvokePattern)confirm.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
            if (!process.WaitForExit(10000)) throw new Exception("Window failed to close");
            if (process.ExitCode != 0) throw new Exception($"App exit: {process.ExitCode}");
            if (Directory.GetFiles(profile, ".*.tmp").Length != 0) throw new Exception("Close left a temporary output");
            Console.WriteLine("PASS: native ContentDialog close, cooperative shutdown, clean exit");
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            if (window is not null)
            {
                Capture($"failure-{theme}-{language}.png");
                foreach (AutomationElement item in window.FindAll(TreeScope.Descendants, Condition.TrueCondition).Cast<AutomationElement>().Take(65))
                    Console.Error.WriteLine($"{item.Current.ControlType?.ProgrammaticName ?? "Unknown"} | {item.Current.AutomationId} | {item.Current.Name}");
            }
            return 1;
        }
        finally
        {
            if (!process.HasExited) { process.Kill(entireProcessTree: true); process.WaitForExit(); }
            process.Dispose();
            if (previousClipboard is not null) System.Windows.Forms.Clipboard.SetDataObject(previousClipboard, true);
            else System.Windows.Forms.Clipboard.Clear();
            // This UUID profile was created by this run; keep screenshots, not large synthetic fixtures.
            if (!Path.GetFullPath(profile).StartsWith(evidence + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new Exception("Profile cleanup escaped evidence directory");
            Directory.Delete(profile, recursive: true);
        }
    }

    private static AutomationElement? Find(string id) => window.FindAll(TreeScope.Descendants,
        new PropertyCondition(AutomationElement.AutomationIdProperty, id)).Cast<AutomationElement>().OrderBy(e => e.Current.IsOffscreen).FirstOrDefault();
    private static Dictionary<string, string> Messages(string executable, string language) =>
        JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(Path.Combine(Path.GetDirectoryName(Path.GetFullPath(executable))!, "Assets", language + ".json")))!;
    private static void WaitVisible(string id) => Wait(() =>
    {
        var element = Find(id);
        if (element is null || element.Current.IsOffscreen) return null;
        var bounds = element.Current.BoundingRectangle;
        return bounds.Width > 0 && bounds.Height > 0 && window.Current.BoundingRectangle.Contains(bounds) ? element : null;
    }, $"Visible {id}");
    private static void WaitMessage(string id, string expected) => Wait(() =>
        Find(id)?.FindAll(TreeScope.Descendants, new PropertyCondition(AutomationElement.AutomationIdProperty, "Message"))
            .Cast<AutomationElement>().FirstOrDefault(e => e.Current.Name == expected), $"Status {id}");
    private static void AssertNavigationClear(string scrollId) => Wait(() =>
    {
        var scroll = Find(scrollId);
        var toggle = Find("TogglePaneButton");
        return scroll is not null && (toggle is null || scroll.Current.BoundingRectangle.Top >= toggle.Current.BoundingRectangle.Bottom)
            ? scroll : null;
    }, "Content below native navigation toggle");
    private static void InvokeResult(string id)
    {
        WaitVisible("Result");
        if (Find(id) is not { } action || action.Current.IsOffscreen)
        {
            var more = Find("ResultActions")!.FindFirst(TreeScope.Descendants,
                new PropertyCondition(AutomationElement.AutomationIdProperty, "MoreButton"));
            ((InvokePattern)more.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
        }
        Invoke(id);
    }
    private static void PickNativePath(string path)
    {
        var picker = Wait(() => window.FindFirst(TreeScope.Descendants,
            new PropertyCondition(AutomationElement.ClassNameProperty, "#32770")), "Native file picker");
        var filename = Wait(() => picker.FindFirst(TreeScope.Descendants,
            new PropertyCondition(AutomationElement.AutomationIdProperty, "1148"))
            ?? picker.FindAll(TreeScope.Descendants, new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Edit))
                .Cast<AutomationElement>().FirstOrDefault(e => e.Current.Name.StartsWith("文件名", StringComparison.Ordinal)
                    || e.Current.Name.StartsWith("File name", StringComparison.OrdinalIgnoreCase)), "Picker filename");
        ((ValuePattern)filename.GetCurrentPattern(ValuePattern.Pattern)).SetValue(path);
        var confirm = picker.FindFirst(TreeScope.Descendants, new AndCondition(
            new PropertyCondition(AutomationElement.AutomationIdProperty, "1"),
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button)));
        ((InvokePattern)confirm.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
    }
    private static T Wait<T>(Func<T?> action, string label) where T : class
    {
        var timer = Stopwatch.StartNew();
        while (timer.Elapsed < TimeSpan.FromSeconds(25))
        {
            if (process.HasExited) throw new Exception($"App exited while waiting for {label}: {process.ExitCode}");
            var result = action(); if (result is not null) return result;
            Thread.Sleep(100);
        }
        throw new TimeoutException(label);
    }
    private static void Set(string id, string value)
    {
        var element = Wait(() => Find(id), id);
        ((ValuePattern)element.GetCurrentPattern(ValuePattern.Pattern)).SetValue(value);
    }
    private static void Invoke(string id)
    {
        var element = Wait(() => Find(id) is { } item && item.Current.IsEnabled ? item : null, id);
        ((InvokePattern)element.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
    }
    private static void SelectNav(string id)
    {
        if (Find(id) is null && Find("TogglePaneButton") is { } toggle)
            ((InvokePattern)toggle.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
        var element = Wait(() => Find(id) is { } item && item.Current.IsEnabled ? item : null, id);
        ((SelectionItemPattern)element.GetCurrentPattern(SelectionItemPattern.Pattern)).Select();
    }
    private static string WaitText(string id, Func<string, bool> match) => Wait(() =>
    {
        var element = Find(id);
        if (element is null) return null;
        var text = ((ValuePattern)element.GetCurrentPattern(ValuePattern.Pattern)).Current.Value;
        return match(text) ? text : null;
    }, $"Result of {id}");
    private static void ChooseMode(int index) => Choose("OperationMode", index);
    private static void AssertSelectedName(string id, string expected) => Wait(() =>
        ((SelectionPattern)Find(id)!.GetCurrentPattern(SelectionPattern.Pattern)).Current.GetSelection()
            .FirstOrDefault(item => item.Current.Name == expected), $"Localized selection of {id}");
    private static void Choose(string id, int index)
    {
        var combo = Wait(() => Find(id), id);
        ((ExpandCollapsePattern)combo.GetCurrentPattern(ExpandCollapsePattern.Pattern)).Expand();
        Thread.Sleep(150);
        var options = combo.FindAll(TreeScope.Descendants, new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.ListItem));
        if (options.Count <= index) options = window.FindAll(TreeScope.Descendants, new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.ListItem));
        ((SelectionItemPattern)options[index].GetCurrentPattern(SelectionItemPattern.Pattern)).Select();
    }
    private static void Capture(string filename)
    {
        Thread.Sleep(400); // Allow the native Frame navigation and theme compositor transition to finish.
        var hwnd = new IntPtr(window.Current.NativeWindowHandle);
        GetWindowRect(hwnd, out var rect);
        using var bitmap = new Bitmap(rect.Right - rect.Left, rect.Bottom - rect.Top);
        using var graphics = Graphics.FromImage(bitmap);
        var dc = graphics.GetHdc();
        try { PrintWindow(hwnd, dc, 2); }
        finally { graphics.ReleaseHdc(dc); }
        bitmap.Save(Path.Combine(evidence, filename), ImageFormat.Png);
    }
    [StructLayout(LayoutKind.Sequential)] private struct Rect { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] private static extern bool GetWindowRect(IntPtr hwnd, out Rect rect);
    [DllImport("user32.dll")] private static extern bool PrintWindow(IntPtr hwnd, IntPtr dc, uint flags);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(IntPtr hwnd);
}
