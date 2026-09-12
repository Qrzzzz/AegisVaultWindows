using System.Text.Json;

namespace AegisVault.App.Services;

internal sealed record BatchFileResult(string InputPath, string Status, string Code, string OutputPath = "",
    long OriginalSize = 0, long OutputSize = 0);

internal static class BatchResponse
{
    public const int MaxFiles = 256;
    public static IReadOnlyList<BatchFileResult> Read(JsonElement value)
    {
        BackendResponse.Object(value);
        if (!value.TryGetProperty("cancelled", out var cancelled) || cancelled.ValueKind is not (JsonValueKind.True or JsonValueKind.False)
            || !value.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array
            || items.GetArrayLength() is < 1 or > MaxFiles) throw BackendResponse.Invalid();
        var results = new List<BatchFileResult>();
        foreach (var entry in items.EnumerateArray())
        {
            BackendResponse.Object(entry);
            var path = BackendResponse.String(entry, "input_path");
            var status = BackendResponse.String(entry, "status");
            var code = BackendResponse.String(entry, "code");
            if (string.IsNullOrWhiteSpace(path) || !TextLimits.HasValidUnicode(path)
                || !entry.TryGetProperty("result", out var result)) throw BackendResponse.Invalid();
            if (status == "completed")
            {
                BackendResponse.Object(result);
                var output = BackendResponse.String(result, "output_path");
                var originalSize = BackendResponse.Int64(result, "original_size");
                var outputSize = BackendResponse.Int64(result, "output_size");
                if (code.Length != 0 || string.IsNullOrWhiteSpace(output) || !TextLimits.HasValidUnicode(output)
                    || output.Contains('\0') || originalSize < 0 || outputSize < 0) throw BackendResponse.Invalid();
                results.Add(new(path, status, code, output, originalSize, outputSize));
            }
            else
            {
                if (result.ValueKind != JsonValueKind.Null || status is not ("failed" or "cancelled" or "pending")
                    || status == "failed" && string.IsNullOrWhiteSpace(code)
                    || status == "cancelled" && code != "operation.cancelled"
                    || status == "pending" && code.Length != 0
                    || status is "cancelled" or "pending" && !cancelled.GetBoolean()) throw BackendResponse.Invalid();
                results.Add(new(path, status, code));
            }
        }
        return results;
    }
}
