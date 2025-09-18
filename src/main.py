import asyncio

# import logging
import os
import shutil
import sys
import gi

from gettext import gettext as _
from gi.events import GLibEventLoopPolicy  # pyrefly: ignore[import-error]
from .helpers import get_debug_info
from .preferences import PreferencesDialog
from .window import PyroseWindow

gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402


class PyroseApplication(Adw.Application):
    """The main application singleton class."""

    settings = Gio.Settings.new("io.github.vanillajonathan.pyrose")

    def __init__(self, version):
        super().__init__(
            application_id="io.github.vanillajonathan.pyrose",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path="/io/github/vanillajonathan/pyrose",
            version=version,
        )
        asyncio.set_event_loop_policy(GLibEventLoopPolicy())

        self.create_action("quit", lambda *_: self.quit(), ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("help", self.on_help_action, ["F1"])
        self.create_action("open-folder", self.on_open_folder_action, ["<Control>M"])
        self.create_action(
            "preferences", self.on_preferences_action, ["<Primary>comma"]
        )

        self.set_accels_for_action("win.run", ["<Control>Return", "F5"])
        self.set_accels_for_action("win.stop", ["<Shift>F5"])
        self.set_accels_for_action("win.fullscreen", ["F11"])
        self.set_accels_for_action(
            "editor.show-goto-line", ["<Control>G", "<Control>I"]
        )
        self.set_accels_for_action("editor.show-search", ["<Control>F"])
        self.set_accels_for_action("editor.show-replace", ["<Control>H"])
        self.set_accels_for_action("editor.search-prev", ["<Control><Shift>G"])
        self.set_accels_for_action("editor.search-next", ["<Control>G"])
        self.set_accels_for_action("terminal.copy", ["<Ctrl><Shift>C"])
        self.set_accels_for_action("terminal.paste", ["<Ctrl><Shift>V"])
        self.set_accels_for_action("terminal.select-all", ["<Ctrl><Shift>A"])
        self.set_accels_for_action("terminal.show-search", ["<Ctrl><Shift>F"])

        user_home_dir = os.path.expanduser("~")
        new_directories = f"{user_home_dir}/.cargo/bin"
        new_directories += f":{user_home_dir}/.local/bin"
        os.environ["PATH"] = new_directories + ":" + os.environ["PATH"]

        if python_path := self.settings.get_string("python-path"):
            os.environ["PYTHONPATH"] = python_path

        self.languages = []
        self.languages.append(
            ("Python", "python3", ".py", sys.executable, ["-B", "-c"])
        )
        if shutil.which("perl"):
            self.languages.append(("Perl", "perl", ".pl", "perl", ["-W"]))
        if shutil.which("gjs"):
            self.languages.append(("JavaScript (GJS)", "js", ".js", "gjs", ["-c"]))
        if shutil.which("ruby"):
            self.languages.append(("Ruby", "ruby", ".rb", "ruby", ["-e"]))

        self.pyrefly_installed = bool(shutil.which("pyrefly"))

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            win = PyroseWindow(application=self, languages=self.languages)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name="PyRose",
            application_icon="io.github.vanillajonathan.pyrose",
            developer_name="Jonathan",
            developers=["Jonathan"],
            copyright="© 2025 Jonathan",
            debug_info=get_debug_info(self.props.version, self.settings),
            issue_url="https://github.com/vanillajonathan/pyrose/issues",
            license_type=Gtk.License.MIT_X11,
            version=f"{self.props.version}",
            website="https://github.com/vanillajonathan/pyrose",
        )
        comments = "Playground for programmers."
        if not self.pyrefly_installed:
            about.add_link("Pyrefly", "https://pyrefly.org/")
            comments += "\n\nYou should really install <a href='https://pyrefly.org/'>Pyrefly</a> for a better Python experience. See the built-in help for instructions."
        about.set_comments(comments)
        # Translators: Replace "translator-credits" with your name/username, and optionally an email or URL.
        about.set_translator_credits(_("translator-credits"))
        about.present(self.props.active_window)

    def on_help_action(self, widget, _):
        """Callback for the app.help action."""
        # Gtk.show_uri is deprecated
        Gtk.show_uri(self.get_active_window(), "help:pyrose", Gdk.CURRENT_TIME)
        # https://gitlab.gnome.org/GNOME/gtk/-/issues/6135
        # Gtk.UriLauncher.new("help:pyrose").launch(self.props.active_window)

    def on_open_folder_action(self, widget, _):
        """Callback for the app.open-folder action."""
        path = os.environ.get("XDG_STATE_HOME", ".pyrose")
        file: Gio.File = Gio.File.new_for_path(path)
        Gtk.FileLauncher.new(file).launch()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        dialog = PreferencesDialog()
        dialog.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    # logging.basicConfig(level=logging.DEBUG)
    app = PyroseApplication(version=version)
    return app.run(sys.argv)
