using Microsoft.UI.Xaml.Controls;
namespace AegisVault.App.Views;
public sealed partial class TextPage : Page
{
    public TextPage() { InitializeComponent(); DataContext = App.Window.TextWorkflow; Workflow.Attach(App.Window.TextWorkflow); }
}
