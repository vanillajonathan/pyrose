import asyncio
import os
import gi

from asyncio import Task
from lsp_types import (
    DiagnosticSeverity,
    DiagnosticTag,
    DocumentHighlight,
    PublishDiagnosticsParams,
)
from .symbol_chooser import SymbolChooser

gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Adw, Gdk, Gio, GObject, Gtk, GtkSource  # noqa: E402


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/code_view.ui")
class CodeView(Gtk.Widget):
    __gtype_name__ = "CodeView"

    buffer: GtkSource.Buffer = Gtk.Template.Child()
    sourceview: GtkSource.View = Gtk.Template.Child()
    symbol_chooser: SymbolChooser = Gtk.Template.Child()
    position_label: Gtk.Label = Gtk.Template.Child()
    error_tag: Gtk.TextTag = Gtk.Template.Child()
    goto_line_entry: Gtk.Entry = Gtk.Template.Child()
    goto_line_revealer: Gtk.Revealer = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    search_revealer: Gtk.Revealer = Gtk.Template.Child()
    replace_entry: Gtk.SearchEntry = Gtk.Template.Child()
    replace_button: Gtk.Button = Gtk.Template.Child()
    replace_all_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        GObject.type_ensure(SymbolChooser)
        self.animate_fade_task: Task | None = None
        self.languages = []
        self.search_context: GtkSource.SearchContext | None = None
        self.search_settings = GtkSource.SearchSettings()

        actions = (
            ("goto-line", self.goto_line),
            ("show-goto-line", self.reveal_goto),
            ("show-search", self.reveal_search),
            ("show-replace", self.reveal_replace),
            ("search-prev", self.search_prev),
            ("search-next", self.search_next),
            ("search-hide", self.search_hide),
        )

        action_group = Gio.SimpleActionGroup()
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        action_group.lookup_action("search-next").set_enabled(False)
        action_group.lookup_action("search-prev").set_enabled(False)
        self.action_group = action_group

        Adw.StyleManager.get_default().bind_property(
            "dark",
            self.buffer,
            "style-scheme",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _, is_dark: self.buffer.set_style_scheme(
                GtkSource.StyleSchemeManager.get_default().get_scheme(
                    "Adwaita-dark" if is_dark else "Adwaita"
                )
            ),
        )

        self.sourceview.install_action("misc.insert-symbol", None, self.insert_symbol)
        self.sourceview.get_extra_menu().insert(  # pyrefly: ignore[missing-attribute]
            0, "Insert Symbol", "misc.insert-symbol"
        )

        self.install_property_action("search-options.regex", "regex_enabled")
        self.install_property_action("search-options.case-sensitive", "case_sensitive")
        self.install_property_action(
            "search-options.match-whole-word", "match_whole_word"
        )
        self.install_property_action("search.replace-mode", "replace_mode")

        self.install_action("search.replace-one", None, self.replace_one)
        self.install_action("search.replace-all", None, self.replace_all)

    @GObject.Property(type=bool, default=False)
    def regex_enabled(self) -> bool:
        return self._regex_enabled

    @regex_enabled.setter
    def regex_enabled(self, enabled):
        self.search_settings.set_regex_enabled(enabled)
        self._regex_enabled = enabled

    @GObject.Property(type=bool, default=False)
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    @case_sensitive.setter
    def case_sensitive(self, enabled):
        self.search_settings.set_case_sensitive(enabled)
        self._case_sensitive = enabled

    @GObject.Property(type=bool, default=False)
    def match_whole_word(self) -> bool:
        return self._match_whole_word

    @match_whole_word.setter
    def match_whole_word(self, enabled):
        self.search_settings.set_at_word_boundaries(enabled)
        self._match_whole_word = enabled

    @GObject.Property(type=bool, default=False)
    def replace_mode(self) -> bool:
        return self._replace_mode

    @replace_mode.setter
    def replace_mode(self, enabled):
        self.replace_entry.set_visible(enabled)
        self.replace_button.set_visible(enabled)
        self.replace_all_button.set_visible(enabled)
        self._replace_mode = enabled
        if enabled:
            self.replace_entry.grab_focus()

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(GtkSource.Buffer,))
    def changed(self, buffer: GtkSource.Buffer):
        """Called every time the changed signal is emitted."""
        pass

    @GObject.Signal(flags=GObject.SignalFlags.RUN_LAST, arg_types=(GtkSource.Buffer,))
    def cursor_moved(self, buffer: GtkSource.Buffer):
        """Called every time the cursor-moved signal is emitted."""
        pass

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST, arg_types=(Gtk.DropTarget, Gio.File)
    )
    def drop(self, target: Gtk.DropTarget, value: Gio.File):
        """Called every time the drop signal is emitted."""
        pass

    @Gtk.Template.Callback()
    def on_droptarget_drop(
        self, target: Gtk.DropTarget, value, _x: float, _y: float
    ) -> bool:
        def is_extension_supported(extension):
            for item in self.languages:
                if item[2] == extension:
                    return True

        extension = os.path.splitext(value.get_basename())[1]
        if is_extension_supported(extension):
            self._set_file(value)
            return True
        dialog = Adw.AlertDialog(
            heading="Unsupported file type",
            body="The file type is not supported by PyRose.",
        )
        dialog.add_response("", "Okay")
        dialog.choose(self)
        return False

    def _set_file(self, file) -> None:
        def get_language_id(extension):
            for item in self.languages:
                if item[2] == extension:
                    return item[1]
            return ""

        with open(file) as f:
            extension = os.path.splitext(f.name)[1]
            language_id = get_language_id(extension)
            language_manager = GtkSource.LanguageManager.get_default()
            language = language_manager.get_language(language_id)
            self.buffer.set_language(language)
            self.buffer.props.text = f.read()

    @Gtk.Template.Callback()
    def on_editor_changed(self, buffer: GtkSource.Buffer):
        self.emit("changed", buffer)

    @Gtk.Template.Callback()
    def on_editor_cursor_moved(self, buffer: GtkSource.Buffer):
        insert_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(insert_mark)
        line = cursor_iter.get_line()
        column = cursor_iter.get_line_offset()
        self.position_label.set_label(f"Ln {line + 1}, Col {column + 1}")

        async def animate_fade():
            self.position_label.get_style_context().add_class("visible")
            await asyncio.sleep(2)
            self.position_label.get_style_context().remove_class("visible")

        if self.animate_fade_task is not None:
            self.animate_fade_task.cancel()
        self.animate_fade_task = asyncio.create_task(animate_fade())
        self.emit("cursor-moved", buffer)

    @Gtk.Template.Callback()
    def on_gestureclick_pressed(self, gesture, n_press: int, x: float, y: float):
        x, y = self.sourceview.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(x), int(y)
        )
        textiter = self.sourceview.get_line_at_y(y)[0]
        textiter.forward_to_line_end()
        self.buffer.place_cursor(textiter)

    @Gtk.Template.Callback()
    def on_goto_line_entry_activate(self, entry: Gtk.Entry):
        self.goto_line(None, None)

    @Gtk.Template.Callback()
    def on_search_entry_activate(self, entry: Gtk.Entry):
        if entry.get_text():
            self.search_next(None, None)
        self.search_revealer.set_reveal_child(False)
        self.sourceview.grab_focus()

    @Gtk.Template.Callback()
    def on_search_entry_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Up or keyval == Gdk.KEY_KP_Up:
            self.activate_action("editor.search-prev", None)
            return True
        if keyval == Gdk.KEY_Down or keyval == Gdk.KEY_KP_Down:
            self.activate_action("editor.search-next", None)
            return True
        return False

    @Gtk.Template.Callback()
    def on_search_changed(self, entry: Gtk.SearchEntry):
        text = entry.get_text()
        self.search_settings.set_search_text(text)
        self.search_settings.set_wrap_around(True)
        self.search_context = GtkSource.SearchContext.new(
            self.buffer, self.search_settings
        )
        self.search_context.forward(self.buffer.get_start_iter())
        if self.search_context.get_occurrences_count() == -1:
            self.action_group.lookup_action("search-prev").set_enabled(False)
            self.action_group.lookup_action("search-next").set_enabled(False)
        elif self.search_context.get_occurrences_count() == 0:
            self.search_entry.get_style_context().add_class("error")
            self.action_group.lookup_action("search-prev").set_enabled(False)
            self.action_group.lookup_action("search-next").set_enabled(False)
        else:
            self.search_entry.get_style_context().remove_class("error")
            self.action_group.lookup_action("search-prev").set_enabled(True)
            self.action_group.lookup_action("search-next").set_enabled(True)
            cursor_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            found, start_iter, end_iter, wrapped = self.search_context.forward(
                cursor_iter
            )
            if found:
                self.buffer.select_range(start_iter, end_iter)
                self.sourceview.scroll_to_iter(start_iter, 0.0, False, 0.0, 0.0)

    @Gtk.Template.Callback()
    def on_symbol_picked(self, widget: SymbolChooser, text: str):
        self.buffer.insert_at_cursor(text)

    def apply_diagnostics(self, params: PublishDiagnosticsParams) -> None:
        self.clear_diagnostics()
        for diagnostic in params["diagnostics"]:
            start_line = diagnostic["range"]["start"]["line"]
            start_char = diagnostic["range"]["start"]["character"]
            end_line = diagnostic["range"]["end"]["line"]
            end_char = diagnostic["range"]["end"]["character"]
            found_start, start_iter = self.buffer.get_iter_at_line_offset(
                start_line, start_char
            )
            found_end, end_iter = self.buffer.get_iter_at_line_offset(
                end_line, end_char
            )
            if not found_start or not found_end:
                continue

            match diagnostic.get("severity", DiagnosticSeverity.Error):
                case DiagnosticSeverity.Error:
                    text_tag = "error"
                case DiagnosticSeverity.Warning:
                    text_tag = "warning"
                case DiagnosticSeverity.Information:
                    text_tag = "information"
                case DiagnosticSeverity.Hint:
                    text_tag = "hint"

            self.buffer.apply_tag_by_name(text_tag, start_iter, end_iter)

            tags = diagnostic.get("tags", [])
            for tag in tags:
                match tag:
                    case DiagnosticTag.Unnecessary:
                        pass
                    case DiagnosticTag.Deprecated:
                        self.buffer.apply_tag_by_name(
                            "deprecated", start_iter, end_iter
                        )

    def clear_diagnostics(self) -> None:
        tags = ["error", "warning", "information", "hint", "deprecated"]
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        for tag in tags:
            self.buffer.remove_tag_by_name(tag, start_iter, end_iter)

    def highlight(self, highlights: list[DocumentHighlight] | None) -> None:
        start_iter = self.buffer.get_start_iter()
        end_iter = self.buffer.get_end_iter()
        self.buffer.remove_tag_by_name("highlight", start_iter, end_iter)
        if not highlights:
            return
        for highlight in highlights:
            start_line = highlight["range"]["start"]["line"]
            start_char = highlight["range"]["start"]["character"]
            end_line = highlight["range"]["end"]["line"]
            end_char = highlight["range"]["end"]["character"]
            found_start, start_iter = self.buffer.get_iter_at_line_offset(
                start_line, start_char
            )
            found_end, end_iter = self.buffer.get_iter_at_line_offset(
                end_line, end_char
            )
            if not found_start or not found_end:
                continue

            self.buffer.apply_tag_by_name("highlight", start_iter, end_iter)

    def goto_line(self, action, parameter):
        line, column = 0, 0
        try:
            line, column = self.goto_line_entry.get_text().split(":")
        except ValueError:
            line = self.goto_line_entry.get_text()
        line = int(line)
        column = int(column)
        found, textiter = self.buffer.get_iter_at_line(line - 1)
        if found:
            if column and textiter.get_chars_in_line() > column:
                textiter.set_line_offset(column)
            self.buffer.place_cursor(textiter)
            self.sourceview.scroll_to_iter(textiter, 0, True, 0.5, 0.5)
            self.goto_line_revealer.set_reveal_child(False)
            self.sourceview.grab_focus()

    def reveal_goto(self, action, parameter):
        self.search_revealer.set_reveal_child(False)
        self.goto_line_revealer.set_reveal_child(True)
        self.goto_line_entry.grab_focus()

    def reveal_search(self, action, parameter):
        self.goto_line_revealer.set_reveal_child(False)
        self.search_revealer.set_reveal_child(True)
        self.on_search_changed(self.search_entry)
        self.search_entry.grab_focus()

    def reveal_replace(self, action, parameter):
        self.replace_mode = True
        self.reveal_search(action, parameter)

    def search_hide(self, action, parameter):
        self.replace_mode = False
        self.search_settings.set_search_text(None)
        self.search_revealer.set_reveal_child(False)
        self.sourceview.grab_focus()

    def search_prev(self, action, parameter):
        if not self.search_context:
            return
        current_pos_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        match, start, end, wrapped = self.search_context.backward(current_pos_iter)
        if match:
            self.buffer.select_range(start, end)
            self.buffer.place_cursor(start)
            self.sourceview.scroll_to_iter(start, 0.1, False, 0, 0)

    def search_next(self, action, parameter):
        if not self.search_context:
            return
        current_pos_iter = self.buffer.get_iter_at_mark(self.buffer.get_insert())
        match, start, end, wrapped = self.search_context.forward(current_pos_iter)
        if match:
            self.buffer.select_range(start, end)
            self.buffer.place_cursor(end)
            self.sourceview.scroll_to_iter(start, 0.1, False, 0, 0)

    def replace_one(self, widget, action: str, parameter):
        bounds = self.buffer.get_selection_bounds()
        if bounds:
            start_iter, end_iter = bounds
            text = self.replace_entry.get_text()
            self.search_context.replace(start_iter, end_iter, text, -1)

    def replace_all(self, widget, action: str, parameter):
        text = self.replace_entry.get_text()
        self.search_context.replace_all(text, -1)

    def insert_symbol(self, view, action, parameter):
        insert_mark = self.buffer.get_insert()
        cursor_iter = self.buffer.get_iter_at_mark(insert_mark)
        rect = view.get_iter_location(cursor_iter)
        x, y = view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET, rect.x, rect.y)
        y, height = view.get_line_yrange(cursor_iter)
        rect = Gdk.Rectangle()
        rect.x, rect.y = x, y + height
        self.symbol_chooser.set_pointing_to(rect)
        self.symbol_chooser.popup()
