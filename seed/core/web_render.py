"""P6.0 Adaptive Web Rendering — fondazione locale e sicura (doc 18).

Questa fase copre SOLTANTO: contratti tipizzati, sanitizzazione HTML/URL
deterministica, classificazione della fedelta' e il fitness gate (genera il
renderer solo se batte "non fare nulla"/browser). Riusa la precedenza P0-P5.

NON fa acquisizione: niente rete, niente browser bridge, niente esecuzione di
JavaScript. Le fasi P6.1+ (acquisizione con consenso, generatore di piano,
preview isolata, promozione governata) restano separate e owner-gated. Per
costruzione questo modulo non importa rete/subprocess/os: e' analisi pura.

Disciplina di sicurezza (doc 18): pagina e istruzioni incorporate sono contenuto
NON affidabile (prompt-injection). La sanitizzazione e' allowlist-oriented:
tutto cio' che non e' esplicitamente sicuro viene rimosso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser

from seed.core import ui_governance

SCHEMA_VERSION = "seed.web-render.v1"

# --- fedelta' dichiarata (doc 18) -----------------------------------------
FIDELITY_FAITHFUL_INTERACTIVE = "faithful_interactive"
FIDELITY_FAITHFUL_READONLY = "faithful_readonly"
FIDELITY_PARTIAL = "partial"
FIDELITY_BLOCKED = "blocked"
FIDELITY_LEVELS = frozenset({
    FIDELITY_FAITHFUL_INTERACTIVE, FIDELITY_FAITHFUL_READONLY,
    FIDELITY_PARTIAL, FIDELITY_BLOCKED,
})

# --- modalita' di acquisizione ammesse (doc 18); nessuna attiva in P6.0 ----
SOURCE_URL = "url"
SOURCE_HTML = "html"
SOURCE_BROWSER_BRIDGE = "browser_bridge"
SOURCE_MODES = frozenset({SOURCE_URL, SOURCE_HTML, SOURCE_BROWSER_BRIDGE})

# Tag strutturali/semantici sicuri: tutto il resto viene scartato o "srotolato".
_ALLOWED_TAGS = frozenset({
    "p", "div", "span", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd", "a", "strong", "em", "b", "i", "u",
    "small", "sub", "sup", "mark", "abbr", "time", "code", "pre", "blockquote",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "caption", "col",
    "figure", "figcaption", "img", "article", "section", "header", "footer",
    "main", "nav", "aside",
})
# Tag pericolosi: si scartano CON il contenuto (script, stile, frame, form...).
_DROP_WITH_CONTENT = frozenset({
    "script", "style", "noscript", "template", "svg", "math", "iframe",
    "object", "embed", "applet", "form", "frame", "frameset", "base", "head",
    "meta", "link", "title",
})
_VOID_TAGS = frozenset({"br", "hr", "img", "col", "wbr"})
# Attributi sicuri (nessun effetto/rete). aria-* sempre ammessi (P1).
_ALLOWED_ATTRS = frozenset({
    "class", "id", "alt", "title", "colspan", "rowspan", "scope", "lang",
    "dir", "datetime", "role", "headers",
})
# Schemi URL pericolosi: mai nell'output inerte.
_UNSAFE_SCHEMES = ("javascript:", "vbscript:", "data:", "file:")


def url_is_unsafe(value: str) -> bool:
    """True se l'URL usa uno schema eseguibile/pericoloso. Tollera spazi e case."""
    v = (value or "").strip().lower().replace("\t", "").replace("\n", "")
    return v.startswith(_UNSAFE_SCHEMES)


@dataclass
class SanitizeReport:
    scripts: int = 0
    styles: int = 0
    event_handlers: int = 0
    unsafe_urls: int = 0
    remote_resources: int = 0
    disallowed_tags: int = 0
    comments: int = 0

    def as_dict(self) -> dict:
        return {
            "scripts": self.scripts, "styles": self.styles,
            "event_handlers": self.event_handlers, "unsafe_urls": self.unsafe_urls,
            "remote_resources": self.remote_resources,
            "disallowed_tags": self.disallowed_tags, "comments": self.comments,
        }

    @property
    def total_removed(self) -> int:
        return (self.scripts + self.styles + self.event_handlers + self.unsafe_urls
                + self.remote_resources + self.disallowed_tags + self.comments)


