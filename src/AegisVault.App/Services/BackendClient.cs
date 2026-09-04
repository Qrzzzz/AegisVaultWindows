using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace AegisVault.App.Services;

public sealed class BackendException(string code) : Exception(code)
{
    public string Code { get; } = code;
}

public sealed record BackendProgress(double Percent, string Stage, long? ProcessedBytes, long? TotalBytes);

public sealed class BackendClient
{
    public static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };

    private static ProcessStartInfo StartInfo()
    {
        var executable = Path.Combine(AppContext.BaseDirectory, "backend", "AegisVault.Backend.exe");
        var info = new ProcessStartInfo
        {
            UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(false), StandardOutputEncoding = new UTF8Encoding(false),
            WorkingDirectory = AppContext.BaseDirectory
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

    public async Task<JsonElement> CallAsync(string operation, object? args = null,
        IProgress<BackendProgress>? progress = null, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using var process = new Process { StartInfo = StartInfo() };
        var id = Guid.NewGuid().ToString("N");
        var request = JsonSerializer.Serialize(new { v = 1, id, op = operation, args = args ?? new { } }, JsonOptions);
        if (Encoding.UTF8.GetByteCount(request) + 1 > 16 * 1024 * 1024)
            throw new BackendException("ipc.request_too_large");
        var started = false;
        Task drain = Task.CompletedTask;
        try
        {
            started = process.Start();
            if (!started) throw new BackendException("ipc.backend_missing");
            // Drain without retaining diagnostics, which must never surface input or secrets.
            drain = DrainAsync(process.StandardError);
            await process.StandardInput.WriteLineAsync(request);
            await process.StandardInput.FlushAsync();
            using var forcedStop = new CancellationTokenSource();
            using var cancel = cancellationToken.Register(() =>
            {
                forcedStop.CancelAfter(TimeSpan.FromSeconds(30));
                try
                {
                    process.StandardInput.WriteLine(JsonSerializer.Serialize(new { v = 1, id, op = "cancel" }));
                    process.StandardInput.Flush();
                }
                catch (Exception ex) when (ex is IOException or ObjectDisposedException or InvalidOperationException) { }
            });
            while (true)
            {
                string? line;
                try { line = await process.StandardOutput.ReadLineAsync(forcedStop.Token); }
                catch (OperationCanceledException)
                {
                    process.Kill(entireProcessTree: true);
                    throw new BackendException("ipc.cancel_timeout");
                }
                if (line is null) throw new BackendException("ipc.backend_exited");
                using var document = JsonDocument.Parse(line);
                var message = document.RootElement;
                if (message.GetProperty("v").GetInt32() != 1 || message.GetProperty("id").GetString() != id)
                    throw new BackendException("ipc.invalid_response");
                switch (message.GetProperty("type").GetString())
                {
                    case "progress":
                        progress?.Report(new(message.GetProperty("percent").GetDouble(),
                            message.GetProperty("stage").GetString() ?? "", Number(message, "processed_bytes"), Number(message, "total_bytes")));
                        break;
                    case "result": return message.GetProperty("result").Clone();
                    case "error": throw new BackendException(message.GetProperty("code").GetString() ?? "app.error");
                    case "cancelled": throw new OperationCanceledException(cancellationToken);
                    default: throw new BackendException("ipc.invalid_response");
                }
            }
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or IOException)
        {
            throw new BackendException("ipc.backend_exited");
        }
        catch (Exception ex) when (ex is JsonException or KeyNotFoundException or InvalidOperationException)
        {
            throw new BackendException("ipc.invalid_response");
        }
        finally
        {
            if (started)
            {
                process.StandardInput.Close(); // EOF is also a cooperative cancellation signal.
                using var shutdown = new CancellationTokenSource(TimeSpan.FromSeconds(30));
                try { await process.WaitForExitAsync(shutdown.Token); }
                catch (OperationCanceledException) { process.Kill(entireProcessTree: true); await process.WaitForExitAsync(); }
                await drain;
            }
        }
    }

    private static long? Number(JsonElement value, string key) =>
        value.TryGetProperty(key, out var number) && number.ValueKind == JsonValueKind.Number ? number.GetInt64() : null;

    private static async Task DrainAsync(StreamReader reader)
    {
        var buffer = new char[1024];
        while (await reader.ReadAsync(buffer) != 0) { }
    }
}
