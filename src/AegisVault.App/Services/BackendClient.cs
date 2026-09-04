using System.Diagnostics;
using System.Runtime.ExceptionServices;
using System.Text;
using System.Text.Json;

namespace AegisVault.App.Services;

public sealed class BackendException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

public sealed record BackendProgress(double Percent, string Stage, long? ProcessedBytes, long? TotalBytes);

internal sealed record BackendTimeouts(
    TimeSpan ShortRequest,
    TimeSpan CancellationGrace,
    TimeSpan ExitGrace,
    TimeSpan ReapGrace)
{
    public static BackendTimeouts Default { get; } = new(
        TimeSpan.FromSeconds(15), TimeSpan.FromSeconds(30),
        TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(5));
}

internal static class BackendResponse
{
    public static JsonElement Object(JsonElement value)
    {
        if (value.ValueKind != JsonValueKind.Object) throw Invalid();
        return value;
    }

    public static int Int32(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var item) || item.ValueKind != JsonValueKind.Number || !item.TryGetInt32(out var result))
            throw Invalid();
        return result;
    }

    public static long Int64(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var item) || item.ValueKind != JsonValueKind.Number || !item.TryGetInt64(out var result))
            throw Invalid();
        return result;
    }

    public static string String(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var item) || item.ValueKind != JsonValueKind.String)
            throw Invalid();
        return item.GetString() ?? throw Invalid();
    }

    public static BackendException Invalid() => new("ipc.invalid_response");
}

public sealed class BackendClient
{
    public static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    private static readonly HashSet<string> ShortOperations =
        ["hello", "settings.get", "settings.update", "recent.add", "recent.clear"];
    private readonly BackendTimeouts timeouts;

    public BackendClient() : this(BackendTimeouts.Default) { }

    internal BackendClient(BackendTimeouts timeouts)
    {
        if (new[] { timeouts.ShortRequest, timeouts.CancellationGrace, timeouts.ExitGrace, timeouts.ReapGrace }
            .Any(value => value <= TimeSpan.Zero || !double.IsFinite(value.TotalMilliseconds)))
            throw new ArgumentOutOfRangeException(nameof(timeouts));
        this.timeouts = timeouts;
    }