class _Sanitizer(HTMLParser):
    """Ricostruisce HTML inerte: solo tag/attributi in allowlist, nessuno script,
    handler evento, risorsa remota o URL pericoloso. Contenuto dei tag pericolosi
    scartato per intero."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.report = SanitizeReport()
        self._skip_depth = 0          # >0 = dentro un tag drop-with-content

    # -- attributi -------------------------------------------------------
    def _clean_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        kept: list[str] = []
        for name, value in attrs:
            name = name.lower()
            value = value or ""
            if name.startswith("on"):
                self.report.event_handlers += 1
                continue
            if name == "style":
                self.report.styles += 1
                continue
            if name in ("src", "href", "action", "formaction", "background",
                        "srcset", "poster", "xlink:href", "longdesc", "cite"):
                if url_is_unsafe(value):
                    self.report.unsafe_urls += 1
                else:
                    # In P6.0 niente rete/navigazione: le risorse/link esterni
                    # vengono neutralizzati e contati (la preview reale e' P6.4).
                    self.report.remote_resources += 1
                continue
            if name in _ALLOWED_ATTRS or name.startswith("aria-"):
                safe = value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
                kept.append(f'{name}="{safe}"')
        return (" " + " ".join(kept)) if kept else ""

    # -- tag -------------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _DROP_WITH_CONTENT:
            self._skip_depth += 1
            if tag == "script":
                self.report.scripts += 1
            elif tag == "style":
                self.report.styles += 1
            else:
                self.report.disallowed_tags += 1
            return
        if self._skip_depth:
            return
        if tag in _ALLOWED_TAGS:
            attr_str = self._clean_attrs(tag, attrs)
            if tag in _VOID_TAGS:
                self.out.append(f"<{tag}{attr_str}>")
            else:
                self.out.append(f"<{tag}{attr_str}>")
        else:
            # tag non in allowlist: "srotola" (scarta il tag, tiene il testo).
            self.report.disallowed_tags += 1

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag in _DROP_WITH_CONTENT:
            if tag == "script":
                self.report.scripts += 1
            else:
                self.report.disallowed_tags += 1
            return
        if self._skip_depth:
            return
        if tag in _ALLOWED_TAGS:
            self.out.append(f"<{tag}{self._clean_attrs(tag, attrs)}>")
        else:
            self.report.disallowed_tags += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _DROP_WITH_CONTENT:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self._skip_depth:
            return
        self.out.append(data.replace("<", "&lt;").replace(">", "&gt;"))

    def handle_comment(self, data):
        # I commenti possono nascondere istruzioni/iniezioni: scartati.
        self.report.comments += 1


def sanitize_html(raw: str) -> tuple[str, dict]:
    """Ritorna (html_inerte, report_rimozioni). Deterministica e idempotente:
    nessuno script, handler, risorsa remota o URL pericoloso sopravvive."""
    parser = _Sanitizer()
    parser.feed(raw or "")
    parser.close()
    return "".join(parser.out), parser.report.as_dict()


# --- classificazione fedelta' (deterministica) ----------------------------
def classify_fidelity(
    *,
    safe: bool,
    content_ratio: float,
    structure_certain: bool,
    interactions_enabled: bool = False,
) -> str:
    """Livello di fedelta' dichiarato. In P6.0 le interazioni sono sempre OFF, quindi
    il massimo raggiungibile e' `faithful_readonly`; `faithful_interactive` resta
    per le fasi con bridge reale (P6.1+)."""
    if not safe:
        return FIDELITY_BLOCKED
    if content_ratio < 0.5 or not structure_certain:
        return FIDELITY_PARTIAL
    if interactions_enabled:
        return FIDELITY_FAITHFUL_INTERACTIVE
    return FIDELITY_FAITHFUL_READONLY


# --- fitness gate: genera solo se conviene davvero (correzione owner) ------
def decide_render_fitness(
    *,
    has_user_evidence: bool,
    expected_value: float,
    do_nothing_value: float = 0.0,
    browser_value: float = 0.0,
) -> dict:
    """SEED propone/genera il renderer SOLO se il valore atteso supera sia "non
    fare nulla" sia l'uso del browser originale. Senza evidenza rilevante la
    capability puo' non essere mai generata. Default = skip."""
    if not has_user_evidence:
        return {"action": "skip", "reason": "no_user_evidence"}
    alternative = max(float(do_nothing_value), float(browser_value))
    if float(expected_value) <= alternative:
        return {"action": "skip", "reason": "not_better_than_alternatives",
                "alternative_value": round(alternative, 6)}
    return {"action": "render", "reason": "value_exceeds_alternatives",
            "alternative_value": round(alternative, 6)}


