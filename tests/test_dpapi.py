"""DPAPI helper unico: roundtrip cifratura/decifratura."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed.core import dpapi  # noqa: E402


def test_str_roundtrip():
    secret = "sk-test-1234567890"
    enc = dpapi.encrypt_str(secret)
    assert enc != secret          # mai in chiaro
    assert dpapi.decrypt_str(enc) == secret


def test_bytes_roundtrip():
    data = b"\x00\x01binary key\xff"
    assert dpapi.unprotect(dpapi.protect(data)) == data


def test_unicode_roundtrip():
    secret = "chiave-àèìòù-🔑"
    assert dpapi.decrypt_str(dpapi.encrypt_str(secret)) == secret
