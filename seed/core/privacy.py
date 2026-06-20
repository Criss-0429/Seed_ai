"""Privacy gate: nulla lascia il PC senza passare di qui.

Doppio layer in serie:
  1. OpenAI Privacy Filter (modello locale, CPU) — API reale:
     `from opf import OPF; OPF(device="cpu").redact(text)` -> RedactionResult
     con .detected_spans (label, start, end, text, placeholder) e .redacted_text.
     Checkpoint risolto da OPF_CHECKPOINT o ~/.opf/privacy_filter (auto-download).
  2. Regex deterministiche (sempre attive: email, telefoni, IBAN, CF, path utente, key)

Pseudonimizzazione stabile (pattern Caveman v2): [PERSON_1] e' sempre la stessa
persona tra sessioni; il mapping vive solo nel DB locale e si re-idrata in output.

fail_closed=True (default): se il layer 1 non e' pronto e il testo va verso l'API,
si usa comunque il layer 2 ma l'evento viene loggato.
"""

from __future__ import annotations

import gc
import getpass
import logging
import re
import socket
import threading
import time
from dataclasses import dataclass, field

log = logging.getLogger("seed.privacy")

# --------------------------------------------------------------------------
# Layer 2 — pattern deterministici (rinforzo italiano incluso)
# --------------------------------------------------------------------------
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL",  re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE",  re.compile(r"(?<!\d)(\+?\d{1,3}[ .-]?)?(\(?\d{2,4}\)?[ .-]?)\d{5,8}(?!\d)")),
    ("IBAN",   re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Z0-9][ ]?){11,30}\b")),
    ("CF",     re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b", re.IGNORECASE)),
    ("SECRET", re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})\b")),
    ("CARD",   re.compile(r"\b(?:\d[ -]?){13,19}\b")),
]


def _runtime_identifiers() -> list[tuple[str, str]]:
    """Nome utente Windows e hostname: noti a runtime, sostituzione diretta."""
    out = []
    try:
        out.append((getpass.getuser(), "[USER]"))
    except Exception:
        pass
    try:
        out.append((socket.gethostname(), "[HOST]"))
    except Exception:
        pass
    return [(s, t) for s, t in out if s and len(s) > 2]


# Entita' PII chieste a GLiNER (zero-shot). Mappate in _LABEL_MAP ai placeholder.
_GLINER_LABELS = [
    "person", "email", "phone number", "address", "organization", "url",
    "date", "credit card number", "iban", "api key", "password",
]


class PrivacyGateBlocked(RuntimeError):
    """fail_closed: il filtro locale ha fallito a meta' su un payload diretto
    all'API. Si BLOCCA l'uscita invece di proseguire con le sole regex."""


@dataclass
class GateResult:
    text: str
    replacements: int = 0
    layers: list[str] = field(default_factory=list)