# --- precedenza P0-P5: un piano non puo' ridurre controllo/accessibilita' --
def plan_respects_precedence(
    *,
    violated_precedence: tuple[str, ...] = (),
    justifying_evidence: tuple[str, ...] = (),
) -> dict:
    """Delega a `ui_governance`: un piano che viola P0 (controllo/sicurezza) o P1
    (accessibilita') non e' ammissibile; uno che contraddice P4 richiede evidenza
    P2/P3. Ritorna {admissible, blocking, reasons}."""
    verdict = ui_governance.evaluate_ui_mutation(
        violated_precedence=violated_precedence,
        justifying_evidence=justifying_evidence)
    return {"admissible": verdict.candidable,
            "blocking": list(verdict.blocking),
            "reasons": list(verdict.reasons)}


# --- contratti minimi (doc 18) --------------------------------------------
class WebRenderError(ValueError):
    """Sollevata quando un contratto P6 viola i suoi invarianti minimi."""


@dataclass(frozen=True)
class RenderRequest:
    source_mode: str
    source_ref: str
    consent_ref: str
    user_goal_ref: str = ""
    requested_scope: str = "document"

    def validate(self) -> None:
        if self.source_mode not in SOURCE_MODES:
            raise WebRenderError(f"source_mode non ammesso: {self.source_mode!r}")
        if not self.consent_ref:
            # Nessuna acquisizione/uso senza consenso esplicito (doc 18).
            raise WebRenderError("consent_ref obbligatorio: niente azione senza consenso")
        if not self.source_ref:
            raise WebRenderError("source_ref mancante")


