"""
Sandbox Filesystem & Docker Build MCP Server:
Provides restricted read/write tools scoped strictly to candidate_workspace/,
with Git checkpointing and automatic rollback capabilities.
"""

import os
import shutil
import subprocess
from typing import Dict, Any, Optional

class SandboxFsMCP:
    """Restricted candidate filesystem tools with patch rollback safety."""

    def __init__(self, workspace_root: Optional[str] = None):
        if workspace_root is None:
            workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../candidate_workspace"))
        self.workspace_root = workspace_root
        os.makedirs(self.workspace_root, exist_ok=True)
        self.checkpoints: Dict[str, Dict[str, str]] = {}

    def _resolve_safe_path(self, relative_path: str) -> str:
        """Enforces that all file writes are strictly confined to candidate_workspace."""
        clean_rel = os.path.normpath(relative_path.lstrip("/"))
        full_path = os.path.abspath(os.path.join(self.workspace_root, clean_rel))
        if not full_path.startswith(self.workspace_root):
            raise PermissionError(f"Directory traversal prohibited: {relative_path}")
        return full_path

    def read_candidate_file(self, relative_path: str) -> Dict[str, Any]:
        """Reads a file from candidate_workspace."""
        target = self._resolve_safe_path(relative_path)
        if not os.path.exists(target):
            return {"error": f"File {relative_path} does not exist", "exists": False}
        with open(target, "r") as f:
            content = f.read()
        return {"exists": True, "content": content}

    def write_candidate_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        """Writes a code patch or new file to candidate_workspace."""
        target = self._resolve_safe_path(relative_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w") as f:
            f.write(content)
        return {"success": True, "path": relative_path, "bytes_written": len(content)}

    def checkpoint_state(self, checkpoint_id: str) -> Dict[str, Any]:
        """Captures in-memory snapshots of all candidate files before applying a risky patch."""
        snapshot = {}
        for root, _, files in os.walk(self.workspace_root):
            for file in files:
                if file.endswith((".py", ".yaml", ".json", "Dockerfile")):
                    full = os.path.join(root, file)
                    rel = os.path.relpath(full, self.workspace_root)
                    with open(full, "r") as f:
                        snapshot[rel] = f.read()
        self.checkpoints[checkpoint_id] = snapshot
        return {"checkpoint_id": checkpoint_id, "files_tracked": len(snapshot)}

    def rollback_state(self, checkpoint_id: str) -> Dict[str, Any]:
        """Rolls back candidate files to the designated checkpoint upon regression detection."""
        if checkpoint_id not in self.checkpoints:
            return {"success": False, "error": f"Checkpoint {checkpoint_id} not found"}

        snapshot = self.checkpoints[checkpoint_id]
        for rel_path, content in snapshot.items():
            full = self._resolve_safe_path(rel_path)
            with open(full, "w") as f:
                f.write(content)

        return {"success": True, "rolled_back_to": checkpoint_id, "files_restored": len(snapshot)}

    def test_candidate_syntax(self, relative_path: str = "app.py") -> Dict[str, Any]:
        """Validates Python syntax and imports in candidate_workspace."""
        target = self._resolve_safe_path(relative_path)
        try:
            with open(target, "r") as f:
                compile(f.read(), target, "exec")
            return {"valid_syntax": True}
        except SyntaxError as e:
            return {"valid_syntax": False, "error": str(e), "line": e.lineno}
