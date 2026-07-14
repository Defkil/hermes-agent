import os
from pathlib import Path

import pytest

from agent.lsp import install, servers


def test_windows_native_wrappers_precede_posix_shim(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(install, "_is_windows", lambda: True)

    candidates = install._native_binary_candidates(Path("pyright-langserver"))

    assert [path.suffix for path in candidates] == [".cmd", ".exe", ".bat"]

    extensionless = tmp_path / "pyright-langserver"
    native = tmp_path / "pyright-langserver.cmd"
    extensionless.write_text("#!/bin/sh\n", encoding="utf-8")
    native.write_text("@echo off\n", encoding="utf-8")
    monkeypatch.setattr(install, "hermes_lsp_bin_dir", lambda: tmp_path)
    monkeypatch.setattr(install.os, "access", lambda path, mode: mode == os.X_OK)
    monkeypatch.setattr(install.shutil, "which", lambda name: None)

    assert install._existing_binary("pyright-langserver") == str(native)


def test_server_lookup_prefers_windows_native_wrapper(monkeypatch) -> None:
    monkeypatch.setattr(servers.os, "name", "nt")
    paths = {
        "bash-language-server.cmd": r"C:\lsp\bash-language-server.cmd",
        "bash-language-server": r"C:\lsp\bash-language-server",
    }
    monkeypatch.setattr(servers.shutil, "which", paths.get)

    assert servers._which("bash-language-server") == paths["bash-language-server.cmd"]


def test_existing_binary_heals_copied_windows_npm_wrapper(monkeypatch, tmp_path) -> None:
    lsp_bin = tmp_path / "bin"
    npm_bin = tmp_path / "node_modules" / ".bin"
    lsp_bin.mkdir()
    npm_bin.mkdir(parents=True)
    source = npm_bin / "bash-language-server.cmd"
    source.write_text("@echo off\n", encoding="utf-8")
    staged = lsp_bin / source.name
    staged.write_text("@echo off\n..\\missing\\cli.js\n", encoding="utf-8")

    monkeypatch.setattr(install, "_is_windows", lambda: True)
    monkeypatch.setattr(install, "hermes_lsp_bin_dir", lambda: lsp_bin)
    monkeypatch.setattr(install.os, "access", lambda path, mode: mode == os.X_OK)

    assert install._existing_binary("bash-language-server") == str(staged)
    assert f'call "{source}" %*' in staged.read_text(encoding="utf-8")


def test_staging_windows_wrapper_does_not_overwrite_symlink_source(
    monkeypatch, tmp_path
) -> None:
    source = tmp_path / "source.cmd"
    destination = tmp_path / "staged.cmd"
    original = "@echo off\necho healthy\n"
    source.write_text(original, encoding="utf-8")
    try:
        destination.symlink_to(source)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    monkeypatch.setattr(install, "_is_windows", lambda: True)

    assert install._stage_binary(source, destination) == str(destination)
    assert source.read_text(encoding="utf-8") == original
    assert f'call "{source}" %*' in destination.read_text(encoding="utf-8")


def test_missing_optional_shellcheck_does_not_emit_runtime_warning(monkeypatch, caplog) -> None:
    monkeypatch.setattr(
        servers,
        "_which",
        lambda name: r"C:\lsp\bash-language-server.cmd"
        if name == "bash-language-server"
        else None,
    )
    monkeypatch.setattr(servers, "_BASH_SHELLCHECK_WARNED", False)

    with caplog.at_level("WARNING"):
        spec = servers._spawn_bash_ls("C:\repo", servers.ServerContext("C:\repo"))

    assert spec is not None
    assert not caplog.records
