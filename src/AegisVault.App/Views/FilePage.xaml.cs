using Microsoft.UI.Xaml.Controls;
namespace AegisVault.App.Views;
public sealed partial class FilePage : Page
{
    public FilePage() { InitializeComponent(); DataContext = App.Window.FileWorkflow; Workflow.Attach(App.Window.FileWorkflow); }
}
