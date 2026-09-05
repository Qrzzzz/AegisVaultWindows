using System.Text;
using System.Text.Json;

namespace AegisVault.App.Services;

public sealed record TextLimitContract(
    int Schema,
    int MaxJsonLineBytes,
    int MaxPlaintextUtf8Bytes,
    int MaxPlaintextUtf16CodeUnits,
    int MaxEncodedTextUtf8Bytes,
    int MaxEncodedTextUtf16CodeUnits,
    int MaxAgv1HeaderBytes);

public static class TextLimits
{
    private static readonly JsonSerializerOptions Options = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
    private static readonly UTF8Encoding StrictUtf8 = new(false, true);
    public static TextLimitContract Contract { get; } = Load();

    public static int Utf8ByteLimit(string kind, int mode) => IsPlaintextInput(kind, mode)
        ? Contract.MaxPlaintextUtf8Bytes : Contract.MaxEncodedTextUtf8Bytes;

    public static int Utf16CodeUnitLimit(string kind, int mode) => IsPlaintextInput(kind, mode)
        ? Contract.MaxPlaintextUtf16CodeUnits : Contract.MaxEncodedTextUtf16CodeUnits;

    public static bool Fits(string kind, int mode, string value)
    {
        if (value.Length > Utf16CodeUnitLimit(kind, mode)) return false;
        try { return StrictUtf8.GetByteCount(value) <= Utf8ByteLimit(kind, mode); }
        catch (EncoderFallbackException) { return false; }
    }

    public static bool HasValidUnicode(string value)
    {
        try { _ = StrictUtf8.GetByteCount(value); return true; }
        catch (EncoderFallbackException) { return false; }
    }

    public static void EnsureBackendMatch(JsonElement hello)
    {
        if (!hello.TryGetProperty("text_limits", out var value) || value.ValueKind != JsonValueKind.Object)
            throw new BackendException("ipc.version_mismatch");
        TextLimitContract? backend;
        try { backend = value.Deserialize<TextLimitContract>(Options); }
        catch (JsonException) { throw new BackendException("ipc.version_mismatch"); }
        if (backend != Contract) throw new BackendException("ipc.version_mismatch");
    }

    private static bool IsPlaintextInput(string kind, int mode) =>
        kind is "text" or "base64_text" && mode == 0;

    private static TextLimitContract Load()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Assets", "text_limits.json");
        TextLimitContract contract;
        try { contract = JsonSerializer.Deserialize<TextLimitContract>(File.ReadAllText(path), Options)!; }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException)
        {
            throw new InvalidDataException("The text resource-limit contract is unavailable.", ex);
        }
        if (contract is null || contract.Schema != 1 ||
            new[] { contract.MaxJsonLineBytes, contract.MaxPlaintextUtf8Bytes,
                contract.MaxPlaintextUtf16CodeUnits, contract.MaxEncodedTextUtf8Bytes,
                contract.MaxEncodedTextUtf16CodeUnits, contract.MaxAgv1HeaderBytes }.Any(value => value <= 0) ||
            contract.MaxPlaintextUtf8Bytes != contract.MaxPlaintextUtf16CodeUnits ||
            contract.MaxEncodedTextUtf8Bytes != contract.MaxEncodedTextUtf16CodeUnits ||
            6L * contract.MaxEncodedTextUtf16CodeUnits + 256 * 1024 > contract.MaxJsonLineBytes)
            throw new InvalidDataException("The text resource-limit contract is invalid.");
        var packageBytes = 8L + 4 + contract.MaxAgv1HeaderBytes + contract.MaxPlaintextUtf8Bytes + 16;
        var maximumTokenBytes = 5 + 4 * ((packageBytes + 2) / 3);
        if (maximumTokenBytes > contract.MaxEncodedTextUtf8Bytes)
            throw new InvalidDataException("The text resource-limit contract is not closed.");
        return contract;
    }
}
