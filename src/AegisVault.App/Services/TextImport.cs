using System.Text;

namespace AegisVault.App.Services;

public static class TextImport
{
    public static async Task<string> ReadAsync(string path, int byteLimit)
    {
        if (new FileInfo(path).Length > byteLimit + 3L) throw new BackendException("resource.limit_exceeded");
        using var stream = File.OpenRead(path);
        var bytes = new byte[byteLimit + 4];
        var count = await stream.ReadAtLeastAsync(bytes, bytes.Length, throwOnEndOfStream: false);
        if (count == bytes.Length) throw new BackendException("resource.limit_exceeded");
        // Consume one encoding signature, preserving every subsequent U+FEFF.
        var offset = count >= 3 && bytes[0] == 0xEF && bytes[1] == 0xBB && bytes[2] == 0xBF ? 3 : 0;
        if (count - offset > byteLimit) throw new BackendException("resource.limit_exceeded");
        return new UTF8Encoding(false, true).GetString(bytes, offset, count - offset);
    }
}
