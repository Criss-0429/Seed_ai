"""S10.5 shadow review su candidate SINTETICHE.

Esercita il design reviewer end-to-end senza toccare candidate reali, lineage di
produzione o promotion. Dati sintetici privacy-safe: nessun dato utente, nessun
segreto. Le review girano in SHADOW (owner gate chiuso per le reali). Prova il
contratto e la registrazione dell'evidenza, non la qualita' del giudizio reale.
"""

from __future__ import annotations

from .directive_pack import build_directive_pack


def synthetic_candidates() -> list[tuple[str, dict, str]]:
    """(candidate_id, artefatti, scope). Caso pulito + caso con potenziale
    violazione dichiarata negli artefatti (permission delta non dichiarato)."""
    clean = {
        "manifest": {"mutation_id": "shadow-clean", "scope": "policy_change"},
        "permission_delta": [],
        "diff": "policy.json: +1 -0 (tono piu' prudente)",
        "test_report": {"outcome": "pass", "tests": 12},
        "rollback_plan": "ripristina parent baseline",
    }
    risky = {
        "manifest": {"mutation_id": "shadow-permission", "scope": "policy_change"},
        "permission_delta": ["network: accesso aggiunto non dichiarato"],
        "diff": "policy.json: +1; capabilities: +network",
        "test_report": {"outcome": "pass", "tests": 12},
        "rollback_plan": "ripristina parent baseline",
    }
    return [
        ("shadow-clean", clean, "policy_change"),
        ("shadow-permission", risky, "policy_change"),
    ]


def run_shadow_review(reviewer, models, *, feature: str = "S10.5 shadow") -> dict:
    """Costruisce i pack sintetici e li passa al reviewer in shadow. Ritorna un
    digest aggregato (verdetti, conteggi), mai artefatti o contenuto."""
    results = []
    for candidate_id, artifacts, scope in synthetic_candidates():
        pack = build_directive_pack(feature=feature, scope=scope, candidate=artifacts)
        res = reviewer.review(pack, models, candidate_id=candidate_id, shadow=True)
        results.append({
            "candidate_id": candidate_id,
            "verdict": res.verdict,
            "violations": len(res.violations),
            "blocking": res.blocking,
        })
    verdicts: dict[str, int] = {}
    for r in results:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    return {"reviewed": len(results), "shadow": True,
            "verdicts": verdicts, "results": results}
