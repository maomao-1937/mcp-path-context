from __future__ import annotations

import json
import io
import os
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pathlib import Path

import mcp_path_context

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "mcp_path_context.py"


class CliTests(unittest.TestCase):
    def run_cli(self, data: bytes) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(SCRIPT)], input=data, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=ROOT, check=False,
        )

    def payload(self, base: Path, paths: list[dict[str, str]], cwd: str = ".") -> bytes:
        return json.dumps({"base_directory": str(base), "launch_cwd": cwd, "paths": paths}).encode()

    def test_exists_file_and_directory_exact_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "main.py").write_text("", encoding="utf-8")
            (base / "config").mkdir()
            result = self.run_cli(self.payload(base, [
                {"label": "script", "value": "main.py", "kind": "file"},
                {"label": "cfg", "value": "config", "kind": "directory"},
            ]))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'{"results":[{"ordinal":1,"status":"ok"},{"ordinal":2,"status":"ok"}]}\n')
        self.assertEqual(result.stderr, b"")

    def test_missing_and_wrong_kind_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "dir").mkdir()
            result = self.run_cli(self.payload(base, [
                {"label": "secret_name", "value": "absent", "kind": "file"},
                {"label": "file_as_dir", "value": "dir", "kind": "file"},
            ]))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b'{"results":[{"ordinal":1,"status":"missing"},{"ordinal":2,"status":"wrong_kind"}]}\n')
        self.assertNotIn(b"secret_name", result.stdout + result.stderr)

    def test_launch_cwd_and_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "sub").mkdir()
            (base / "sub" / "item").touch()
            absolute = base / "sub" / "item"
            result = self.run_cli(self.payload(base, [
                {"label": "rel", "value": "item", "kind": "file"},
                {"label": "abs", "value": str(absolute), "kind": "file"},
            ], "sub"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {"results": [{"ordinal": 1, "status": "ok"}, {"ordinal": 2, "status": "ok"}]})

    def test_invalid_documents_have_fixed_error_without_input_echo(self) -> None:
        for raw, expected in [(b"{", b'{"error":"invalid_json"}\n'), (b"\xff", b'{"error":"invalid_json"}\n')]:
            with self.subTest(raw=raw):
                result = self.run_cli(raw)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, b"")

    def test_duplicate_key_is_rejected(self) -> None:
        result = self.run_cli(b'{"base_directory":"/tmp","base_directory":"/tmp","launch_cwd":".","paths":[{"label":"x","value":"x","kind":"file"}]}')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'{"error":"duplicate_key"}\n')

    def test_oversize_rejected(self) -> None:
        result = self.run_cli(b" " * (256 * 1024 + 1))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'{"error":"input_too_large"}\n')

    def test_unsupported_path_forms_rejected_without_echo(self) -> None:
        bad_values = ["//server/share", "\\\\server\\share", "C:relative", "C://host/share", "file:///tmp/x", "name:stream", "\\\\?\\C:\\x", "\\??\\C:\\x", "NUL", "folder/trailing."]
        with tempfile.TemporaryDirectory() as tmp:
            for bad in bad_values:
                result = self.run_cli(self.payload(Path(tmp), [{"label": "secret_label", "value": bad, "kind": "file"}]))
                self.assertEqual(result.returncode, 2, bad)
                self.assertEqual(result.stdout, b'{"error":"unsupported_path"}\n', bad)
                self.assertNotIn(bad.encode(), result.stdout + result.stderr)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink support unavailable")
    def test_relative_symlink_escape_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base = Path(tmp)
            try:
                (base / "jump").symlink_to(Path(outside), target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc.__class__.__name__}")
            result = self.run_cli(self.payload(base, [{"label": "x", "value": "jump/secret", "kind": "file"}]))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'{"error":"path_escape"}\n')

    def test_relative_launch_cwd_escape_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = self.run_cli(self.payload(base, [{"label": "x", "value": "x", "kind": "file"}], "../outside"))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'{"error":"path_escape"}\n')

    def test_absolute_launch_cwd_outside_base_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base = Path(tmp)
            # Absolute path entries may intentionally target outside the base,
            # but the effective launch cwd itself must remain contained.
            external_file = Path(outside) / "allowed-explicit-target"
            external_file.touch()
            result = self.run_cli(self.payload(base, [
                {"label": "absolute_target", "value": str(external_file), "kind": "file"},
            ], str(Path(outside))) )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b'{"error":"path_escape"}\n')
        self.assertNotIn(b"allowed-explicit-target", result.stdout + result.stderr)

    def test_absolute_path_entry_outside_base_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base = Path(tmp)
            external_file = Path(outside) / "target"
            external_file.touch()
            result = self.run_cli(self.payload(base, [
                {"label": "absolute_target", "value": str(external_file), "kind": "file"},
            ], "."))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'{"results":[{"ordinal":1,"status":"ok"}]}\n')

    def test_resolution_runtime_error_is_normalized_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.payload(Path(tmp), [
                {"label": "secret_label", "value": "secret_path", "kind": "file"},
            ])
            fake_stdin = SimpleNamespace(buffer=io.BytesIO(payload))
            output = io.BytesIO()
            fake_stdout = SimpleNamespace(buffer=output)
            with patch.object(mcp_path_context.sys, "stdin", fake_stdin), \
                    patch.object(mcp_path_context.sys, "stdout", fake_stdout), \
                    patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop at secret_path")):
                code = mcp_path_context.main()
        self.assertEqual(code, 2)
        self.assertEqual(output.getvalue(), b'{"error":"io_error"}\n')
        self.assertNotIn(b"secret_label", output.getvalue())
        self.assertNotIn(b"secret_path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
