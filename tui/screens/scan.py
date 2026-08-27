"""Écrans de scan — formulaire + exécution plein écran + discussion IA."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, ProgressBar, RichLog, SelectionList, Static
from textual import work

import db
import llm
import logs
import tools
from tui import i18n
from tui.screens.chat import ChatScreen
from tui.screens.session import AttackScreen, SessionDetailScreen, _attack_commands


TOOL_FUNCS = {
    "nmap": tools.run_nmap,
    "whois": tools.run_whois,
    "whatweb": tools.run_whatweb,
    "curl": tools.run_curl_headers,
    "dig": tools.run_dig,
    "nikto": tools.run_nikto,
}

_SEV_COLORS = {"CRITICAL": "red", "HIGH": "orange1", "MEDIUM": "yellow", "LOW": "green"}


def _log_markup(line: str) -> str:
    """Colore une ligne du journal de scan (outils, tours, sévérités, risque)."""
    esc = str(line).replace("[", "\\[").replace("]", "\\]")
    up = line.strip().upper()
    if "TOUR" in up and ("ANALYSE" in up or "/" in up):
        return f"[bold yellow]{esc}[/]"
    if "ANALYSE FINALE" in up or "PLUS AUCUN OUTIL" in up:
        return f"[bold green]{esc}[/]"
    if line.strip().startswith("▸"):
        return f"[bold cyan]{esc}[/]"
    for sev, color in _SEV_COLORS.items():
        if f"SEVERITY: {sev}" in up or f"SEVERITY:{sev}" in up:
            return f"[bold {color}]{esc}[/]"
    if up.startswith("RISK_LEVEL:"):
        for sev, color in _SEV_COLORS.items():
            if sev in up:
                return f"[bold {color}]{esc}[/]"
    if up.startswith(("VULN:", "EXPLOIT:", "ATTACK:", "ATTACK_CMDS:")):
        return f"[bold cyan]{esc}[/]"
    if up.startswith(("DESC:", "FIX:", "RESULT:", "NOTES:")):
        return f"[dim]{esc}[/]"
    return esc


class NewScanScreen(Screen):
    """Formulaire : cible + choix des outils."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("ctrl+r", "run", description=i18n.t("binding.scan_run"), id="binding.scan_run", show=True),
    ]

    def __init__(self, target: str = "", preselected: list | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial_target = target
        self._preselected = preselected or []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('scan.title')}[/]", id="scan-title")
        yield Input(placeholder=i18n.t("scan.target.placeholder"), id="scan-target")
        yield Static(f"[bold]{i18n.t('scan.tools')}[/]", id="scan-tools-label")
        yield SelectionList(
            (i18n.t("tool.nmap"), "nmap"),
            (i18n.t("tool.whois"), "whois"),
            (i18n.t("tool.whatweb"), "whatweb"),
            (i18n.t("tool.curl"), "curl"),
            (i18n.t("tool.dig"), "dig"),
            (i18n.t("tool.nikto"), "nikto"),
            id="scan-tools",
        )
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        if self._initial_target:
            self.query_one("#scan-target", Input).value = self._initial_target
        if self._preselected:
            sel = self.query_one("#scan-tools", SelectionList)
            for v in self._preselected:
                try:
                    sel.select(v)
                except Exception:
                    pass
        self.query_one("#scan-target", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_run()

    def action_run(self) -> None:
        target = self.query_one("#scan-target", Input).value.strip()
        if not target:
            self.app.notify(i18n.t("scan.no_target"), severity="warning")
            return
        selected = list(self.query_one("#scan-tools", SelectionList).selected)
        if not selected:
            self.app.notify(i18n.t("scan.no_tools"), severity="warning")
            return
        sl_no = db.create_session(target)
        self.app.switch_screen(ScanRunScreen(sl_no, target, selected))


class ScanRunScreen(Screen):
    """Exécution plein écran : log uniquement, puis chat / session."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("c", "chat", description=i18n.t("binding.chat"), id="binding.chat", show=True),
        Binding("s", "session", description=i18n.t("binding.session"), id="binding.session", show=True),
        Binding("a", "attack", description=i18n.t("binding.attack"), id="binding.attack", show=False),
    ]

    class LogLine(Message):
        def __init__(self, line: str) -> None:
            self.line = line
            super().__init__()

    class Done(Message):
        def __init__(self, risk: str) -> None:
            self.risk = risk
            super().__init__()

    def __init__(self, sl_no: int, target: str, selected: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sl_no = sl_no
        self.target = target
        self.selected = selected
        self._done = False
        self._result = None
        self._first_attack = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('scan.running')}[/]  ·  [dim]{self.target}[/]",
            id="run-title",
        )
        yield ProgressBar(show_percentage=False, id="run-progress")
        yield RichLog(id="run-log", markup=True, wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._run_worker()

    @work(thread=True)
    def _run_worker(self) -> None:
        logs.set_log(lambda m: self.post_message(self.LogLine(logs.strip_ansi(m))))
        try:
            results = {}
            for key in self.selected:
                fn = TOOL_FUNCS.get(key)
                if not fn:
                    continue
                self.post_message(self.LogLine(f"▸ {key}"))
                results[key] = fn(self.target)
            raw_scan = tools.format_recon_for_llm(results)
            self.post_message(self.LogLine(i18n.t("scan.tours.explain")))
            self.post_message(self.LogLine(i18n.t("scan.analyzing")))
            result = llm.analyse_target(self.target, raw_scan)
            self._result = result
            self._save(result)
            self.post_message(self.Done(result.get("risk_level", "UNKNOWN")))
        except Exception as e:
            self.post_message(self.LogLine(f"[!] {e}"))
            self.post_message(self.Done("UNKNOWN"))
        finally:
            logs.set_log(None)

    def _save(self, result: dict) -> None:
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

    def on_scan_run_screen_log_line(self, event: LogLine) -> None:
        self.query_one("#run-log", RichLog).write(_log_markup(event.line))

    def on_scan_run_screen_done(self, event: Done) -> None:
        self._done = True
        try:
            self.query_one("#run-progress", ProgressBar).display = False
        except Exception:
            pass
        self.app.notify(i18n.t("scan.done", sl=self.sl_no, risk=event.risk))
        # si une attaque est disponible, on propose le raccourci « a »
        self._first_attack = self._find_first_attack()
        self._set_attack_visible(bool(self._first_attack))
        self.query_one("#run-title", Static).update(
            f"[bold red]METATRON[/]  ·  [cyan]{self.target}[/]  ·  [bold green]{event.risk}[/]\n"
            f"[dim]{i18n.t('scan.finished')}[/]"
        )

    def _find_first_attack(self) -> str:
        if not self._result:
            return ""
        for v in self._result.get("vulnerabilities", []):
            attack = v.get("attack", "")
            cmds = _attack_commands(attack)
            if cmds.strip():
                return cmds
        return ""

    def _set_attack_visible(self, visible: bool) -> None:
        try:
            i18n.localize_bindings(self, show_overrides={"binding.attack": visible})
        except Exception:
            pass

    def action_attack(self) -> None:
        if not self._done or not self._first_attack:
            self.app.notify(i18n.t("attack.no_commands"), severity="warning")
            return
        self.app.push_screen(AttackScreen(self.target, self._first_attack))

    def _chat_context(self) -> str:
        r = self._result or {}
        parts = [
            f"CIBLE : {self.target}",
            f"Risque global : {r.get('risk_level', 'UNKNOWN')}",
        ]
        if r.get("summary"):
            parts.append(f"Résumé : {r.get('summary')}")
        if r.get("full_response"):
            parts.append("Analyse complète :\n" + r.get("full_response", ""))
        return "\n\n".join(parts)

    def action_chat(self) -> None:
        if not self._done:
            self.app.notify(i18n.t("scan.not_done"), severity="warning")
            return
        self.app.push_screen(
            ChatScreen(self.target, self._chat_context(), chat_key=f"scan:{self.sl_no}")
        )

    def action_session(self) -> None:
        if not self._done:
            self.app.notify(i18n.t("scan.not_done"), severity="warning")
            return
        self.app.switch_screen(SessionDetailScreen(self.sl_no))
