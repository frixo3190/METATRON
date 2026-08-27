"""Écran d'accueil — menu principal (avec l'ange Metatron animé)."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from tui import i18n
from tui.angel import angel_frame
from tui.screens.history import HistoryScreen
from tui.screens.scan import NewScanScreen
from tui.screens.settings import SettingsScreen


class MainMenuScreen(Screen):
    """Menu principal : nouveau scan, historique, paramètres, quitter."""

    BINDINGS = [
        Binding("1", "scan", description=i18n.t("binding.scan"), id="binding.scan", show=True),
        Binding("2", "history", description=i18n.t("binding.history"), id="binding.history", show=True),
        Binding("3", "settings", description=i18n.t("binding.settings"), id="binding.settings", show=True),
        Binding("q", "quit", description=i18n.t("binding.quit"), id="binding.quit", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._frame = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="menu-root"):
            yield Static(angel_frame(0), id="angel", markup=False)
            yield Static(self._banner(), id="banner")
            yield ListView(
                ListItem(Label(i18n.t("menu.scan")), id="m-scan"),
                ListItem(Label(i18n.t("menu.history")), id="m-history"),
                ListItem(Label(i18n.t("menu.settings")), id="m-settings"),
                ListItem(Label(i18n.t("menu.quit")), id="m-quit"),
                id="menu",
            )
        yield Footer()

    def _banner(self) -> str:
        return (
            "[bold red]METATRON[/]\n"
            f"[cyan]{i18n.t('app.subtitle')}[/]\n"
            f"[dim]{i18n.t('menu.tagline')}[/]"
        )

    def on_mount(self) -> None:
        self._localize()
        self.set_interval(0.45, self._animate_angel)

    def _animate_angel(self) -> None:
        self._frame += 1
        try:
            self.query_one("#angel", Static).update(angel_frame(self._frame))
        except Exception:
            pass

    def on_screen_resume(self) -> None:
        self._localize()

    def _localize(self) -> None:
        try:
            self.query_one("#banner", Static).update(self._banner())
        except Exception:
            pass
        for item_id, key in (
            ("m-scan", "menu.scan"),
            ("m-history", "menu.history"),
            ("m-settings", "menu.settings"),
            ("m-quit", "menu.quit"),
        ):
            try:
                self.query_one(f"#{item_id} Label", Label).update(i18n.t(key))
            except Exception:
                pass
        i18n.localize_bindings(self)

    def _go(self, item_id: str) -> None:
        if item_id == "m-scan":
            self.app.push_screen(NewScanScreen())
        elif item_id == "m-history":
            self.app.push_screen(HistoryScreen())
        elif item_id == "m-settings":
            self.app.push_screen(SettingsScreen())
        elif item_id == "m-quit":
            self.app.exit()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._go(event.item.id)

    def action_scan(self) -> None:
        self._go("m-scan")

    def action_history(self) -> None:
        self._go("m-history")

    def action_settings(self) -> None:
        self._go("m-settings")

    def action_quit(self) -> None:
        self.app.exit()
