import asyncio
import os
import re
import signal
import gi

from asyncio import Task

gi.require_version("Gtk", "4.0")
gi.require_version("Vte", "3.91")
from gi.repository import Gio, GLib, Gtk, GObject, Vte  # noqa: E402


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/terminal.ui")
class Terminal(Gtk.Widget):
    __gtype_name__ = "Terminal"

    status_label: Gtk.Label = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    search_revealer: Gtk.Revealer = Gtk.Template.Child()
    terminal: Vte.Terminal = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        GObject.type_ensure(Vte.Terminal)
        self.animate_fade_task: Task | None = None
        self.pid: int | None = None

        actions = (
            ("show-search", self.show_search),
            ("reset", lambda action, parameter: self.terminal.reset(True, True)),
            (
                "copy",
                lambda action, parameter: self.terminal.copy_clipboard_format(
                    Vte.Format.TEXT
                ),
            ),
            ("paste", lambda action, parameter: self.terminal.paste_clipboard()),
            ("select-all", lambda action, parameter: self.terminal.select_all()),
            (
                "search-prev",
                lambda action, parameter: self.terminal.search_find_previous(),
            ),
            ("search-next", lambda action, parameter: self.terminal.search_find_next()),
            ("search-hide", self.hide_search),
        )

        action_group = Gio.SimpleActionGroup()
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        action_group.lookup_action("copy").set_enabled(False)
        self.action_group = action_group

    @GObject.Signal
    def bell(self):
        """Called every time the bell signal is emitted."""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(int,))
    def child_exited(self, exit_status: int):
        """Called every time the child-exited signal is emitted."""
        pass

    @Gtk.Template.Callback()
    def on_bell(self, terminal: Vte.Terminal) -> None:
        self.emit("bell")

    @Gtk.Template.Callback()
    def on_child_exited(self, terminal, exit_status: int) -> None:
        RED = "\033[31m"
        GREEN = "\033[32m"
        RESET = "\033[0m"
        if exit_status == 0:
            bullet = f"{GREEN}●{RESET}"
        else:
            bullet = f"{RED}●{RESET}"
        terminal.feed(
            f"\r\n{bullet} Process exited with status: {exit_status}\r\n".encode()
        )

        bullet = "🟢" if exit_status == 0 else "🔴"
        self.status_label.set_label(
            f"{bullet} Process exited with status: {exit_status}"
        )

        async def animate_fade():
            self.status_label.get_style_context().add_class("visible")
            await asyncio.sleep(2)
            self.status_label.get_style_context().remove_class("visible")

        if self.animate_fade_task is not None:
            self.animate_fade_task.cancel()
        self.animate_fade_task = asyncio.create_task(animate_fade())
        self.emit("child-exited", exit_status)

    @Gtk.Template.Callback()
    def on_search_changed(self, entry: Gtk.SearchEntry):
        pattern = entry.get_text()
        text = re.escape(pattern)
        PCRE2_CASELESS = 0x00000008
        PCRE2_MULTILINE = 0x00000400
        regex = Vte.Regex.new_for_search(
            text, len(text), PCRE2_MULTILINE | PCRE2_CASELESS
        )
        self.terminal.unselect_all()
        self.terminal.search_set_regex(regex, 0)
        self.terminal.search_find_next()

    @Gtk.Template.Callback()
    def on_selection_changed(self, terminal: Vte.Terminal) -> None:
        has_selection = terminal.get_has_selection()
        self.action_group.lookup_action("copy").set_enabled(has_selection)

    def show_search(self, action, parameter):
        self.search_revealer.set_reveal_child(True)
        self.search_entry.grab_focus()

    def hide_search(self, action, parameter):
        self.search_revealer.set_reveal_child(False)
        self.terminal.unselect_all()

    async def spawn(self, program: str, args: list[str], code: str) -> int:
        """Spawn a process."""

        def spawn_callback(terminal, pid: int, error: GLib.GError):
            if error:
                self.terminal.feed(f"{error.message}\r\n".encode())
                future.set_exception(RuntimeError(error))
            else:
                self.pid = pid
                future.set_result(pid)

        future = asyncio.Future()
        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ.get("XDG_DATA_HOME", ".pyrose"),  # CWD for the command
            [
                "nice",
                "-n",
                "19",
                program,
                *args,
                code,
            ],  # Command and args
            [],  # envv
            GLib.SpawnFlags.DEFAULT,  # spawn_flags
            None,  # child_setup
            None,  # child_setup action
            -1,  # timeout
            None,  # cancellable
            spawn_callback,  # callback for when process finishes
            (),  # user_data for callback
        )
        return await future

    def terminate(self) -> None:
        """Terminate the running process."""
        if self.pid:
            os.kill(self.pid, signal.SIGTERM)
            self.pid = None
