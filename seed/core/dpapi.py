"""DPAPI: cifratura at-rest delle credenziali, unica implementazione.

Su Windows usa CryptProtectData/CryptUnprotectData (chiave legata all'utente);
fuori da Windows e' un passthrough (i test girano cosi'). Prima questo codice era
duplicato in provider_hub e voice_credentials: qui sta una volta sola.
"""

from __future__ import annotations

import base64
import ctypes
import os


class DpapiError(RuntimeError):
    pass


if os.name == "nt":
    import ctypes.wintypes as wt

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _crypt(data: bytes, fn, error: str) -> bytes:
        buf = ctypes.create_string_buffer(data, len(data))
        blob_in = _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        blob_out = _DATA_BLOB()
        if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
            raise DpapiError(error)
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(blob_out.pbData)

    def protect(data: bytes) -> bytes:
        return _crypt(data, ctypes.windll.crypt32.CryptProtectData, "DPAPI encryption failed")

    def unprotect(data: bytes) -> bytes:
        return _crypt(data, ctypes.windll.crypt32.CryptUnprotectData, "DPAPI decryption failed")
else:
    def protect(data: bytes) -> bytes:
        return data

    def unprotect(data: bytes) -> bytes:
        return data


def encrypt_str(value: str) -> str:
    return base64.b64encode(protect(value.encode("utf-8"))).decode("ascii")


def decrypt_str(value: str) -> str:
    return unprotect(base64.b64decode(value.encode("ascii"))).decode("utf-8")
