"""Écran Détail d'une session + chat IA + test d'attaque + export/suppression."""

import os
import subprocess

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
    Log,
    Static,
    TabbedContent,
    TextArea,
)
from textual import work

import db
import export as export_mod
import llm
import logs
import tools
from tui import i18n
from tui.screens.chat import ChatScreen
from tui.screens.edit import EditItemScreen

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


def _vuln_group_item(v, fixes) -> str:
    sev = (v[3] or "unknown").lower()
    color = _sev_color(sev)
    lines = [
        f"[bold {color}]▌ {_sev_label(sev)}[/] [bold]{_esc(v[2])}[/]",
        f"[dim]{i18n.t('session.port')}: {_esc(v[4])}    {i18n.t('session.service')}: {_esc(v[5])}[/]",
    ]
    if v[6]:
        lines.append(_esc(v[6]))
    if fixes:
        lines.append(f"[bold {color}]▸ {i18n.t('session.tab.fixes')}[/]")
        for f in fixes:
            lines.append(f"    • {_esc(f)}")
    if len(v) > 7 and v[7]:
        lines.append(f"[bold {color}]▸ {i18n.t('session.attack')}[/]")
        lines.append(_esc(v[7]))
    return "\n".join(x for x in lines if str(x).strip())


def _attack_commands(attack_text: str) -> str:
    """Extrait les commandes d'un bloc ATTACK pour l'éditeur."""
    cmds = []
    in_cmds = False
    for line in str(attack_text or "").splitlines():
        s = line.strip()
        if s.startswith("ATTACK_CMDS:"):
            in_cmds = True
            continue
        if not in_cmds:
            continue
        if not s:
            continue
        if s.startswith(("ATTACK:", "VULN:", "EXPLOIT:", "RISK_LEVEL:", "SUMMARY:")):
            break
        cmds.append(s)
    return "\n".join(cmds)


def _colorize_analysis(text: str) -> str:
    """Colore les lignes de l'analyse IA (sévérités, risque, en-têtes)."""
    out = []
    for line in str(text or "").splitlines():
        esc = _esc(line)
        up = line.strip().upper()
        colored = False
        for sev, color in SEV_COLORS.items():
            if f"SEVERITY: {sev.upper()}" in up or f"SEVERITY:{sev.upper()}" in up:
                out.append(f"[bold {color}]{esc}[/]")
                colored = True
                break
        if colored:
            continue
        if up.startswith("RISK_LEVEL:"):
            for sev, color in SEV_COLORS.items():
                if sev.upper() in up:
                    out.append(f"[bold {color}]{esc}[/]")
                    colored = True
                    break
        if colored:
            continue
        if up.startswith(("VULN:", "EXPLOIT:", "ATTACK:", "ATTACK_CMDS:")):
            out.append(f"[bold cyan]{esc}[/]")
        elif up.startswith(("DESC:", "FIX:", "RESULT:", "NOTES:")):
            out.append(f"[dim]{esc}[/]")
        else:
            out.append(esc)
    return "\n".join(out)


class SessionDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("e", "export", description=i18n.t("binding.export"), id="binding.export", show=True),
        Binding("r", "rerun", description=i18n.t("binding.rerun"), id="binding.rerun", show=True),
        Binding("a", "attack", description=i18n.t("binding.attack"), id="binding.attack", show=False),
        Binding("x", "edit", description=i18n.t("binding.edit"), id="binding.edit", show=True),
        Binding("d", "delete", description=i18n.t("binding.delete"), id="binding.delete", show=True),
        Binding("left", "prev_tab", show=False),
        Binding("right", "next_tab", show=False),
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
        self._fixes_by_vuln = {}
        self._exploits = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="session-header")
        with TabbedContent(
            i18n.t("session.tab.vulns"),
            i18n.t("session.tab.exploits"),
            i18n.t("session.tab.analysis"),
        ):
            yield ListView(id="vulns-list")
            yield ListView(id="exploits-list")
            yield VerticalScroll(Static("", id="analysis-text"))
        yield Footer()

    async def on_mount(self) -> None:
        i18n.localize_bindings(self)
        await self._load()

    def on_tabbed_content_tab_activated(self, event) -> None:
        """Donne le focus à la liste du nouvel onglet (navigation clavier)."""
        self._focus_active_list()

    def action_prev_tab(self) -> None:
        self._switch_tab(-1)

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def _switch_tab(self, direction: int) -> None:
        try:
            tc = self.query_one(TabbedContent)
            ids = [f"tab-{i + 1}" for i in range(tc.tab_count)]
            current = tc.active if tc.active in ids else ids[0]
            new_idx = (ids.index(current) + direction) % len(ids)
            tc.active = ids[new_idx]
            self._focus_active_list()
        except Exception:
            pass

    def _focus_active_list(self) -> None:
        try:
            pane = self.query_one(TabbedContent).active_pane
            for w in pane.query(ListView):
                w.focus()
                return
            for w in pane.query(VerticalScroll):
                w.focus()
                return
        except Exception:
            pass

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        self._update_attack_binding()

    def _update_attack_binding(self) -> None:
        """Affiche le raccourci « attaquer » seulement si la vuln a des commandes."""
        show = False
        try:
            vl = self.query_one("#vulns-list", ListView)
            if vl.display and vl.index is not None and vl.index < len(self._vulns):
                v = self._vulns[vl.index]
                show = bool((v[7] if len(v) > 7 else "") and _attack_commands(v[7]).strip())
        except Exception:
            pass
        try:
            i18n.localize_bindings(self, show_overrides={"binding.attack": show})
        except Exception:
            pass

    async def _load(self) -> None:
        self.data = db.get_session(self.sl_no)
        if not self.data or not self.data.get("history"):
            self.app.notify("Session introuvable.", severity="error")
            self.app.pop_screen()
            return
        self.target = self.data["history"][1]
        self._vulns = self.data["vulns"]
        self._exploits = self.data["exploits"]
        self._fixes_by_vuln = {}
        for f in self.data["fixes"]:
            self._fixes_by_vuln.setdefault(f[2], []).append(f[3])
        await self._populate()

    async def _populate(self) -> None:
        h = self.data["history"]
        sl, target, date, status = h[0], h[1], str(h[2]), h[3]
        header = f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('session.title', sl=sl, target=target)}[/]"
        s = self.data.get("summary")
        if s:
            header += f"\n[bold]{i18n.t('session.risk')} :[/] [bold red]{_sev_label(s[4])}[/]"
        header += f"\n[dim]{i18n.t('session.select_hint')}[/]"
        self.query_one("#session-header", Static).update(header)

        await self._fill_vulns()
        await self._fill_exploits()
        self._render_analysis()
        self._update_attack_binding()

        if self._is_ai_error():
            self.app.notify(i18n.t("session.ai_error"), severity="warning", timeout=8)

    async def _fill_vulns(self) -> None:
        lst = self.query_one("#vulns-list", ListView)
        await lst.clear()
        if not self._vulns:
            lst.append(ListItem(Static(f"[dim]{i18n.t('session.none')}[/]"), id="v-empty"))
            lst.index = None
            return
        items = []
        for i, v in enumerate(self._vulns):
            fixes = self._fixes_by_vuln.get(v[0], [])
            items.append(ListItem(Static(_vuln_group_item(v, fixes)), id=f"v-{i}"))
        await lst.extend(items)
        lst.index = 0

    async def _fill_exploits(self) -> None:
        lst = self.query_one("#exploits-list", ListView)
        await lst.clear()
        if not self._exploits:
            lst.append(ListItem(Static(f"[dim]{i18n.t('session.none')}[/]"), id="e-empty"))
            lst.index = None
            return
        items = []
        for i, e in enumerate(self._exploits):
            lines = [
                f"[bold]{_esc(e[2])}[/]  [dim]({_esc(e[3])})[/]",
                f"[dim]{i18n.t('session.result')}: {_esc(e[5])}[/]",
            ]
            if e[4]:
                lines.append(f"[dim]{i18n.t('session.payload')}:[/] {_esc(e[4])}")
            if e[6]:
                lines.append(f"[dim]{i18n.t('session.notes')}:[/] {_esc(e[6])}")
            items.append(ListItem(Static("\n".join(lines)), id=f"e-{i}"))
        await lst.extend(items)
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
        text = _colorize_analysis(str(s[3] or ""))
        risk_color = _sev_color(s[4])
        self.query_one("#analysis-text", Static).update(
            f"[bold]{i18n.t('session.risk')} :[/] [bold {risk_color}]{_esc(risk)}[/]\n"
            f"[dim]{i18n.t('session.generated')} : {_esc(gen)}[/]\n\n"
            f"{text}"
        )

    # ── Sélection d'un item → chat IA ──
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        iid = event.item.id
        if not iid or iid.endswith("-empty"):
            return
        prefix, idx = iid.split("-", 1)
        if prefix == "v":
            v = self._vulns[int(idx)]
            ctx = self._chat_context("vulnerability", v, self._fixes_by_vuln.get(v[0], []))
            chat_key = f"vuln:{self.sl_no}:{v[0]}"
        elif prefix == "e":
            e = self._exploits[int(idx)]
            ctx = self._chat_context("exploit", e, [])
            chat_key = f"exploit:{self.sl_no}:{e[0]}"
        else:
            return
        self.app.push_screen(ChatScreen(self.target, ctx, chat_key))

    def _chat_context(self, kind: str, row, fixes) -> str:
        parts = [f"[{kind}]"]
        if kind == "vulnerability":
            parts.append(f"Nom : {row[2]}")
            parts.append(f"Sévérité : {_sev_label(row[3])}")
            parts.append(f"Port : {row[4]} | Service : {row[5]}")
            if row[6]:
                parts.append(f"Description : {row[6]}")
            if fixes:
                parts.append("Correctifs :\n" + "\n".join(f"- {f}" for f in fixes))
            if len(row) > 7 and row[7]:
                parts.append(f"Attaque :\n{row[7]}")
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

    # ── Test d'attaque ──
    def action_attack(self) -> None:
        lst = self.query_one("#vulns-list", ListView)
        idx = lst.index
        if idx is None or idx >= len(self._vulns):
            self.app.notify(i18n.t("attack.no_commands"), severity="warning")
            return
        v = self._vulns[idx]
        attack = v[7] if len(v) > 7 else ""
        cmds = _attack_commands(attack)
        if not cmds.strip():
            self.app.notify(i18n.t("attack.no_commands"), severity="warning")
            return
        self.app.push_screen(AttackScreen(self.target, cmds))

    # ── Édition / suppression d'un élément ──
    def action_edit(self) -> None:
        vl = self.query_one("#vulns-list", ListView)
        el = self.query_one("#exploits-list", ListView)
        if vl.display and vl.index is not None and vl.index < len(self._vulns):
            v = self._vulns[vl.index]
            fixes = [f for f in self.data["fixes"] if f[2] == v[0]]
            self.app.push_screen(
                EditItemScreen("vuln", self.sl_no, v, fixes),
                callback=self._on_edit_done,
            )
        elif el.display and el.index is not None and el.index < len(self._exploits):
            e = self._exploits[el.index]
            self.app.push_screen(
                EditItemScreen("exploit", self.sl_no, e),
                callback=self._on_edit_done,
            )
        else:
            self.app.notify(i18n.t("session.none"), severity="warning")

    def _on_edit_done(self, _) -> None:
        self.call_after_refresh(self._load)

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
        # Retourne sur la vue scan, pré-remplie (cible + outils détectés), sans lancer.
        from tui.screens.scan import NewScanScreen
        target = self.data["history"][1]
        raw_scan = str(self.data["summary"][2] or "") if self.data.get("summary") else ""
        preselected = tools.detect_tools(raw_scan)
        self.app.push_screen(NewScanScreen(target=target, preselected=preselected))


