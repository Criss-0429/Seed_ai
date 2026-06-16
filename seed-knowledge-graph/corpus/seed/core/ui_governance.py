"""U7: governance UI — le Design Guidelines guidano i modelli (doc 17).

Le regole UI/UX (Laws of UX + euristiche Nielsen, gerarchia di precedenza P0-P5)
diventano direttive verificabili per il design reviewer. Una mutazione che tocca
la UI/`ui_manifest` viene valutata contro queste direttive in modo deterministico:

- viola **P0** (controllo/sicurezza utente) o **P1** (accessibilita') -> NON
  candidabile (mai derogabili);
- viola **P4** (best practice) -> deve dichiarare evidenza **P2/P3** che la
  giustifica, altrimenti non candidabile;
- altrimenti candidabile (il reviewer LLM resta evidenza, non promotion).

Deterministico, zero LLM: la precedenza e' una regola, non un giudizio.
"""

from __future__ import annotations

from dataclasses import dataclass

UI_DIRECTIVE_SET_VERSION = "seed.ui-directives.v2"

# Gerarchia di precedenza non negoziabile (doc 17).
UI_PRECEDENCE = (
    "P0_control_safety",
    "P1_accessibility",
    "P2_explicit_correction",
    "P3_repeated_behavior",
    "P4_best_practice",
    "P5_aesthetics",
)
_NEVER_DEROGABLE = frozenset({"P0_control_safety", "P1_accessibility"})

# Direttive UI derivate dalle Guidelines (Laws of UX / Nielsen), con il livello
# di precedenza a cui appartengono.
def _directive(source_id: str, precedence: str, text: str) -> dict:
    return {"directive_id": f"ui.{source_id.lower().replace('-', '_')}",
            "source_id": source_id, "precedence": precedence, "text": text}


# Copertura completa delle regole actionable in SEED Design Guidelines:
# A Laws of UX, B Nielsen, C desktop/visual, D human-AI ed E accessibilita'.
UI_DIRECTIVES: tuple[dict, ...] = (
    _directive("A-01", "P1_accessibility", "Target >=24px; 44px su touch; azioni frequenti vicine."),
    _directive("A-02", "P4_best_practice", "Poche azioni visibili; aggiungerne una richiede compensazione."),
    _directive("A-03", "P4_best_practice", "Convenzioni note: input in basso, Esc chiude, invio invia."),
    _directive("A-04", "P4_best_practice", "Raggruppare informazione; evitare muri e liste non strutturate."),
    _directive("A-05", "P0_control_safety", "Ack entro 400ms e stato percepibile durante il lavoro."),
    _directive("A-06", "P4_best_practice", "Curare chiusura task e riparazione errori."),
    _directive("A-07", "P5_aesthetics", "Separare qualita' estetica da utilita' misurata."),
    _directive("A-08", "P4_best_practice", "Una sola enfasi per superficie."),
    _directive("A-09", "P4_best_practice", "La UI assorbe complessita'; non la scarica sull'utente."),
    _directive("A-10", "P4_best_practice", "Input elastico, output prevedibile e coerente."),
    _directive("B-01", "P0_control_safety", "Stato del sistema sempre visibile."),
    _directive("B-02", "P4_best_practice", "Usare linguaggio dell'utente, non gergo interno."),
    _directive("B-03", "P0_control_safety", "Uscita, annulla, pausa, permessi e rollback sempre accessibili."),
    _directive("B-04", "P4_best_practice", "Coerenza tra superfici e stati."),
    _directive("B-05", "P0_control_safety", "Prevenire errori prima degli effetti."),
    _directive("B-06", "P4_best_practice", "Far riconoscere opzioni e stato; non imporre memoria."),
    _directive("B-07", "P3_repeated_behavior", "Scorciatoie solo proposte da comportamento ripetuto."),
    _directive("B-08", "P4_best_practice", "Ogni elemento aggiunto deve giustificare la propria presenza."),
    _directive("B-09", "P0_control_safety", "Ammettere errore e offrire correzione semplice."),
    _directive("B-10", "P4_best_practice", "Aiuto contestuale, non manuali imposti."),
    _directive("C-01", "P4_best_practice", "Gerarchia visiva funzionale, non decorazione."),
    _directive("C-02", "P4_best_practice", "L'interfaccia resta deferente al contenuto e al focus."),
    _directive("C-03", "P4_best_practice", "Rispettare convenzioni desktop."),
    _directive("C-04", "P1_accessibility", "Rispettare impostazioni di sistema."),
    _directive("C-05", "P1_accessibility", "Testo leggibile e dimensioni minime."),
    _directive("C-06", "P0_control_safety", "Ogni input riceve feedback percepibile."),
    _directive("D-01", "P0_control_safety", "Capacita' e limiti dichiarati chiaramente."),
    _directive("D-02", "P0_control_safety", "Non interrompere il focus; attendere pause naturali."),
    _directive("D-03", "P0_control_safety", "Dichiarare quando si usa contesto osservato."),
    _directive("D-04", "P0_control_safety", "Niente stereotipi; tono adattabile, identita' stabile."),
    _directive("D-05", "P0_control_safety", "Invocazione, correzione e congedo facili."),
    _directive("D-06", "P0_control_safety", "Con bassa confidenza ridurre portata o chiedere."),
    _directive("D-07", "P0_control_safety", "Ogni comportamento resta spiegabile su richiesta."),
    _directive("D-08", "P0_control_safety", "Apprendimento dichiarato, ispezionabile e correggibile."),
    _directive("D-09", "P0_control_safety", "Mutazioni caute, annunciate e spiegate."),
    _directive("D-10", "P0_control_safety", "Mostrare subito conseguenze delle correzioni."),
    _directive("D-11", "P0_control_safety", "Controlli globali dominano inferenze e mutazioni."),
    _directive("D-12", "P0_control_safety", "Mostrare incertezza; non simulare sicurezza."),
    _directive("E-01", "P1_accessibility", "Contrasto WCAG anche per accenti evoluti."),
    _directive("E-02", "P1_accessibility", "Tutto operabile da tastiera, focus visibile e non intrappolato."),
    _directive("E-03", "P1_accessibility", "Target >=24x24 CSS o spaziatura equivalente."),
    _directive("E-04", "P1_accessibility", "Reduce-motion; animazione mai unico segnale."),
    _directive("E-05", "P1_accessibility", "Nessuna informazione affidata al solo colore."),
    _directive("BRAND-01", "P5_aesthetics", "Colore guadagnato da eventi reali; mai piu' maturo della relazione."),
)

