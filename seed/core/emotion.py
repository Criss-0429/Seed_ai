"""S11.2 Speech Emotion Recognition — segnale affettivo PER-TURNO.

Backend: wav2vec2 SER via `transformers` (Windows-friendly: torch gia' presente,
nessun compilatore). emotion2vec/funasr scartato perche' la dipendenza
`editdistance` non ha wheel per Python 3.14 e richiede un compilatore C++.

Regole canoniche (wiki `Jarvis_User_Knowledge_Ontology` / harness cognitivo):
- un'emozione vocale NON e' un fatto psicologico, NON e' personalita' stabile,
  NON e' autorizzazione, NON e' diagnosi clinica;
- uso consentito: tono, velocita', chiedere conferma, ridurre verbosity — solo
  nel turno corrente, SOLO nel pannello voce;
- non viene mai persistito come claim/knowledge; l'audit registra solo il label
  aggregato, mai audio o transcript;
- la correzione esplicita dell'utente prevale sul segnale.

Opt-in e graceful: senza `funasr`/modello, `recognize` ritorna None e la voce
funziona comunque (senza segnale affettivo).
"""

from __future__ import annotations

import io
import logging
import math
import time
from dataclasses import dataclass

log = logging.getLogger("seed.emotion")

DEFAULT_MODEL = "superb/wav2vec2-base-superb-er"  # carica pulito con pipeline standard
_TTL_S = 90.0  # il segnale scade: e' temporaneo, non memoria


@dataclass(frozen=True)
class AffectSignal:
    label: str  # es. neutral | happy | sad | angry | fearful ...
    confidence: float
    model: str
    captured_at: float

    def expired(self, now: float | None = None) -> bool:
        return (now or time.time()) - self.captured_at > _TTL_S

    def tone_hint(self) -> str:
        """Istruzione di tono prudente per il turno. Mai diagnosi."""
        return {
            "sad": "L'utente nel parlato suona giu': tono caldo e breve, niente diagnosi.",
            "angry": "L'utente suona teso: resta calmo, conciso, non difensivo.",
            "fearful": "L'utente suona incerto: rassicura con concretezza, chiedi conferma.",
            "happy": "L'utente suona positivo: puoi essere piu' leggero, resta utile.",
            "surprised": "L'utente suona sorpreso: chiarisci con calma.",
            "disgusted": "L'utente suona infastidito: vai dritto al punto.",
        }.get(label_key(self.label), "Tono neutro adeguato.")


def label_key(label: str) -> str:
    """Normalizza i label emotion2vec (possono essere in cinese/inglese)."""
    low = (label or "").strip().lower()
    table = {
        "生气": "angry",
        "angry": "angry",
        "ang": "angry",
        "开心": "happy",
        "高兴": "happy",
        "happy": "happy",
        "hap": "happy",
        "伤心": "sad",
        "难过": "sad",
        "sad": "sad",
        "害怕": "fearful",
        "恐惧": "fearful",
        "fearful": "fearful",
        "neu": "neutral",
        "惊讶": "surprised",
        "surprised": "surprised",
        "厌恶": "disgusted",
        "disgust": "disgusted",
        "disgusted": "disgusted",
        "中立": "neutral",
        "neutral": "neutral",
        "calm": "neutral",
    }
    for key, norm in table.items():
        if key in low:
            return norm
    return "neutral"


class EmotionRecognizer:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        from .model_bundle import resolve

        self.model_name = resolve(model_name)
        self._model = None
        self._tried = False
        self._ok = False

    def _ensure(self) -> bool:
        if self._tried:
            return self._ok
        self._tried = True
        try:
            from transformers import pipeline

            self._model = pipeline("audio-classification", model=self.model_name, top_k=1)
            self._ok = True
            log.info("emotion recognizer caricato: %s", self.model_name)
        except Exception as exc:
            log.info("emotion recognizer non disponibile (%s): voce senza affect", exc)
            self._ok = False
        return self._ok

    @property
    def available(self) -> bool:
        return self._ensure()

    def recognize(self, audio_bytes: bytes, *, suffix: str = ".wav") -> AffectSignal | None:
        """Ritorna il segnale affettivo del turno, o None se non disponibile.
        L'audio (atteso wav 16k mono, ma resamplato) non viene persistito."""
        if not audio_bytes or not self._ensure():
            return None
        try:
            import numpy as np
            import soundfile as sf
            from scipy.signal import resample_poly

            wave, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
            wave = np.mean(wave, axis=1)
            if sample_rate != 16000:
                divisor = math.gcd(sample_rate, 16000)
                wave = resample_poly(wave, 16000 // divisor, sample_rate // divisor)
            out = self._model({"raw": wave, "sampling_rate": 16000})
            if not out:
                return None
            best = out[0]  # top_k=1, ordinato per score desc
            return AffectSignal(
                label=str(best["label"]),
                confidence=float(best["score"]),
                model=self.model_name,
                captured_at=time.time(),
            )
        except Exception as exc:
            log.warning("riconoscimento emozione fallito: %s", exc)
            return None
