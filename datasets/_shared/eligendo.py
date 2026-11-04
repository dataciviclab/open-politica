"""Helper condivisi per le fonti Eligendo/DAIT (ZIP con CSV/TXT/XLSX).

Codice di dominio del repo: evita di duplicare download, selezione delle entry
e lettura tabellare nei `preprocess.py` dei dataset elettorali. Non e' un
contratto del toolkit.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime
from fnmatch import fnmatch

from lab_connectors.http.download import download as _download

XLSX_EXTS = (".xlsx", ".xlsm")


def download_bytes(url: str, *, timeout: int = 120) -> bytes:
    return _download(url, timeout=timeout)


def select_entries(
    payload: bytes,
    *,
    match: str | list[str] | None = None,
    exclude: str | list[str] | None = None,
    only_ext: list[str] | None = None,
) -> dict[str, bytes]:
    """Entry dello ZIP filtrate per glob sul nome e/o estensione (ordine ZIP)."""
    patterns = _as_list(match)
    excluded = _as_list(exclude)
    exts = [ext.lower() for ext in (only_ext or [])]
    out: dict[str, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            base = _safe_name(name).lower()
            if exts and not any(base.endswith(ext) for ext in exts):
                continue
            if patterns and not any(fnmatch(base, pat.lower()) for pat in patterns):
                continue
            if excluded and any(fnmatch(base, pat.lower()) for pat in excluded):
                continue
            out[_safe_name(name)] = zf.read(name)
    return out


def read_table(data: bytes, name: str) -> tuple[list[str], list[list[str]]]:
    """Legge un CSV/TXT (delim ;) o un foglio XLSX e restituisce (header, righe)."""
    if name.lower().endswith(XLSX_EXTS):
        return _read_excel(data)
    text = _smart_decode(data)
    rows = [
        row
        for row in csv.reader(io.StringIO(text), delimiter=";")
        if any(cell.strip() for cell in row)
    ]
    if not rows:
        return [], []
    return rows[0], rows[1:]


def merge_on(
    left: list[dict],
    right: list[dict],
    keys: list[str],
    *,
    how: str = "left",
) -> list[dict]:
    """Join tra due liste di dict su ``keys`` (senza dipendenze esterne)."""
    index: dict[tuple[str, ...], dict] = {}
    for row in right:
        index.setdefault(tuple(str(row.get(k, "")) for k in keys), row)

    merged: list[dict] = []
    for row in left:
        key = tuple(str(row.get(k, "")) for k in keys)
        match = index.get(key)
        if match is None and how == "inner":
            continue
        combined = dict(row)
        if match:
            for name, value in match.items():
                combined.setdefault(name, value)
        merged.append(combined)
    return merged


def _read_excel(data: bytes) -> tuple[list[str], list[list[str]]]:
    import openpyxl

    workbook = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return [], []
    header = [_cell_to_str(value) or f"col{i}" for i, value in enumerate(rows[0])]
    body = [[_cell_to_str(value) for value in row] for row in rows[1:]]
    return header, body


def _cell_to_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _smart_decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _safe_name(name: str) -> str:
    return name.replace("\\", "/").split("/")[-1] or "file.bin"


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]
