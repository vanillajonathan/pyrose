import asyncio
import lsp_types as lsp
from .lsp_client import LspClient
from .pango_utils import markdown_to_pango
from gi.repository import GObject, Gtk, GtkSource


class HoverProvider(GObject.GObject, GtkSource.HoverProvider):
    """LSP-powered hover provider for source view.

    Args:
      client: The LSP client.
      uri: The URI for the document being edited.

    Attributes:
      uri: The URI for the document being edited.
    """

    def __init__(self, client: LspClient, uri: lsp.DocumentUri):
        super().__init__()
        self.uri = uri
        self._client = client

    """
    def do_populate_async(
        self,
        context: GtkSource.HoverContext,
        display: GtkSource.HoverDisplay,
        cancellable: Optional[Gio.Cancellable] = None,
        callback: Optional[Callable[..., None]] = None,
        *user_data: Any,
    ) -> None:
        asyncio.create_task(self._hover(context, display))
    """

    def do_populate(self, context, display):
        display.append(Gtk.Label())
        asyncio.create_task(self._hover(context, display))
        return True

    async def _hover(
        self, context: GtkSource.HoverContext, display: GtkSource.HoverDisplay
    ):
        success, hover_iter = context.get_iter()
        if not success:
            return

        params: lsp.HoverParams = {
            "textDocument": {"uri": self.uri},
            "position": {
                "line": hover_iter.get_line(),
                "character": hover_iter.get_line_offset(),
            },
        }
        data = await self._client.requests.hover(params)

        if data is None:
            return

        contents = data["contents"]
        label = Gtk.Label(margin_top=12, margin_start=12, margin_end=12)
        label.set_selectable(True)

        if "kind" in contents and "value" in contents:
            kind = contents["kind"]
            text = contents["value"]
            match kind:
                case lsp.MarkupKind.Markdown:
                    label.set_markup(markdown_to_pango(text))
                case lsp.MarkupKind.PlainText:
                    label.set_text(text)
        else:
            return

        display.prepend(label)
