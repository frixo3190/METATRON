"""Écran Historique — liste des sessions avec DataTable."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static
from textual import work

import db
from tui import i18n
from tui.screens.session import SessionDetailScreen


_TOOL_MARKERS = {
    "nmap":    ["NMAP OUTPUT"],
    "whois":   ["WHOIS OUTPUT"],
    "whatweb": ["WHATWEB OUTPUT"],
    "curl":    ["CURL_HEADERS", "CURL HEADERS"],
    "dig":     ["DIG DNS", "DIG OUTPUT"],
    "nikto":   ["NIKTO OUTPUT"],
}


def _detect_tools(raw_scan) -> list:
    """Détecte les outils de recon lancés, à partir du raw_scan enregistré."""
    if not raw_scan:
        return []
    s = str(raw_scan).upper()
    found = []
    for tool, markers in _TOOL_MARKERS.items():
        if any(m in s for m in markers):
            found.append(tool)
    return found


def _tools_markup(tools: list) -> str:
    if not tools:
        return "[dim]—[/]"
    return " ".join(f"[cyan]{t}[/]" for t in tools)


class HistoryScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("r", "reload", description="↻", show=True),
    ]

    class RowsLoaded(Message):
        def __init__(self, rows) -> None:
            self.rows = rows
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('history.title')}[/]",
            id="history-title",
        )
        yield Static("", id="history-status")
        yield DataTable(id="history-table")
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        table = self.query_one("#history-table", DataTable)
        table.cursor_type = "row"
        self.action_reload()

    def action_reload(self) -> None:
        self._reload_worker()

    @work(thread=True)
    def _reload_worker(self) -> None:
        rows = db.get_history_with_scans()
        self.post_message(self.RowsLoaded(rows))

    def on_history_screen_rows_loaded(self, event: RowsLoaded) -> None:
        table = self.query_one("#history-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "SL#",
            i18n.t("history.col.target"),
            i18n.t("history.col.date"),
            i18n.t("history.col.status"),
            i18n.t("history.col.tools"),
        )
        if not event.rows:
            self.query_one("#history-status", Static).update(
                f"[yellow]{i18n.t('history.empty')}[/]"
            )
            return
        for r in event.rows:
            sl, target, date, status = r[0], r[1], str(r[2]), r[3]
            raw_scan = r[4] if len(r) > 4 else None
            tools = _detect_tools(raw_scan)
            table.add_row(
                str(sl),
                str(target or ""),
                date,
                str(status or ""),
                _tools_markup(tools),
                key=str(sl),
            )
        self.query_one("#history-status", Static).update(
            f"[dim]{i18n.t('history.count', n=len(event.rows))}[/]"
        )
        try:
            table.focus()
        except Exception:
            pass

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        sl = int(event.row_key.value)
        self.app.push_screen(SessionDetailScreen(sl))
