"""Écran de chat IA — bulles (IA à gauche / utilisateur à droite), Markdown."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, LoadingIndicator, Markdown, Static
from textual import work

import db
import llm
import logs
import prompts
from tui import i18n


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
        self._history = []
        self._thinking_row = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="chat-left"):
                yield Static(
                    f"[bold red]METATRON[/]  ·  [cyan]{i18n.t('chat.title')}[/]",
                    id="chat-title",
                )
                yield VerticalScroll(id="chat-messages")
                yield Input(placeholder=i18n.t("chat.input.placeholder"), id="chat-input")
            with VerticalScroll(id="chat-right"):
                yield Static(f"[bold]{i18n.t('chat.context.title')}[/]", id="chat-context-title")
                yield Static(self.context_text, id="chat-context", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        i18n.localize_bindings(self)
        if self.chat_key:
            for role, content in db.get_chat_messages(self.chat_key):
                self._history.append({"role": role, "content": content})
                self._add_bubble(role, content)
        if not self._history:
            self._add_bubble(
                "assistant", f"*{i18n.t('chat.welcome')}*"
            )
        self.query_one("#chat-input", Input).focus()

    def _add_bubble(self, role: str, content: str) -> None:
        container = self.query_one("#chat-messages", VerticalScroll)
        if role == "user":
            bubble = Static(str(content), classes="bubble-user", markup=False)
            align = "right"
        else:
            bubble = Markdown(str(content), classes="bubble-ai")
            align = "left"
        row = Horizontal(bubble, classes="msg-row")
        row.styles.align_horizontal = align
        container.mount(row)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            return
        self.query_one("#chat-input", Input).value = ""
        self._add_bubble("user", q)
        self._history.append({"role": "user", "content": q})
        if self.chat_key:
            db.save_chat_message(self.chat_key, "user", q)
        # indicateur « réflexion »
        container = self.query_one("#chat-messages", VerticalScroll)
        self._thinking_row = Horizontal(LoadingIndicator(), classes="msg-row")
        self._thinking_row.styles.align_horizontal = "left"
        container.mount(self._thinking_row)
        self._ask_worker(q)

    @work(thread=True)
    def _ask_worker(self, q: str) -> None:
        logs.set_log(lambda m: None)
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
        template = prompts.get(
            "chat_system_prompt",
            "Tu es METATRON. CIBLE : {target}\n\nCONTEXTE :\n{context}",
        )
        try:
            return template.format(target=self.target, context=self.context_text)
        except Exception:
            return f"Tu es METATRON.\n\nCIBLE : {self.target}\n\nCONTEXTE :\n{self.context_text}"

    async def on_chat_screen_reply(self, event: Reply) -> None:
        if self._thinking_row is not None:
            try:
                await self._thinking_row.remove()
            except Exception:
                pass
            self._thinking_row = None
        self._add_bubble("assistant", event.text)
