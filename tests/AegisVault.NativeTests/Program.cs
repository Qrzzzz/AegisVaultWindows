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
            Set("TextInput", "WinUI AGV1 roundtrip");
            Set("Password", "native-test-password"); Set("ConfirmPassword", "native-test-password");
            Find("Password")!.SetFocus();
            System.Windows.Forms.SendKeys.SendWait("^{ENTER}");
            var token = WaitText("Result", value => value.StartsWith("AGV1.", StringComparison.Ordinal));
            Capture($"text-{theme}-{language}.png");
            ChooseMode(1);
            Set("TextInput", token); Set("Password", "native-test-password"); Invoke("Run");
            WaitText("Result", value => value == "WinUI AGV1 roundtrip");
            Console.WriteLine("PASS: native Text encrypt/decrypt and password confirmation");
            SelectNav("NavFile"); Wait(() => Find("InputFile"), "File page");
            var input = Path.Combine(profile, "fixture.bin");
            File.WriteAllBytes(input, Enumerable.Range(0, 256).Select(i => (byte)i).ToArray());
            Invoke("PickFile");
            var picker = Wait(() => window.FindFirst(TreeScope.Descendants,
                new PropertyCondition(AutomationElement.ClassNameProperty, "#32770")), "Native file picker");
            var filename = Wait(() => picker.FindFirst(TreeScope.Descendants,
                new PropertyCondition(AutomationElement.AutomationIdProperty, "1148")), "Picker filename");
            ((ValuePattern)filename.GetCurrentPattern(ValuePattern.Pattern)).SetValue(input);
            var open = picker.FindFirst(TreeScope.Descendants, new AndCondition(
                new PropertyCondition(AutomationElement.AutomationIdProperty, "1"),
                new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.Button)));
            ((InvokePattern)open.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
            WaitText("InputFile", value => value == input);
            Console.WriteLine("PASS: Windows App SDK native file picker");
            Set("Password", "native-file-password"); Set("ConfirmPassword", "native-file-password");
            Invoke("Run");
            var fileResult = WaitText("Result", value => value.Contains(".agv", StringComparison.Ordinal));
            var encryptedPath = fileResult.Split(['\r', '\n'])[0].Trim();
            if (!File.Exists(encryptedPath)) throw new Exception("Native file operation did not produce its result");
            Capture($"file-{theme}-{language}.png");
            ChooseMode(1); Set("InputFile", encryptedPath); Set("Password", "native-file-password"); Invoke("Run");
            var restoredPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            if (!File.ReadAllBytes(input).SequenceEqual(File.ReadAllBytes(restoredPath))) throw new Exception("Native file roundtrip differs");
            Console.WriteLine("PASS: native File encrypt/decrypt");
            var large = Path.Combine(profile, "cancel.bin");
            using (var stream = File.Create(large)) stream.SetLength(512L * 1024 * 1024);
            ChooseMode(0); Set("InputFile", large); Set("Password", "cancel-password"); Set("ConfirmPassword", "cancel-password");
            Invoke("Run"); Invoke("Cancel");
            Wait(() => Find("Message") is { } message && (message.Current.Name.Contains("cancelled", StringComparison.OrdinalIgnoreCase) || message.Current.Name.Contains("已取消", StringComparison.Ordinal)) ? message : null, "Cancellation terminal");
            if (File.Exists(large + ".agv") || Directory.GetFiles(profile, ".*.tmp").Length != 0) throw new Exception("Cancellation left partial output");
            Console.WriteLine("PASS: native cooperative cancellation and partial-output cleanup");
            SelectNav("NavBase64"); Wait(() => Find("TextInput"), "Base64 page");
            Set("TextInput", "hello"); Invoke("Run"); WaitText("Result", value => value == "aGVsbG8=");
            ChooseMode(1); Set("TextInput", "aGVsbG8="); Invoke("Run"); WaitText("Result", value => value == "hello");
            ((TogglePattern)Find("IgnoreWhitespace")!.GetCurrentPattern(TogglePattern.Pattern)).Toggle();
            Set("TextInput", "aG Vs bG8=\r\n"); Invoke("Run"); WaitText("Result", value => value == "hello");
            Capture($"base64-{theme}-{language}.png");
            Console.WriteLine("PASS: native Base64 encode/decode");
            Choose("InputKind", 1); Wait(() => Find("InputFile"), "Base64 file page");
            Set("InputFile", input); Invoke("Run");
            var encodedPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            ChooseMode(1); Set("InputFile", encodedPath); Invoke("Run");
            var decodedPath = WaitText("Result", value => value.Contains("→", StringComparison.Ordinal)).Split(['\r', '\n'])[0].Trim();
            if (!File.ReadAllBytes(input).SequenceEqual(File.ReadAllBytes(decodedPath))) throw new Exception("Native Base64 file roundtrip differs");
            Console.WriteLine("PASS: native Base64 file encode/decode");
            SelectNav("NavSettings"); Wait(() => Find("SaveSettings"), "Settings page"); Capture($"settings-{theme}-{language}.png");
            Invoke("SaveSettings");
            Wait(() => Find("SaveSettings") is { } save && save.Current.IsEnabled ? save : null, "Settings save completion");
            var nativeWindows = AutomationElement.RootElement.FindAll(TreeScope.Children,
                new PropertyCondition(AutomationElement.ProcessIdProperty, process.Id));
            if (nativeWindows.Count != 1) throw new Exception($"Expected one top-level window; found {nativeWindows.Count}");
            var pattern = (TransformPattern)window.GetCurrentPattern(TransformPattern.Pattern);
            pattern.Resize(680, 640);
            Thread.Sleep(300);
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
                    Console.Error.WriteLine($"{item.Current.ControlType.ProgrammaticName} | {item.Current.AutomationId} | {item.Current.Name}");
            }
            return 1;
        }
        finally { if (!process.HasExited) process.Kill(entireProcessTree: true); process.Dispose(); }
    }

    private static AutomationElement? Find(string id) => window.FindAll(TreeScope.Descendants,
        new PropertyCondition(AutomationElement.AutomationIdProperty, id)).Cast<AutomationElement>().OrderBy(e => e.Current.IsOffscreen).FirstOrDefault();
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
