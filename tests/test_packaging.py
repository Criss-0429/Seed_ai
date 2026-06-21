"""Packaging contract tests."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_release_version_is_consistent_across_runtime_and_bootstrap():
    expected = "0.3.3-pilot-p2"
    package = (ROOT / "seed" / "__init__.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "scripts" / "seed_bootstrap_installer.py").read_text(
        encoding="utf-8"
    )
    builder = (ROOT / "scripts" / "build_bootstrap_release.py").read_text(
        encoding="utf-8"
    )

    assert f'__version__ = "{expected}"' in package
    assert f'VERSION = "{expected}"' in bootstrap
    assert f'default="{expected}"' in builder


def test_pyinstaller_uses_package_entrypoint():
    spec = (ROOT / "packaging" / "pyinstaller" / "seed.spec").read_text(encoding="utf-8")
    assert "['../../build_entry.py']" in spec
    assert "['../seed/__main__.py']" not in spec
    assert "'tiktoken_ext.openai_public'" in spec
    assert "COLLECT(" in spec
    assert "exclude_binaries=True" in spec
    assert "icon='../../assets/seed.ico'" in spec
    assert "('../../assets', 'assets')" in spec


def test_build_entry_imports_seed_main_as_package():
    tree = ast.parse((ROOT / "build_entry.py").read_text(encoding="utf-8"))
    imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "seed.__main__"
        and any(alias.name == "main" for alias in node.names)
    ]
    assert imports


def test_runtime_has_noninteractive_smoke_mode():
    source = (ROOT / "seed" / "__main__.py").read_text(encoding="utf-8")
    assert 'if "--smoke" in argv:' in source
    assert "app.shutdown()" in source


def test_supervisor_pyinstaller_uses_package_entrypoint():
    spec = (ROOT / "packaging" / "pyinstaller" / "supervisor.spec").read_text(encoding="utf-8")
    assert "['../../supervisor_entry.py']" in spec
    assert "console=True" in spec
    assert "COLLECT(" in spec
    assert "exclude_binaries=True" in spec
    assert "icon='../../assets/seed.ico'" in spec


def test_supervisor_entry_imports_cli_as_package():
    tree = ast.parse((ROOT / "supervisor_entry.py").read_text(encoding="utf-8"))
    imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "seed.supervisor_cli"
        and any(alias.name == "main" for alias in node.names)
    ]
    assert imports


def test_repl_commands_tolerate_extra_colons():
    from seed.core.app import normalize_repl_command

    assert normalize_repl_command(":report") == ":report"
    assert normalize_repl_command(":::report") == ":report"
    assert normalize_repl_command("messaggio") == ""


def test_inno_shortcuts_always_launch_supervisor_and_preserve_data():
    installer = (ROOT / "installer" / "SEED.iss").read_text(encoding="utf-8")
    assert 'Filename: "{app}\\supervisor\\SEEDSupervisor.exe"' in installer
    assert '--boot --runtime ""{app}\\runtime\\SEED.exe""' in installer
    assert "{localappdata}\\SEED" in installer
    assert "DelTree" in installer and "RemoveData" in installer
    assert "UninstallSilent" in installer
    assert "MB_DEFBUTTON2" in installer
    assert "SetupIconFile=..\\assets\\seed.ico" in installer
    assert 'IconFilename: "{app}\\runtime\\SEED.exe"' in installer


def test_brand_assets_are_local_and_packaged():
    assert (ROOT / "assets" / "seed-mark.svg").is_file()
    icon = (ROOT / "assets" / "seed.ico").read_bytes()
    assert icon[:6] == b"\x00\x00\x01\x00\x01\x00"
    assert len(icon) > 22


def test_release_builder_requires_all_three_ml_bundles():
    script = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
    assert '"privacy-filter"' in script
    assert '"emotion-wav2vec2"' in script
    assert '"embedding-mpnet"' in script
    assert "release-manifest.json" in script
    assert "SHA256SUMS.txt" in script
    assert "finalize_installer" in script
    assert '"installer"' in script
    assert "prune_runtime" in script
    assert "Reset-SEED-Keep-Memory.ps1" in script


def test_tester_reset_script_is_guarded_and_release_hashed():
    reset = ROOT / "installer" / "Reset-SEED-Keep-Memory.ps1"
    source = reset.read_text(encoding="utf-8")
    bootstrap = (ROOT / "scripts" / "build_bootstrap_release.py").read_text(
        encoding="utf-8"
    )

    assert reset.is_file()
    assert "SupportsShouldProcess" in source and "$WhatIfPreference" in source
    assert 'Read-Host "Scrivi RESET-SEED per continuare"' in source
    assert "Assert-SafeLocalPath" in source and "Test-IsUnder" in source
    assert '@("seed.db", "seed.db-wal", "seed.db-shm")' in source
    assert "Get-FileHash" in source and "Assert-SqliteHeader" in source
    assert "CurrentVersion\\Run" in source and "SEED.lnk" in source
    assert 'release_assets["tester_reset"]' in bootstrap
    assert 'target / "Reset-SEED-Keep-Memory.ps1"' in bootstrap


def test_tester_reset_powershell_parses_when_available():
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return
    reset = ROOT / "installer" / "Reset-SEED-Keep-Memory.ps1"
    command = (
        "$tokens=$null; $errors=$null; "
        f"[void][System.Management.Automation.Language.Parser]::ParseFile('{reset}',"
        "[ref]$tokens,[ref]$errors); "
        "if($errors.Count){$errors | ForEach-Object { Write-Error $_ }; exit 1}"
    )
    subprocess.run(
        [powershell, "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )


def test_runtime_pruning_removes_tests_caches_and_unused_audio_stack(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "build_release", ROOT / "scripts" / "build_release.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    for relative in (
        "torch/testing/example.py",
        "pkg/__pycache__/cached.pyc",
        "librosa/module.py",
        "llvmlite.libs/native.dll",
        "keep/runtime.py",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")

    removed = module.prune_runtime(tmp_path)

    assert removed == {"files": 4, "bytes": 4}
    assert (tmp_path / "keep" / "runtime.py").is_file()