class PrivacyGate:
    def __init__(self, memory, opf_checkpoint: str = "", recall_bias: bool = True,
                 fail_closed: bool = True, *, lite_mode: bool = False,
                 idle_unload_s: int = 120, backend: str = "opf"):
        self._memory = memory          # per pii_map persistente
        self._fail_closed = fail_closed
        self._opf_engine = None
        self._opf_tried = False        # load lazy: niente RAM finche' non si redige
        self._opf_checkpoint = opf_checkpoint
        self._recall_bias = recall_bias
        # Backend Layer-1 selezionabile da config:
        #   opf    : OpenAI Privacy Filter (~2.7GB, max accuracy) — default
        #   gliner : GLiNER multilingue PII (~300MB, sempre-attivo, italiano)
        #   regex  : nessun modello (solo Layer-2) — equivale a lite_mode
        self._backend = (backend or "opf").strip().lower()
        # Lite mode: solo regex, nessun modello ML caricato.
        self._lite_mode = lite_mode or self._backend == "regex"
        # Unload-on-idle: il modello viene scaricato dopo N s di inattivita',
        # cosi' SEED aperto ma fermo torna a RAM bassa. 0 = mai scaricare.
        self._idle_unload_s = max(0, int(idle_unload_s))
        self._opf_lock = threading.Lock()
        self._opf_last_use = 0.0
        self._opf_watch_started = False

    # ------------------------------------------------------------------
    def init_opf(self) -> bool:
        """Carica il Privacy Filter (API reale OPF). Auto-download al primo uso.

        Lazy: idempotente, eseguito al primo `redact` se non gia' chiamato. Cosi'
        il boot non carica il modello in RAM e una sessione di sola configurazione
        non paga il costo del filtro. In lite_mode non carica nulla (solo regex)."""
        if self._lite_mode:
            self._opf_tried = True
            return False
        with self._opf_lock:
            if self._opf_tried:
                return self._opf_engine is not None
            self._opf_tried = True
            return self._load_model_locked()

    def _load_model_locked(self) -> bool:
        loader = {"gliner": self._load_gliner, "opf": self._load_opf}.get(
            self._backend, self._load_opf)
        try:
            engine = loader()
            self._opf_engine = engine
            self._opf_last_use = time.monotonic()
            self._start_idle_watch()
            log.info("privacy backend '%s' caricato (cpu)", self._backend)
            return True
        except Exception as exc:  # modello non installato / download fallito
            log.warning("privacy backend '%s' non disponibile (%s): solo layer regex",
                        self._backend, exc)
            self._opf_engine = None
            return False

    def _load_opf(self):
        from opf import OPF  # type: ignore

        from .model_bundle import resolve
        kwargs = {"device": "cpu", "output_mode": "typed"}
        if self._opf_checkpoint:
            kwargs["model"] = resolve(self._opf_checkpoint)
        else:
            bundled = resolve("privacy_filter")
            if bundled != "privacy_filter":
                kwargs["model"] = bundled
        engine = OPF(**kwargs)
        engine.redact("warm up test")   # forza il load del checkpoint
        return engine

    def _load_gliner(self):
        from gliner import GLiNER  # type: ignore

        from .model_bundle import resolve
        name = resolve("gliner_pii")
        if name == "gliner_pii":
            name = "urchade/gliner_multi_pii-v1"   # PII-tuned, multilingue
        engine = GLiNER.from_pretrained(name)
        engine.predict_entities("warm up", _GLINER_LABELS, threshold=0.5)
        return engine

    def _start_idle_watch(self) -> None:
        if self._idle_unload_s <= 0 or self._opf_watch_started:
            return
        self._opf_watch_started = True
        threading.Thread(target=self._idle_watch, name="opf-idle",
                         daemon=True).start()

    def _maybe_unload(self) -> bool:
        """Scarica il modello se idle oltre la soglia. Ritorna True se liberato."""
        with self._opf_lock:
            if (self._opf_engine is None or self._idle_unload_s <= 0
                    or time.monotonic() - self._opf_last_use < self._idle_unload_s):
                return False
            self._opf_engine = None
            self._opf_tried = False   # consenti reload lazy al prossimo uso
        gc.collect()
        log.info("Privacy Filter scaricato per inattivita' (RAM liberata)")
        return True

    def _idle_watch(self) -> None:
        """Scarica il modello dopo inattivita': RAM torna bassa a SEED fermo.
        Il prossimo `redact` lo ricarica lazy."""
        interval = max(5, min(30, self._idle_unload_s // 2))
        while True:
            time.sleep(interval)
            self._maybe_unload()

    @property
    def opf_ready(self) -> bool:
        return self._opf_engine is not None

    # ------------------------------------------------------------------
    def redact(
        self,
        text: str,
        purpose: str = "llm",
        *,
        persist_mapping: bool = True,
    ) -> GateResult:
        """Da chiamare PRIMA di qualunque uscita verso l'API o i log."""
        result = GateResult(text=text)

        # Layer 1 — modello locale (load lazy al primo uso reale)
        if not self._opf_tried and purpose in {"llm", "research"}:
            self.init_opf()
        # Ref locale: il watchdog idle puo' azzerare self._opf_engine in parallelo,
        # ma il modello resta vivo per questa chiamata finche' `engine` lo tiene.
        engine = self._opf_engine
        if engine is not None:
            self._opf_last_use = time.monotonic()
            try:
                spans = self._detect_model(engine, result.text)
                result.text = self._pseudonymize_spans(
                    result.text, spans, persist_mapping=persist_mapping
                )
                result.replacements += len(spans)
                result.layers.append(self._backend)
            except Exception as exc:
                log.error("privacy backend '%s' failure: %s", self._backend, exc)
                if self._fail_closed and purpose == "llm":
                    # fail-closed reale: NON proseguire verso l'API con sole regex.
                    raise PrivacyGateBlocked(
                        "privacy filter fallito su payload llm (fail_closed)"
                    ) from exc

        # Layer 2 — sempre, in serie
        for ident, placeholder in _runtime_identifiers():
            if ident in result.text:
                result.text = result.text.replace(ident, placeholder)
                result.replacements += 1
        for label, pattern in _PATTERNS:
            def _sub(m, _label=label):
                return self._placeholder_for(
                    m.group(0), _label, persist_mapping=persist_mapping
                )
            new = pattern.sub(_sub, result.text)
            if new != result.text:
                result.replacements += 1
                result.text = new
        result.layers.append("regex")
        return result

    def rehydrate(self, text: str) -> str:
        """Ripristina i valori reali nei testi mostrati all'utente. MAI nei log."""
        for placeholder, real in self._memory.pii_map_all():
            text = text.replace(placeholder, real)
        return text

    # ------------------------------------------------------------------
    def _detect_model(self, engine, text: str) -> list[dict]:
        if self._backend == "gliner":
            return self._detect_gliner(engine, text)
        return self._detect_opf(engine, text)

    def _detect_opf(self, engine, text: str) -> list[dict]:
        """Invoca OPF.redact e converte RedactionResult.detected_spans
        nel formato interno [{start, end, label, value}]."""
        result = engine.redact(text)
        if isinstance(result, str):             # output_text_only mode
            return []
        spans = []
        for span in getattr(result, "detected_spans", ()) or ():
            spans.append({
                "start": int(span.start),
                "end": int(span.end),
                "label": str(span.label),
                "value": str(span.text),
            })
        return spans

    def _detect_gliner(self, engine, text: str) -> list[dict]:
        """GLiNER.predict_entities → formato interno. Soglia conservativa."""
        ents = engine.predict_entities(text, _GLINER_LABELS, threshold=0.5)
        spans = []
        for e in ents:
            spans.append({
                "start": int(e["start"]),
                "end": int(e["end"]),
                "label": str(e["label"]),
                "value": str(e.get("text") or text[e["start"]:e["end"]]),
            })
        return spans

    _LABEL_MAP = {
        # OPF labels
        "private_person": "PERSON", "private_email": "EMAIL",
        "private_phone": "PHONE", "private_address": "ADDR",
        "private_url": "URL", "private_date": "DATE",
        "account_number": "ACCT", "secret": "SECRET",
        # GLiNER labels (vedi _GLINER_LABELS)
        "person": "PERSON", "email": "EMAIL", "phone number": "PHONE",
        "address": "ADDR", "organization": "ORG", "url": "URL", "date": "DATE",
        "credit card number": "CARD", "iban": "IBAN", "api key": "SECRET",
        "password": "SECRET",
    }

    def _pseudonymize_spans(
        self,
        text: str,
        spans: list[dict],
        *,
        persist_mapping: bool = True,
    ) -> str:
        for span in sorted(spans, key=lambda s: s.get("start", 0), reverse=True):
            value = span.get("value") or text[span["start"]:span["end"]]
            label = self._LABEL_MAP.get(span.get("label", ""), "PII")
            ph = self._placeholder_for(
                value, label, persist_mapping=persist_mapping
            )
            text = text[: span["start"]] + ph + text[span["end"]:]
        return text

    def _placeholder_for(
        self,
        value: str,
        label: str,
        *,
        persist_mapping: bool = True,
    ) -> str:
        """Placeholder stabile: stesso valore -> stesso placeholder, persistito."""
        if not persist_mapping:
            return f"[{label}]"
        existing = self._memory.pii_map_lookup(value)
        if existing:
            return existing
        n = self._memory.pii_map_count(label) + 1
        placeholder = f"[{label}_{n}]"
        self._memory.pii_map_store(placeholder, value, label)
        return placeholder