UI_DIRECTIVE_IDS = frozenset(d["directive_id"] for d in UI_DIRECTIVES)


class UiGovernanceError(ValueError):
    pass


@dataclass(frozen=True)
class UiMutationVerdict:
    candidable: bool
    blocking: tuple[str, ...]        # livelli P violati che bloccano
    reasons: tuple[str, ...]


def evaluate_ui_mutation(*, violated_precedence: tuple[str, ...] = (),
                         justifying_evidence: tuple[str, ...] = ()) -> UiMutationVerdict:
    """Gate deterministico P0-P5 su una mutazione UI.

    `violated_precedence`: livelli che la mutazione violerebbe (dichiarati dal
    reviewer/analisi). `justifying_evidence`: evidenze P2/P3 dichiarate."""
    for level in violated_precedence:
        if level not in UI_PRECEDENCE:
            raise UiGovernanceError(f"livello di precedenza sconosciuto: {level!r}")

    blocking: list[str] = []
    reasons: list[str] = []

    for level in violated_precedence:
        if level in _NEVER_DEROGABLE:
            blocking.append(level)
            reasons.append(f"{level}_violated_never_derogable")

    if "P4_best_practice" in violated_precedence:
        has_evidence = any(e in ("P2_explicit_correction", "P3_repeated_behavior")
                           for e in justifying_evidence)
        if not has_evidence:
            blocking.append("P4_best_practice")
            reasons.append("P4_violated_without_P2_P3_evidence")

    if not blocking:
        reasons.append("ui_precedence_ok")
    return UiMutationVerdict(not blocking, tuple(blocking), tuple(reasons))


def ui_directives_section() -> dict:
    """Sezione `ui_directives` per il DesignDirectivePack (U7)."""
    return {
        "ui_directive_set_version": UI_DIRECTIVE_SET_VERSION,
        "precedence": list(UI_PRECEDENCE),
        "never_derogable": sorted(_NEVER_DEROGABLE),
        "directives": [dict(d) for d in UI_DIRECTIVES],
    }
