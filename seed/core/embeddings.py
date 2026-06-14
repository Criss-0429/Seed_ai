"""M3 embedder locale opzionale: lo stream VECTOR del retrieval.

Lezione agentmemory (doc 14): BM25/lessicale e' sempre attivo; il vettore e' un
boost. Qui idem: se `sentence-transformers` o il modello non sono disponibili,
l'embedder degrada (None) e il retrieval resta su lexical + graph, senza
rompersi. Modello multilingue di default (l'utente parla italiano); il peso non
e' un vincolo, la qualita' si'. Caricamento e download avvengono lazy al primo
uso, non all'avvio.
"""

from __future__ import annotations

import logging

log = logging.getLogger("seed.embeddings")

DEFAULT_MODEL = "paraphrase-multilingual-mpnet-base-v2"   # 768d, multilingue


class LocalEmbedder:
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
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._ok = True
            log.info("embedder caricato: %s", self.model_name)
        except Exception as exc:                  # dep mancante o download fallito
            log.info("embedder non disponibile (%s): retrieval su lexical+graph", exc)
            self._ok = False
        return self._ok

    @property
    def available(self) -> bool:
        return self._ensure()

    def rank(self, query: str, texts: list[str]) -> list[int] | None:
        """Indici di `texts` ordinati per cosine desc rispetto a `query`.
        None se l'embedder non e' disponibile (lo stream vector viene saltato)."""
        if not texts or not query.strip() or not self._ensure():
            return None
        try:
            import numpy as np
            embs = self._model.encode([query] + list(texts),
                                      normalize_embeddings=True)
            q = np.asarray(embs[0])
            mat = np.asarray(embs[1:])
            sims = mat @ q
            return [int(i) for i in np.argsort(-sims)]
        except Exception as exc:
            log.warning("ranking vettoriale fallito: %s", exc)
            return None
