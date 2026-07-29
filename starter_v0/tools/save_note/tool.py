from __future__ import annotations

from pathlib import Path
from typing import Any

from tools._shared import ROOT


NOTES_DIR = ROOT / "notes"
_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def _safe_filename(filename: str) -> tuple[str, str | None]:
    candidate = filename.strip()
    if not candidate:
        return "", "filename is required"
    if candidate in {".", ".."} or candidate.startswith("."):
        return "", "filename cannot be hidden or use a relative path marker"
    if any(character in _INVALID_FILENAME_CHARS or ord(character) < 32 for character in candidate):
        return "", "filename must be a plain file name without path or control characters"
    if candidate.endswith((" ", ".")):
        return "", "filename cannot end with a space or dot"

    path = Path(candidate)
    if path.suffix and path.suffix.casefold() != ".md":
        return "", "filename must use the .md extension"
    if not path.suffix:
        candidate += ".md"
        path = Path(candidate)

    if len(candidate) > 120:
        return "", "filename must be at most 120 characters"
    if path.stem.casefold() in _WINDOWS_RESERVED_NAMES:
        return "", "filename is reserved by the operating system"
    return candidate, None


def _error(code: str, message: str, filename: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {
        "tool": "save_note",
        "status": "error",
        "error": code,
        "message": message,
    }
    if filename:
        result["path"] = f"notes/{filename}"
    return result


def save_note(
    markdown: str = "",
    filename: str = "",
    confirmed: bool = False,
) -> dict[str, Any]:
    """Save Markdown under starter_v0/notes only after explicit confirmation."""
    try:
        if not isinstance(markdown, str) or not markdown.strip():
            return _error("invalid_markdown", "markdown must be a non-empty string")
        if not isinstance(filename, str):
            return _error("invalid_filename", "filename must be a string")
        if not isinstance(confirmed, bool):
            return _error("invalid_confirmation", "confirmed must be a boolean")

        safe_name, validation_error = _safe_filename(filename)
        if validation_error:
            return _error("invalid_filename", validation_error)

        relative_path = f"notes/{safe_name}"
        if not confirmed:
            return {
                "tool": "save_note",
                "status": "needs_confirmation",
                "path": relative_path,
                "message": (
                    f"Confirm before saving {relative_path}. "
                    "No file has been written."
                ),
                "error": None,
            }

        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        target = NOTES_DIR / safe_name
        try:
            with target.open("x", encoding="utf-8", newline="\n") as note_file:
                note_file.write(markdown)
        except FileExistsError:
            return _error(
                "already_exists",
                "the note already exists; choose a different filename",
                safe_name,
            )

        return {
            "tool": "save_note",
            "status": "saved",
            "path": relative_path,
            "characters_written": len(markdown),
            "bytes_written": len(markdown.encode("utf-8")),
            "error": None,
        }
    except Exception as exc:
        return _error(type(exc).__name__, str(exc))
