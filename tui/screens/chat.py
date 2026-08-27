"""Écran de chat IA — split view : gauche = conversation, droite = contexte.

La discussion est persistée en base (chat_key) et rechargée à l'ouverture.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual import work

import db
import llm
import logs
from tui import i18n


def _esc(s) -> str:
    return str(s or "").replace("[", "\\[").replace("]", "\\]")


class ChatScreen(Screen):
    """Discussion avec l'IA sur un résultat précis, avec le contexte du scan."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
        Binding("q", "app.pop_screen", description=i18n.t("binding.back"), id="binding.back", show=True),
    ]

    class Reply(Message):
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    def __init__(self, target: str, context_text: str, chat_key: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.target = target
        self.context_text = context_text
        self.chat_key = chat_key
        self._history = []  # liste de dicts {"role", "content"}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="chat-left"):
                yield Static(
                    f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('chat.title')}[/]",
                    id="chat-title",
                )
                yield RichLog(id="chat-log", markup=True, wrap=True)
                yield Input(placeholder=i18n.t("chat.input.placeholder"), id="chat-input")
            with VerticalScroll(id="chat-right"):
                yield Static(f"[bold]{i18n.t('chat.context.title')}[/]", id="chat-context-title")
                yield Static(self.context_text, id="chat-context", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        self._log = self.query_one("#chat-log", RichLog)
        # Recharge la discussion persistée (si chat_key fourni)
        if self.chat_key:
            for role, content in db.get_chat_messages(self.chat_key):
                self._history.append({"role": role, "content": content})
                self._render_message(role, content)
        if not self._history:
            self._log.write(f"[dim]{i18n.t('chat.welcome')}[/]")
        self.query_one("#chat-input", Input).focus()

    def _render_message(self, role: str, content: str) -> None:
        if role == "user":
            self._log.write(f"[bold cyan]{i18n.t('chat.you')} :[/] [cyan]{_esc(content)}[/]")
        else:
            self._log.write(f"[bold green]{i18n.t('chat.ai')} :[/] {_esc(content)}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            return
        self.query_one("#chat-input", Input).value = ""
        self._render_message("user", q)
        self._history.append({"role": "user", "content": q})
        if self.chat_key:
            db.save_chat_message(self.chat_key, "user", q)
        self._log.write(f"[dim]{i18n.t('chat.ai')} · {i18n.t('chat.thinking')}[/]")
        self._ask_worker(q)

    @work(thread=True)
    def _ask_worker(self, q: str) -> None:
        logs.set_log(lambda m: None)  # ne pas imprimer dans le terminal TUI
        try:
            messages = [{"role": "system", "content": self._system_prompt()}]
            messages.extend(self._history)
            resp = llm.ask_llm(messages, max_tokens=1200)
            self._history.append({"role": "assistant", "content": resp})
            if self.chat_key:
                db.save_chat_message(self.chat_key, "assistant", resp)
            self.post_message(self.Reply(resp))
        finally:
            logs.set_log(None)

    def _system_prompt(self) -> str:
        return (
            "Tu es METATRON, un assistant expert en test d'intrusion. "
            "Tu discutes d'un résultat précis avec l'utilisateur.\n\n"
            f"CIBLE : {self.target}\n\n"
            "CONTEXTE :\n"
            f"{self.context_text}\n\n"
            "Réponds de façon précise, technique et utile. "
            "Réponds dans la langue de la question de l'utilisateur."
        )

    def on_chat_screen_reply(self, event: Reply) -> None:
        self._render_message("assistant", event.text)
