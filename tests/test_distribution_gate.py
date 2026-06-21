"""P5 distribution gate: one explicit test per `Gate Distribuzione` condition
from ProductionPlan.md, wired to the real modules. Consolidates guarantees built
across P0-P4 into a single release-blocking contract, and closes the real gap on
``scrub_legacy_provider_keys`` (legacy config migration / key redaction).

Automated subset only: real hardware, SmartScreen, Defender and the pilot stay
owner-gated (see docs/12_ImplementationPlan.md, P5 Feature Context Pack).
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import config as config_mod  # noqa: E402
from seed.core import forbidden  # noqa: E402
from seed.core import model_bundle  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.llm import LLMResponse  # noqa: E402
from seed.core.model_router import ModelRouter  # noqa: E402
from seed.core.provider_hub import ProviderHub  # noqa: E402
from seed.supervisor import BootSupervisor  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- fakes (no real provider, no real key) --------------------------------
class _Response:
    def __init__(self, payload, ok=True):
        self.payload, self.ok = payload, ok

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("401")

    def json(self):
        return self.payload


class _FakeHTTP:
    def __init__(self, models=None):
        self.models = models or ["gemma4:31b", "qwen3-coder-next", "gpt-oss:120b"]

    def __call__(self, method, url, **kwargs):
        if method == "GET":
            return _Response({"data": [{"id": m} for m in self.models]})
        return _Response({"choices": [{"message": {"content": "OK"}}]})


class _FakeClient:
    def __init__(self, fail=False):
        self.has_key = True
        self.fail = fail
        self.calls = []

    def chat(self, messages, *, model=None, **kwargs):
        self.calls.append(model)
        if self.fail:
            raise RuntimeError("provider down")
        return LLMResponse(text=f"ok:{model}")


# --- Gate 1: perdita dati -------------------------------------------------
def test_gate_no_data_loss_user_data_lives_outside_payload_and_survives_update(
    tmp_path, monkeypatch
):
    installer = (ROOT / "installer" / "SEED.iss").read_text(encoding="utf-8")
    # i dati utente stanno sotto %LOCALAPPDATA%\SEED, mai nell'app installata
    assert "{localappdata}\\SEED" in installer
    # contratto operativo: l'update dichiara la preservazione dei dati
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    app = SeedApp(SeedConfig())
    try:
        assert app.ui_operations()["data_preserved_during_update"] is True
    finally:
        app.memory.close()


# --- Gate 2: key esposta --------------------------------------------------
def test_gate_no_key_exposed_at_rest_or_in_public_output(tmp_path):
    hub = ProviderHub(tmp_path / "providers.json", request=_FakeHTTP())
    hub.validate_and_save("ollama_cloud", "super-secret-key")
    assert "super-secret-key" not in hub.path.read_text(encoding="utf-8")
    assert "super-secret-key" not in json.dumps(hub.status())
    assert hub.runtime().api_key == "super-secret-key"   # ma utilizzabile a runtime


def test_gate_legacy_plaintext_keys_are_scrubbed_after_hub_migration(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "core_config_dir", lambda: tmp_path)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "llm": {"api_key": "legacy-llm-key", "base_url": "x"},
        "models": {"api_key": "legacy-models-key", "provider": "openrouter"},
    }), encoding="utf-8")

    changed = config_mod.scrub_legacy_provider_keys(path=cfg)

    assert changed is True
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["llm"]["api_key"] == ""
    assert data["models"]["api_key"] == ""
    assert data["llm"]["base_url"] == "x"          # resto del config intatto
    # idempotente: senza key legacy non riscrive e ritorna False
    assert config_mod.scrub_legacy_provider_keys(path=cfg) is False


def test_gate_scrub_refuses_files_outside_installed_core_config(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "core_config_dir", lambda: tmp_path / "core")
    (tmp_path / "core").mkdir()
    stray = tmp_path / "config.json"      # fuori dalla root core_config
    stray.write_text(json.dumps({"llm": {"api_key": "k"}}), encoding="utf-8")
    assert config_mod.scrub_legacy_provider_keys(path=stray) is False
    assert json.loads(stray.read_text(encoding="utf-8"))["llm"]["api_key"] == "k"


# --- Gate 3 + 4: update non reversibile / crash non recuperabile ----------
def test_gate_update_is_reversible_apply_then_rollback(tmp_path):
    sup = BootSupervisor(tmp_path / "data")
    runtime_dir = tmp_path / "install" / "runtime"
    runtime_dir.mkdir(parents=True)
    runtime = runtime_dir / "SEED.exe"
    runtime.write_bytes(b"OLD")
    updates = sup.root / "operations" / "updates"
    updates.mkdir(parents=True)
    package = updates / "runtime.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("SEED.exe", b"NEW")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (updates / "pending_update.json").write_text(json.dumps({
        "schema_version": "seed.pending-update.v1", "package": package.name,
        "sha256": digest, "apply_on_next_supervised_boot": True,
    }), encoding="utf-8")

    applied = sup.apply_pending_update(runtime)
    assert applied["applied"] is True and runtime.read_bytes() == b"NEW"

    rolled = sup.rollback_runtime_update(applied)
    assert rolled["rolled_back"] is True and runtime.read_bytes() == b"OLD"


def test_gate_corrupt_update_fails_closed_runtime_stays_recoverable(tmp_path):
    sup = BootSupervisor(tmp_path)
    runtime = tmp_path / "SEED.exe"
    runtime.write_bytes(b"OLD-RUNTIME")
    updates = tmp_path / "operations" / "updates"
    updates.mkdir(parents=True)
    pkg = updates / "update-pkg.exe"
    pkg.write_bytes(b"NEW-RUNTIME")
    (updates / "pending_update.json").write_text(json.dumps({
        "schema_version": "seed.pending-update.v1", "package": pkg.name,
        "sha256": "0" * 64, "apply_on_next_supervised_boot": True,   # hash errato
    }), encoding="utf-8")

    result = sup.apply_pending_update(runtime)
    assert result["applied"] is False
    assert runtime.read_bytes() == b"OLD-RUNTIME"          # known-good intatto


# --- Gate 5: checkpoint ML mancante ---------------------------------------
def test_gate_release_requires_all_three_ml_checkpoints():
    script = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
    for bundle in ('"privacy-filter"', '"emotion-wav2vec2"', '"embedding-mpnet"'):
        assert bundle in script


def test_gate_bundled_models_resolve_locally(tmp_path, monkeypatch):
    root = tmp_path / "models"
    for name in ("privacy-filter", "emotion-wav2vec2", "embedding-mpnet"):
        (root / name).mkdir(parents=True)
    monkeypatch.setenv("SEED_MODEL_BUNDLE", str(root))
    assert model_bundle.resolve("privacy_filter") == str(root / "privacy-filter")


# --- Gate 6: download runtime inatteso ------------------------------------
def test_gate_bundled_runtime_offline_only_when_forced(tmp_path, monkeypatch):
    import os
    root = tmp_path / "models"
    (root / "privacy-filter").mkdir(parents=True)
    monkeypatch.setenv("SEED_MODEL_BUNDLE", str(root))
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.delenv("SEED_FORCE_OFFLINE", raising=False)
    # default: bundle presente ma NIENTE offline globale (i modelli opzionali
    # devono potersi scaricare on-demand; i bundlati caricano per path locale).
    assert model_bundle.enforce_offline_if_bundled() is True
    assert "HF_HUB_OFFLINE" not in os.environ
    # offline duro solo se richiesto esplicitamente
    monkeypatch.setenv("SEED_FORCE_OFFLINE", "1")
    assert model_bundle.enforce_offline_if_bundled() is True
    assert os.environ["HF_HUB_OFFLINE"] == "1"


# --- Gate 7: onboarding aggirabile senza provider -------------------------
def test_gate_onboarding_not_bypassable_without_validated_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
    cfg = SeedConfig()
    cfg.provider_hub.required = True
    app = SeedApp(cfg)
    try:
        app.handle_message("accetto")
        blocked = app.handle_message("Sono una persona e questo e personale")
        assert app.onboarding.state["phase"] == "provider"
        assert "provider BYOK" in blocked
    finally:
        app.memory.close()


# --- Gate 8: fallback PAYG automatico -------------------------------------
def test_gate_cross_provider_fallback_is_ollama_only():
    primary = _FakeClient(fail=True)
    ollama = _FakeClient()
    router = ModelRouter(
        primary, {"conversation": "payg-model"}, provider="openrouter",
        ollama_fallback_client=ollama,
        ollama_fallback_roles={"conversation": "gemma4:31b"})
    assert router.invoke("conversation", []).text == "ok:gemma4:31b"
    assert ollama.calls == ["gemma4:31b"]


def test_gate_no_silent_payg_fallback_without_ollama_client():
    primary = _FakeClient(fail=True)
    router = ModelRouter(
        primary, {"conversation": "payg-model"}, provider="openrouter")
    # nessun client ollama: il primario fallito NON salta a un altro PAYG, rilancia
    with pytest.raises(RuntimeError, match="provider down"):
        router.invoke("conversation", [])


# --- Gate 9: uninstall cancella dati senza consenso -----------------------
def test_gate_uninstall_keeps_data_by_default_and_asks_consent():
    installer = (ROOT / "installer" / "SEED.iss").read_text(encoding="utf-8")
    assert "RemoveData" in installer        # scelta esplicita conserva/elimina
    assert "MB_DEFBUTTON2" in installer     # default = NON cancellare i dati
    assert "{localappdata}\\SEED" in installer
