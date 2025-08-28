import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject  # noqa: E402


@Gtk.Template(resource_path="/io/github/vanillajonathan/pyrose/symbol_chooser.ui")
class SymbolChooser(Gtk.Popover):
    __gtype_name__ = "SymbolChooser"
    __gsignals__ = {
        "symbol-picked": (
            GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION,
            None,
            (str,),
        ),
    }

    symbols: Gtk.FlowBox = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        for symbol in symbols:
            label = Gtk.Label(label=symbol["symbol"], tooltip_text=symbol["desc"])
            self.symbols.append(label)

    @Gtk.Template.Callback()
    def on_symbol_activated(self, flowbox: Gtk.FlowBox, item: Gtk.FlowBoxChild):
        symbol = item.get_child().get_label()
        self.emit("symbol-picked", symbol)
        self.popdown()

    @Gtk.Template.Callback()
    def on_keynav_failed(self, flowbox: Gtk.FlowBox, _):
        pass


symbols = [
    {"symbol": "–", "desc": "En dash (range of values)"},
    {"symbol": "—", "desc": "Em dash (interruption in speech)"},
    {"symbol": "°", "desc": "Degrees"},
    {"symbol": "∑", "desc": "Summation"},
    {"symbol": "≈", "desc": "Approximation"},
    {"symbol": "≠", "desc": "Inequation (not equal)"},
    {"symbol": "≤", "desc": "Less than"},
    {"symbol": "≥", "desc": "Greater than"},
    {"symbol": "±", "desc": "Plus-or-minus"},
    {"symbol": "−", "desc": "Minus"},
    {"symbol": "×", "desc": "Multiplication"},
    {"symbol": "÷", "desc": "Division"},
    {"symbol": "·", "desc": "Interpunct"},
    {"symbol": "∞", "desc": "Infinite"},
    {"symbol": "π", "desc": "Pi"},
    {"symbol": "≔", "desc": "Assignment"},
    # Arrows
    {"symbol": "←", "desc": "Left arrow"},
    {"symbol": "→", "desc": "Right arrow"},
    {"symbol": "↑", "desc": "Up arrow"},
    {"symbol": "↓", "desc": "Down arrow"},
    {"symbol": "↔", "desc": "Left–right arrow"},
    {"symbol": "↕", "desc": "Up–down arrow"},
    # Logical operators
    {"symbol": "∧", "desc": "Logical and"},
    {"symbol": "∨", "desc": "Logical or"},
    {"symbol": "¬", "desc": "Logical not"},
    # Set theory
    {"symbol": "∈", "desc": "Element of"},
    {"symbol": "⊆", "desc": "Subset of"},
    {"symbol": "∪", "desc": "Union"},
    {"symbol": "∩", "desc": "Intersection"},
]