    private static ProcessStartInfo StartInfo()
    {
        var executable = Path.Combine(AppContext.BaseDirectory, "backend", "AegisVault.Backend.exe");
        var info = new ProcessStartInfo
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(false), StandardOutputEncoding = new UTF8Encoding(false),
            StandardErrorEncoding = new UTF8Encoding(false), WorkingDirectory = AppContext.BaseDirectory
        };
        if (File.Exists(executable)) info.FileName = executable;
        else
        {
#if DEBUG
            // Development override is intentionally unavailable in published Release builds.
            info.FileName = Environment.GetEnvironmentVariable("AEGISVAULT_PYTHON")
                ?? throw new BackendException("ipc.backend_missing");
            info.ArgumentList.Add("-I");
            info.ArgumentList.Add("-m");
            info.ArgumentList.Add("aegisvault.backend");
#else
            throw new BackendException("ipc.backend_missing");
#endif
        }
        info.Environment["PYTHONUTF8"] = "1";
        info.Environment.Remove("PYTHONPATH");
        info.Environment.Remove("PYTHONHOME");
        return info;
    }

    public Task<JsonElement> CallAsync(string operation, object? args = null,
        IProgress<BackendProgress>? progress = null, CancellationToken cancellationToken = default) =>
        Task.Run(() => CallOnWorkerAsync(operation, args, progress, cancellationToken));

    private async Task<JsonElement> CallOnWorkerAsync(string operation, object? args,
        IProgress<BackendProgress>? progress, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        string request;
        try { request = JsonSerializer.Serialize(new { v = 1, id = Guid.NewGuid().ToString("N"), op = operation, args = args ?? new { } }, JsonOptions); }
        catch (Exception ex) when (ex is JsonException or NotSupportedException)
        {
            throw new BackendException("ipc.invalid_request");
        }
        if (Encoding.UTF8.GetByteCount(request) + 1 > 16 * 1024 * 1024)
            throw new BackendException("ipc.request_too_large");

        using var process = new Process { StartInfo = StartInfo() };
        try
        {
            if (!process.Start()) throw new BackendException("ipc.backend_missing");
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or IOException)
        {
            throw new BackendException("ipc.backend_exited");
        }

        using var lifetime = new CancellationTokenSource();
        using var drainLifetime = new CancellationTokenSource();
        var cancelled = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        using var cancellation = cancellationToken.Register(() => cancelled.TrySetResult());
        using var inputGate = new SemaphoreSlim(1, 1);
        var terminalReceived = 0;
        var requestSent = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        Task<string>? requestDeadline = ShortOperations.Contains(operation)
            ? DeadlineAsync(timeouts.ShortRequest, "ipc.request_timeout", lifetime.Token) : null;
        Task<string> cancellationDeadline = CancellationDeadlineAsync(cancelled.Task, lifetime.Token);
        Task drain = Task.Run(() => DrainAsync(process.StandardError, drainLifetime.Token));
        Task<JsonElement> exchange = Task.Run(() => ExchangeAsync(
            process, request, operation, progress, inputGate, requestSent, lifetime.Token,
            () => Interlocked.Exchange(ref terminalReceived, 1)));
        Task notifyCancellation = Task.Run(() => NotifyCancellationAsync(
            process, request, cancelled.Task, requestSent.Task, inputGate, lifetime.Token));
        Observe(drain); Observe(exchange); Observe(notifyCancellation);

        JsonElement result = default;
        ExceptionDispatchInfo? failure = null;
        var forceStop = false;
        try
        {
            var contenders = requestDeadline is null
                ? new Task[] { exchange, cancellationDeadline }
                : [exchange, cancellationDeadline, requestDeadline];
            var winner = await Task.WhenAny(contenders);
            if (winner == exchange) result = await exchange;
            else
            {
                forceStop = true;
                throw new BackendException(await ((Task<string>)winner));
            }
        }
        catch (Exception ex)
        {
            forceStop |= Volatile.Read(ref terminalReceived) == 0;
            failure = ExceptionDispatchInfo.Capture(ex);
        }

        await CleanupAsync(process, lifetime, drainLifetime,
            [exchange, notifyCancellation, drain], forceStop);
        failure?.Throw();
        return result;
    }

    private async Task<JsonElement> ExchangeAsync(Process process, string request, string operation,
        IProgress<BackendProgress>? progress, SemaphoreSlim inputGate, TaskCompletionSource<bool> requestSent,
        CancellationToken lifetime,
        Action terminal)
    {
        try
        {
            await WriteAsync(process.StandardInput, request, inputGate, lifetime);
            requestSent.TrySetResult(true);
        }
        catch
        {
            requestSent.TrySetResult(false);
            throw;
        }
        var id = RequestId(request);
        while (true)
        {
            string? line;
            try { line = await process.StandardOutput.ReadLineAsync(lifetime); }
            catch (OperationCanceledException) when (lifetime.IsCancellationRequested) { throw new BackendException("ipc.backend_exited"); }
            if (line is null) throw new BackendException("ipc.backend_exited");
            try
            {
                using var document = JsonDocument.Parse(line);
                var message = BackendResponse.Object(document.RootElement);
                if (BackendResponse.Int32(message, "v") != 1 || BackendResponse.String(message, "id") != id)
                    throw BackendResponse.Invalid();
                switch (BackendResponse.String(message, "type"))
                {
                    case "progress":
                        var percent = Double(message, "percent");
                        if (!double.IsFinite(percent) || percent is < 0 or > 1) throw BackendResponse.Invalid();
                        var stage = BackendResponse.String(message, "stage");
                        var processedBytes = OptionalInt64(message, "processed_bytes");
                        var totalBytes = OptionalInt64(message, "total_bytes");
                        progress?.Report(new(percent, stage, processedBytes, totalBytes));
                        break;
                    case "result":
                        if (!message.TryGetProperty("result", out var value)) throw BackendResponse.Invalid();
                        ValidateResult(operation, value);
                        terminal();
                        return value.Clone();
                    case "error":
                        var code = BackendResponse.String(message, "code");
                        if (string.IsNullOrWhiteSpace(code)) throw BackendResponse.Invalid();
                        terminal();
                        throw new BackendException(code);
                    case "cancelled":
                        terminal();
                        throw new OperationCanceledException();
                    default: throw BackendResponse.Invalid();
                }
            }
            catch (BackendException) { throw; }
            catch (Exception ex) when (ex is JsonException or KeyNotFoundException or InvalidOperationException or FormatException)
            {
                throw BackendResponse.Invalid();
            }
        }
    }

    private async Task NotifyCancellationAsync(Process process, string request, Task cancelled, Task<bool> requestSent,
        SemaphoreSlim inputGate, CancellationToken lifetime)
    {
        await cancelled.WaitAsync(lifetime);
        if (!await requestSent.WaitAsync(lifetime)) return;
        var id = RequestId(request);
        await WriteAsync(process.StandardInput, JsonSerializer.Serialize(new { v = 1, id, op = "cancel" }), inputGate, lifetime);
    }

    private static async Task WriteAsync(StreamWriter writer, string value, SemaphoreSlim gate, CancellationToken token)
    {
        await gate.WaitAsync(token);
        try
        {
            await writer.WriteLineAsync(value.AsMemory(), token);
            await writer.FlushAsync(token);
        }
        finally { gate.Release(); }
    }

    private async Task<string> CancellationDeadlineAsync(Task cancelled, CancellationToken lifetime)
    {
        await cancelled.WaitAsync(lifetime);
        await Task.Delay(timeouts.CancellationGrace, lifetime);
        return "ipc.cancel_timeout";
    }

    private static async Task<string> DeadlineAsync(TimeSpan delay, string code, CancellationToken lifetime)
    {
        await Task.Delay(delay, lifetime);
        return code;
    }

    private async Task CleanupAsync(Process process, CancellationTokenSource lifetime,
        CancellationTokenSource drainLifetime, Task[] backgroundTasks, bool forceStop)
    {
        lifetime.Cancel();
        if (forceStop) Kill(process);
        Task closeInput = Task.Run(() =>
        {
            try { process.StandardInput.BaseStream.Dispose(); }
            catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException) { }
        });
        Task exit = process.WaitForExitAsync();
        Observe(closeInput); Observe(exit);
        if (!forceStop && !await CompletesWithinAsync(IgnoreFailuresAsync([closeInput, exit]), timeouts.ExitGrace))
            Kill(process);
        if (!await CompletesWithinAsync(exit, timeouts.ReapGrace))
            throw new BackendException("ipc.cleanup_failed");
        try { await exit; }
        catch (Exception) { throw new BackendException("ipc.cleanup_failed"); }
        if (!process.HasExited) throw new BackendException("ipc.cleanup_failed");
        drainLifetime.Cancel();
        if (!await CompletesWithinAsync(IgnoreFailuresAsync([.. backgroundTasks, closeInput]), timeouts.ReapGrace))
            throw new BackendException("ipc.cleanup_failed");
    }

    private static void Kill(Process process)
    {
        try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        catch (InvalidOperationException) { }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or NotSupportedException)
        {
            throw new BackendException("ipc.cleanup_failed");
        }
    }

    private static async Task<bool> CompletesWithinAsync(Task task, TimeSpan timeout) =>
        await Task.WhenAny(task, Task.Delay(timeout)) == task;

    private static async Task IgnoreFailuresAsync(Task[] tasks)
    {
        try { await Task.WhenAll(tasks); }
        catch (Exception) { }
    }

    private static void Observe(Task task) => _ = task.ContinueWith(
        completed => _ = completed.Exception, CancellationToken.None,
        TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);

    private static string RequestId(string request)
    {
        using var document = JsonDocument.Parse(request);
        return document.RootElement.GetProperty("id").GetString()!;
    }

    private static double Double(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var item) || item.ValueKind != JsonValueKind.Number || !item.TryGetDouble(out var result))
            throw BackendResponse.Invalid();
        return result;
    }

    private static long? OptionalInt64(JsonElement value, string key)
    {
        if (!value.TryGetProperty(key, out var item) || item.ValueKind == JsonValueKind.Null) return null;
        if (item.ValueKind != JsonValueKind.Number || !item.TryGetInt64(out var result) || result < 0)
            throw BackendResponse.Invalid();
        return result;
    }

    private static void ValidateResult(string operation, JsonElement result)
    {
        BackendResponse.Object(result);
        if (operation == "hello")
        {
            _ = BackendResponse.Int32(result, "protocol");
            _ = BackendResponse.String(result, "version");
        }
        else if (operation is "file.encrypt" or "file.decrypt" or "base64.encode_file" or "base64.decode_file")
        {
            _ = BackendResponse.String(result, "output_path");
            if (BackendResponse.Int64(result, "original_size") < 0 || BackendResponse.Int64(result, "output_size") < 0)
                throw BackendResponse.Invalid();
        }
        else if (operation is "text.encrypt" or "text.decrypt" or "base64.encode_text" or "base64.decode_text")
        {
            var key = operation == "text.encrypt" ? "ciphertext" : operation == "text.decrypt" ? "plaintext" : "text";
            _ = BackendResponse.String(result, key);
        }
    }

    private static async Task DrainAsync(StreamReader reader, CancellationToken token)
    {
        var buffer = new char[1024];
        try { while (await reader.ReadAsync(buffer, token) != 0) { } }
        catch (OperationCanceledException) when (token.IsCancellationRequested) { }
    }
}
