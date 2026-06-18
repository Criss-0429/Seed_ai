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

import getpass
import logging
import re
import socket
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
                 fail_closed: bool = True):
        self._memory = memory          # per pii_map persistente
        self._fail_closed = fail_closed
        self._opf_engine = None
        self._opf_tried = False        # load lazy: niente RAM finche' non si redige
        self._opf_checkpoint = opf_checkpoint
        self._recall_bias = recall_bias

    # ------------------------------------------------------------------
    def init_opf(self) -> bool:
        """Carica il Privacy Filter (API reale OPF). Auto-download al primo uso.

        Lazy: idempotente, eseguito al primo `redact` se non gia' chiamato. Cosi'
        il boot non carica il modello in RAM e una sessione di sola configurazione
        non paga il costo del filtro."""
        if self._opf_tried:
            return self._opf_engine is not None
        self._opf_tried = True
        try:
            from opf import OPF  # type: ignore
            from .model_bundle import resolve
            kwargs = {"device": "cpu", "output_mode": "typed"}
            if self._opf_checkpoint:
                kwargs["model"] = resolve(self._opf_checkpoint)
            else:
                bundled = resolve("privacy_filter")
                if bundled != "privacy_filter":
                    kwargs["model"] = bundled
            self._opf_engine = OPF(**kwargs)
            # warm-up: forza load del checkpoint (e l'eventuale download)
            self._opf_engine.redact("warm up test")
            log.info("OpenAI Privacy Filter caricato (cpu)")
            return True
        except Exception as exc:  # modello non installato / download fallito
            log.warning("Privacy Filter non disponibile (%s): attivo solo layer regex", exc)
            self._opf_engine = None
            return False

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
        if self._opf_engine is not None:
            try:
                spans = self._detect_opf(result.text)
                result.text = self._pseudonymize_spans(
                    result.text, spans, persist_mapping=persist_mapping
                )
                result.replacements += len(spans)
                result.layers.append("opf")
            except Exception as exc:
                log.error("OPF failure: %s", exc)
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
    def _detect_opf(self, text: str) -> list[dict]:
        """Invoca OPF.redact e converte RedactionResult.detected_spans
        nel formato interno [{start, end, label, value}]."""
        result = self._opf_engine.redact(text)  # type: ignore[union-attr]
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

    _LABEL_MAP = {
        "private_person": "PERSON", "private_email": "EMAIL",
        "private_phone": "PHONE", "private_address": "ADDR",
        "private_url": "URL", "private_date": "DATE",
        "account_number": "ACCT", "secret": "SECRET",
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
