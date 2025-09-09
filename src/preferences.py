from typing import Final
import os
import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk, Gio  # noqa: E402

SETTING_PYTHON_PATH: Final[str] = "python-path"


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/preferences.ui")
class PreferencesDialog(Adw.PreferencesDialog):
    __gtype_name__ = "PreferencesDialog"
    python_path_entry: Adw.EntryRow = Gtk.Template.Child()
    settings: Gio.Settings = Gio.Settings.new("io.github.vanillajonathan.pyrose")

    def __init__(self):
        super().__init__()
        if python_path := self.settings.get_string(SETTING_PYTHON_PATH):
            self.python_path_entry.set_text(python_path)

    @Gtk.Template.Callback()
    def on_apply(self, entry_row: Adw.EntryRow) -> None:
        python_path = entry_row.get_text()
        self.settings.set_string(SETTING_PYTHON_PATH, python_path)
        os.environ["PYTHONPATH"] = python_path
