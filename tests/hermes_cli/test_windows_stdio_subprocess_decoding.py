"""Regression tests for Windows subprocess text decoding."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows locale regression")
def test_configure_windows_stdio_makes_text_subprocess_decode_utf8() -> None:
    """A UTF-8 continuation byte invalid in cp1252 must not kill _readerthread."""
    script = r'''
import subprocess
import sys
from hermes_cli.stdio import configure_windows_stdio

configure_windows_stdio()
result = subprocess.run(
    [sys.executable, "-c", "import sys; sys.stdout.buffer.write('Ł'.encode('utf-8'))"],
    capture_output=True,
    text=True,
    check=True,
)
assert result.stdout == "Ł", repr(result.stdout)
'''
    env = dict(os.environ)
    env["PYTHONUTF8"] = "0"
    env.pop("PYTHONIOENCODING", None)

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "UnicodeDecodeError" not in result.stderr
    assert "_readerthread" not in result.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="Windows locale regression")
def test_configure_windows_stdio_preserves_explicit_and_binary_subprocess_modes() -> None:
    """The process-wide default must not override deliberate caller choices."""
    from hermes_cli import stdio

    stdio._CONFIGURED = False
    stdio.configure_windows_stdio()

    explicit = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9')"],
        capture_output=True,
        text=True,
        encoding="latin-1",
        check=True,
    )
    binary = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff')"],
        capture_output=True,
        check=True,
    )

    assert explicit.stdout == "é"
    assert binary.stdout == b"\xff"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows locale regression")
def test_configure_windows_stdio_handles_all_implicit_text_mode_forms() -> None:
    """errors-only and positional universal_newlines must also select UTF-8."""
    from hermes_cli import stdio

    stdio._CONFIGURED = False
    stdio.configure_windows_stdio()
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write('Ł'.encode('utf-8'))",
    ]

    errors_only = subprocess.run(
        command,
        capture_output=True,
        errors="replace",
        check=True,
    )
    positional = subprocess.Popen(
        command,
        -1,
        None,
        None,
        subprocess.PIPE,
        subprocess.PIPE,
        None,
        True,
        False,
        None,
        None,
        True,
    )
    positional_stdout, positional_stderr = positional.communicate(timeout=30)

    assert errors_only.stdout == "Ł"
    assert positional.returncode == 0, positional_stderr
    assert positional_stdout == "Ł"
