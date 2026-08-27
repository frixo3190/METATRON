"""METATRON — Textual application shell."""

from textual.app import App

from tui import i18n
from tui.screens.menu import MainMenuScreen


class MetatronApp(App):
    """Application principale du TUI METATRON."""

    TITLE = "METATRON"
    SUB_TITLE = "AI Penetration Testing Assistant"
    CSS_PATH = "styles.tcss"

    def on_mount(self) -> None:
        self.sub_title = i18n.t("app.subtitle")
        self.push_screen(MainMenuScreen())

    def apply_language(self) -> None:
        """Re-applique la langue sélectionnée (titre de l'app)."""
        self.sub_title = i18n.t("app.subtitle")
        self.refresh_bindings()
