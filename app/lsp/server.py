from pathlib import Path
import logging

from app.lsp.base_server import BaseLanguageServer

logger = logging.getLogger(__name__)


class PythonLanguageServer(BaseLanguageServer):
    def __init__(self):
        super().__init__("python")

    def get_server_command(self) -> list[str]:
        return ["pyright-langserver", "--stdio"]


class RustLanguageServer(BaseLanguageServer):
    def __init__(self):
        super().__init__("rust")

    def get_server_command(self) -> list[str]:
        return ["rust-analyzer"]


class LanguageServerManager:
    def __init__(self):
        self.servers: dict[str, BaseLanguageServer] = {
            "python": PythonLanguageServer(),
            "rust": RustLanguageServer(),
        }
        self.extension_map = {
            ".py": "python",
            ".rs": "rust",
        }

    def _get_server(self, path: Path) -> BaseLanguageServer | None:
        lang_id = self.extension_map.get(path.suffix)
        if not lang_id:
            return None
        server = self.servers.get(lang_id)
        if not server:
            return None
        if not server.process:
            server.initialize()
        return server

    def send_did_open_notification(
        self,
        requested_path: Path,
        content: str,
    ) -> bool:
        server = self._get_server(requested_path)
        if server:
            return server.send_did_open_notification(requested_path, content)
        return False

    def send_did_change_notification(self, requested_path: Path, content: str) -> str:
        server = self._get_server(requested_path)
        if server:
            return server.send_did_change_notification(requested_path, content)
        return ""
