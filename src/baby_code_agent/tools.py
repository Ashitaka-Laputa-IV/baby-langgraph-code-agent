"""Filesystem and shell tools exposed to the agent."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from langchain_core.tools import BaseTool, tool

DEFAULT_OUTPUT_LIMIT = 12_000
SHELL_TIMEOUT_SECONDS = 60
VCS_METADATA = ".git"


class PathOutsideRoot(ValueError):
    """Raised when a tool path resolves outside the working directory."""


def _resolve_inside_root(root: Path, path: str) -> Path:
    root_resolved = root.resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root_resolved / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root_resolved):
        raise PathOutsideRoot(f"path escapes the working directory: {path}")
    return candidate


def _is_vcs_metadata(root: Path, candidate: Path) -> bool:
    relative = candidate.relative_to(root.resolve())
    return bool(relative.parts) and relative.parts[0].casefold() == VCS_METADATA


def format_command_for_display(command: str) -> str:
    """Render a command so control characters and newlines are visible, not executed by the terminal."""
    visible = []
    for char in command:
        if char == "\n":
            visible.append("\\n")
        elif char == "\r":
            visible.append("\\r")
        elif char == "\t":
            visible.append("\\t")
        elif char == "\x1b":
            visible.append("\\e")
        elif ord(char) < 32 or ord(char) == 127:
            visible.append(f"\\x{ord(char):02x}")
        else:
            visible.append(char)
    return "".join(visible)


def _truncate(text: str, limit: int = DEFAULT_OUTPUT_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n...[output truncated at {limit} characters]"


def build_tools(
    root: Path,
    confirm: Callable[[str], bool],
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
) -> list[BaseTool]:
    """Create the tool set rooted at ``root``.

    ``confirm`` receives the exact command text and returns whether it may run.
    """

    root = root.resolve()

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and directories under a path inside the working directory."""
        try:
            target = _resolve_inside_root(root, path)
        except PathOutsideRoot as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: no such directory: {path}"
        if not target.is_dir():
            return f"Error: not a directory: {path}"

        entries = []
        for entry in sorted(target.iterdir(), key=lambda item: item.name.casefold()):
            entries.append(f"{entry.name}/" if entry.is_dir() else entry.name)
        if not entries:
            return "(empty directory)"
        return _truncate("\n".join(entries), output_limit)

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file inside the working directory and return it with line numbers."""
        try:
            target = _resolve_inside_root(root, path)
        except PathOutsideRoot as exc:
            return f"Error: {exc}"
        if not target.is_file():
            return f"Error: no such file: {path}"
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: not a UTF-8 text file: {path}"
        except OSError as exc:
            return f"Error: cannot read {path}: {exc}"

        numbered = [f"{number:>5}\t{line}" for number, line in enumerate(text.splitlines(), 1)]
        if not numbered:
            return "(empty file)"
        return _truncate("\n".join(numbered), output_limit)

    @tool
    def write_file(path: str, content: str) -> str:
        """Write UTF-8 text to a file inside the working directory, creating parent directories."""
        try:
            target = _resolve_inside_root(root, path)
        except PathOutsideRoot as exc:
            return f"Error: {exc}"
        if _is_vcs_metadata(root, target):
            return f"Error: refusing to write version-control metadata: {path}"
        if target.exists() and target.is_dir():
            return f"Error: path is a directory: {path}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            return f"Error: cannot write {path}: {exc}"
        return f"Wrote {len(content)} characters to {path}"

    @tool
    def run_shell(command: str) -> str:
        """Run a shell command in the working directory after the user approves it."""
        if "\x00" in command:
            return "Error: command contains a NUL byte and cannot be displayed or run unambiguously"
        if not confirm(command):
            return "Error: user denied command"

        try:
            completed = subprocess.run(
                command,
                shell=True,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {SHELL_TIMEOUT_SECONDS} seconds"
        except OSError as exc:
            return f"Error: cannot run command: {exc}"

        output = (completed.stdout or "") + (completed.stderr or "")
        header = f"$ {command}\n"
        if completed.returncode != 0:
            header += f"[exit code {completed.returncode}]\n"
        if not output.strip():
            output = "(no output)\n"
        return _truncate(header + output, output_limit)

    return [list_dir, read_file, write_file, run_shell]