@dataclass(frozen=True)
class AdaptationProfile:
    constraints: tuple[str, ...] = ()
    explicit_preferences: tuple[str, ...] = ()
    accessibility_needs: tuple[str, ...] = ()
    context: str = ""
    provenance: str = ""
    confidence: float = 0.0

    def validate(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise WebRenderError(f"confidence fuori range [0,1]: {self.confidence!r}")


@dataclass(frozen=True)
class TransformPlan:
    plan_id: str
    target_scope: str
    rollback_plan: str
    css_rules: tuple[str, ...] = ()
    dom_operations: tuple[str, ...] = ()
    content_filters: tuple[str, ...] = ()
    preserved_semantics: tuple[str, ...] = ()
    permissions_delta: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.plan_id:
            raise WebRenderError("plan_id mancante")
        if not self.rollback_plan:
            # Reversibilita' obbligatoria (doc 18 / contratto mutazione).
            raise WebRenderError("rollback_plan obbligatorio: trasformazione reversibile")


@dataclass(frozen=True)
class RenderResult:
    status: str
    fidelity_level: str
    warnings: tuple[str, ...] = ()
    blocked_resources: tuple[str, ...] = ()
    accessibility_report: dict = field(default_factory=dict)
    preview_ref: str = ""
    audit_ref: str = ""

    def validate(self) -> None:
        if self.fidelity_level not in FIDELITY_LEVELS:
            raise WebRenderError(f"fidelity_level non valido: {self.fidelity_level!r}")


# ==========================================================================
# P6.1 — Acquisizione sorgente con consenso (gated, default OFF)
# ==========================================================================
class AcquisitionError(WebRenderError):
    """Sollevata quando un'acquisizione viola consenso/gate/modalita'."""


def acquire_source(
    request: "RenderRequest",
    *,
    provided_html: str | None = None,
    fetch=None,
    browser_bridge=None,
    allow_network: bool = False,
    allow_browser: bool = False,
) -> dict:
    """Acquisisce il contenuto sorgente SOLO con consenso e gate espliciti.

    - `html`: usa l'HTML fornito dall'utente (nessuna rete);
    - `url`: richiede `allow_network=True` (config.network_acquisition_enabled) e un
      `fetch` iniettato; mai fetch silenzioso, mai accesso a tab/cookie/sessioni;
    - `browser_bridge`: richiede `allow_browser=True` e un `browser_bridge` iniettato,
      limitato alla pagina corrente e revocabile.

    Il contenuto e' temporaneo (nessuna persistenza qui). La rete NON e' importata
    dal modulo: il chiamante inietta `fetch`/`browser_bridge`, che il runtime
    fornisce solo dietro i flag owner. Ritorna `{raw_html, source_mode, persisted}`."""
    request.validate()
    if request.source_mode == SOURCE_HTML:
        if not provided_html:
            raise AcquisitionError("modalita' html: provided_html mancante")
        return {"raw_html": provided_html, "source_mode": SOURCE_HTML, "persisted": False}
    if request.source_mode == SOURCE_URL:
        if not allow_network:
            raise AcquisitionError("acquisizione di rete disabilitata (owner gate OFF)")
        if fetch is None:
            raise AcquisitionError("fetch non iniettato: nessuna rete nel modulo")
        if url_is_unsafe(request.source_ref):
            raise AcquisitionError(f"url non sicuro: {request.source_ref!r}")
        return {"raw_html": str(fetch(request.source_ref)),
                "source_mode": SOURCE_URL, "persisted": False}
    # browser_bridge
    if not allow_browser:
        raise AcquisitionError("browser bridge disabilitato (owner gate OFF)")
    if browser_bridge is None:
        raise AcquisitionError("browser_bridge non iniettato")
    return {"raw_html": str(browser_bridge(request.source_ref)),
            "source_mode": SOURCE_BROWSER_BRIDGE, "persisted": False}


# ==========================================================================
# P6.2 — Generatore di TransformPlan tipizzato (emergente, non hardcoded)
# ==========================================================================
# Trasformazioni allowlistate per BISOGNO/PREFERENZA semantici, MAI per sito.
# Ogni voce dichiara la precedenza e l'invariante: nessuna riduce P0/P1. La classe
# e' aperta (si aggiungono bisogni), ma ogni regola e' sicura per costruzione.
_ACCESSIBILITY_TRANSFORMS: dict[str, dict] = {
    "larger_text": {"precedence": "P1_accessibility",
                    "css": ("html{font-size:125%;line-height:1.6}",)},
    "high_contrast": {"precedence": "P1_accessibility",
                      "css": ("body{background:#fff;color:#111}a{color:#0b3d91}",)},
    "reduce_motion": {"precedence": "P1_accessibility",
                      "css": ("*{animation:none!important;transition:none!important}",)},
    "readable_spacing": {"precedence": "P1_accessibility",
                         "css": ("p,li{max-width:70ch;letter-spacing:.01em;line-height:1.7}",)},
    "strong_focus": {"precedence": "P1_accessibility",
                     "css": (":focus{outline:3px solid #0b3d91;outline-offset:2px}",)},
}
_PREFERENCE_TRANSFORMS: dict[str, dict] = {
    "calm_palette": {"precedence": "P5_aesthetics",
                     "css": ("body{background:#f6f5f2}",)},
    "reduce_visual_noise": {"precedence": "P5_aesthetics",
                            "content_filters": ("collapse:non_essential_decoration",)},
    "reading_focus": {"precedence": "P5_aesthetics",
                      "content_filters": ("emphasize:main_content",)},
}
# Semantica sempre preservata (mai rimossa da un'estetica).
_PRESERVED_SEMANTICS = ("headings", "landmarks", "links", "reading_order",
                        "form_labels", "focus_order")


def build_transform_plan(
    profile: "AdaptationProfile",
    *,
    plan_id: str,
    target_scope: str = "document",
) -> "TransformPlan":
    """Costruisce un `TransformPlan` EMERGENTE dal profilo: nasce dai bisogni di
    accessibilita' e dalle preferenze esplicite, non da branch per sito/tema. Bisogni
    sconosciuti vengono ignorati (mai inventati). Le regole sono allowlistate e
    sicure: nessuna riduce contrasto/focus/leggibilita'/controlli (P0/P1)."""
    profile.validate()
    css: list[str] = []
    content_filters: list[str] = []
    for need in profile.accessibility_needs:
        rule = _ACCESSIBILITY_TRANSFORMS.get(need)
        if rule:
            css.extend(rule.get("css", ()))
            content_filters.extend(rule.get("content_filters", ()))
    for pref in profile.explicit_preferences:
        rule = _PREFERENCE_TRANSFORMS.get(pref)
        if rule:
            css.extend(rule.get("css", ()))
            content_filters.extend(rule.get("content_filters", ()))
    return TransformPlan(
        plan_id=plan_id,
        target_scope=target_scope,
        rollback_plan="ripristina l'originale: la sorgente non viene mai modificata",
        css_rules=tuple(css),
        dom_operations=(),                 # P6.2 non emette DOM ops dirette
        content_filters=tuple(content_filters),
        preserved_semantics=_PRESERVED_SEMANTICS,
        permissions_delta=(),              # nessuna nuova autorita'
        risks=tuple(profile.constraints),
    )


# ==========================================================================
# P6.3 — Evaluator deterministico + gate (sicurezza / WCAG / anti-injection)
# ==========================================================================
# Anti-pattern che un piano non puo' contenere: iniezione o riduzione P0/P1.
_PLAN_FORBIDDEN = (
    "<script", "javascript:", "expression(", "@import", "url(http",
    "outline:none", "outline: none", "user-select:none",
)
# Riduzioni P1 esplicite (accessibilita'): mai ammesse.
_P1_REDUCERS = ("outline:none", "outline: none", "font-size:0", "display:none}")


def evaluate_transform_plan(plan: "TransformPlan") -> dict:
    """Valuta un piano PRIMA dell'attivazione: anti-injection, WCAG-rilevante,
    precedenza P0-P5, reversibilita'. Deterministico, gate fail-closed."""
    plan.validate()
    blocking: list[str] = []
    warnings: list[str] = []
    blob = " ".join(plan.css_rules + plan.dom_operations + plan.content_filters).lower()

    for bad in _PLAN_FORBIDDEN:
        if bad in blob:
            blocking.append(f"injection_or_unsafe:{bad}")
    violated: list[str] = []
    if any(red in blob for red in _P1_REDUCERS):
        violated.append("P1_accessibility")
    # un piano non puo' nascondere i controlli SEED o lo stato (P0).
    if "seed-controls" in blob or "[data-seed]" in blob:
        violated.append("P0_control_safety")

    precedence = plan_respects_precedence(violated_precedence=tuple(dict.fromkeys(violated)))
    if not precedence["admissible"]:
        blocking.extend(f"precedence:{b}" for b in precedence["blocking"])

    semantics_ok = bool(plan.preserved_semantics)
    if not semantics_ok:
        warnings.append("nessuna semantica dichiarata come preservata")

    status = "pass" if not blocking else "blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "blocking": blocking,
        "warnings": warnings,
        "preserves_semantics": semantics_ok,
        "rollback_present": bool(plan.rollback_plan),
        "accessibility_report": {
            "preserved": list(plan.preserved_semantics),
            "reduces_p1": "P1_accessibility" in violated,
        },
    }