class AttackScreen(Screen):
    """Éditeur de commandes d'attaque + exécution."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("ctrl+s", "run", description=i18n.t("binding.run"), id="binding.run", show=True),
    ]

    class Line(Message):
        def __init__(self, line: str) -> None:
            self.line = line
            super().__init__()

    class Done(Message):
        def __init__(self) -> None:
            super().__init__()

    def __init__(self, target: str, commands_text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.target = target
        self.commands_text = commands_text

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('attack.title')}[/]  ·  [dim]{self.target}[/]",
            id="attack-title",
        )
        yield Static(f"[yellow]{i18n.t('attack.warning')}[/]", id="attack-warning")
        yield TextArea(self.commands_text, id="attack-editor", language="bash")
        yield Static(i18n.t("attack.hint"), id="attack-hint")
        yield Log(id="attack-log")
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)

    def action_run(self) -> None:
        cmds_text = self.query_one("#attack-editor", TextArea).text
        self.query_one("#attack-log", Log).clear()
        self._run_worker(cmds_text)

    @work(thread=True)
    def _run_worker(self, cmds_text: str) -> None:
        cmds = [l for l in cmds_text.splitlines() if l.strip() and not l.strip().startswith("#")]
        if not cmds:
            self.post_message(self.Line(i18n.t("attack.no_commands")))
            self.post_message(self.Done())
            return
        for cmd in cmds:
            self.post_message(self.Line(f"$ {cmd}"))
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                out = (r.stdout or "").strip()
                err = (r.stderr or "").strip()
                for l in out.splitlines():
                    self.post_message(self.Line(l))
                for l in err.splitlines():
                    self.post_message(self.Line(l))
            except subprocess.TimeoutExpired:
                self.post_message(self.Line("[!] timeout"))
            except Exception as e:
                self.post_message(self.Line(f"[!] {e}"))
        self.post_message(self.Done())

    def on_attack_screen_line(self, event: Line) -> None:
        self.query_one("#attack-log", Log).write_line(event.line)

    def on_attack_screen_done(self, event: Done) -> None:
        self.app.notify(i18n.t("attack.done"))


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
        yield VerticalScroll(Static("", id="run-log-static", markup=False))
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._run_worker()

    @work(thread=True)
    def _run_worker(self) -> None:
        logs.set_log(lambda m: self.post_message(self.LogLine(logs.strip_ansi(m))))
        try:
            self.post_message(self.LogLine(i18n.t("scan.tours.explain")))
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
        self.query_one("#run-log-static", Static).update("\n".join(self._lines[-60:]))

    def on_run_analysis_screen_done(self, event: Done) -> None:
        if event.ok:
            self.app.notify(i18n.t("rerun.done", sl=self.sl_no, risk=event.risk))
        else:
            self.app.notify(i18n.t("rerun.failed"), severity="error")
        self.dismiss(event.ok)
