"""Écran temporaire « à venir » pour les phases suivantes."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tui import i18n


class PlaceholderScreen(Screen):
    """Affiche un message d'attente avec un bouton de retour."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    def __init__(self, title: str, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold red]METATRON[/]  ·  [cyan]{self._title}[/]", id="ph-title")
        yield Static(self._message, id="ph-msg")
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