# ==========================================================================
# P6.4 — Preview fullscreen isolata (script/rete OFF, controlli sempre accessibili)
# ==========================================================================
# Content-Security-Policy che impone l'isolamento: nessuno script, nessuna rete,
# nessuna immagine remota. Lo stile inline serve solo a rendere il piano.
_PREVIEW_CSP = ("default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; "
                "script-src 'none'; connect-src 'none'; frame-src 'none'; form-action 'none'")

# Chrome SEED in classi dedicate: per Guidelines (B-01 stato visibile, B-03 uscita/
# rollback sempre accessibili, A-01 target >=44px, A-08 una sola enfasi). Le regole
# del piano agiscono solo dentro `.seed-adapted`, mai sui controlli.
_PREVIEW_CHROME_CSS = """
:root{--paper:oklch(94% .004 85);--app:oklch(97% .005 85);--ink:oklch(23% .008 80);
--mut:oklch(62% .01 85);--line:oklch(88% .006 85);--accent:oklch(62% .07 45);
--sans:"Segoe UI Variable Text","Segoe UI",system-ui,sans-serif}
html,body{margin:0;height:100%;background:var(--app);color:var(--ink);font-family:var(--sans)}
.seed-chrome{position:fixed;top:0;left:0;right:0;display:flex;gap:8px;align-items:center;
padding:8px 12px;background:var(--paper);border-bottom:1px solid var(--line);z-index:2147483647}
.seed-status{flex:1;font-size:13px;color:var(--mut)}
.seed-chrome [data-seed-action]{min-height:44px;min-width:44px;padding:0 14px;border:1px solid var(--line);
background:var(--app);color:var(--ink);border-radius:10px;font:inherit;cursor:pointer}
.seed-chrome [data-seed-action]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.seed-pane{margin-top:60px;padding:24px;max-width:70ch}
.seed-original{display:none}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
"""


