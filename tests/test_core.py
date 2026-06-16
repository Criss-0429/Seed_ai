"""Smoke test del core SEED — eseguibili anche su Linux (dev/CI).

Coprono: forbidden paths, privacy regex + pseudonimi, audit statico AST,
memoria, validazione manifest, evolution (validate/apply/rollback) con LLM mock.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import forbidden, sandbox  # noqa: E402
from seed.core.capabilities import validate_manifest  # noqa: E402
from seed.core.memory import Memory  # noqa: E402
from seed.core.privacy import PrivacyGate  # noqa: E402


# ---------------------------------------------------------------------------
# forbidden
# ---------------------------------------------------------------------------
class TestForbidden:
    def test_system_roots_write_denied(self):
        for p in (r"C:\Windows\System32\evil.dll",
                  r"C:\Program Files\app\x.exe",
                  r"C:\ProgramData\x",
                  r"C:\Boot\x"):
            assert forbidden.is_write_denied(p), p

    def test_other_user_profile_denied(self):
        assert forbidden.is_write_denied(r"C:\Users\altroutente\Desktop\x.txt")
        assert forbidden.is_read_denied(r"C:\Users\altroutente\Documents\diario.txt")

    def test_secret_files_read_denied(self):
        for p in (r"C:\Users\me\.ssh\id_rsa",
                  r"C:\repo\.env",
                  r"C:\x\cert.pem",
                  r"C:\Users\me\AppData\Local\Google\Chrome\User Data\Default\Login Data"):
            assert forbidden.is_read_denied(p), p

    def test_workspace_write_allowed(self):
        ws = forbidden.workspace_dir() / "out.txt"
        assert not forbidden.is_write_denied(str(ws))

    def test_core_config_write_denied(self):
        cfg = forbidden.core_config_dir() / "config.json"
        assert forbidden.is_write_denied(str(cfg))

    def test_check_raises(self):
        with pytest.raises(PermissionError):
            forbidden.check(r"C:\Windows\notepad.exe", "write")


# ---------------------------------------------------------------------------
# privacy (layer regex; il layer opf richiede il modello installato)
# ---------------------------------------------------------------------------
class TestPrivacy:
    @pytest.fixture()
    def gate(self, tmp_path):
        mem = Memory(tmp_path / "t.db")
        return PrivacyGate(mem), mem

    def test_email_redacted_and_stable(self, gate):
        g, _ = gate
        r1 = g.redact("scrivi a mario.rossi@example.com per il report")
        assert "mario.rossi@example.com" not in r1.text
        assert "[EMAIL_1]" in r1.text
        r2 = g.redact("poi mario.rossi@example.com risponde")
        assert "[EMAIL_1]" in r2.text  # placeholder stabile

    def test_secrets_redacted(self, gate):
        g, _ = gate
        r = g.redact("la key e' sk-abcdefghijklmnop1234567890")
        assert "sk-abcdefghijklmnop" not in r.text

    def test_iban_cf_phone(self, gate):
        g, _ = gate
        r = g.redact("IBAN IT60X0542811101000000123456, CF RSSMRA85T10A562S, tel +39 333 1234567")
        assert "IT60X0542811101000000123456" not in r.text
        assert "RSSMRA85T10A562S" not in r.text.upper() or "[CF_" in r.text

    def test_rehydrate_roundtrip(self, gate):
        g, _ = gate
        g.redact("contatta mario.rossi@example.com")
        out = g.rehydrate(f"Ok, scrivo a {'[EMAIL_1]'}")
        assert "mario.rossi@example.com" in out

    def test_non_persistent_redaction_does_not_create_pii_map(self, gate):
        g, memory = gate
        red = g.redact(
            "contatta mario.rossi@example.com", persist_mapping=False
        )

        assert red.text == "contatta [EMAIL]"
        assert memory.pii_map_all() == []


# ---------------------------------------------------------------------------
# audit statico
# ---------------------------------------------------------------------------
class TestStaticAudit:
    def test_clean_code_passes(self):
        code = "import json, sys\npayload = json.loads(sys.stdin.read())\nprint(json.dumps({'ok': True}))\n"
        assert sandbox.static_audit(code).passed

    def test_eval_rejected(self):
        assert not sandbox.static_audit("eval('1+1')").passed

    def test_subprocess_rejected(self):
        assert not sandbox.static_audit("import subprocess\n").passed

    def test_ctypes_winreg_rejected(self):
        assert not sandbox.static_audit("import ctypes\n").passed
        assert not sandbox.static_audit("import winreg\n").passed

    def test_network_without_flag_rejected(self):
        code = "import urllib.request\n"
        assert not sandbox.static_audit(code, needs_network=False).passed
        assert sandbox.static_audit(code, needs_network=True).passed

    def test_forbidden_path_literal_rejected(self):
        assert not sandbox.static_audit("p = 'C:\\\\Windows\\\\System32'\n").passed

    def test_os_system_rejected(self):
        assert not sandbox.static_audit("import os\nos.system('dir')\n").passed


# ---------------------------------------------------------------------------
# memoria
# ---------------------------------------------------------------------------
class TestMemory:
    def test_episode_fact_pref_roundtrip(self, tmp_path):
        m = Memory(tmp_path / "m.db")
        eid = m.add_episode("chat", {"text": "ciao"}, category="chat")
        fid = m.add_fact("usa excel ogni mattina", 0.8, [eid])
        assert m.active_facts()[0]["statement"] == "usa excel ogni mattina"
        m.supersede_fact(fid)
        assert m.active_facts() == []
        m.set_preference("lingua", "it")
        assert m.preferences() == {"lingua": "it"}

    def test_grants(self, tmp_path):
        m = Memory(tmp_path / "g.db")
        m.record_grant("open_app", "spotify", "allow", True)
        assert m.find_grant("open_app", "spotify") == "allow"
        assert m.find_grant("open_app", "altra") is None

    def test_capability_stats(self, tmp_path):
        m = Memory(tmp_path / "s.db")
        m.bump_capability("x", True)
        m.bump_capability("x", False)
        s = m.capability_stats()[0]
        assert s["invocations"] == 2 and s["successes"] == 1


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------
class TestManifest:
    def _base(self):
        return {"capability_id": "t", "description": "d", "input_schema": {},
                "risk_class": "safe", "origin": "generated"}

    def test_valid(self):
        assert validate_manifest(self._base()) == []

    def test_destructive_rejected(self):
        m = {**self._base(), "risk_class": "destructive"}
        assert any("vietata" in e for e in validate_manifest(m))

    def test_missing_keys(self):
        assert validate_manifest({"capability_id": "x"})


# ---------------------------------------------------------------------------
# evolution con LLM mock
# ---------------------------------------------------------------------------
class TestEvolution:
    @pytest.fixture()
    def engine(self, tmp_path, monkeypatch):
        from seed.core import config as cfg_mod
        from seed.core.evolution import EvolutionEngine
        from seed.core.permissions import PermissionBroker

        monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
        mem = Memory(tmp_path / "e.db")
        gate = PrivacyGate(mem)
        broker = PermissionBroker(mem, ask_callback=lambda r: {"decision": "allow", "remember": False})

        class MockLLM:
            def __init__(self):
                self.responses = []

            def chat(self, messages, **kw):
                from seed.core.llm import LLMResponse
                return LLMResponse(text=self.responses.pop(0))

        from seed.core.capabilities import CapabilityRegistry
        reg = CapabilityRegistry(mem, broker, builtin_dir=tmp_path / "none")
        cfg = cfg_mod.SeedConfig()
        llm = MockLLM()
        eng = EvolutionEngine(cfg, mem, gate, llm, reg)
        return eng, llm, mem

    def test_trait_change_applied_and_cooldown(self, engine):
        eng, llm, _ = engine
        mutation = {"type": "trait_change", "target": "ui.density",
                    "diff": {"value": 0.8}, "reason": "test",
                    "expected_signal": "x", "risk_class": "safe"}
        ok, _ = eng._validate_and_apply(mutation)
        assert ok
        assert eng.user_model()["ui"]["density"] == 0.8
        ok2, note = eng._validate_and_apply(mutation)
        assert not ok2 and "cooldown" in note

    def test_unknown_type_rejected(self, engine):
        eng, _, _ = engine
        ok, _ = eng._validate_and_apply({"type": "hack_core", "diff": {}})
        assert not ok

    def test_full_reflection_with_mock(self, engine):
        eng, llm, mem = engine
        llm.responses = [
            json.dumps({"mutations": [
                {"type": "ui_change", "target": "theme",
                 "diff": {"accent": "#cc7722"},
                 "reason": "usa spesso app creative",
                 "expected_signal": "apre l'app domani", "risk_class": "safe"}]}),
            json.dumps({"selected": [0], "reasoning": "unica candidata"}),
        ]
        digest = eng.run_reflection()
        assert digest["applied"] == []
        assert len(digest["proposed"]) == 1
        assert eng.ui_manifest()["theme"]["accent"] == "#888888"
        mutation_id = digest["proposed"][0]["mutation_id"]
        assert eng.lineage.current_status(mutation_id) == "shadow"
        assert eng.lineage.proposal(mutation_id)["diff"]["accent"] == "#cc7722"
        assert eng.lineage.has_passing_evaluation(mutation_id)
        assert digest["proposed"][0]["evaluation"]["outcome"] == "pass"
        assert digest["proposed"][0]["evaluation"]["descendant_executed"] is False
        assert digest["proposed"][0]["evaluation"]["provider_called"] is False
        artifact = digest["proposed"][0]["artifact_ref"]
        assert eng.descendants.verify(forbidden.seed_data_dir() / artifact)
        from seed.core.telemetry import Telemetry
        lineage_report = Telemetry(mem, eng).build_report()["evolution"]["lineage"]
        assert lineage_report == {
            "available": True,
            "integrity_ok": True,
            "candidates": 1,
            "evaluations": 2,
            "status_counts": {"shadow": 1},
            "exposure_starts": {"shadow": 1, "canary": 0},
            "exposure_observations": 0,
            "promotion_authorizations": 0,
            "promotion_decisions": {},
            "lineage_rollbacks": 0,
        }

    def test_reflection_accepts_fenced_json(self, engine):
        eng, llm, _ = engine
        llm.responses = [
            '```json\n' + json.dumps({"mutations": [
                {"type": "ui_change", "target": "theme",
                 "diff": {"accent": "#cc7722"},
                 "reason": "fixture fenced",
                 "expected_signal": "observe", "risk_class": "safe",
                 "permissions_delta": []}]}) + '\n```',
            'Risposta:\n' + json.dumps({"selected": [0], "reasoning": "valid"}),
        ]
        digest = eng.run_reflection()
        assert len(digest["proposed"]) == 1
        assert digest["proposed"][0]["status"] == "shadow"

    def test_ui_deterministic_design_gate_blocks_shadow(self, engine):
        from seed.core.design_review import DesignReviewer

        class Models:
            def model_for(self, role):
                return "unused"

        eng, llm, _ = engine
        eng.set_design_reviewer(DesignReviewer(), Models())
        llm.responses = [
            json.dumps({"mutations": [
                {"type": "ui_change", "target": "theme",
                 "diff": {"accent": "#cc7722"},
                 "reason": "test governance",
                 "expected_signal": "observe", "risk_class": "safe",
                 "ui_violated_precedence": ["P0_control_safety"]}]}),
            json.dumps({"selected": [0], "reasoning": "test"}),
        ]
        digest = eng.run_reflection()
        assert digest["proposed"], digest
        proposed = digest["proposed"][0]
        assert proposed["status"] == "rejected"
        assert proposed["design_review"]["model"] == "deterministic-ui-gate"
        assert proposed["design_review"]["blocking"] == 1

    def test_rollback_restores(self, engine):
        eng, _, _ = engine
        version = eng._snapshot().name
        ok, _ = eng._validate_and_apply(
            {"type": "ui_change", "target": "theme", "diff": {"accent": "#ff0000"},
             "reason": "legacy migration test", "expected_signal": "s", "risk_class": "safe"})
        assert ok
        assert eng.ui_manifest()["theme"]["accent"] == "#ff0000"
        assert eng.rollback(version, suppression_key="ui_change:theme")
        assert eng.ui_manifest()["theme"]["accent"] == "#888888"
        assert eng.policy()["suppressions"][0]["key"] == "ui_change:theme"

    def test_invalid_selected_proposal_is_recorded_then_rejected(self, engine):
        eng, llm, _ = engine
        llm.responses = [
            json.dumps({"mutations": [
                {"type": "hack_core", "target": "", "diff": {},
                 "reason": "", "expected_signal": "", "risk_class": "write"}]}),
            json.dumps({"selected": [0], "reasoning": "test invalid"}),
        ]
        digest = eng.run_reflection()
        rejected = next(note for note in digest["notes"]
                        if isinstance(note, dict) and note.get("status") == "rejected")
        assert eng.lineage.current_status(rejected["mutation_id"]) == "rejected"
        assert eng.lineage.proposal(rejected["mutation_id"])["type"] == "hack_core"

    def test_descendant_build_failure_is_rejected(self, engine):
        eng, llm, _ = engine
        llm.responses = [
            json.dumps({"mutations": [
                {"type": "ui_change", "target": "theme",
                 "diff": {"unknown_theme_key": "x"},
                 "reason": "test builder rejection",
                 "expected_signal": "observe", "risk_class": "safe"}]}),
            json.dumps({"selected": [0], "reasoning": "test build failure"}),
        ]
        digest = eng.run_reflection()
        failed = next(note for note in digest["notes"]
                      if isinstance(note, dict) and note.get("status") == "build_failed")
        assert eng.lineage.current_status(failed["mutation_id"]) == "rejected"
        assert not eng.lineage.has_passing_evaluation(failed["mutation_id"])

    def test_evaluator_failure_after_build_is_rejected(self, engine):
        eng, llm, _ = engine
        (eng.evaluator.replay_fixtures_root / "invalid.json").write_text(json.dumps({
            "fixture_id": "raw-fixture",
            "source": "trace",
            "redacted": False,
            "assertions": [{
                "assertion_id": "theme-exists",
                "file": "state/ui_manifest.json",
                "operator": "exists",
                "path": "theme",
            }],
        }), encoding="utf-8")
        llm.responses = [
            json.dumps({"mutations": [
                {"type": "ui_change", "target": "theme",
                 "diff": {"accent": "#cc7722"},
                 "reason": "test evaluator rejection",
                 "expected_signal": "observe", "risk_class": "safe"}]}),
            json.dumps({"selected": [0], "reasoning": "test evaluator failure"}),
        ]

        digest = eng.run_reflection()
        failed = next(note for note in digest["notes"]
                      if isinstance(note, dict)
                      and note.get("status") == "evaluation_failed")
        assert eng.lineage.current_status(failed["mutation_id"]) == "rejected"
        assert not eng.lineage.has_passing_evaluation(failed["mutation_id"])

    def test_snapshots_are_unique(self, engine):
        eng, _, _ = engine
        first = eng._snapshot()
        second = eng._snapshot()
        assert first != second
        assert first.exists() and second.exists()

    def test_baseline_instance_no_mutations(self, engine):
        eng, _, _ = engine
        eng._cfg.enabled = False
        digest = eng.run_reflection()
        assert digest["applied"] == []
        assert digest["proposed"] == []


# ---------------------------------------------------------------------------
# sandbox run (esegue davvero un tool builtin-like)
# ---------------------------------------------------------------------------
class TestSandboxRun:
    def test_run_tool_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
        cap = tmp_path / "echo_cap"
        cap.mkdir()
        (cap / "tool.py").write_text(
            "import json, sys\n"
            "p = json.loads(sys.stdin.read())\n"
            "print(json.dumps({'echo': p.get('msg', '')}))\n",
            encoding="utf-8")
        result = sandbox.run_tool(cap, {"msg": "ciao"}, timeout=10)
        assert result.ok and result.output == {"echo": "ciao"}

    def test_timeout_kills(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
        cap = tmp_path / "slow_cap"
        cap.mkdir()
        (cap / "tool.py").write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
        result = sandbox.run_tool(cap, {}, timeout=2)
        assert not result.ok and result.timed_out

    def test_env_has_no_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(forbidden, "seed_data_dir", lambda: tmp_path / "SEED")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-secret")
        cap = tmp_path / "env_cap"
        cap.mkdir()
        (cap / "tool.py").write_text(
            "import json, os\n"
            "print(json.dumps({'leak': os.environ.get('OPENROUTER_API_KEY', 'NONE')}))\n",
            encoding="utf-8")
        result = sandbox.run_tool(cap, {}, timeout=10)
        assert result.ok and result.output["leak"] == "NONE"
