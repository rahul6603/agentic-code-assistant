from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from app.ui.app import ChatApp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Callable[[ChatApp], None]


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(
        self, name: str, *, description: str = ""
    ) -> Callable[[Callable[[ChatApp], None]], Callable[[ChatApp], None]]:
        def decorator(
            fn: Callable[[ChatApp], None],
        ) -> Callable[[ChatApp], None]:
            if name in self._commands:
                logger.warning(f"Overwriting existing command: /{name}")
            self._commands[name] = Command(
                name=name, description=description, handler=fn
            )
            return fn

        return decorator

    def is_command(self, text: str) -> bool:
        if not text.startswith("/"):
            return False
        cmd_name = text.split()[0][1:]
        return cmd_name in self._commands

    def execute(self, app: ChatApp, text: str) -> bool:
        cmd_name = text[1:]

        command = self._commands.get(cmd_name)
        if command is None:
            return False

        command.handler(app)
        return True

    def list_commands(self) -> list[Command]:
        return sorted(self._commands.values(), key=lambda c: c.name)


registry = CommandRegistry()
