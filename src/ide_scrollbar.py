# https://github.com/GNOME/gnome-builder/blob/main/src/libide/editor/ide-scrollbar.c
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gdk, GObject, Graphene, Gtk, GtkSource

SCROLLBAR_H_MARGIN: int = 7
SCROLLBAR_V_MARGIN: int = 6
SLIDER_W: int = 3


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/ide_scrollbar.ui")
class IdeScrollbar(Gtk.Widget):
    __gtype_name__ = "IdeScrollbar"

    scrollbar: Gtk.Scrollbar = Gtk.Template.Child()

    def __init__(
        self,
    ):
        super().__init__()
        self._cursor_color = Gdk.RGBA()
        self._error_color = Gdk.RGBA()
        self._warning_color = Gdk.RGBA()
        self._information_color = Gdk.RGBA()
        self._hint_color = Gdk.RGBA()
        self._chunks = []

        def on_color_scheme_changed(widget, value):
            if widget.get_dark():
                self._cursor_color.parse("#c0bfbc")
                self._error_color.parse("#a51d2d")
                self._warning_color.parse("#e5a50a")
                self._information_color.parse("#1a5fb4")
                self._hint_color.parse("#26a269")
            else:
                self._cursor_color.parse("#5e5c64")
                self._error_color.parse("#E01B24")
                self._warning_color.parse("#F6D32D")
                self._information_color.parse("#3584E4")
                self._hint_color.parse("#33D17A")

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", on_color_scheme_changed)
        style_manager.notify("dark")

    @GObject.Property(type=GtkSource.View, flags=GObject.ParamFlags.READWRITE)
    def view(self) -> GtkSource.View:
        return self._view

    @view.setter
    def view(self, view: GtkSource.View):
        self._buffer = view.get_buffer()
        self._view = view

        v_adjustment = view.get_vadjustment()
        # Trying to snapshot GtkGizmo 0x62c940016f60 without a current allocation
        self.scrollbar.set_adjustment(v_adjustment)

    @Gtk.Template.Callback()
    def on_motion_enter(self, widget: Gtk.EventControllerMotion, x, y):
        self.scrollbar.add_css_class("hovering")

    @Gtk.Template.Callback()
    def on_motion_leave(self, widget: Gtk.EventControllerMotion):
        self.scrollbar.remove_css_class("hovering")

    def update_chunks(self, params) -> None:
        """Update chunks and diagnostics."""
        self._chunks.clear()
        if params:
            for diagnostic in params["diagnostics"]:
                start_line = diagnostic["range"]["start"]["line"]
                end_line = diagnostic["range"]["end"]["line"] + 1
                severity = diagnostic.get("severity", 1)
                self._chunks.append((start_line, end_line, severity))
        self.queue_draw()

    def do_snapshot(self, snapshot):
        total_lines = self._buffer.get_line_count()
        width = self.get_width()
        height = self.get_height()
        vadjustment = self._view.get_vadjustment()
        if vadjustment is None or total_lines == 0:
            return
        view_height = vadjustment.get_upper()
        ratio = height / view_height
        top_margin = ratio * self._view.get_top_margin() + SCROLLBAR_V_MARGIN
        bottom_margin = ratio * self._view.get_bottom_margin() + SCROLLBAR_V_MARGIN
        line_height = (height - top_margin - bottom_margin) / total_lines

        cursor_position = self._buffer.props.cursor_position
        textiter = self._buffer.get_iter_at_offset(cursor_position)
        cursor_line = textiter.get_line()

        if cursor_line >= 0 and cursor_line < total_lines:
            line_height = min(line_height, 18)  # ugh, dirty workaround
            cursor_y = top_margin + cursor_line * line_height
            bounds = Graphene.Rect().init(0, cursor_y, width, max(int(line_height), 2))
            snapshot.append_color(self._cursor_color, bounds)

        for start_line, end_line, chunk_type in self._chunks:
            chunk_start_y = start_line * line_height
            chunk_end_y = end_line * line_height
            self._snapshot_chunk(
                snapshot, chunk_type, chunk_start_y, chunk_end_y, width
            )

        self.snapshot_child(self.scrollbar, snapshot)

    def _snapshot_chunk(
        self, snapshot, chunk_type, start_y: int, end_y: int, width: int
    ):
        match chunk_type:
            case 1:
                color = self._error_color
            case 2:
                color = self._warning_color
            case 3:
                color = self._information_color
            case 4:
                color = self._hint_color
            case _:
                color = None

        if color and end_y > start_y:
            height = max(end_y - start_y, 2)
            chunk_width = min(SCROLLBAR_H_MARGIN, (width - SLIDER_W) / 2)
            bounds = Graphene.Rect().init(
                width - chunk_width, start_y, chunk_width, height
            )
            snapshot.append_color(color, bounds)
