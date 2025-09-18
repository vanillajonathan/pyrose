import os
import platform
import subprocess
import gi
import lsp_types as lsp

gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
gi.require_version("Vte", "3.91")
from gi.repository import Adw, Gtk, GtkSource, GLib, Vte  # noqa: E402


def get_debug_info(version, settings) -> str:
    debug_info = f"PyRose {version}\n\n"
    debug_info += f"{GLib.get_os_info('PRETTY_NAME')}\n"
    debug_info += (
        f"GLib {GLib.MAJOR_VERSION}.{GLib.MINOR_VERSION}.{GLib.MICRO_VERSION}\n"
    )
    debug_info += f"GTK {Gtk.MAJOR_VERSION}.{Gtk.MINOR_VERSION}.{Gtk.MICRO_VERSION}\n"
    debug_info += f"GtkSourceView {GtkSource.MAJOR_VERSION}.{GtkSource.MINOR_VERSION}.{GtkSource.MICRO_VERSION}\n"

    debug_info += "PyGObject {}.{}.{}\n".format(
        *gi.version_info  # pyrefly: ignore[missing-attribute]
    )
    debug_info += (
        f"libadwaita {Adw.MAJOR_VERSION}.{Adw.MINOR_VERSION}.{Adw.MICRO_VERSION}\n"
    )
    debug_info += (
        f"libvte {Vte.MAJOR_VERSION}.{Vte.MINOR_VERSION}.{Vte.MICRO_VERSION}\n"
    )
    debug_info += f"Python {platform.python_version()}\n"

    try:
        result = subprocess.run(["pyrefly", "--version"], capture_output=True)
        debug_info += result.stdout.decode() + "\n\n"
    except FileNotFoundError:
        debug_info += "The Python LSP server Pyrefly was not found.\n\n"

    debug_info += "Environment variables:\n"
    debug_info += f"- LANG: {os.environ.get('LANG')}\n"
    for env in os.environ:
        if env.startswith(("GTK_", "GDK", "PYTHON")):
            debug_info += f"- {env}:  {os.environ.get(env)}\n"
    debug_info += "\n"

    debug_info += "Settings:\n"
    schema = settings.props.settings_schema
    for key in schema.list_keys():
        debug_info += f"- {key}: {settings.get_value(key)}\n"
    return debug_info


def get_initialize_params(version: str) -> lsp.InitializeParams:
    """Get LSP initialization parameters.

    Args:
      version: The client version.

    Returns:
      Initialization parameters for the LSP.
    """
    params: lsp.InitializeParams = {
        "processId": os.getpid(),
        "clientInfo": {"name": "PyRose", "version": version},
        "locale": "en",
        "rootUri": None,
        "capabilities": {
            "textDocument": {
                "completion": {
                    "completionItem": {
                        "snippetSupport": False,
                        "documentationFormat": [
                            lsp.MarkupKind.Markdown,
                            lsp.MarkupKind.PlainText,
                        ],
                        "deprecatedSupport": True,
                        "tagSupport": {"valueSet": [lsp.CompletionItemTag.Deprecated]},
                        "labelDetailsSupport": True,
                    },
                    "completionItemKind": {
                        "valueSet": [
                            lsp.CompletionItemKind.Text,
                            lsp.CompletionItemKind.Method,
                            lsp.CompletionItemKind.Function,
                            lsp.CompletionItemKind.Constructor,
                            lsp.CompletionItemKind.Field,
                            lsp.CompletionItemKind.Variable,
                            lsp.CompletionItemKind.Class,
                            lsp.CompletionItemKind.Interface,
                            lsp.CompletionItemKind.Module,
                            lsp.CompletionItemKind.Property,
                            lsp.CompletionItemKind.Unit,
                            lsp.CompletionItemKind.Value,
                            lsp.CompletionItemKind.Enum,
                            lsp.CompletionItemKind.Keyword,
                            lsp.CompletionItemKind.Snippet,
                            lsp.CompletionItemKind.Color,
                            lsp.CompletionItemKind.File,
                            lsp.CompletionItemKind.Reference,
                            lsp.CompletionItemKind.Folder,
                            lsp.CompletionItemKind.EnumMember,
                            lsp.CompletionItemKind.Constant,
                            lsp.CompletionItemKind.Struct,
                            lsp.CompletionItemKind.Event,
                            lsp.CompletionItemKind.Operator,
                            lsp.CompletionItemKind.TypeParameter,
                        ]
                    },
                    # "contextSupport": True
                },
                "hover": {
                    "contentFormat": [lsp.MarkupKind.Markdown, lsp.MarkupKind.PlainText]
                },
                "publishDiagnostics": {
                    "tagSupport": {
                        "valueSet": [
                            lsp.DiagnosticTag.Unnecessary,
                            lsp.DiagnosticTag.Deprecated,
                        ]
                    }
                },
            },
            "general": {
                "regularExpressions": {
                    "engine": "Python",
                    "version": platform.python_version(),
                },
                "positionEncodings": [lsp.PositionEncodingKind.UTF8],
            },
        },
        "trace": lsp.TraceValue.Off,
    }

    return params
