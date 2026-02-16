from openai import OpenAI
from textual.app import App, ComposeResult
from textual.widgets import RichLog, TextArea
from rich.markdown import Markdown
from textual.binding import Binding
from textual.message import Message
from textual import work

from app.core.agent import Agent
from app.config import API_KEY, BASE_URL


class ChatArea(TextArea):
    BINDINGS = [
        Binding("enter", "submit", "Submit", show=False, priority=True),
        Binding("ctrl+j", "insert_newline", "Newline", show=False),
    ]

    class Submitted(Message):
        def __init__(self, value: str):
            super().__init__()
            self.value = value

    def action_submit(self):
        self.post_message(self.Submitted(self.text))
        self.clear()

    def action_insert_newline(self):
        self.insert("\n")


class ChatApp(App[None]):
    CSS = """
    ChatArea {
        dock: bottom;
        height: 5;
    }
    RichLog {
        height: 1fr;
        border: solid green;
    }
    """

    def __init__(self):
        super().__init__()
        self.agent: Agent | None = None

    def compose(self) -> ComposeResult:
        yield RichLog(highlight=True, markup=True, wrap=True)
        yield ChatArea(placeholder="How can I help you today?")

    def on_mount(self) -> None:
        if not API_KEY:
            self.query_one(RichLog).write(
                "[bold red]Error:[/bold red] OpenRouter API key is not set"
            )
            self.query_one(ChatArea).disabled = True
            return
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        self.agent = Agent(client, self.handle_error, self.display_message)
        self.query_one(ChatArea).focus()

    def on_chat_area_submitted(self, event: ChatArea.Submitted) -> None:
        if not self.agent:
            self.handle_error(
                "[bold red]Error: Could not initialize the OpenRouter client, try again[/bold red]"
            )
            return

        user_input = event.value.strip()
        if not user_input:
            return

        self.query_one(ChatArea).text = ""
        self.query_one(ChatArea).disabled = True

        log = self.query_one(RichLog)
        log.write(f"[bold green]User[/bold green]\n{user_input}")

        self.agent.add_user_message(user_input)
        self.process_response()

    def enable_input(self) -> None:
        input_widget = self.query_one(ChatArea)
        input_widget.disabled = False
        input_widget.focus()

    def handle_error(self, error_msg: str):
        log = self.query_one(RichLog)
        self.call_from_thread(log.write, f"[bold red]Error:[/bold red] {error_msg}")

    def display_message(self, content: str):
        log = self.query_one(RichLog)
        self.call_from_thread(log.write, "[bold blue]Assistant[/bold blue]")
        self.call_from_thread(log.write, Markdown(content))

    @work(thread=True)
    def process_response(self) -> None:
        if not self.agent:
            return
        should_continue = True
        while should_continue:
            should_continue = self.agent.process_turn()
        self.call_from_thread(self.enable_input)
