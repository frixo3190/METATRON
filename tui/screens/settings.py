"""Écran Paramètres (IA) — provider, clé API, modèle, crédits, langue, test."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)
from textual import work

import config
import llm
import prompts
from tui import i18n


def _fmt_cost(v):
    if v is None:
        return "n/a"
    if v == 0:
        return "$0.00"
    return f"${v:.2f}"


# ─────────────────────────────────────────────
#  ÉCRAN PRINCIPAL DES PARAMÈTRES
# ─────────────────────────────────────────────

class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("r", "refresh_credits", description=i18n.t("binding.credits"), id="binding.credits", show=True),
    ]

    class CreditsLoaded(Message):
        def __init__(self, credits) -> None:
            self.credits = credits
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._credits = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self._info(), id="settings-info")
        yield ListView(
            ListItem(Label(self._provider_label()), id="s-provider"),
            ListItem(Label(i18n.t("settings.key")), id="s-key"),
            ListItem(Label(i18n.t("settings.model")), id="s-model"),
            ListItem(Label(i18n.t("settings.credits")), id="s-credits"),
            ListItem(Label(i18n.t("settings.test")), id="s-test"),
            ListItem(Label(self._lang_label()), id="s-lang"),
            ListItem(Label(i18n.t("settings.back")), id="s-back"),
            id="settings-menu",
        )
        yield Footer()

    # ── Rendu de l'en-tête d'informations ──
    def _info(self) -> str:
        provider = config.get("provider", "ollama").upper()
        model = config.get("model", "metatron-qwen")
        lang = i18n.lang_name(config.get("language", "en"))
        key = config.mask_key(config.get("api_key", ""))

        lines = [
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('settings.title')}[/]",
            "",
            f"[b]{i18n.t('field.provider')} :[/] {provider}",
            f"[b]{i18n.t('field.model')}      :[/] {model}",
            f"[b]{i18n.t('field.lang')}      :[/] {lang}",
            f"[b]{i18n.t('field.key')}         :[/] [dim]{key}[/]",
        ]

        if provider == "OPENROUTER":
            c = self._credits
            label = i18n.t("field.credits")
            if c is None:
                lines.append(f"[b]{label}      :[/] [dim]{i18n.t('credits.fetching')}[/]")
            elif c.get("error") == "no_key":
                lines.append(f"[b]{label}      :[/] [dim]{i18n.t('credits.no_key')}[/]")
            elif c.get("error") == "unauthorized":
                lines.append(f"[b]{label}      :[/] [red]{i18n.t('credits.invalid')}[/]")
            elif c.get("remaining") is not None:
                lines.append(
                    f"[b]{label}      :[/] [green]${c['remaining']:.2f}[/]"
                    + (f"  ({i18n.t('credits.used')} : ${c['usage']:.2f})" if c.get("usage") is not None else "")
                )
            elif c.get("usage") is not None:
                lines.append(f"[b]{label}      :[/] Usage ${c['usage']:.2f}")
            else:
                lines.append(f"[b]{label}      :[/] [yellow]{i18n.t('credits.unavailable')}[/]")

        return "\n".join(lines)

    def _provider_label(self) -> str:
        prov = config.get("provider", "ollama").upper()
        return i18n.t("settings.provider_label", p=prov)

    def _lang_label(self) -> str:
        return i18n.t("settings.lang", l=i18n.lang_name(config.get("language", "en")))

    def _refresh_info(self) -> None:
        try:
            self.query_one("#settings-info", Static).update(self._info())
        except Exception:
            pass
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        for item_id, text in (
            ("s-provider", self._provider_label()),
            ("s-key", i18n.t("settings.key")),
            ("s-model", i18n.t("settings.model")),
            ("s-credits", i18n.t("settings.credits")),
            ("s-test", i18n.t("settings.test")),
            ("s-lang", self._lang_label()),
            ("s-back", i18n.t("settings.back")),
        ):
            try:
                self.query_one(f"#{item_id} Label", Label).update(text)
            except Exception:
                pass

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        if config.get("provider", "ollama") == "openrouter":
            self.action_refresh_credits()

    # ── Actions ──
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id == "s-provider":
            self._toggle_provider()
        elif item_id == "s-key":
            self.app.push_screen(KeyScreen())
        elif item_id == "s-model":
            self.app.push_screen(ModelSelectScreen())
        elif item_id == "s-credits":
            self.action_refresh_credits()
        elif item_id == "s-test":
            self.app.push_screen(TestOpenRouterScreen())
        elif item_id == "s-lang":
            self._toggle_language()
        elif item_id == "s-back":
            self.app.pop_screen()

    def _toggle_provider(self) -> None:
        cur = config.get("provider", "ollama")
        new = "openrouter" if cur == "ollama" else "ollama"
        config.set("provider", new)
        if new == "openrouter":
            if not config.get("api_key", "").strip():
                self.app.notify(i18n.t("notify.key_missing"), severity="warning")
            self.app.notify(i18n.t("notify.provider.openrouter"))
            self._verify_model()
        else:
            self.app.notify(i18n.t("notify.provider.ollama"))
        self._refresh_info()

    def _toggle_language(self) -> None:
        self.app.push_screen(LanguageScreen(), callback=self._on_language_choice)

    def _on_language_choice(self, code) -> None:
        if code in ("fr", "en"):
            config.set("language", code)
            self.app.notify(i18n.t("notify.lang", l=i18n.lang_name(code)))
            self._localize()
            if hasattr(self.app, "apply_language"):
                self.app.apply_language()

    def _localize(self) -> None:
        """Ré-applique la langue sélectionnée sur cet écran."""
        self._refresh_info()
        i18n.localize_bindings(self)

    def _verify_model(self) -> None:
        model = config.get("model", "")
        if not model or not config.get("api_key", "").strip():
            return
        self._verify_model_worker(model)

    @work(thread=True)
    def _verify_model_worker(self, model: str) -> None:
        res = llm.openrouter_model_exists(model)
        if res.get("exists"):
            self.app.notify(i18n.t("notify.model_found", m=model))
        else:
            self.app.notify(i18n.t("notify.model_missing", m=model), severity="warning")

    def action_refresh_credits(self) -> None:
        if config.get("provider", "ollama") != "openrouter":
            self.app.notify(i18n.t("notify.no_credits"), severity="warning")
            return
        self._credits = None
        self._refresh_info()
        self._credits_worker()

    @work(thread=True)
    def _credits_worker(self) -> None:
        credits = llm.get_openrouter_credits()
        self.post_message(self.CreditsLoaded(credits))

    def on_settings_screen_credits_loaded(self, event: CreditsLoaded) -> None:
        self._credits = event.credits
        self._refresh_info()


# ─────────────────────────────────────────────
#  MODAL — SAISIE DE LA CLÉ API
# ─────────────────────────────────────────────

class LanguageScreen(ModalScreen):
    """Choix de la langue (Français / Anglais)."""

    BINDINGS = [Binding("escape", "dismiss", show=False)]

    def compose(self) -> ComposeResult:
        with Vertical(id="lang-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('settings.lang', l='')}[/]", id="lang-title")
            yield ListView(
                ListItem(Label(i18n.t("lang.fr")), id="l-fr"),
                ListItem(Label(i18n.t("lang.en")), id="l-en"),
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.dismiss("fr" if event.item.id == "l-fr" else "en")


class KeyScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="key-dialog"):
            yield Static(f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('key.title')}[/]", id="key-title")
            yield Static(f"{i18n.t('key.current')} : [dim]{config.mask_key(config.get('api_key', ''))}[/]")
            yield Input(
                placeholder="sk-or-v1-…",
                password=True,
                id="key-input",
            )
            yield Static(f"[dim]{i18n.t('key.hint')}[/]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if not value:
            self.dismiss()
            return
        config.set("api_key", value)
        self.app.notify(i18n.t("notify.key_saved"))
        self.dismiss()


# ─────────────────────────────────────────────
#  ÉCRAN — SÉLECTION DU MODÈLE (avec coût)
# ─────────────────────────────────────────────

class ModelSelectScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    class ModelsLoaded(Message):
        def __init__(self, models) -> None:
            self.models = models
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._models = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('model.title')}[/]\n"
            f"[dim]{i18n.t('model.subtitle')}[/]",
            id="model-title",
        )
        yield Input(placeholder=i18n.t("model.search"), id="model-search")
        yield Static(f"[yellow]{i18n.t('model.loading')}[/]", id="model-status")
        yield ListView(id="model-list")
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._load_models()

    @work(thread=True)
    def _load_models(self) -> None:
        models = llm.fetch_openrouter_models()
        self.post_message(self.ModelsLoaded(models))

    async def on_input_changed(self, event: Input.Changed) -> None:
        await self._rebuild(event.value)

    async def _rebuild(self, query: str) -> None:
        if not self._models:
            return
        q = query.strip().lower()
        lst = self.query_one("#model-list", ListView)
        items = []
        count = 0
        for i, m in enumerate(self._models):
            if q and q not in m["id"].lower() and q not in (m.get("name") or "").lower():
                continue
            cost = f"{_fmt_cost(m['prompt_usd_per_m'])} / {_fmt_cost(m['completion_usd_per_m'])}"
            label = f"{m['id']:<40}  [cyan]{cost}[/]"
            items.append(ListItem(Label(label), id=f"model-{i}"))
            count += 1
        await lst.clear()
        if items:
            await lst.extend(items)
        if q:
            self.query_one("#model-status", Static).update(
                f"[green]{i18n.t('model.results', n=count, q=query.strip(), total=len(self._models))}[/]"
            )
        else:
            self.query_one("#model-status", Static).update(
                f"[green]{i18n.t('model.count', n=len(self._models))}[/]"
            )

    async def on_model_select_screen_models_loaded(self, event: ModelsLoaded) -> None:
        self._models = event.models
        if not self._models:
            self.query_one("#model-status", Static).update(
                f"[red]{i18n.t('model.none')}[/]"
            )
            return
        await self._rebuild("")
        try:
            self.query_one("#model-search", Input).focus()
        except Exception:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.item.id
        if not idx or not idx.startswith("model-"):
            return
        i = int(idx.split("-")[1])
        chosen = self._models[i]
        config.set("model", chosen["id"])
        config.set("provider", "openrouter")
        self.app.notify(i18n.t("notify.model_selected", m=chosen["id"]))
        self.app.pop_screen()


# ─────────────────────────────────────────────
#  ÉCRAN — TEST OPENROUTER
# ─────────────────────────────────────────────

class TestOpenRouterScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    class TestDone(Message):
        def __init__(self, text) -> None:
            self.text = text
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('test.title')}[/]",
            id="test-title",
        )
        yield Static(f"[yellow]{i18n.t('test.sending', m=config.get('model', ''))}[/]", id="test-status")
        yield Static("", id="test-result", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        model = config.get("model", "")
        self.query_one("#test-status", Static).update(
            f"[yellow]{i18n.t('test.sending', m=model)}[/]"
        )
        self._run()

    @work(thread=True)
    def _run(self) -> None:
        api_key = config.get("api_key", "").strip()
        model = config.get("model", "").strip()
        if not api_key:
            self.post_message(self.TestDone(f"[red]{i18n.t('test.no_key')}[/]"))
            return
        if not model:
            self.post_message(self.TestDone(f"[red]{i18n.t('test.no_model')}[/]"))
            return
        resp = llm.ask_openrouter([
            {"role": "user",
             "content": prompts.get("test_prompt", "Réponds en une seule phrase : es-tu opérationnel ?")}
        ], max_tokens=128, temperature=0.3)
        self.post_message(self.TestDone(resp))

    def on_test_open_router_screen_test_done(self, event: TestDone) -> None:
        self.query_one("#test-status", Static).update(f"[dim]{i18n.t('test.reply')} :[/]")
        self.query_one("#test-result", Static).update(event.text)
