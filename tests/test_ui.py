"""UI track: U7 governance (P0-P5 gate + ui_directives), U2/U3 bridge hooks
(Modello Utente, Permessi), e struttura della surface."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from seed.core import ui_governance as ui  # noqa: E402
from seed.core.directive_pack import build_directive_pack  # noqa: E402
from seed.core.app import SeedApp  # noqa: E402
from seed.core.config import SeedConfig  # noqa: E402
from seed.core.knowledge import UserClaim  # noqa: E402
from seed.ui.shell import JsApi  # noqa: E402

_SURFACE = Path(__file__).resolve().parents[1] / "seed" / "ui" / "surface" / "index.html"


# --- U7: precedence gate --------------------------------------------------
def test_p0_violation_not_candidable():
    v = ui.evaluate_ui_mutation(violated_precedence=("P0_control_safety",))
    assert not v.candidable and "P0_control_safety" in v.blocking


def test_p1_violation_not_candidable():
    v = ui.evaluate_ui_mutation(violated_precedence=("P1_accessibility",))
    assert not v.candidable


def test_p4_violation_blocked_without_evidence():
    v = ui.evaluate_ui_mutation(violated_precedence=("P4_best_practice",))
    assert not v.candidable and "P4_best_practice" in v.blocking


def test_p4_violation_ok_with_p2_p3_evidence():
    v = ui.evaluate_ui_mutation(violated_precedence=("P4_best_practice",),
                                justifying_evidence=("P3_repeated_behavior",))
    assert v.candidable


def test_clean_mutation_is_candidable():
    v = ui.evaluate_ui_mutation(violated_precedence=())
    assert v.candidable and v.reasons == ("ui_precedence_ok",)


def test_unknown_precedence_raises():
    with pytest.raises(ui.UiGovernanceError):
        ui.evaluate_ui_mutation(violated_precedence=("P9_void",))


# --- U7: directive pack ui section ---------------------------------------
def test_ui_directives_section_has_never_derogable():
    section = ui.ui_directives_section()
    assert "P0_control_safety" in section["never_derogable"]
    assert "P1_accessibility" in section["never_derogable"]


def test_pack_with_ui_directives_changes_version_and_adds_section():
    base = build_directive_pack(feature="core", scope="policy", candidate={})
    withui = build_directive_pack(feature="ui", scope="ui", candidate={})
    assert withui.directive_pack_version != base.directive_pack_version
    assert withui.to_dict()["ui_directives"]["precedence"][0] == "P0_control_safety"
    assert "ui_directives" not in base.to_dict()

def test_guidelines_are_fully_represented():
    ids = {d["source_id"] for d in ui.UI_DIRECTIVES}
    for prefix, count in (("A", 10), ("B", 10), ("C", 6), ("D", 12), ("E", 5)):
        assert {f"{prefix}-{i:02d}" for i in range(1, count + 1)} <= ids


# --- U2: bridge hooks (Modello Utente + Permessi) -------------------------
def _app(tmp_path, monkeypatch):
    monkeypatch.setenv("SEED_DATA_ROOT", str(tmp_path))
    return SeedApp(SeedConfig())


def test_user_model_excludes_sensitive_and_shows_provenance(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    app.knowledge_store.record(UserClaim(
        claim_type="fact", subject="lavoro", value="ingegnere",
        confidence=0.9, confidence_source="explicit", provenance=[1]).normalized())
    app.knowledge_store.record(UserClaim(
        claim_type="fact", subject="salute", value="dettaglio clinico",
        confidence=0.9, confidence_source="explicit", sensitivity="sensitive").normalized())
    model = app.ui_user_model()
    values = [c["value"] for c in model]
    assert "ingegnere" in values
    assert "dettaglio clinico" not in values        # sensibile escluso
    assert all("provenance" in c for c in model)
    app.shutdown()


def test_correct_claim_false_supersedes(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    app.knowledge_store.record(UserClaim(
        claim_type="fact", subject="citta", value="Roma",
        confidence=0.9, confidence_source="explicit").normalized())
    claim = app.ui_user_model()[0]
    res = app.ui_correct_claim(claim["id"], is_true=False)
    assert res["action"] == "corrected"
    assert all(c["value"] != "Roma" for c in app.ui_user_model())   # superseded
    app.shutdown()


def test_permissions_surface_reports_observation_off_by_default(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    perms = app.ui_permissions()
    assert perms["observation"]["enabled"] is False
    assert perms["observation"]["consented_classes"] == []
    app.shutdown()


def test_jsapi_exposes_surface_methods(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    jsapi = JsApi(app)
    assert isinstance(jsapi.user_model(), list)
    assert "observation" in jsapi.permissions()
    assert isinstance(jsapi.daemon_status(), dict)
    assert jsapi.initial_state()["onboarding_complete"] is False
    app.shutdown()

def test_jsapi_voice_bridge_and_window_modes(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.setattr(app, "voice_message",
                        lambda audio, mime: {"transcript": str(len(audio)), "answer": mime})
    monkeypatch.setattr(app, "voice_reply_audio", lambda text: b"mp3")
    jsapi = JsApi(app)
    assert jsapi.voice_message("YWJj", "audio/webm") == {
        "transcript": "3", "answer": "audio/webm"}
    assert jsapi.voice_reply_audio("ciao")["audio_b64"] == "bXAz"
    assert jsapi.set_window_mode("overlay")["ok"] is False
    app.shutdown()

def test_jsapi_window_mode_resizes_and_sets_topmost(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)

    class Window:
        on_top = False
        size = None
        def restore(self): pass
        def resize(self, width, height): self.size = (width, height)

    window = Window()
    jsapi = JsApi(app)
    jsapi.attach(window)
    result = jsapi.set_window_mode("overlay")
    assert result["ok"] and window.size == (660, 116) and window.on_top is True
    app.shutdown()


# --- UI surface structure: design fedele al SEED Prototype (oklch/DM/orb) -----
def test_surface_uses_prototype_design_tokens():
    html = _SURFACE.read_text(encoding="utf-8")
    assert "oklch(" in html                          # palette del prototipo
    assert "Segoe UI Variable Text" in html and "Cascadia Mono" in html  # offline
    assert "sd-breathe" in html                      # motion = respiro
    assert "SEED Prototype" in html                  # riferimento al design


def test_surface_has_orb_states_and_accessibility():
    html = _SURFACE.read_text(encoding="utf-8")
    for state in ("idle", "listening", "thinking", "speaking"):
        assert state in html                         # 5 stati orb del prototipo
    assert "prefers-reduced-motion" in html          # P1 reduce-motion
    assert "seedAskPermission" in html               # P0 permission dialog
    assert "code === 'Period'" in html or "Ctrl + ." in html  # superfici


def test_surface_is_offline_no_react_no_claude_complete():
    html = _SURFACE.read_text(encoding="utf-8")
    # app Python offline: niente runtime React/DC ne window.claude del prototipo
    assert "window.claude" not in html
    assert "support.js" not in html
    assert "window.pywebview.api" in html            # wired al backend Python
    assert "https://" not in html and "http://" not in html


def test_surface_has_user_model_and_permissions_surfaces():
    html = _SURFACE.read_text(encoding="utf-8")
    assert "user_model" in html and "correct_claim" in html
    assert "set_observation_consent" in html and "revoke_observations" in html
    assert "MODELLO UTENTE" in html and "PERMESSI E PRIVACY" in html


def test_surface_fills_window_no_fake_chrome_and_mode_exit():
    html = _SURFACE.read_text(encoding="utf-8")
    # niente finta finestra mac: #win riempie il SO, nessuna card centrata/fissa
    assert "100vw; height: 100vh" in html
    assert "min(1100px" not in html              # rimossa la dimensione fissa
    assert '<div class="dot">' not in html       # rimossi i pallini stile mac (titlebar)
    # ritorno garantito da presenza/overlay (non solo Esc)
    assert 'id="mode-exit"' in html
    assert "body.mode-presence #mode-exit" in html and "body.mode-overlay #mode-exit" in html


def test_frameless_window_with_custom_titlebar_controls():
    html = _SURFACE.read_text(encoding="utf-8")
    # titlebar custom trascinabile (finestra frameless) + min/chiudi
    assert "pywebview-drag-region" in html
    assert 'id="min-btn"' in html and 'id="close-btn"' in html
    assert "window_minimize" in html and "window_close" in html
    # backend frameless + controlli
    shell = (Path(__file__).resolve().parents[1] / "seed" / "ui" / "shell.py").read_text(encoding="utf-8")
    assert "frameless=True" in shell
    assert "def window_minimize" in shell and "def window_close" in shell


def test_presence_keeps_input_and_voice_layout_scrolls():
    html = _SURFACE.read_text(encoding="utf-8")
    # presenza nasconde la barra titolo ma NON la barra input (si puo' scrivere)
    assert "body.mode-presence .titlebar, body.mode-presence .hints { display: none; }" in html
    assert "body.mode-presence .inputwrap" in html
    # voice: area messaggio scrollabile (niente sovrapposizione col bottone)
    assert 'class="vmsg seed-scroll"' in html and "#voice .vmsg" in html
    assert ">OPPURE<" not in html                # divisore ridondante rimosso


def test_overlay_expands_in_place_and_window_draggable_everywhere():
    html = _SURFACE.read_text(encoding="utf-8")
    # overlay: niente auto-switch a presenza; si espande in-place con la risposta
    assert "setWindowMode('presence')" not in html
    assert 'id="ov-answer"' in html and "set_overlay_size" in html
    assert "body.mode-overlay.ov-answer #ov-answer" in html
    # maniglia di trascinamento in ogni modalita' (presenza/overlay/voce)
    assert 'id="grip"' in html and "pywebview-drag-region" in html
    assert "body.voicing #grip" in html
    shell = (Path(__file__).resolve().parents[1] / "seed" / "ui" / "shell.py").read_text(encoding="utf-8")
    assert "def set_overlay_size" in shell


def test_panel_action_buttons_have_consistent_style():
    html = _SURFACE.read_text(encoding="utf-8")
    # i bottoni full-width dei pannelli non usano lo stile OS di default
    assert ".close { display: block;" in html
    assert "button.chip:hover" in html


def test_mode_switch_is_decoupled_from_resize():
    html = _SURFACE.read_text(encoding="utf-8")
    # setWindowMode applica le classi sempre; il resize e' best-effort, mai bloccante
    assert "classList.add('mode-' + mode)" in html
    assert "if (api && api.set_window_mode) await api.set_window_mode(mode)" in html
    assert "if (!result.ok)" not in html         # niente abort-prima-di-applicare


def test_surface_has_system_surface_wired_to_managers():
    html = _SURFACE.read_text(encoding="utf-8")
    assert "openSystem" in html and "SISTEMA" in html
    # collegata ai manager via JsApi (tool builder / mutazioni / operazioni)
    assert "tool_candidates" in html and "tool_install" in html
    assert "promote_mutation" in html and "advance_mutations" in html
    assert "operations_status" in html and "create_backup" in html

def test_surface_connects_onboarding_voice_modes_and_evolution():
    html = _SURFACE.read_text(encoding="utf-8")
    for token in ("initial_state", "voice_message", "voice_reply_audio",
                  "set_window_mode", "openEvolution", "Ctrl + Spazio"):
        assert token in html
