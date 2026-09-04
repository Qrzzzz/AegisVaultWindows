using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;

namespace AegisVault.App.ViewModels;

public abstract class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    protected bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value; Raise(name); return true;
    }
    protected void Raise([CallerMemberName] string? name = null) => PropertyChanged?.Invoke(this, new(name));
}

public sealed class ActionCommand(Action action, Func<bool>? enabled = null) : ICommand
{
    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? parameter) => enabled?.Invoke() ?? true;
    public void Execute(object? parameter) { if (CanExecute(parameter)) action(); }
    public void Refresh() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}
