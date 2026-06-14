"""Packaging contract tests."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyinstaller_uses_package_entrypoint():
    spec = (ROOT / "build" / "seed.spec").read_text(encoding="utf-8")
    assert "['../build_entry.py']" in spec
    assert "['../seed/__main__.py']" not in spec
    assert "'tiktoken_ext.openai_public'" in spec
    assert "COLLECT(" in spec
    assert "exclude_binaries=True" in spec


def test_build_entry_imports_seed_main_as_package():
    tree = ast.parse((ROOT / "build_entry.py").read_text(encoding="utf-8"))
    imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "seed.__main__"
        and any(alias.name == "main" for alias in node.names)
    ]
    assert imports


def test_supervisor_pyinstaller_uses_package_entrypoint():
    spec = (ROOT / "build" / "supervisor.spec").read_text(encoding="utf-8")
    assert "['../supervisor_entry.py']" in spec
    assert "console=True" in spec
    assert "COLLECT(" in spec
    assert "exclude_binaries=True" in spec


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


def test_release_builder_requires_all_three_ml_bundles():
    script = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
    assert '"privacy-filter"' in script
    assert '"emotion-wav2vec2"' in script
    assert '"embedding-mpnet"' in script
    assert "release-manifest.json" in script
    assert "SHA256SUMS.txt" in script
