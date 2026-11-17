#!/usr/bin/env python3
"""Offline, bounded preflight for explicitly labeled local paths."""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

MAX_INPUT = 256 * 1024
MAX_PATH_TEXT = 4096
_DRIVE = re.compile(r"^[A-Za-z]:")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_RESERVED_DEVICE = re.compile(r"^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?$", re.IGNORECASE)


class Invalid(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate_key")
        result[key] = value
    return result


def _bad_constant(_: str) -> None:
    raise Invalid("invalid_json")


def _validate_local_path(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_TEXT:
        raise Invalid("invalid_path")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise Invalid("invalid_path")
    # Windows treats these names (and trailing dots/spaces) specially even
    # when the checker itself is running on another platform.
    for part in re.split(r"[\\/]", value):
        trimmed = part.rstrip(" .")
        if trimmed and _RESERVED_DEVICE.fullmatch(trimmed):
            raise Invalid("unsupported_path")
        if part not in ("", ".", "..") and trimmed != part:
            raise Invalid("unsupported_path")
    # Reject URI schemes (including file:), UNC/network and device namespaces
    # before Path.resolve/stat can touch the filesystem.
    if value.startswith(("\\\\", "//")) or value.startswith(("\\?", "\\.")):
        raise Invalid("unsupported_path")
    if value.lower().startswith(("\\??\\", "\\device\\", "\\global??\\")):
        raise Invalid("unsupported_path")
    drive = _DRIVE.match(value)
    if drive:
        if len(value) < 3 or value[2] not in "\\/":
            raise Invalid("unsupported_path")  # drive-relative, e.g. C:foo
        if value[2:4] in ("//", "\\\\"):
            raise Invalid("unsupported_path")
        tail = value[2:]
        if ":" in tail:
            raise Invalid("unsupported_path")  # alternate data stream
        return value
    if _SCHEME.match(value):
        raise Invalid("unsupported_path")
    if ":" in value:
        raise Invalid("unsupported_path")
    return value


def _make_path(value: str) -> Path:
    # This utility checks paths native to the host running it. Foreign Windows
    # absolute paths on POSIX and vice versa are rejected rather than guessed.
    if os.name == "nt":
        if value.startswith("/") and not value.startswith("/\\"):
            # A single leading slash is rooted on the current drive; avoid it.
            raise Invalid("unsupported_path")
    elif _DRIVE.match(value):
        raise Invalid("unsupported_path")
    return Path(value)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _evaluate(document: dict[str, Any]) -> dict[str, Any]:
    if set(document) != {"base_directory", "launch_cwd", "paths"}:
        raise Invalid("invalid_shape")
    base_text = _validate_local_path(document["base_directory"])
    cwd_text = _validate_local_path(document["launch_cwd"])
    entries = document["paths"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise Invalid("invalid_shape")

    checked: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"label", "value", "kind"}:
            raise Invalid("invalid_shape")
        label, value, kind = entry["label"], entry["value"], entry["kind"]
        if not isinstance(label, str) or not _LABEL.fullmatch(label):
            raise Invalid("invalid_label")
        value = _validate_local_path(value)
        if kind not in ("file", "directory"):
            raise Invalid("invalid_kind")
        checked.append((value, kind))

    base = _make_path(base_text)
    if not base.is_absolute():
        raise Invalid("invalid_base")
    try:
        root = base.resolve(strict=True)
        if not root.is_dir():
            raise Invalid("invalid_base")
        cwd = _make_path(cwd_text)
        effective_cwd = cwd if cwd.is_absolute() else root / cwd
        effective_cwd = effective_cwd.resolve(strict=False)
        if not _inside(effective_cwd, root):
            raise Invalid("path_escape")
        if effective_cwd.exists() and not effective_cwd.is_dir():
            raise Invalid("invalid_cwd")
        results = []
        for ordinal, (value, kind) in enumerate(checked, 1):
            raw = _make_path(value)
            candidate = raw if raw.is_absolute() else effective_cwd / raw
            # resolve(strict=False) follows existing symlink/junction components,
            # allowing a missing leaf to be reported without opening it.
            resolved = candidate.resolve(strict=False)
            if not raw.is_absolute() and not _inside(resolved, root):
                raise Invalid("path_escape")
            try:
                info = resolved.stat()
            except FileNotFoundError:
                status = "missing"
            else:
                matches = stat.S_ISREG(info.st_mode) if kind == "file" else stat.S_ISDIR(info.st_mode)
                status = "ok" if matches else "wrong_kind"
            results.append({"ordinal": ordinal, "status": status})
        return {"results": results}
    except Invalid:
        raise
    except (OSError, RuntimeError):
        raise Invalid("io_error") from None


def main() -> int:
    try:
        data = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(data) > MAX_INPUT:
            raise Invalid("input_too_large")
        try:
            text = data.decode("utf-8", errors="strict")
            document = json.loads(
                text,
                object_pairs_hook=_pairs_no_duplicates,
                parse_constant=_bad_constant,
            )
        except Invalid:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
            raise Invalid("invalid_json") from None
        if not isinstance(document, dict):
            raise Invalid("invalid_shape")
        output = _evaluate(document)
        code = 0 if all(item["status"] == "ok" for item in output["results"]) else 1
    except Invalid as exc:
        output = {"error": exc.code}
        code = 2
    except OSError:
        output = {"error": "io_error"}
        code = 2
    # Write bytes to keep the JSON wire format identical on Windows and POSIX.
    sys.stdout.buffer.write((json.dumps(output, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n").encode("ascii"))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
