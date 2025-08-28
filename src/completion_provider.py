import asyncio
import lsp_types as lsp

from gettext import gettext as _
from gi.repository import Gio, GObject, Gtk, GtkSource
from gi.repository.GtkSource import CompletionActivation
from .lsp_client import LspClient
from .pango_utils import markdown_to_pango


class CompletionProposal(GObject.Object, GtkSource.CompletionProposal):
    def __init__(self, item: lsp.CompletionItem):
        super().__init__()
        self.item = item
        self.label: str = item["label"]
        self.text: str = item["label"]
        self.kind: lsp.CompletionItemKind = item["kind"]
        self.info: str = ""
        self.sort_text = item.get("sortText", self.label)
        self.detail: str | None = item.get("detail")
        self.documentation: str | lsp.MarkupContent | None = item.get("documentation")
        self.label_details: lsp.CompletionItemLabelDetails | None = item.get(
            "labelDetails"
        )

    def is_deprecated(self) -> bool:
        """Whether the completion item is deprecated."""
        if lsp.CompletionItemTag.Deprecated in self.item.get("tags", []):
            return True
        if self.item.get("deprecated"):
            return True
        return False


class FilterData:
    word: str


class CompletionProvider(GObject.GObject, GtkSource.CompletionProvider):
    """LSP-powered completion provider for source view.

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
        self._filter_data: FilterData = FilterData()

    def do_activate(self, context, proposal) -> None:
        buffer = context.get_buffer()
        buffer.begin_user_action()
        has_selection, begin, end = context.get_bounds()
        if has_selection:
            buffer.delete(begin, end)
        buffer.insert(begin, proposal.text, len(proposal.text))
        buffer.end_user_action()

    def do_display(
        self,
        context: GtkSource.CompletionContext,
        proposal: CompletionProposal,
        cell: GtkSource.CompletionCell,
    ) -> None:
        language = ""
        if language := context.get_language():
            language = language.props.id

        if cell.props.column == GtkSource.CompletionColumn.ICON:
            self._set_icon(cell, proposal, language)
        elif cell.props.column == GtkSource.CompletionColumn.BEFORE:
            cell.set_text(self._get_text(proposal.kind))
            pass
        elif cell.props.column == GtkSource.CompletionColumn.TYPED_TEXT:
            if proposal.is_deprecated():
                cell.set_markup(f"<s>{proposal.text}</s>")
            else:
                cell.set_text(proposal.text)
        elif cell.props.column == GtkSource.CompletionColumn.AFTER:
            text = ""
            if proposal.is_deprecated():
                text += _("Deprecated")
            if proposal.label_details:
                if details := proposal.label_details.get("detail"):
                    text += details
                if description := proposal.label_details.get("description"):
                    text += description
            if text:
                cell.set_text(text)
        elif cell.props.column == GtkSource.CompletionColumn.COMMENT:
            if proposal.detail:
                cell.set_markup(f"<tt>{proposal.detail}</tt>")
        elif cell.props.column == GtkSource.CompletionColumn.DETAILS:
            if not proposal.documentation:
                return
            if widget := cell.props.widget:
                widget.set_selectable(True)  # pyrefly: ignore[missing-attribute]
                widget.set_margin_bottom(6)
                widget.set_margin_top(6)
                widget.set_margin_start(6)
                widget.set_margin_end(6)
            if isinstance(proposal.documentation, str):
                cell.set_text(proposal.documentation)
            else:
                match proposal.documentation["kind"]:
                    case lsp.MarkupKind.Markdown:
                        markup = markdown_to_pango(proposal.documentation["value"])
                        cell.set_markup(markup)
                    case lsp.MarkupKind.PlainText:
                        cell.set_text(proposal.documentation["value"])

    def _set_icon(
        self, cell: GtkSource.CompletionCell, proposal, language: str
    ) -> None:
        match proposal.kind:
            case lsp.CompletionItemKind.Text.value:
                css_class = "lang-text"
            case lsp.CompletionItemKind.Method.value:
                css_class = "lang-method"
            case lsp.CompletionItemKind.Function.value:
                css_class = "lang-function"
            case lsp.CompletionItemKind.Constructor.value:
                css_class = "lang-constructor"
            case lsp.CompletionItemKind.File.value:
                css_class = "lang-field"
            case lsp.CompletionItemKind.Variable.value:
                css_class = "lang-variable"
            case lsp.CompletionItemKind.Class.value:
                css_class = "lang-class"
                if proposal.label.endswith("Error"):
                    css_class = "lang-exception"
            case lsp.CompletionItemKind.Interface.value:
                css_class = "lang-interface"
            case lsp.CompletionItemKind.Module.value:
                css_class = "lang-module"
            case lsp.CompletionItemKind.Property.value:
                css_class = "lang-property"
            case lsp.CompletionItemKind.Unit.value:
                css_class = "lang-unit"
            case lsp.CompletionItemKind.Value.value:
                css_class = "lang-value"
            case lsp.CompletionItemKind.Enum.value:
                css_class = "lang-enum"
            case lsp.CompletionItemKind.Keyword.value:
                css_class = "lang-keyword"
            case lsp.CompletionItemKind.Snippet.value:
                css_class = "lang-snippet"
            case lsp.CompletionItemKind.Color.value:
                css_class = "lang-color"
            case lsp.CompletionItemKind.File.value:
                css_class = "lang-file"
            case lsp.CompletionItemKind.Reference.value:
                css_class = "lang-reference"
            case lsp.CompletionItemKind.Folder.value:
                css_class = "lang-folder"
            case lsp.CompletionItemKind.EnumMember.value:
                css_class = "lang-enum-member"
            case lsp.CompletionItemKind.Constant.value:
                css_class = "lang-constant"
            case lsp.CompletionItemKind.Struct.value:
                css_class = "lang-struct"
            case lsp.CompletionItemKind.Event.value:
                css_class = "lang-event"
            case lsp.CompletionItemKind.Operator.value:
                css_class = "lang-operator"
            case lsp.CompletionItemKind.TypeParameter.value:
                css_class = "lang-type-parameter"
            case _:
                css_class = ""

        cell.set_css_classes(["cell", "icon", css_class])
        cell.set_icon_name("circle-outline-thick-symbolic")

    def _get_text(self, kind: int) -> str:
        match kind:
            case lsp.CompletionItemKind.Text.value:
                return "Text"
            case lsp.CompletionItemKind.Method.value:
                return "Method"
            case lsp.CompletionItemKind.Function.value:
                return "Function"
            case lsp.CompletionItemKind.Constructor.value:
                return "Constructor"
            case lsp.CompletionItemKind.Field.value:
                return "Field"
            case lsp.CompletionItemKind.Variable.value:
                return "Variable"
            case lsp.CompletionItemKind.Class.value:
                return "Class"
            case lsp.CompletionItemKind.Interface.value:
                return "Interface"
            case lsp.CompletionItemKind.Module.value:
                return "Module"
            case lsp.CompletionItemKind.Property.value:
                return "Property"
            case lsp.CompletionItemKind.Unit.value:
                return "Unit"
            case lsp.CompletionItemKind.Value.value:
                return "Value"
            case lsp.CompletionItemKind.Enum.value:
                return "Enum"
            case lsp.CompletionItemKind.Keyword.value:
                return "Keyword"
            case lsp.CompletionItemKind.Snippet.value:
                return "Snippet"
            case lsp.CompletionItemKind.Color.value:
                return "Color"
            case lsp.CompletionItemKind.File.value:
                return "File"
            case lsp.CompletionItemKind.Reference.value:
                return "Reference"
            case lsp.CompletionItemKind.Folder.value:
                return "Folder"
            case lsp.CompletionItemKind.EnumMember.value:
                return "EnumMember"
            case lsp.CompletionItemKind.Constant.value:
                return "Constant"
            case lsp.CompletionItemKind.Struct.value:
                return "Struct"
            case lsp.CompletionItemKind.Event.value:
                return "Event"
            case lsp.CompletionItemKind.Operator.value:
                return "Operator"
            case lsp.CompletionItemKind.TypeParameter.value:
                return "TypeParameter"
            case _:
                return ""

    def do_is_trigger(self, text_iter: Gtk.TextIter, ch: str) -> bool:
        if ch != "." and ch != "(":
            return False
        success = text_iter.backward_char()
        if not success:
            return False
        return text_iter.ends_word()

    def do_populate_async(self, context, cancellable, callback, user_data=None) -> None:
        asyncio.create_task(self._complete(context))

    async def _complete(self, context: GtkSource.CompletionContext):
        store = Gio.ListStore.new(CompletionProposal)
        self._filter_data.word = context.get_word()

        buffer = context.get_buffer()
        if not buffer:
            return
        insert_mark = buffer.get_insert()
        cursor_iter = buffer.get_iter_at_mark(insert_mark)
        line = cursor_iter.get_line()
        column = cursor_iter.get_line_offset()

        params: lsp.CompletionParams = {
            "textDocument": {"uri": self.uri},
            "position": {"line": line, "character": column},
        }

        activation = context.get_activation()
        if activation == CompletionActivation.INTERACTIVE:
            success, begin, end = context.get_bounds()
            if success and end.backward_char():
                ch = end.get_char()
                if ch == "." or ch == "(":
                    params["context"] = {
                        "triggerKind": lsp.CompletionTriggerKind.TriggerCharacter,
                        "triggerCharacter": ch,
                    }
                else:
                    params["context"] = {
                        "triggerKind": lsp.CompletionTriggerKind.Invoked
                    }
        elif activation == CompletionActivation.USER_REQUESTED:
            params["context"] = {"triggerKind": lsp.CompletionTriggerKind.Invoked}

        result = await self._client.requests.completion(params)
        if result is None:
            return
        elif isinstance(result, list):
            items: list[lsp.CompletionItem] = result
        else:
            items: list[lsp.CompletionItem] = result["items"]

        for item in items:
            proposal = CompletionProposal(item)
            store.append(proposal)

        def filter_fn(proposal, data) -> bool:
            return proposal.text.startswith(data.word)

        store_filter = Gtk.CustomFilter.new(filter_fn, self._filter_data)
        proposals = Gtk.FilterListModel.new(store, store_filter)
        context.set_proposals_for_provider(self, proposals)

    def do_refilter(self, context: GtkSource.CompletionContext, model) -> None:
        word = context.get_word()
        old_word = self._filter_data.word
        change = Gtk.FilterChange.DIFFERENT
        if old_word and word.startswith(old_word):
            change = Gtk.FilterChange.MORE_STRICT
        elif old_word and old_word.startswith(word):
            change = Gtk.FilterChange.LESS_STRICT
        self._filter_data.word = word
        model.get_filter().changed(change)
