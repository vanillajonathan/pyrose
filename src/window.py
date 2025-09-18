import asyncio
import logging
import os
import gi

from lsp_types import DocumentUri, MessageType
from .code_view import CodeView
from .lsp_client import LspClient, start_lsp_process
from .completion_provider import CompletionProvider
from .hover_provider import HoverProvider
from .helpers import get_initialize_params
from .terminal import Terminal

gi.require_version("Adw", "1")
gi.require_version("GtkSource", "5")
gi.require_version("Vte", "3.91")
from gi.repository import Adw, Gdk, Gio, GObject, Gtk, GtkSource  # noqa: E402

logger = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/window.ui")
class PyroseWindow(Adw.ApplicationWindow):
    __gtype_name__ = "PyroseWindow"

    banner: Adw.Banner = Gtk.Template.Child()
    code_view: CodeView = Gtk.Template.Child()
    lang_string_list: Gtk.StringList = Gtk.Template.Child()
    selected_language = GObject.Property(type=int, default=0, nick="selected_language")
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    unfullscreen_button: Gtk.Button = Gtk.Template.Child()
    terminal: Terminal = Gtk.Template.Child()

    def __init__(self, languages, **kwargs):
        GtkSource.init()
        GObject.type_ensure(CodeView)
        GObject.type_ensure(Terminal)
        super().__init__(**kwargs)
        self.lsp_client: LspClient | None = None
        self.completion_provider: CompletionProvider | None = None
        self.hover_provider: HoverProvider | None = None
        self.languages = languages
        self.code_view.languages = languages

        if self.props.application.props.application_id.endswith(".devel"):
            self.add_css_class("devel")

        for language in languages:
            self.lang_string_list.append(language[0])

        action = Gio.SimpleAction(name="run")
        action.connect("activate", self.on_run_activated)
        self.add_action(action)

        action = Gio.SimpleAction(name="stop")
        action.connect("activate", self.on_stop_activated)
        action.set_enabled(False)
        self.add_action(action)

        action = Gio.SimpleAction(name="fullscreen")
        action.connect("activate", self.on_fullscreen)
        self.add_action(action)

        self.insert_action_group("editor", self.code_view.action_group)
        self.insert_action_group("terminal", self.terminal.action_group)

        self.connect("unrealize", self.on_unrealize)

        if not self.props.application.pyrefly_installed:
            self.banner.set_revealed(True)

    @Gtk.Template.Callback()
    def on_banner_button_clicked(self, banner: Adw.Banner) -> None:
        banner.set_revealed(False)
        Gtk.show_uri(self, "help:pyrose/python", Gdk.CURRENT_TIME)

    @Gtk.Template.Callback()
    def on_editor_changed(self, code_view: CodeView, buffer: GtkSource.Buffer):
        if self.lsp_client is None:
            return
        task = self.lsp_client.update_document(
            self.uri, self.code_view.buffer.props.text
        )
        self.get_application().create_asyncio_task(task)

    @Gtk.Template.Callback()
    def on_editor_cursor_moved(self, code_view: CodeView, buffer: GtkSource.Buffer):
        if self.lsp_client is None or self.lsp_client.server_capabilities is None:
            return
        if "documentHighlightProvider" not in self.lsp_client.server_capabilities:
            return
        if self.lsp_client.server_capabilities["documentHighlightProvider"] is False:
            return

        async def highlight():
            insert_mark = buffer.get_insert()
            cursor_iter = buffer.get_iter_at_mark(insert_mark)
            line = cursor_iter.get_line()
            column = cursor_iter.get_line_offset()
            try:
                highlights = await self.lsp_client.requests.document_highlight(
                    {
                        "textDocument": {"uri": self.uri},
                        "position": {"line": line, "character": column},
                    }
                )
            except ValueError:
                return

            self.code_view.highlight(highlights)

        asyncio.create_task(highlight())

    @Gtk.Template.Callback()
    def on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape and state == 0:
            self.code_view.goto_line_revealer.set_reveal_child(False)
            self.code_view.activate_action("editor.search-hide")
            self.terminal.search_revealer.set_reveal_child(False)
            self.code_view.sourceview.get_completion().hide()
            self.code_view.sourceview.grab_focus()
            return True
        return False

    @Gtk.Template.Callback()
    def on_language_selection_changed(self, dropdown: Gtk.DropDown, _):
        if string_object := dropdown.get_selected_item():
            language = string_object.get_string()
            self.save_buffer()
            self.set_language(language)

    def on_run_activated(self, action, parameter):
        action.set_enabled(False)
        language = self.languages[self.selected_language]
        program = language[3]
        args = language[4]
        self.run(action, program, args)

    @Gtk.Template.Callback()
    def on_child_exited(self, terminal, exit_status: int) -> None:
        self.lookup_action("run").set_enabled(True)
        self.lookup_action("stop").set_enabled(False)

    @Gtk.Template.Callback()
    def on_terminal_bell(self, terminal) -> None:
        async def visual_bell():
            self.get_style_context().add_class("bell")
            await asyncio.sleep(0.5)
            self.get_style_context().remove_class("bell")

        asyncio.create_task(visual_bell())

    def run(self, action, program: str, args: list[str]):
        async def my_run():
            code = self.code_view.buffer.props.text
            try:
                self.lookup_action("run").set_enabled(False)
                self.lookup_action("stop").set_enabled(True)
                await self.terminal.spawn(program, args, code)
            except RuntimeError:
                self.lookup_action("run").set_enabled(True)
                self.lookup_action("stop").set_enabled(False)

        self.get_application().create_asyncio_task(my_run())

    def on_fullscreen(self, action, parameter):
        if self.is_fullscreen():
            self.unfullscreen()
            self.header_bar.set_show_end_title_buttons(True)
            self.unfullscreen_button.set_visible(False)
        else:
            self.fullscreen()
            self.header_bar.set_show_end_title_buttons(False)
            self.unfullscreen_button.set_visible(True)

    def on_stop_activated(self, action, parameter):
        action.set_enabled(False)
        self.lookup_action("run").set_enabled(True)
        self.terminal.terminate()

    def set_language(self, language: str) -> None:
        def get_language_id(language):
            for item in self.languages:
                if item[0] == language:
                    return item[1]
            return ""

        async def start_lsp(uri):
            try:
                process = await start_lsp_process("pyrefly", ["lsp"])
            except OSError:
                logger.debug("LSP not started")
                return
            assert process.stdin and process.stdout
            self.lsp_client = LspClient(process.stdout, process.stdin)
            self.lsp_client.set_notification_handler(self.on_lsp_notification)
            initialize_params = get_initialize_params(
                self.get_application().props.version
            )
            await self.lsp_client.initialize(initialize_params)
            if self.lsp_client.server_capabilities is None:
                print("failed to connect lsp")
                return
            await self.lsp_client.open_document(uri, self.code_view.buffer.props.text)
            if "completionProvider" in self.lsp_client.server_capabilities:
                self.completion_provider = CompletionProvider(self.lsp_client, uri)
                self.code_view.sourceview.get_completion().add_provider(
                    self.completion_provider
                )
            if "hoverProvider" in self.lsp_client.server_capabilities:
                self.hover_provider = HoverProvider(self.lsp_client, uri)
                self.code_view.sourceview.get_hover().add_provider(self.hover_provider)

        async def exit_lsp(lsp_client):
            await lsp_client.exit()

        if self.lsp_client:
            self.get_application().create_asyncio_task(exit_lsp(self.lsp_client))
            self.lsp_client = None
            if self.completion_provider:
                self.code_view.sourceview.get_completion().remove_provider(
                    self.completion_provider
                )
            if self.hover_provider:
                self.code_view.sourceview.get_hover().remove_provider(
                    self.hover_provider
                )

        self.code_view.clear_diagnostics()
        language_manager = GtkSource.LanguageManager.get_default()
        source_language = language_manager.get_language(get_language_id(language))
        self.code_view.buffer.set_language(source_language)
        # print(language_manager.get_language_ids())

        base_dir = os.environ.get("XDG_STATE_HOME", ".pyrose")
        buffer_file = os.path.join(base_dir, "buffer.txt")
        uri = f"file://{buffer_file}"
        self.uri: DocumentUri = uri

        pyproject_file = os.path.join(base_dir, "pyproject.toml")
        if not os.path.exists(pyproject_file):
            with open(pyproject_file, "w") as f:
                f.write("[tool.pyrefly]")

        if source_language and source_language.props.id == "python3":
            self.get_application().create_asyncio_task(start_lsp(self.uri))

        if not os.path.exists(buffer_file):
            with open(buffer_file, "w") as f:
                f.write("")

        with open(buffer_file) as f:
            self.code_view.buffer.props.text = f.read()

    def on_lsp_notification(self, method: str, params) -> None:
        match method:
            case "$/cancelRequest":
                # id
                pass
            case "$/logTrace":
                # message, verbose?
                pass
            case "textDocument/publishDiagnostics":
                self.code_view.apply_diagnostics(params)
                return
            case "$/progress":
                # token, value
                pass
            case "telemetry/event":
                pass
            case "window/showMessage":
                match params["type"]:
                    case MessageType.Error:
                        pass
                    case MessageType.Warning:
                        pass
                    case MessageType.Info:
                        pass
                    case MessageType.Log:
                        pass
                    case MessageType.Debug:
                        pass
                pass
            case "window/logMessage":
                match params["type"]:
                    case MessageType.Error:
                        pass
                    case MessageType.Warning:
                        pass
                    case MessageType.Info:
                        pass
                    case MessageType.Log:
                        pass
                    case MessageType.Debug:
                        pass
                pass
        print("on_lsp_notification:", method, params)

    def on_unrealize(self, window):
        if self.lsp_client:
            asyncio.create_task(self.lsp_client.exit())
        self.save_buffer()

    def save_buffer(self):
        if self.code_view.buffer.get_modified():
            base_dir = os.environ.get("XDG_STATE_HOME", ".pyrose")
            buffer_file = os.path.join(base_dir, "buffer.txt")
            with open(buffer_file, "w") as f:
                f.write(self.code_view.buffer.props.text)
            self.code_view.buffer.set_modified(False)
