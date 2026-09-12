using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Automation;

internal static partial class Program
{
    // Opt-in interactive gate. Uses an actual Explorer window and the OS input path,
    // never calls the app's drop handler or substitutes picker/VM acceptance.
    private static void CheckExplorerDrops(string profile, string theme, string language, Dictionary<string, string> labels)
    {
        var folder = Path.Combine(profile, "explorer-drop-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        foreach (var name in new[] { "drag-a.txt", "drag-b.txt", "drag-c.txt" }) File.WriteAllText(Path.Combine(folder, name), name);
        Directory.CreateDirectory(Path.Combine(folder, "rejected-folder"));
        var large = Path.Combine(profile, "busy-drop.bin");
        using (var stream = File.Create(large)) stream.SetLength(512L * 1024 * 1024);
        AutomationElement? explorer = null;
        var oldBounds = window.Current.BoundingRectangle;
        var appTransform = (TransformPattern)window.GetCurrentPattern(TransformPattern.Pattern);
        try
        {
            var screen = System.Windows.Forms.Screen.PrimaryScreen!.WorkingArea;
            if (screen.Width < 1360) throw new InvalidOperationException("Explorer drop gate needs at least 1360 physical pixels of desktop width.");
            appTransform.Move(screen.Left + screen.Width / 2, screen.Top);
            appTransform.Resize(screen.Width / 2, screen.Height - 40);
            Process.Start(new ProcessStartInfo("explorer.exe", $"/n,\"{folder}\"") { UseShellExecute = true });
            explorer = Wait(() => AutomationElement.RootElement.FindAll(TreeScope.Children,
                new PropertyCondition(AutomationElement.ClassNameProperty, "CabinetWClass")).Cast<AutomationElement>()
                .FirstOrDefault(item => item.Current.Name.Contains(Path.GetFileName(folder), StringComparison.Ordinal)), "Owned Explorer source");
            var sourceTransform = (TransformPattern)explorer.GetCurrentPattern(TransformPattern.Pattern);
            ((WindowPattern)explorer.GetCurrentPattern(WindowPattern.Pattern)).SetWindowVisualState(WindowVisualState.Normal);
            sourceTransform.Resize(screen.Width / 2, screen.Height - 40); sourceTransform.Move(screen.Left, screen.Top);
            DragExplorerEntries(explorer, ["drag-a.txt", "drag-b.txt"]);
            WaitQueueCount(2);
            if (Find("TextInput") is not null) throw new Exception("Text storage drop did not route to File queue");
            Capture($"explorer-drop-text-file-{theme}-{language}.png");
            DragExplorerEntries(explorer, ["drag-a.txt"]); WaitQueueCount(2);
            Console.WriteLine("PASS: real Explorer multi-file drop routes Text to File and suppresses duplicates");

            SelectNav("NavBase64"); Choose("InputKind", 0);
            DragExplorerEntries(explorer, ["drag-a.txt"]); WaitQueueCount(1);
            AssertSelectedName("InputKind", labels["file"]);
            DragExplorerEntries(explorer, ["drag-b.txt", "rejected-folder"]); WaitQueueCount(2);
            WaitMessage("Status", labels["queue_files_only"]);
            DragExplorerEntries(explorer, ["rejected-folder"]); WaitQueueCount(2);
            WaitMessage("Status", labels["queue_files_only"]);
            Capture($"explorer-drop-base64-folder-{theme}-{language}.png");
            Console.WriteLine("PASS: real Explorer drop routes Base64 text to file mode; mixed and folder-only drops reject folders");

            Invoke("ClearQueue"); ChooseMode(0); PickNativeFiles([large]);
            Invoke("Run");
            Wait(() => Find("OperationMode") is { } mode && !mode.Current.IsEnabled ? mode : null, "Busy before external append");
            DragExplorerEntries(explorer, ["drag-c.txt"]); WaitQueueCount(2);
            if (Find("OperationMode")!.Current.IsEnabled) throw new Exception("Batch ended before external append could be accepted as a busy drop");
            Capture($"explorer-drop-busy-{theme}-{language}.png");
            Invoke("Cancel");
            Wait(() => Find("OperationMode") is { } mode && mode.Current.IsEnabled ? mode : null, "Cancel after external append");
            WaitQueueCount(2);
            if (Directory.GetFiles(profile, ".*.tmp").Length != 0) throw new Exception("External-append cancellation left temporary output");
            Console.WriteLine("PASS: real Explorer append while batch remains busy, followed by safe cancellation retaining queue");
        }
        finally
        {
            if (explorer is not null)
            {
                try { ((WindowPattern)explorer.GetCurrentPattern(WindowPattern.Pattern)).Close(); }
                catch (ElementNotAvailableException) { }
            }
            appTransform.Move(oldBounds.X, oldBounds.Y); appTransform.Resize(oldBounds.Width, oldBounds.Height);
        }
    }

    private static void DragExplorerEntries(AutomationElement explorer, string[] names)
    {
        var foregroundAccepted = SetForegroundWindow(new IntPtr(explorer.Current.NativeWindowHandle));
        var items = names.Select(name => Wait(() => explorer.FindAll(TreeScope.Descendants,
            new PropertyCondition(AutomationElement.ControlTypeProperty, ControlType.ListItem)).Cast<AutomationElement>()
            .FirstOrDefault(item => item.Current.Name == name || item.Current.Name == Path.GetFileNameWithoutExtension(name)), "Explorer item " + name)).ToArray();
        ((SelectionItemPattern)items[0].GetCurrentPattern(SelectionItemPattern.Pattern)).Select();
        foreach (var item in items.Skip(1)) ((SelectionItemPattern)item.GetCurrentPattern(SelectionItemPattern.Pattern)).AddToSelection();
        if (items[0].TryGetCurrentPattern(ScrollItemPattern.Pattern, out var scroll)) ((ScrollItemPattern)scroll).ScrollIntoView();
        Thread.Sleep(200);
        var start = items[0].Current.BoundingRectangle;
        var target = Find("TextInput") ?? Find("PickFile") ?? throw new Exception("No visible drop target");
        var end = target.Current.BoundingRectangle;
        if (start.IsEmpty || end.IsEmpty || target.Current.IsOffscreen) throw new Exception("External drop target/source is offscreen");
        var point = items[0].GetClickablePoint();
        var fromX = point.X; var fromY = point.Y;
        var toX = end.Left + end.Width / 2; var toY = end.Top + end.Height / 2;
        Console.WriteLine($"Explorer drag [{string.Join(",", names)}]: foreground={foregroundAccepted}, source={fromX},{fromY}, target={toX},{toY}, app={window.Current.BoundingRectangle}, explorer={explorer.Current.BoundingRectangle}");
        SetCursorPos((int)fromX, (int)fromY); Thread.Sleep(100);
        SendMouse(0x0002);
        try
        {
            for (var step = 1; step <= 30; step++)
            {
                SetCursorPos((int)(fromX + (toX - fromX) * step / 30), (int)(fromY + (toY - fromY) * step / 30));
                Thread.Sleep(25);
            }
            Thread.Sleep(200);
        }
        finally { SendMouse(0x0004); }
        Thread.Sleep(200);
    }
    private static void SendMouse(uint flags)
    {
        var input = new MouseInputEnvelope { Type = 0, Mouse = new NativeMouseInput { Flags = flags } };
        if (SendInput(1, [input], Marshal.SizeOf<MouseInputEnvelope>()) != 1)
            throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(), "OS mouse injection failed");
    }
    [StructLayout(LayoutKind.Sequential)] private struct MouseInputEnvelope { public uint Type; public NativeMouseInput Mouse; }
    [StructLayout(LayoutKind.Sequential)] private struct NativeMouseInput
    { public int X, Y; public uint MouseData, Flags, Time; public UIntPtr ExtraInfo; }
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] private static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll", SetLastError = true)] private static extern uint SendInput(uint count, MouseInputEnvelope[] inputs, int size);
}
