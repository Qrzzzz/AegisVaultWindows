using System.Diagnostics;
using System.Text;
using System.Text.Json;
using AegisVault.App.Services;
using AegisVault.App.ViewModels;
using Microsoft.UI.Xaml.Controls;

var root = Path.Combine(Path.GetTempPath(), "aegisvault-2.5-ipc-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
Environment.SetEnvironmentVariable("LOCALAPPDATA", root);
Environment.SetEnvironmentVariable("APPDATA", root);
Environment.SetEnvironmentVariable("AEGISVAULT_TEST_PYTHON", Environment.GetEnvironmentVariable("AEGISVAULT_TEST_PYTHON"));
Environment.SetEnvironmentVariable("AEGISVAULT_TEST_SOURCE", Path.GetFullPath(Environment.GetEnvironmentVariable("AEGISVAULT_TEST_SOURCE")!));
var marker = Path.Combine(root, "owned-process.json");
Environment.SetEnvironmentVariable("AEGISVAULT_TEST_MARKER", marker);
// Hosted Windows runners can need more than a sub-second budget for a cold .NET process start.
// Keep every injected boundary well below production while leaving startup headroom.
var fast = new BackendTimeouts(TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(1),
    TimeSpan.FromMilliseconds(750), TimeSpan.FromSeconds(5));
var failures = new List<string>();

void Check(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException("ASSERT: " + message);
}
void Log(string scenario, object evidence) => Console.WriteLine(JsonSerializer.Serialize(new { scenario, evidence }));
async Task Run(string name, Func<Task> test)
{
    try { await test().WaitAsync(TimeSpan.FromSeconds(20)); Log(name, new { passed = true }); }
    catch (Exception ex) { failures.Add($"{name}: {ex}"); Log(name, new { passed = false, error = ex.ToString() }); }
}
void Mode(string value)
{
    Environment.SetEnvironmentVariable("AEGISVAULT_TEST_MODE", value);
    Environment.SetEnvironmentVariable("AEGISVAULT_TEST_RESPONSE", null);
    if (File.Exists(marker)) File.Delete(marker);
}
async Task<(int pid, string stage)> WaitMarker(string stage)
{
    var watch = Stopwatch.StartNew();
    while (watch.Elapsed < TimeSpan.FromSeconds(10))
    {
        try
        {
            using var document = JsonDocument.Parse(await File.ReadAllTextAsync(marker));
            if (document.RootElement.GetProperty("stage").GetString() == stage)
                return (document.RootElement.GetProperty("pid").GetInt32(), stage);
        }
        catch (Exception ex) when (ex is IOException or JsonException) { }
        await Task.Delay(10);
    }
    throw new TimeoutException(stage);
}
bool Alive(int pid)
{
    try
    {
        using var process = Process.GetProcessById(pid);
        // Windows can reuse a PID while the longer real-backend matrix runs.
        var started = long.Parse(File.ReadAllText($"{marker}.{pid}.pid"));
        return !process.HasExited && process.StartTime.ToUniversalTime().Ticks == started;
    }
    catch (ArgumentException) { return false; }
}
async Task<string> ErrorCode(Task task)
{
    try { await task; throw new InvalidOperationException("Expected BackendException"); }
    catch (BackendException ex) { return ex.Code; }
}

try
{
    Check(BackendTimeouts.Default == new BackendTimeouts(TimeSpan.FromSeconds(15), TimeSpan.FromSeconds(30),
        TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(5)), "production deadline policy drifted");

    await Run("short-request-write-block", async () =>
    {
        Mode("no-read");
        var watch = Stopwatch.StartNew();
        var call = new BackendClient(fast).CallAsync("settings.update", new { theme = new string('a', 1024 * 1024) });
        var owned = await WaitMarker("no-read");
        Check(await ErrorCode(call) == "ipc.request_timeout", "short send timeout code");
        Check(watch.Elapsed < TimeSpan.FromSeconds(15) && !Alive(owned.pid), "short send was not bounded/reaped");
    });

    await Run("cancel-before-blocked-send-finishes", async () =>
    {
        Mode("blocked-cancel-write");
        using var cancellation = new CancellationTokenSource();
        var call = new BackendClient(fast).CallAsync("base64.encode_text",
            new { text = new string('a', 1024 * 1024) }, cancellationToken: cancellation.Token);
        var owned = await WaitMarker("blocked-cancel-write");
        cancellation.Cancel();
        Check(await ErrorCode(call) == "ipc.cancel_timeout", "blocked cancellation code");
        Check(!Alive(owned.pid), "blocked cancellation process leaked");
    });

    await Run("read-hang-cancellation", async () =>
    {
        Mode("no-response");
        using var cancellation = new CancellationTokenSource();
        var call = new BackendClient(fast).CallAsync("base64.encode_text", new { text = "value" }, cancellationToken: cancellation.Token);
        var owned = await WaitMarker("no-response");
        cancellation.Cancel();
        Check(await ErrorCode(call) == "ipc.cancel_timeout" && !Alive(owned.pid), "read hang was not cancelled/reaped");
    });

    await Run("terminal-without-exit", async () =>
    {
        Mode("terminal-no-exit");
        var result = await new BackendClient(fast).CallAsync("hello");
        var owned = await WaitMarker("terminal-no-exit");
        Check(BackendResponse.Int32(result, "protocol") == 1 && !Alive(owned.pid), "terminal result or forced exit failed");
    });

    await Run("exit-cancel-race", async () =>
    {
        Mode("exit-cancel-race");
        using var cancellation = new CancellationTokenSource();
        var call = new BackendClient(fast).CallAsync("base64.encode_text", new { text = "value" }, cancellationToken: cancellation.Token);
        var owned = await WaitMarker("exit-cancel-race");
        cancellation.Cancel();
        Check(await ErrorCode(call) == "ipc.backend_exited" && !Alive(owned.pid), "exit/cancel race did not converge");
    });

    await Run("continuous-stderr", async () =>
    {
        Mode("stderr-flood");
        var result = await new BackendClient(fast).CallAsync("hello");
        var owned = await WaitMarker("stderr-flood");
        Check(BackendResponse.Int32(result, "protocol") == 1 && !Alive(owned.pid), "stderr was not drained/reaped");
    });

    await Run("numeric-invalid-response", async () =>
    {
        var responses = new[]
        {
            "{\"v\":1.5,\"id\":\"__ID__\",\"type\":\"result\",\"result\":{}}",
            "{\"v\":2147483648,\"id\":\"__ID__\",\"type\":\"result\",\"result\":{}}",
            "{\"v\":\"1\",\"id\":\"__ID__\",\"type\":\"result\",\"result\":{}}",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"fault\",\"processed_bytes\":0.5,\"total_bytes\":1}",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"fault\",\"processed_bytes\":9223372036854775808,\"total_bytes\":1}",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"fault\",\"processed_bytes\":1,\"total_bytes\":0.5}",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"fault\",\"processed_bytes\":1,\"total_bytes\":9223372036854775808}",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"fault\",\"processed_bytes\":\"1\",\"total_bytes\":1}"
        };
        foreach (var response in responses)
        {
            Mode("numeric"); Environment.SetEnvironmentVariable("AEGISVAULT_TEST_RESPONSE", response);
            var code = await ErrorCode(new BackendClient(fast).CallAsync("hello", progress: new InlineProgress()));
            Check(code == "ipc.invalid_response", "numeric fault escaped unified mapping");
        }
        foreach (var result in new[]
        {
            "{\"output_path\":\"x\",\"original_size\":0.5,\"output_size\":1}",
            "{\"output_path\":\"x\",\"original_size\":9223372036854775808,\"output_size\":1}",
            "{\"output_path\":\"x\",\"original_size\":1,\"output_size\":0.5}",
            "{\"output_path\":\"x\",\"original_size\":1,\"output_size\":\"1\"}"
        })
        {
            Mode("numeric");
            Environment.SetEnvironmentVariable("AEGISVAULT_TEST_RESPONSE",
                $"{{\"v\":1,\"id\":\"__ID__\",\"type\":\"result\",\"result\":{result}}}");
            var code = await ErrorCode(new BackendClient(fast).CallAsync("base64.encode_file", new { input_path = "x" }));
            Check(code == "ipc.invalid_response", "file result numeric fault escaped unified mapping");
        }
        Mode("numeric");
        Environment.SetEnvironmentVariable("AEGISVAULT_TEST_RESPONSE",
            "{\"v\":1,\"id\":\"__ID__\",\"type\":\"progress\",\"percent\":0.5,\"stage\":\"valid\",\"processed_bytes\":1,\"total_bytes\":2}");
        using var cancellation = new CancellationTokenSource();
        var progress = new InlineProgress();
        var validCall = new BackendClient(fast).CallAsync("base64.encode_text", new { text = "x" }, progress, cancellation.Token);
        await WaitMarker("numeric");
        await Task.Delay(50); cancellation.Cancel();
        Check(await ErrorCode(validCall) == "ipc.cancel_timeout" && progress.Count == 1, "valid numeric control was not evaluated");
    });

    await Run("settings-timeout-retry", async () =>
    {
        Mode("settings-timeout-retry");
        File.Delete(marker + ".first");
        var settings = new SettingsService(new BackendClient(fast));
        Check(await ErrorCode(settings.LoadAsync()) == "ipc.request_timeout", "settings timeout code");
        Check(!settings.IsBusy && settings.ActiveTask.IsCompleted, "settings lifecycle stayed busy");
        await settings.LoadAsync();
        Check(!settings.IsBusy && settings.Current.Theme == "dark" && settings.Current.ShowAdvancedOptions,
            "settings retry or compatibility field failed");
    });

    foreach (var mode in new[] { "file-recent-timeout", "file-recent-cancel" })
    {
        await Run(mode, async () =>
        {
            Mode(mode);
            var input = Path.Combine(root, Guid.NewGuid().ToString("N") + ".bin");
            await File.WriteAllBytesAsync(input, Encoding.UTF8.GetBytes("committed file result"));
            var settings = new SettingsService(new BackendClient(fast));
            var workflow = new WorkflowViewModel("base64_file", new BackendClient(fast), settings) { InputPath = input };
            var call = workflow.RunAsync();
            var owned = await WaitMarker("recent-hang");
            Check(workflow.HasResult && File.Exists(workflow.ResultPath), "file result not committed before history");
            Check(workflow.ResultActionsVisibility == Microsoft.UI.Xaml.Visibility.Collapsed && workflow.CanCancel,
                "result actions displaced cancellation while the workflow was still busy");
            if (mode.EndsWith("cancel", StringComparison.Ordinal)) await workflow.CancelAndWaitAsync();
            else await call;
            Check(workflow.HasResult && !workflow.IsBusy && !settings.IsBusy && !Alive(owned.pid), "history failure erased result or stayed busy");
            Check(workflow.Severity == InfoBarSeverity.Warning && workflow.LastErrorCode == "", "history warning semantics");
            Check(await File.ReadAllTextAsync(workflow.ResultPath) == Convert.ToBase64String(await File.ReadAllBytesAsync(input)),
                "real Python file output differs");
        });
    }

    await Run("long-file-has-no-short-rpc-deadline", async () =>
    {
        Mode("delayed-file");
        var result = await new BackendClient(new BackendTimeouts(TimeSpan.FromMilliseconds(100), TimeSpan.FromMilliseconds(250),
            TimeSpan.FromMilliseconds(200), TimeSpan.FromSeconds(2))).CallAsync("base64.encode_file", new { input_path = "synthetic" });
        Check(BackendResponse.Int64(result, "output_size") == 4, "long file operation inherited short RPC deadline");
    });

    foreach (var mode in new[] { "invalid-utf8-line", "invalid-utf8-eof", "invalid-utf8-continuation" })
    {
        await Run(mode, async () =>
        {
            Mode(mode);
            var call = new BackendClient(fast).CallAsync("hello");
            var owned = await WaitMarker(mode);
            Check(await ErrorCode(call) == "ipc.invalid_response", "UTF-8 fault escaped unified mapping");
            Check(!Alive(owned.pid), "invalid UTF-8 process leaked");
        });
    }
    await Run("valid-utf8-split", async () =>
    {
        Mode("valid-utf8-split");
        var result = await new BackendClient(fast).CallAsync("base64.encode_text", new { text = "synthetic" });
        var owned = await WaitMarker("valid-utf8-split");
        Check(BackendResponse.String(result, "text") == "🔐" && !Alive(owned.pid), "split UTF-8/CRLF control failed");
    });

    await Run("bounded-response-line", async () =>
    {
        Mode("oversized-response");
        var call = new BackendClient(fast).CallAsync("hello");
        var owned = await WaitMarker("oversized-response");
        var code = await ErrorCode(call);
        Check(code == "ipc.response_too_large" && !Alive(owned.pid), "oversized response was not bounded/reaped");
    });

    await Run("text-budget-contract-and-use-result", async () =>
    {
        Mode("healthy");
        var limits = TextLimits.Contract;
        Check(limits.MaxJsonLineBytes == 16 * 1024 * 1024, "JSON Line limit");
        Check(limits.MaxPlaintextUtf8Bytes == 1_507_294 && limits.MaxEncodedTextUtf8Bytes == 2 * 1024 * 1024,
            "text budget values");
        foreach (var kind in new[] { "base64_text", "text" })
        {
            var settings = new SettingsService(new BackendClient(fast));
            var workflow = new WorkflowViewModel(kind, new BackendClient(fast), settings);
            Check(workflow.InputCodeUnitLimit == limits.MaxPlaintextUtf16CodeUnits, "forward UTF-16 limit");
            Check(workflow.TrySetExternalInput(new string('a', limits.MaxPlaintextUtf8Bytes)), "forward boundary input");
            await workflow.RunAsync("budget-password", "budget-password");
            Check(workflow.HasResult && workflow.Output.Length <= limits.MaxEncodedTextUtf16CodeUnits,
                $"{kind} bounded result");
            var generated = workflow.Output;
            Check(workflow.UseResult() && workflow.Mode == 1 && workflow.Input == generated,
                $"{kind} UseResult closure");
            await workflow.RunAsync("budget-password");
            Check(workflow.HasResult && workflow.Output == new string('a', limits.MaxPlaintextUtf8Bytes),
                $"{kind} full reverse roundtrip");
            Check(!workflow.TrySetExternalInput(new string('a', limits.MaxEncodedTextUtf16CodeUnits + 1))
                && workflow.LastErrorCode == "resource.limit_exceeded", "encoded boundary rejection");
        }
        var invalid = new WorkflowViewModel("base64_text", new BackendClient(fast), new SettingsService(new BackendClient(fast)));
        Check(!invalid.TrySetExternalInput("\ud800") && invalid.LastErrorCode == "ipc.invalid_request",
            "isolated surrogate input classification");
    });

    await Run("utf8-import-preserves-body-bom", async () =>
    {
        Mode("healthy");
        var path = Path.Combine(root, "import.txt");
        foreach (var (source, expected) in new (string, string)[] {
            ("abc", "abc"), ("\ufeffabc", "abc"), ("\ufeff\ufeffabc", "\ufeffabc"),
            ("\ufeff\ufeff\ufeffabc", "\ufeff\ufeffabc"), ("a\ufeffb", "a\ufeffb"),
            ("", ""), ("\ufeff", ""), ("\ufeff\ufeff", "\ufeff") })
        {
            await File.WriteAllBytesAsync(path, Encoding.UTF8.GetBytes(source));
            var imported = await TextImport.ReadAsync(path, 128);
            Check(imported == expected, "import removed body U+FEFF");
            if (imported.Length == 0) continue;
            foreach (var kind in new[] { "base64_text", "text" })
            {
                var vm = new WorkflowViewModel(kind, new BackendClient(fast), new SettingsService(new BackendClient(fast)));
                Check(vm.TrySetExternalInput(imported), "import rejected valid text");
                await vm.RunAsync("synthetic-password", "synthetic-password");
                Check(vm.HasResult, "import encoding failed");
                if (kind == "base64_text") Check(vm.Output == Convert.ToBase64String(Encoding.UTF8.GetBytes(expected)), "Base64 import bytes");
                Check(vm.UseResult(), "import result reuse failed");
                await vm.RunAsync("synthetic-password");
                Check(vm.Output == expected, "import roundtrip lost body U+FEFF");
            }
        }
        await File.WriteAllBytesAsync(path, [0xFF]);
        try { await TextImport.ReadAsync(path, 8); throw new Exception("invalid UTF-8 accepted"); }
        catch (DecoderFallbackException) { }
        await File.WriteAllBytesAsync(path, Encoding.UTF8.GetBytes("\ufeff12345678"));
        Check(await TextImport.ReadAsync(path, 8) == "12345678", "BOM budget boundary");
        await File.WriteAllBytesAsync(path, Encoding.UTF8.GetBytes("123456789"));
        Check(await ErrorCode(TextImport.ReadAsync(path, 8)) == "resource.limit_exceeded", "byte budget was bypassed");
    });

    await Run("settings-two-drafts-preserve-unedited-fields", async () =>
    {
        Mode("healthy");
        var first = new SettingsService(new BackendClient(fast));
        var second = new SettingsService(new BackendClient(fast));
        await first.LoadAsync(); await second.LoadAsync();
        var a = new SettingsViewModel(first);
        var b = new SettingsViewModel(second);
        a.RememberRecent = false;
        await a.SaveAsync();
        b.ThemeIndex = 2;
        await b.SaveAsync();
        Check(!second.Current.RememberRecentFiles && second.Current.Theme == "dark", "stale draft re-enabled history");
        await second.AddRecentAsync(Path.Combine(root, "synthetic.txt"));
        Check(second.Current.RecentFiles.Length == 0, "disabled history recorded a path");
        // A service refresh from a history action must not redefine a draft's baseline.
        a.OutputFolder = root;
        await first.ClearRecentAsync();
        await a.SaveAsync();
        Check(first.Current.Theme == "dark" && first.Current.DefaultOutputDir == root, "history refresh overwrote another field");
        b.ThemeIndex = 1;
        await b.SaveAsync();
        a.ThemeIndex = 0;
        await a.SaveAsync();
        Check(first.Current.Theme == "system", "same-field edits must use last explicit save");
        await first.SaveAsync(first.Current with { DefaultOutputDir = "", RememberRecentFiles = true });
    });

    await Run("batch-queue-live-edits-and-real-backend", async () =>
    {
        Mode("healthy");
        var settings = new SettingsService(new BackendClient(fast));
        await settings.LoadAsync();
        var folder = Path.Combine(root, "queue-live"); Directory.CreateDirectory(folder);
        var changedDefault = Path.Combine(root, "queue-changed-default"); Directory.CreateDirectory(changedDefault);
        var paths = Enumerable.Range(0, 3).Select(index => Path.Combine(folder, index + ".txt")).ToArray();
        foreach (var path in paths) await File.WriteAllTextAsync(path, "payload " + path);
        var workflow = new WorkflowViewModel("base64_file", new BackendClient(fast), settings);
        workflow.AddFiles(paths.Take(2)); workflow.AddFiles([paths[0]]);
        Check(workflow.Files.Count == 2, "duplicate queue input accepted");
        var first = workflow.Files[0]; var removed = workflow.Files[1];
        var edited = false;
        workflow.PropertyChanged += (_, change) =>
        {
            if (change.PropertyName != "QueueSummary" || edited || first.State != "running") return;
            edited = true;
            workflow.RemoveFile(first); // The active file cannot be removed.
            workflow.RemoveFile(removed); workflow.AddFiles([paths[2]]);
            workflow.Mode = 1; workflow.OutputDir = "must-not-change";
            // A different settings writer must not redirect this already-started batch.
            settings.SaveAsync(settings.Current with { DefaultOutputDir = changedDefault }).GetAwaiter().GetResult();
        };
        await workflow.RunAsync();
        Check(edited && workflow.Files.Count == 2 && workflow.Files[0] == first, "live edit or running guard failed");
        Check(workflow.Mode == 0 && workflow.OutputDir == "", "running options changed");
        Check(workflow.Files.All(file => file.State == "completed"), "live queue did not drain");
        Check(!File.Exists(paths[1] + ".b64"), "removed pending file was processed");
        foreach (var file in workflow.Files)
        {
            Check(Path.GetDirectoryName(file.ResultPath) == folder, "running batch followed a later default-directory change");
            Check(await File.ReadAllTextAsync(file.ResultPath) == Convert.ToBase64String(await File.ReadAllBytesAsync(file.InputPath)), "batch output differs");
        }
        Check(workflow.CopyContent.Split(Environment.NewLine).Length == 2 && !workflow.CanRun && !workflow.IsBusy,
            "batch copy content or terminal state invalid");
        await settings.SaveAsync(settings.Current with { DefaultOutputDir = "" });
    });

    await Run("batch-partial-failure-retry-and-resume", async () =>
    {
        Mode("healthy");
        var settings = new SettingsService(new BackendClient(fast)); await settings.LoadAsync();
        var folder = Path.Combine(root, "queue-retry"); Directory.CreateDirectory(folder);
        var bad = Path.Combine(folder, "bad.b64"); var good = Path.Combine(folder, "good.b64");
        await File.WriteAllTextAsync(bad, "@@@@"); await File.WriteAllTextAsync(good, "aGVsbG8=");
        var workflow = new WorkflowViewModel("base64_file", new BackendClient(fast), settings) { Mode = 1 };
        workflow.AddFiles([bad, good]); await workflow.RunAsync();
        Check(workflow.Files[0].State == "failed" && workflow.Files[1].State == "completed" && workflow.HasResult,
            "partial failure erased or skipped successful output");
        var preserved = workflow.Files[1].ResultPath;
        await File.WriteAllTextAsync(bad, "cmV0cmllZA=="); workflow.RetryFile(workflow.Files[0]); await workflow.RunAsync();
        Check(workflow.Files.All(file => file.State == "completed") && workflow.Files[1].ResultPath == preserved,
            "retry reprocessed completed input");
        Check(await File.ReadAllTextAsync(workflow.Files[0].ResultPath) == "retried", "retry output differs");
        workflow.ClearQueue(); workflow.Mode = 0; workflow.AddFiles([bad, good]);
        var cancelled = false;
        workflow.PropertyChanged += (_, change) =>
        {
            if (change.PropertyName == "HasResult" && !cancelled && workflow.HasResult)
            { cancelled = true; workflow.CancelCommand.Execute(null); }
        };
        await workflow.RunAsync();
        Check(cancelled && workflow.Files[0].State == "completed" && workflow.Files[1].State == "pending" && workflow.CanEditQueue,
            "cancel lost committed result, processed waiting input or locked queue");
        var beforeResume = workflow.Files[0].ResultPath;
        await workflow.RunAsync();
        Check(workflow.Files.All(file => file.State == "completed") && workflow.Files[0].ResultPath == beforeResume,
            "resume repeated committed work");
    });

    await Run("batch-response-boundary", () =>
    {
        var valid = """{"cancelled":false,"items":[{"input_path":"source","status":"completed","code":"","result":{"output_path":"output","original_size":1,"output_size":4}}]}""";
        foreach (var malformed in new[] { valid.Replace("\"original_size\":1", "\"original_size\":1.5"),
            valid.Replace("\"output_size\":4", "\"output_size\":-1"), valid.Replace("\"completed\"", "\"unknown\""),
            valid.Replace("\"output_path\":\"output\"", "\"output_path\":null"),
            """{"cancelled":false,"items":[]}""", """{"cancelled":"false","items":[]}""" })
        {
            using var document = JsonDocument.Parse(malformed);
            try { BatchResponse.Read(document.RootElement); throw new Exception("malformed batch accepted"); }
            catch (BackendException ex) { Check(ex.Code == "ipc.invalid_response", "batch response error not unified"); }
        }
        return Task.CompletedTask;
    });

    foreach (var pidFile in Directory.GetFiles(root, "owned-process.json.*.pid"))
    {
        var pid = int.Parse(Path.GetFileName(pidFile).Split('.')[2]);
        Check(!Alive(pid), $"owned test process {pid} leaked");
    }
}
finally
{
    if (failures.Count == 0 && Directory.Exists(root)) Directory.Delete(root, recursive: true);
}

if (failures.Count != 0) throw new AggregateException(failures.Select(message => new Exception(message)));
Console.WriteLine("PASS: all linked-source IPC lifecycle assertions");

sealed class InlineProgress : IProgress<BackendProgress>
{
    public int Count { get; private set; }
    public void Report(BackendProgress value) => Count++;
}
