import os
from pathlib import Path

from agent.lsp import install


def test_windows_native_wrappers_precede_posix_shim(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(install, "_is_windows", lambda: True)

    candidates = install._native_binary_candidates(Path("pyright-langserver"))

    assert [path.suffix for path in candidates] == [".cmd", ".exe", ".bat", ""]

    extensionless = tmp_path / "pyright-langserver"
    native = tmp_path / "pyright-langserver.cmd"
    extensionless.write_text("#!/bin/sh\n", encoding="utf-8")
    native.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(install, "hermes_lsp_bin_dir", lambda: tmp_path)
    monkeypatch.setattr(install.os, "access", lambda path, mode: mode == os.X_OK)
    monkeypatch.setattr(install.shutil, "which", lambda name: None)

    assert install._existing_binary("pyright-langserver") == str(native)
