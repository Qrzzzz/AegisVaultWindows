using System.Diagnostics;
using System.Text;
using System.Text.Json;
using AegisVault.App.Services;
using AegisVault.App.ViewModels;
using Microsoft.UI.Xaml.Controls;

var root = Path.Combine(Path.GetTempPath(), "aegisvault-2.4-ipc-" + Guid.NewGuid().ToString("N"));
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
    try { using var process = Process.GetProcessById(pid); return !process.HasExited; }
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
