from abc import ABC, abstractmethod
from pathlib import Path
import subprocess
import json
import time
import os
import logging
import shutil

from app.lsp.diagnostics import collect_diagnostics, read_lsp_message

logger = logging.getLogger(__name__)


class BaseLanguageServer(ABC):
    def __init__(self, language_id: str):
        self.language_id: str = language_id
        self.open_file_uris: dict[str, int] = {}
        self.process: subprocess.Popen[bytes] | None = None

    @abstractmethod
    def get_server_command(self) -> list[str]:
        pass

    def initialize(self):
        if self.process:
            return

        try:
            command = self.get_server_command()
            if not command:
                logger.error(f"Command for {self.language_id} server not configured")
                return

            if not shutil.which(command[0]):
                logger.warning(f"{command[0]} executable not found")
                return

            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
            )

            initialize_params = {
                "processId": os.getpid(),
                "rootUri": Path.cwd().as_uri(),
                "capabilities": {},
                "trace": "verbose",
            }

            initialize_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": initialize_params,
            }

            json_content = json.dumps(initialize_request).encode("utf-8")
            content_length = len(json_content)
            header = f"Content-Length: {content_length}\r\n\r\n".encode("utf-8")

            if self.process.stdin:
                self.process.stdin.write(header + json_content)
                self.process.stdin.flush()

                time.sleep(0.5)

                response = read_lsp_message(self.process)
                if not response:
                    logger.error(
                        f"No response from {self.language_id} language server initialization"
                    )
                    self.process.terminate()
                    self.process = None
                    return

                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "initialized",
                    "params": {},
                }

                json_content = json.dumps(initialized_notification).encode("utf-8")
                header = f"Content-Length: {len(json_content)}\r\n\r\n".encode("utf-8")
                self.process.stdin.write(header + json_content)
                self.process.stdin.flush()

                logger.info(f"{self.language_id} language server initialized")

        except Exception as e:
            logger.error(f"Failed to start {self.language_id} language server: {e}")
            self.process = None

    def send_did_open_notification(
        self,
        requested_path: Path,
        content: str,
    ) -> bool:
        if not self.process:
            self.initialize()

        if not self.process or not self.process.stdin:
            return False

        uri = requested_path.as_uri()
        if uri in self.open_file_uris:
            return True

        did_open_notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "languageId": self.language_id,
                    "version": 1,
                    "text": content,
                }
            },
        }
        try:
            json_content = json.dumps(did_open_notification).encode("utf-8")
            content_length = len(json_content)
            header = f"Content-Length: {content_length}\r\n\r\n".encode("utf-8")
            self.process.stdin.write(header + json_content)
            self.process.stdin.flush()
            self.open_file_uris[uri] = 1
            return True
        except Exception as e:
            logger.error(
                f"Failed to send didOpen notification for {self.language_id}: {e}"
            )
        return False

    def send_did_change_notification(self, requested_path: Path, content: str) -> str:
        if not self.process:
            self.initialize()

        if not self.process or not self.process.stdin:
            return ""

        if not self.send_did_open_notification(requested_path, content):
            return ""

        uri = requested_path.as_uri()
        next_version = self.open_file_uris.get(uri, 0) + 1
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "version": next_version,
                },
                "contentChanges": [{"text": content}],
            },
        }

        try:
            json_content = json.dumps(notification).encode("utf-8")
            header = f"Content-Length: {len(json_content)}\r\n\r\n".encode("utf-8")
            self.process.stdin.write(header + json_content)
            self.process.stdin.flush()
            self.open_file_uris[uri] = next_version

            diags = collect_diagnostics(self.process, uri)
            if diags:
                diagnostics_output = "\nDiagnostics:\n" + "\n".join(diags)
            else:
                diagnostics_output = "\nNo diagnostics returned."
            return diagnostics_output
        except Exception as e:
            logger.error(f"LSP Error ({self.language_id}): {e}")
        return ""
