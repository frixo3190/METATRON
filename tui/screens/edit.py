"""Écrans d'édition / suppression d'une vulnérabilité ou d'un exploit."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

import db
from tui import i18n


def _esc(s) -> str:
    return str(s or "").replace("[", "\\[").replace("]", "\\]")


def _sev_label(sev: str) -> str:
    s = (sev or "unknown").lower()
    key = f"sev.{s}"
    return i18n.t(key) if key in i18n.STRINGS else s.upper()


SEVERITIES = ["critical", "high", "medium", "low"]


class TextEditModal(ModalScreen):
    """Modal de saisie d'une valeur texte."""

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def __init__(self, title: str, value: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._title = title
        self._value = value

    def compose(self) -> ComposeResult:
        with Vertical(id="textedit-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{self._title}[/]", id="textedit-title")
            yield Input(value=self._value, id="textedit-input")

    def on_mount(self) -> None:
        self.query_one("#textedit-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class SeverityModal(ModalScreen):
    """Modal de choix de la sévérité."""

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="sev-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('edit.field.severity')}[/]", id="sev-title")
            yield ListView(
                ListItem(Label(i18n.t("sev.critical")), id="s-critical"),
                ListItem(Label(i18n.t("sev.high")), id="s-high"),
                ListItem(Label(i18n.t("sev.medium")), id="s-medium"),
                ListItem(Label(i18n.t("sev.low")), id="s-low"),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id.replace("s-", ""))


class FixEditScreen(ModalScreen):
    """Édition / suppression d'un correctif."""

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def __init__(self, sl_no: int, fix_row, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sl_no = sl_no
        self.fix = fix_row  # (id, sl_no, vuln_id, fix_text, source)

    def compose(self) -> ComposeResult:
        with Vertical(id="fix-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('edit.title.fix')}[/]", id="fix-title")
            yield Static(self.fix[3], id="fix-text", markup=False)
            yield ListView(
                ListItem(Label(i18n.t("edit.field.description")), id="fx-edit"),
                ListItem(Label(i18n.t("edit.delete.fix")), id="fx-delete"),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id == "fx-edit":
            self.dismiss("edit")
        elif event.item.id == "fx-delete":
            self.dismiss("delete")


class EditItemScreen(Screen):
    """Écran d'édition d'un élément (vulnérabilité ou exploit)."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    VULN_FIELDS = [
        ("f-name", "vuln_name", "edit.field.name"),
        ("f-severity", "severity", "edit.field.severity"),
        ("f-port", "port", "edit.field.port"),
        ("f-service", "service", "edit.field.service"),
        ("f-description", "description", "edit.field.description"),
        ("f-attack", "attack", "edit.field.attack"),
    ]

    EXPLOIT_FIELDS = [
        ("f-name", "exploit_name", "edit.field.name"),
        ("f-tool", "tool_used", "edit.field.tool"),
        ("f-payload", "payload", "edit.field.payload"),
        ("f-result", "result", "edit.field.result"),
        ("f-notes", "notes", "edit.field.notes"),
    ]

    def __init__(self, kind: str, sl_no: int, item, fixes=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.kind = kind
        self.sl_no = sl_no
        self.item = item
        self.fixes = fixes or []
        self._current_fix_id = None
        self._current_fix_text = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("", id="edit-header")
        yield ListView(id="edit-list")
        yield Footer()

    async def on_mount(self) -> None:
        i18n.localize_bindings(self)
        await self._populate()

    async def _populate(self) -> None:
        if self.kind == "vuln":
            self.query_one("#edit-header", Static).update(
                f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('edit.title.vuln')} #{self.item[0]}[/]\n"
                f"[bold {('red' if (self.item[3] or '') == 'critical' else '')}]{_sev_label(self.item[3])}[/]"
            )
        else:
            self.query_one("#edit-header", Static).update(
                f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('edit.title.exploit')} #{self.item[0]}[/]"
            )

        lst = self.query_one("#edit-list", ListView)
        await lst.clear()

        items = []
        fields = self.VULN_FIELDS if self.kind == "vuln" else self.EXPLOIT_FIELDS
        colmap = {
            "vuln_name": 2, "severity": 3, "port": 4, "service": 5,
            "description": 6, "attack": 7,
            "exploit_name": 2, "tool_used": 3, "payload": 4, "result": 5, "notes": 6,
        }
        for item_id, field, label_key in fields:
            val = self.item[colmap[field]]
            if field == "severity":
                val = _sev_label(val)
            display = str(val or "").replace("\n", " ")
            display = (display[:60] + "…") if len(display) > 60 else display
            items.append(ListItem(Label(f"{i18n.t(label_key)} : [dim]{_esc(display)}[/]"), id=item_id))

        if self.kind == "vuln" and self.fixes:
            items.append(ListItem(Label(f"[bold]{i18n.t('edit.fixes')}[/]"), id="fixes-hdr"))
            for i, f in enumerate(self.fixes):
                txt = str(f[3] or "").replace("\n", " ")[:50]
                items.append(ListItem(Label(f"  Fix #{f[0]} : [dim]{_esc(txt)}[/]"), id=f"fix-{i}"))

        if self.kind == "vuln":
            items.append(ListItem(Label(f"[red]{i18n.t('edit.delete.vuln')}[/]"), id="delete"))
        else:
            items.append(ListItem(Label(f"[red]{i18n.t('edit.delete.exploit')}[/]"), id="delete"))

        await lst.extend(items)
        lst.index = 0

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        iid = event.item.id
        if not iid:
            return
        if iid == "delete":
            name = self.item[2] if self.kind == "vuln" else self.item[2]
            self.app.push_screen(
                ConfirmModal(i18n.t("edit.confirm.delete", t=name)),
                callback=self._on_delete_confirm,
            )
            return
        if iid == "fixes-hdr":
            return
        if iid.startswith("fix-"):
            i = int(iid.split("-")[1])
            self._current_fix_id = self.fixes[i][0]
            self._current_fix_text = self.fixes[i][3]
            self.app.push_screen(
                FixEditScreen(self.sl_no, self.fixes[i]),
                callback=self._on_fix_action,
            )
            return
        # champ à éditer
        fields = self.VULN_FIELDS if self.kind == "vuln" else self.EXPLOIT_FIELDS
        for item_id, field, label_key in fields:
            if item_id == iid:
                colmap = {
                    "vuln_name": 2, "severity": 3, "port": 4, "service": 5,
                    "description": 6, "attack": 7,
                    "exploit_name": 2, "tool_used": 3, "payload": 4, "result": 5, "notes": 6,
                }
                current = self.item[colmap[field]] or ""
                if field == "severity":
                    self.app.push_screen(SeverityModal(), callback=lambda v: self._apply(field, v))
                else:
                    self.app.push_screen(
                        TextEditModal(i18n.t(label_key), str(current)),
                        callback=lambda v: self._apply(field, v),
                    )
                return

    def _apply(self, field: str, value) -> None:
        if value is None:
            return
        if self.kind == "vuln":
            db.edit_vulnerability(self.item[0], field, value)
        else:
            db.edit_exploit(self.item[0], field, value)
        self.app.notify(i18n.t("edit.done"))
        self.call_after_refresh(self._reload_item)

    async def _reload_item(self) -> None:
        if self.kind == "vuln":
            rows = db.get_vulnerabilities(self.sl_no)
            for r in rows:
                if r[0] == self.item[0]:
                    self.item = r
                    break
            fixes = [f for f in db.get_fixes(self.sl_no) if f[2] == self.item[0]]
            self.fixes = fixes
        else:
            rows = db.get_exploits(self.sl_no)
            for r in rows:
                if r[0] == self.item[0]:
                    self.item = r
                    break
        await self._populate()

    def _on_delete_confirm(self, ok: bool) -> None:
        if not ok:
            return
        if self.kind == "vuln":
            db.delete_vulnerability(self.item[0])
        else:
            db.delete_exploit(self.item[0])
        self.app.notify(i18n.t("edit.done"))
        self.dismiss(True)

    def _on_fix_action(self, action) -> None:
        if action == "edit":
            self.app.push_screen(
                TextEditModal(i18n.t("edit.field.description"), str(self._current_fix_text)),
                callback=self._apply_fix,
            )
        elif action == "delete":
            self.app.push_screen(
                ConfirmModal(i18n.t("edit.confirm.delete", t=f"fix #{self._current_fix_id}")),
                callback=self._delete_fix,
            )

    def _apply_fix(self, value) -> None:
        if value is None:
            return
        db.edit_fix(self._current_fix_id, value)
        self.app.notify(i18n.t("edit.done"))
        self.call_after_refresh(self._reload_item)

    def _delete_fix(self, ok: bool) -> None:
        if not ok:
            return
        db.delete_fix(self._current_fix_id)
        self.app.notify(i18n.t("edit.done"))
        self.call_after_refresh(self._reload_item)


class ConfirmModal(ModalScreen):
    """Confirmation Oui / Non."""

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