def build_preview(
    *,
    sanitized_adapted_html: str,
    plan: "TransformPlan",
    fidelity_level: str,
    sanitized_original_html: str = "",
    provenance: str = "",
) -> dict:
    """Genera il documento di preview ISOLATO (stringa HTML inerte). Script e rete
    sono OFF via CSP; i controlli SEED (uscita, confronto, rollback) e lo stato sono
    sempre accessibili e non sovrascrivibili dal piano; l'originale resta separato
    e non modificato. Gli input HTML devono essere gia' sanitizzati (`sanitize_html`).

    La preview non contiene JavaScript: le azioni sono dichiarate via
    `data-seed-action`; il guscio host (pywebview) le collega. Cosi' P0 (controllo/
    sicurezza) e l'isolamento restano garantiti."""
    if fidelity_level not in FIDELITY_LEVELS:
        raise WebRenderError(f"fidelity_level non valido: {fidelity_level!r}")
    plan.validate()
    # Le regole del piano agiscono SOLO dentro `.seed-adapted` (l'originale e il
    # chrome restano intatti): ogni regola viene scoping-prefissata.
    plan_css = "\n".join(f".seed-adapted {rule}" for rule in plan.css_rules)
    fidelity_label = {
        FIDELITY_FAITHFUL_INTERACTIVE: "fedele, interattivo",
        FIDELITY_FAITHFUL_READONLY: "fedele, sola lettura",
        FIDELITY_PARTIAL: "parziale",
        FIDELITY_BLOCKED: "bloccato",
    }[fidelity_level]
    prov = (provenance or "sorgente fornita").replace("<", "&lt;")
    document = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{_PREVIEW_CSP}">
