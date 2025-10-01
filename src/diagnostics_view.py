import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk, GObject  # noqa: E402


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/diagnostics_view.ui")
class DiagnosticsView(Gtk.Widget):
    __gtype_name__ = "DiagnosticsView"

    messages: Gio.ListStore = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

    def set_messages(self, params) -> None:
        """Set diagnostic messages."""
        self.messages.remove_all()
        if params:
            for diagnostic in params["diagnostics"]:
                severity = diagnostic.get("severity", 1)
                message = diagnostic["message"]
                self.messages.append(DiagnosticMessage(severity, message))


class DiagnosticMessage(GObject.Object):
    __gtype_name__ = "DiagnosticMessage"

    css_classes: str = GObject.Property(type=GObject.Strv)  # type: ignore
    icon_name: str = GObject.Property(type=str)  # type: ignore
    message: str = GObject.Property(type=str)  # type: ignore

    def __init__(self, severity, message: str):
        super().__init__()

        match severity:
            case 1:
                css_class = "error"
                icon_name = "exclamation-mark-symbolic"
            case 2:
                css_class = "warning"
                icon_name = "warning-outline-symbolic"
            case 3:
                css_class = "accent"
                icon_name = "info-outline-symbolic"
            case 4:
                css_class = "success"
                icon_name = "info-outline-symbolic"

        self.css_classes = [css_class]
        self.icon_name = icon_name
        self.message = message
