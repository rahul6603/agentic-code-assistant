from typing import Callable
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_function_tool_call_param import Function

from app.lsp.server import LanguageServerManager
from app.tools.definitions import TOOL_DEFINITIONS
from app.tools.bash import execute_bash_tool
from app.tools.read import execute_read_tool
from app.tools.write import execute_write_tool


class Agent:
    def __init__(
        self,
        client: OpenAI,
        on_error: Callable[[str], None],
        on_message: Callable[[str], None],
    ):
        self.client: OpenAI = client
        self.language_server_manager: LanguageServerManager = LanguageServerManager()
        self.conversation_history: list[ChatCompletionMessageParam] = []
        self.on_error: Callable[[str], None] = on_error
        self.on_message: Callable[[str], None] = on_message

    def process_turn(self) -> bool:
        try:
            chat = self.client.chat.completions.create(
                model="openrouter/free",
                messages=self.conversation_history,
                tools=TOOL_DEFINITIONS,
            )
        except Exception:
            self.on_error("Could not call the OpenRouter API, try again")
            return False

        if not chat.choices:
            self.on_error("No choices in response")
            return False

        message = chat.choices[0].message
        tool_calls = message.tool_calls
        content = message.content

        assistant_message = ChatCompletionAssistantMessageParam(
            role="assistant",
            content=content,
        )

        if not tool_calls:
            if content:
                self.on_message(content)
                self.conversation_history.append(assistant_message)
            return False

        assistant_message["tool_calls"] = []
        tool_messages: list[ChatCompletionToolMessageParam] = []

        for tool_call in tool_calls:
            if tool_call.type == "function":
                tool_call_id = tool_call.id
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments

                assistant_message["tool_calls"].append(
                    ChatCompletionMessageFunctionToolCallParam(
                        id=tool_call.id,
                        type=tool_call.type,
                        function=Function(name=function_name, arguments=arguments),
                    )
                )

                if function_name == "Read":
                    tool_response = execute_read_tool(
                        self.language_server_manager, arguments
                    )
                elif function_name == "Write":
                    tool_response = execute_write_tool(
                        self.language_server_manager, arguments
                    )
                elif function_name == "Bash":
                    tool_response = execute_bash_tool(arguments)
                else:
                    tool_response = f"Unknown tool: {function_name}"

                tool_messages.append(
                    ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=tool_call_id,
                        content=tool_response,
                    )
                )

        self.conversation_history.append(assistant_message)
        self.conversation_history.extend(tool_messages)
        return True

    def add_user_message(self, content: str) -> None:
        self.conversation_history.append(
            ChatCompletionUserMessageParam(role="user", content=content)
        )