<title>SEED — anteprima adattata</title>
<style>{_PREVIEW_CHROME_CSS}
/* piano applicato, scoping su .seed-adapted */
{plan_css}
</style></head>
<body>
<div class="seed-chrome" role="toolbar" aria-label="Controlli SEED anteprima">
  <span class="seed-status" aria-live="polite">Anteprima adattata · fedelta': {fidelity_label} · origine: {prov}</span>
  <button type="button" data-seed-action="compare" aria-label="Confronta con l'originale">Confronta</button>
  <button type="button" data-seed-action="rollback" aria-label="Ripristina l'originale">Ripristina</button>
  <button type="button" data-seed-action="exit" aria-label="Esci dall'anteprima (Esc)">Esci</button>
</div>
<main class="seed-pane seed-adapted" aria-label="Contenuto adattato">
{sanitized_adapted_html}
</main>
<section class="seed-pane seed-original" aria-label="Originale (non modificato)" hidden>
{sanitized_original_html}
</section>
</body></html>"""
    return {
        "schema_version": SCHEMA_VERSION,
        "preview_document": document,
        "controls": ("compare", "rollback", "exit"),
        "fidelity_level": fidelity_level,
        "script_free": "<script" not in document.lower(),
        "network_blocked": True,
        "original_preserved": True,
    }


# ==========================================================================
# P6.5 — Candidate -> promozione governata (temporaneo resta temporaneo)
# ==========================================================================
@dataclass(frozen=True)
class RenderCandidate:
    candidate_id: str
    source_ref: str
    target_scope: str
    plan_id: str
    fidelity_level: str
    evidence: tuple[str, ...] = ()
    expected_signals: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    preview_ref: str = ""
    rollback_plan: str = ""
    persistent: bool = False              # default: temporaneo

    def validate(self) -> None:
        if self.fidelity_level not in FIDELITY_LEVELS:
            raise WebRenderError(f"fidelity_level non valido: {self.fidelity_level!r}")
        if not self.rollback_plan:
            raise WebRenderError("rollback_plan obbligatorio")


def propose_render_candidate(
    request: "RenderRequest",
    plan: "TransformPlan",
    result: "RenderResult",
    *,
    candidate_id: str,
    evidence: tuple[str, ...] = (),
    expected_signals: tuple[str, ...] = (),
) -> RenderCandidate:
    """Ogni trasformazione nuova nasce come candidate ISOLATA e temporanea: porta
    evidenza, segnali attesi, rischi e rollback. Non e' attiva ne' persistente."""
    request.validate()
    plan.validate()
    cand = RenderCandidate(
        candidate_id=candidate_id,
        source_ref=request.source_ref,
        target_scope=plan.target_scope,
        plan_id=plan.plan_id,
        fidelity_level=result.fidelity_level,
        evidence=tuple(evidence),
        expected_signals=tuple(expected_signals),
        risks=tuple(plan.risks),
        preview_ref=result.preview_ref,
        rollback_plan=plan.rollback_plan,
        persistent=False,
    )
    cand.validate()
    return cand


def promote_render(
    candidate: RenderCandidate,
    *,
    owner_approved: bool,
    evaluation_passed: bool,
    persist: bool = False,
    generalize: bool = False,
) -> dict:
    """Promozione governata. Default = non promosso. Una trasformazione NON viene
    generalizzata ad altri siti/contesti senza evidenza e consenso: `generalize`
    e' sempre rifiutato qui. Le preferenze temporanee restano temporanee se
    `persist` non e' esplicitamente richiesto E approvato dall'owner."""
    candidate.validate()
    if generalize:
        return {"promoted": False, "reason": "no_cross_site_generalization",
                "scope": candidate.target_scope, "persistent": False}
    if not evaluation_passed:
        return {"promoted": False, "reason": "evaluation_not_passed",
                "scope": candidate.target_scope, "persistent": False}
    if not owner_approved:
        return {"promoted": False, "reason": "owner_approval_required",
                "scope": candidate.target_scope, "persistent": False}
    return {"promoted": True, "reason": "owner_approved",
            "scope": candidate.target_scope,
            # persiste solo se esplicitamente richiesto E approvato; altrimenti temporaneo.
            "persistent": bool(persist)}
