using System.Reflection;

namespace AegisVault.App.Services;

public static class ProductInfo
{
    public static string Version { get; } = typeof(ProductInfo).Assembly
        .GetCustomAttribute<AssemblyInformationalVersionAttribute>()!.InformationalVersion;
    public static string DisplayName => $"AegisVault {Version}";
}
