from __future__ import annotations

from typing import TYPE_CHECKING

from app.commands.registry import registry

if TYPE_CHECKING:
    from app.ui.app import ChatApp


@registry.register("exit", description="Exit the application")
def cmd_exit(app: ChatApp) -> None:
    app.exit()


@registry.register("clear", description="Clear conversation history and chat UI")
def cmd_clear(app: ChatApp) -> None:
    if app.agent:
        app.agent.clear_conversation()

    from textual.containers import VerticalScroll

    scroll = app.query_one(VerticalScroll)
    scroll.remove_children()

    app._streaming_widget = None
    app._streaming_content = ""

    from app.ui.app import ChatArea

    chat_area = app.query_one(ChatArea)
    chat_area.placeholder = "How can I help you today?"
    app._first_message = True


@registry.register("help", description="Show available commands")
def cmd_help(app: ChatApp) -> None:
    from textual.widgets import Static
    from textual.containers import VerticalScroll

    commands = registry.list_commands()
    lines = ["[bold]Available commands:[/bold]", ""]
    for cmd in commands:
        desc = f" - {cmd.description}" if cmd.description else ""
        lines.append(f"[green]/{cmd.name}[/green]{desc}")

    scroll = app.query_one(VerticalScroll)
    scroll.mount(Static("\n".join(lines), classes="streaming-text"))
    scroll.scroll_end(animate=False)
