using System.Diagnostics;
using System.Text;
using System.Text.Json;

Console.InputEncoding = new UTF8Encoding(false);
Console.OutputEncoding = new UTF8Encoding(false);
var mode = Environment.GetEnvironmentVariable("AEGISVAULT_TEST_MODE") ?? "healthy";
var marker = Environment.GetEnvironmentVariable("AEGISVAULT_TEST_MARKER")!;
void Record(int pid)
{
    using var owned = Process.GetProcessById(pid);
    File.WriteAllText($"{marker}.{pid}.pid", owned.StartTime.ToUniversalTime().Ticks.ToString());
}
void Mark(string stage)
{
    Record(Environment.ProcessId);
    File.WriteAllText(marker, JsonSerializer.Serialize(new { pid = Environment.ProcessId, stage }));
}

if (mode is "no-read" or "blocked-cancel-write")
{
    Mark(mode);
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}

var raw = await Console.In.ReadLineAsync();
if (raw is null) return;
using var request = JsonDocument.Parse(raw);
var id = request.RootElement.GetProperty("id").GetString();
var op = request.RootElement.GetProperty("op").GetString();

if (mode == "no-response")
{
    Mark(mode);
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}
if (mode == "terminal-no-exit")
{
    Mark(mode);
    Console.WriteLine($"{{\"v\":1,\"id\":\"{id}\",\"type\":\"result\",\"result\":{{\"protocol\":1,\"version\":\"2.5\"}}}}");
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}
if (mode == "exit-cancel-race")
{
    Mark(mode);
    _ = await Console.In.ReadLineAsync();
    return;
}
if (mode == "stderr-flood")
{
    Mark(mode);
    using var stop = new CancellationTokenSource();
    var flood = Task.Run(async () =>
    {
        var block = new string('e', 4096);
        try { while (!stop.IsCancellationRequested) await Console.Error.WriteLineAsync(block); }
        catch (IOException) { }
    });
    Console.WriteLine($"{{\"v\":1,\"id\":\"{id}\",\"type\":\"result\",\"result\":{{\"protocol\":1,\"version\":\"2.5\"}}}}");
    while (await Console.In.ReadLineAsync() is not null) { }
    stop.Cancel();
    await flood;
    return;
}
if (mode == "numeric")
{
    Mark(mode);
    var response = Environment.GetEnvironmentVariable("AEGISVAULT_TEST_RESPONSE")!.Replace("__ID__", id);
    Console.WriteLine(response);
    while (await Console.In.ReadLineAsync() is not null) { }
    return;
}
if (mode.StartsWith("invalid-utf8-", StringComparison.Ordinal))
{
    Mark(mode);
    using var wireOutput = Console.OpenStandardOutput();
    var bytes = mode switch
    {
        "invalid-utf8-line" => new byte[] { 0xff, 0x0a },
        "invalid-utf8-eof" => new byte[] { 0xf0, 0x9f },
        _ => new byte[] { 0xe2, 0x28, 0xa1, 0x0a }
    };
    await wireOutput.WriteAsync(bytes);
    await wireOutput.FlushAsync();
    return;
}
if (mode == "valid-utf8-split")
{
    Mark(mode);
    using var wireOutput = Console.OpenStandardOutput();
    var prefix = $"{{\"v\":1,\"id\":\"{id}\",\"type\":\"result\",\"result\":{{\"text\":\"";
    var text = new string(' ', 8191 - Encoding.UTF8.GetByteCount(prefix)) + prefix + "🔐\"}}\r\n";
    var bytes = Encoding.UTF8.GetBytes(text);
    await wireOutput.WriteAsync(bytes.AsMemory(0, 8192));
    await wireOutput.FlushAsync();
    await Task.Delay(50);
    await wireOutput.WriteAsync(bytes.AsMemory(8192));
    await wireOutput.FlushAsync();
    return;
}
if (mode == "oversized-response")
{
    Mark(mode);
    await Console.Out.WriteAsync(new string('x', 16 * 1024 * 1024));
    await Console.Out.WriteLineAsync("x");
    while (await Console.In.ReadLineAsync() is not null) { }
    return;
}
if (mode == "settings-timeout-retry")
{
    var first = marker + ".first";
    if (!File.Exists(first))
    {
        File.WriteAllText(first, "first"); Mark("settings-hang");
        await Task.Delay(Timeout.InfiniteTimeSpan);
        return;
    }
    Mark("settings-retry");
    Console.WriteLine($"{{\"v\":1,\"id\":\"{id}\",\"type\":\"result\",\"result\":{{\"language\":\"en-US\",\"theme\":\"dark\",\"default_output_dir\":\"\",\"overwrite_outputs\":false,\"remember_recent_files\":true,\"show_advanced_options\":true,\"recent_files\":[]}}}}");
    while (await Console.In.ReadLineAsync() is not null) { }
    return;
}
if (mode.StartsWith("file-recent-", StringComparison.Ordinal) && op == "recent.add")
{
    Mark("recent-hang");
    await Task.Delay(Timeout.InfiniteTimeSpan);
    return;
}
if (mode == "delayed-file")
{
    Mark(mode); await Task.Delay(500);
    Console.WriteLine($"{{\"v\":1,\"id\":\"{id}\",\"type\":\"result\",\"result\":{{\"output_path\":\"synthetic.b64\",\"original_size\":1,\"output_size\":4}}}}");
    while (await Console.In.ReadLineAsync() is not null) { }
    return;
}

Mark("proxy");
var python = Environment.GetEnvironmentVariable("AEGISVAULT_TEST_PYTHON")!;
var source = Environment.GetEnvironmentVariable("AEGISVAULT_TEST_SOURCE")!;
var bootstrap = $"import sys;sys.path.insert(0,{JsonSerializer.Serialize(source)});from aegisvault.backend.server import main;raise SystemExit(main())";
var info = new ProcessStartInfo(python) {
    UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true,
    RedirectStandardOutput = true, RedirectStandardError = true, StandardInputEncoding = new UTF8Encoding(false)
};
info.ArgumentList.Add("-I"); info.ArgumentList.Add("-c"); info.ArgumentList.Add(bootstrap);
using var child = Process.Start(info)!;
Record(child.Id);
var output = child.StandardOutput.BaseStream.CopyToAsync(Console.OpenStandardOutput());
var error = child.StandardError.BaseStream.CopyToAsync(Console.OpenStandardError());
await child.StandardInput.WriteLineAsync(raw); await child.StandardInput.FlushAsync();
while (await Console.In.ReadLineAsync() is { } line)
{
    await child.StandardInput.WriteLineAsync(line); await child.StandardInput.FlushAsync();
}
child.StandardInput.Close();
await child.WaitForExitAsync(); await Task.WhenAll(output, error);
Environment.ExitCode = child.ExitCode;
