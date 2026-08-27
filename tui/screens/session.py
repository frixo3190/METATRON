"""Écran Détail d'une session + export/suppression/relance + chat IA."""

import os

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
)
from textual import work

import db
import export as export_mod
import llm
import logs
from tui import i18n
from tui.screens.chat import ChatScreen

SEV_COLORS = {
    "critical": "red",
    "high": "orange1",
    "medium": "yellow",
    "low": "green",
    "unknown": "grey",
}


def _esc(s) -> str:
    return str(s or "").replace("[", "\\[").replace("]", "\\]")


def _sev_label(sev: str) -> str:
    s = (sev or "unknown").lower()
    key = f"sev.{s}"
    return i18n.t(key) if key in i18n.STRINGS else s.upper()


def _sev_color(sev: str) -> str:
    return SEV_COLORS.get((sev or "unknown").lower(), "grey")


def _vuln_item(v) -> str:
    sev = (v[3] or "unknown").lower()
    lines = [
        f"[bold {_sev_color(sev)}]{_sev_label(sev)}[/]  [bold]{_esc(v[2])}[/]",
        f"[dim]{i18n.t('session.port')}: {_esc(v[4])}    {i18n.t('session.service')}: {_esc(v[5])}[/]",
        _esc(v[6]),
    ]
    return "\n".join(x for x in lines if str(x).strip())


def _fix_item(f) -> str:
    return f"[dim]{i18n.t('session.vuln_id')} #{_esc(f[2])}[/]\n{_esc(f[3])}"


def _exploit_item(e) -> str:
    lines = [
        f"[bold]{_esc(e[2])}[/]  [dim]({_esc(e[3])})[/]",
        f"[dim]{i18n.t('session.result')}: {_esc(e[5])}[/]",
    ]
    if e[4]:
        lines.append(f"[dim]{i18n.t('session.payload')}:[/] {_esc(e[4])}")
    if e[6]:
        lines.append(f"[dim]{i18n.t('session.notes')}:[/] {_esc(e[6])}")
    return "\n".join(lines)


class SessionDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("e", "export", description=i18n.t("binding.export"), id="binding.export", show=True),
        Binding("r", "rerun", description=i18n.t("binding.rerun"), id="binding.rerun", show=True),
        Binding("d", "delete", description=i18n.t("binding.delete"), id="binding.delete", show=True),
    ]

    class ExportDone(Message):
        def __init__(self, paths=None, error=None) -> None:
            self.paths = paths
            self.error = error
            super().__init__()

    def __init__(self, sl_no: int, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sl_no = sl_no
        self.data = None
        self.target = ""
        self._vulns = []
        self._fixes = []
        self._exploits = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="session-header")
        with TabbedContent(
            i18n.t("session.tab.vulns"),
            i18n.t("session.tab.fixes"),
            i18n.t("session.tab.exploits"),
            i18n.t("session.tab.analysis"),
        ):
            yield ListView(id="vulns-list")
            yield ListView(id="fixes-list")
            yield ListView(id="exploits-list")
            yield VerticalScroll(Static("", id="analysis-text", markup=False))
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._load()

    def _load(self) -> None:
        self.data = db.get_session(self.sl_no)
        if not self.data or not self.data.get("history"):
            self.app.notify("Session introuvable.", severity="error")
            self.app.pop_screen()
            return
        self.target = self.data["history"][1]
        self._vulns = self.data["vulns"]
        self._fixes = self.data["fixes"]
        self._exploits = self.data["exploits"]
        self._populate()

    def _populate(self) -> None:
        h = self.data["history"]
        sl, target, date, status = h[0], h[1], str(h[2]), h[3]
        header = f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('session.title', sl=sl, target=target)}[/]"
        s = self.data.get("summary")
        if s:
            header += f"\n[bold]{i18n.t('session.risk')} :[/] [bold red]{_sev_label(s[4])}[/]"
        header += f"\n[dim]{i18n.t('session.select_hint')}[/]"
        self.query_one("#session-header", Static).update(header)

        self._fill_list("vulns-list", "v", self._vulns, _vuln_item)
        self._fill_list("fixes-list", "f", self._fixes, _fix_item)
        self._fill_list("exploits-list", "e", self._exploits, _exploit_item)
        self._render_analysis()

        if self._is_ai_error():
            self.app.notify(i18n.t("session.ai_error"), severity="warning", timeout=8)

    def _fill_list(self, widget_id: str, prefix: str, rows, item_fn) -> None:
        lst = self.query_one(f"#{widget_id}", ListView)
        lst.remove_children()
        if not rows:
            lst.append(ListItem(Static(f"[dim]{i18n.t('session.none')}[/]"), id=f"{prefix}-empty"))
            lst.index = None
            return
        for i, row in enumerate(rows):
            lst.append(ListItem(Static(item_fn(row)), id=f"{prefix}-{i}"))
        lst.index = 0

    def _is_ai_error(self) -> bool:
        s = self.data.get("summary")
        if not s:
            return False
        text = str(s[3] or "").strip()
        if not text:
            return True
        return text.startswith("[!]") or "[!] OpenRouter" in text or "[!] Ollama" in text

    def _render_analysis(self) -> None:
        s = self.data.get("summary")
        if not s:
            self.query_one("#analysis-text", Static).update(i18n.t("session.none"))
            return
        risk = _sev_label(s[4])
        gen = str(s[5] or "")
        text = str(s[3] or "")
        self.query_one("#analysis-text", Static).update(
            f"{i18n.t('session.risk')} : {risk}\n"
            f"{i18n.t('session.generated')} : {gen}\n\n{text}"
        )

    # ── Sélection d'un item → chat IA ──
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        iid = event.item.id
        if not iid or iid.endswith("-empty"):
            return
        prefix, idx = iid.split("-", 1)
        if prefix == "v":
            ctx = self._chat_context("vulnerability", self._vulns[int(idx)])
        elif prefix == "f":
            ctx = self._chat_context("fix", self._fixes[int(idx)])
        elif prefix == "e":
            ctx = self._chat_context("exploit", self._exploits[int(idx)])
        else:
            return
        self.app.push_screen(ChatScreen(self.target, ctx))

    def _chat_context(self, kind: str, row) -> str:
        parts = [f"[{kind}]"]
        if kind == "vulnerability":
            parts.append(f"Nom : {row[2]}")
            parts.append(f"Sévérité : {_sev_label(row[3])}")
            parts.append(f"Port : {row[4]} | Service : {row[5]}")
            if row[6]:
                parts.append(f"Description : {row[6]}")
        elif kind == "fix":
            parts.append(f"Correctif lié à la vulnérabilité #{row[2]}")
            parts.append(f"Contenu : {row[3]}")
        else:
            parts.append(f"Nom : {row[2]}")
            parts.append(f"Outil : {row[3]}")
            if row[4]:
                parts.append(f"Payload : {row[4]}")
            parts.append(f"Résultat : {row[5]}")
            if row[6]:
                parts.append(f"Notes : {row[6]}")
        s = self.data.get("summary")
        if s:
            parts.append(f"Risque global du scan : {_sev_label(s[4])}")
            raw = str(s[2] or "")
            if raw:
                parts.append("Données de scan (extrait) :\n" + raw[:2000])
        return "\n\n".join(parts)

    # ── Actions ──
    def action_export(self) -> None:
        if not self.data:
            return
        self.app.push_screen(ExportScreen(), callback=self._on_export_choice)

    def _on_export_choice(self, fmt) -> None:
        if not fmt:
            return
        self._export_worker(fmt)

    @work(thread=True)
    def _export_worker(self, fmt: str) -> None:
        outdir = os.path.expanduser("~/METATRON/reports")
        os.makedirs(outdir, exist_ok=True)
        try:
            paths = []
            if fmt in ("e-pdf", "e-both"):
                paths.append(export_mod.export_pdf(self.data, outdir))
            if fmt in ("e-html", "e-both"):
                paths.append(export_mod.export_html(self.data, outdir))
            self.post_message(self.ExportDone(paths=paths))
        except Exception as e:
            self.post_message(self.ExportDone(error=str(e)))

    def on_session_detail_screen_export_done(self, event: ExportDone) -> None:
        if event.error:
            self.app.notify(i18n.t("export.failed", e=event.error), severity="error")
        else:
            self.app.notify(i18n.t("export.saved", p=", ".join(event.paths)))

    def action_delete(self) -> None:
        self.app.push_screen(
            ConfirmScreen(i18n.t("delete.confirm", sl=self.sl_no)),
            callback=self._on_delete_confirm,
        )

    def _on_delete_confirm(self, ok: bool) -> None:
        if not ok:
            return
        db.delete_full_session(self.sl_no)
        self.app.notify(i18n.t("delete.done", sl=self.sl_no))
        self.app.pop_screen()

    def action_rerun(self) -> None:
        if not self.data or not self.data.get("summary"):
            self.app.notify(i18n.t("rerun.no_scan"), severity="warning")
            return
        raw_scan = str(self.data["summary"][2] or "")
        if not raw_scan.strip():
            self.app.notify(i18n.t("rerun.no_scan"), severity="warning")
            return
        target = self.data["history"][1]
        self.app.push_screen(
            RunAnalysisScreen(self.sl_no, target, raw_scan),
            callback=self._on_rerun_done,
        )

    def _on_rerun_done(self, ok: bool) -> None:
        if ok:
            self._load()


class ExportScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="export-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('export.title')}[/]", id="export-title")
            yield ListView(
                ListItem(Label(i18n.t("export.pdf")), id="e-pdf"),
                ListItem(Label(i18n.t("export.html")), id="e-html"),
                ListItem(Label(i18n.t("export.both")), id="e-both"),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id)


class ConfirmScreen(ModalScreen):
    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def __init__(self, message: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self._message, id="confirm-msg", markup=False)
            yield ListView(
                ListItem(Label(i18n.t("confirm.yes")), id="c-yes"),
                ListItem(Label(i18n.t("confirm.no")), id="c-no"),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id == "c-yes")


class RunAnalysisScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True)]

    class LogLine(Message):
        def __init__(self, line: str) -> None:
            self.line = line
            super().__init__()

    class Done(Message):
        def __init__(self, ok: bool, risk: str = "") -> None:
            self.ok = ok
            self.risk = risk
            super().__init__()

    def __init__(self, sl_no: int, target: str, raw_scan: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sl_no = sl_no
        self.target = target
        self.raw_scan = raw_scan
        self._lines = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('rerun.title')}[/]", id="run-title")
        yield VerticalScroll(Static("", id="run-log", markup=False))
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._run_worker()

    @work(thread=True)
    def _run_worker(self) -> None:
        logs.set_log(lambda m: self.post_message(self.LogLine(logs.strip_ansi(m))))
        try:
            result = llm.analyse_target(self.target, self.raw_scan)
            self._save(result)
            self.post_message(self.Done(True, result.get("risk_level", "UNKNOWN")))
        except Exception:
            self.post_message(self.Done(False))
        finally:
            logs.set_log(None)

    def _save(self, result: dict) -> None:
        db.clear_session_results(self.sl_no)
        for vuln in result["vulnerabilities"]:
            vid = db.save_vulnerability(
                self.sl_no,
                vuln["vuln_name"],
                vuln["severity"],
                vuln["port"],
                vuln["service"],
                vuln["description"],
                vuln.get("attack", ""),
            )
            if vuln.get("fix"):
                db.save_fix(self.sl_no, vid, vuln["fix"], source="ai")
        for exp in result["exploits"]:
            db.save_exploit(
                self.sl_no,
                exp["exploit_name"],
                exp["tool_used"],
                exp["payload"],
                exp["result"],
                exp["notes"],
            )
        db.save_summary(
            self.sl_no,
            result["raw_scan"],
            result["full_response"],
            result["risk_level"],
        )

    def on_run_analysis_screen_log_line(self, event: LogLine) -> None:
        self._lines.append(event.line)
        self.query_one("#run-log", Static).update("\n".join(self._lines[-60:]))

    def on_run_analysis_screen_done(self, event: Done) -> None:
        if event.ok:
            self.app.notify(i18n.t("rerun.done", sl=self.sl_no, risk=event.risk))
        else:
            self.app.notify(i18n.t("rerun.failed"), severity="error")
        self.dismiss(event.ok)
