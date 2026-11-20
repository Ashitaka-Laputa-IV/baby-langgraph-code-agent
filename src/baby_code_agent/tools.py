"""Filesystem and shell tools exposed to the agent."""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path

from langchain_core.tools import BaseTool, tool

DEFAULT_OUTPUT_LIMIT = 12_000
SHELL_TIMEOUT_SECONDS = 60
VCS_METADATA = ".git"
BIDI_CONTROLS = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


class PathOutsideRoot(ValueError):
    """Raised when a tool path resolves outside the working directory."""


def _resolve_inside_root(root: Path, path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root):
        raise PathOutsideRoot(f"path escapes the working directory: {path}")
    return candidate


def _is_vcs_metadata(root: Path, candidate: Path) -> bool:
    relative = candidate.relative_to(root)
    return any(part.casefold() == VCS_METADATA.casefold() for part in relative.parts)


def _escape_control(char: str, *, show_whitespace: bool) -> str:
    if char == "\n":
        return "\\n" if show_whitespace else char
    if char == "\r":
        return "\\r" if show_whitespace else char
    if char == "\t":
        return "\\t" if show_whitespace else char
    if char == "\x1b":
        return "\\e"
    codepoint = ord(char)
    if codepoint < 32 or codepoint == 127 or 128 <= codepoint <= 159:
        return f"\\x{codepoint:02x}"
    if char in BIDI_CONTROLS:
        return f"\\u{codepoint:04x}"
    return char


def format_command_for_display(command: str) -> str:
    """Render a command so control characters and newlines are visible, not executed by the terminal."""
    return "".join(_escape_control(char, show_whitespace=True) for char in command)


def sanitize_for_terminal(text: str) -> str:
    """Render control characters visible so tool and model output cannot drive the terminal."""
    return "".join(_escape_control(char, show_whitespace=False) for char in text)


def _kill_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except ProcessLookupError:
        pass


def _truncate(text: str) -> str:
    if len(text) <= DEFAULT_OUTPUT_LIMIT:
        return text
    return f"{text[:DEFAULT_OUTPUT_LIMIT]}\n...[output truncated at {DEFAULT_OUTPUT_LIMIT} characters]"


def build_tools(root: Path, confirm: Callable[[str], bool]) -> list[BaseTool]:
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
        if not target.is_dir():
            if target.exists():
                return f"Error: not a directory: {path}"
            return f"Error: no such directory: {path}"

        entries = []
        for entry in sorted(target.iterdir(), key=lambda item: item.name.casefold()):
            entries.append(f"{entry.name}/" if entry.is_dir() else entry.name)
        if not entries:
            return "(empty directory)"
        return _truncate("\n".join(entries))

    @tool
    def read_file(path: str) -> str:
        """Read a UTF-8 text file inside the working directory and return it with line numbers."""
        try:
            target = _resolve_inside_root(root, path)
        except PathOutsideRoot as exc:
            return f"Error: {exc}"
        try:
            text = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"Error: no such file: {path}"
        except IsADirectoryError:
            return f"Error: not a file: {path}"
        except UnicodeDecodeError:
            return f"Error: not a UTF-8 text file: {path}"
        except OSError as exc:
            return f"Error: cannot read {path}: {exc}"

        numbered = [f"{number:>5}\t{line}" for number, line in enumerate(text.splitlines(), 1)]
        if not numbered:
            return "(empty file)"
        return _truncate("\n".join(numbered))

    @tool
    def write_file(path: str, content: str) -> str:
        """Write UTF-8 text to a file inside the working directory, creating parent directories."""
        try:
            target = _resolve_inside_root(root, path)
        except PathOutsideRoot as exc:
            return f"Error: {exc}"
        if _is_vcs_metadata(root, target):
            return f"Error: refusing to write version-control metadata: {path}"
        if target.is_dir():
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
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                start_new_session=os.name != "nt",
                creationflags=(
                    subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
                ),
            )
        except OSError as exc:
            return f"Error: cannot run command: {exc}"

        timed_out = False
        try:
            output, _ = process.communicate(timeout=SHELL_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_tree(process)
            try:
                output, _ = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                output = ""

        header = f"$ {command}\n"
        if timed_out:
            header += f"Error: command timed out after {SHELL_TIMEOUT_SECONDS} seconds\n"
        elif process.returncode != 0:
            header += f"[exit code {process.returncode}]\n"
        if not (output or "").strip():
            output = "(no output)\n"
        return _truncate(header + output)

    return [list_dir, read_file, write_file, run_shell]
