import argparse
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    chat = client.chat.completions.create(
        model="anthropic/claude-haiku-4.5",
        # model="openrouter/free",
        messages=[{"role": "user", "content": args.p}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "Read and return the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to read",
                            }
                        },
                        "required": ["file_path"],
                    },
                },
            }
        ],
    )

    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")

    message = chat.choices[0].message
    tool_calls = message.tool_calls
    if tool_calls and len(tool_calls) > 0:
        for tool_call in tool_calls:
            if tool_call.type == "function":
                function_name = tool_call.function.name
                if function_name == "Read":
                    arguments = json.loads(tool_call.function.arguments)
                    if isinstance(arguments, dict):
                        file_path = arguments.get("file_path")
                        if file_path:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            print(content)
    else:
        print(chat.choices[0].message.content)


if __name__ == "__main__":
    main()
