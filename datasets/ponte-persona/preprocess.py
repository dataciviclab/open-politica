#!/usr/bin/env python3
"""Ponte persona_id (Camera) ↔ senator_id (Senato).

Unifica l'identità di una persona tra i due rami del Parlamento tramite
match esatto su cognome+nome normalizzati (UPPER, senza accenti).

Il sistema parlamentare non espone una chiave condivisa Camera↔Senato:
la stessa persona ha un `persona_id` (dati.camera.it) e un `senatore_id`
(dati.senato.it) diversi. Questo ponte produce la mappa 1:1 quando il
match è univoco e segnala i casi ambigui o non risolti.

Uso:
    python preprocess.py
    python preprocess.py --root ../../out
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

CON = duckdb.connect()


def norm_name(s: str | None) -> str:
    if not s:
        return ""
    out = s.upper()
    # rimuove accenti (es. DE LUCA → DE LUCA, FERRERO→FERRERO invariato)
    for a, b in [
        ("À", "A"), ("Á", "A"), ("È", "E"), ("É", "E"), ("Ì", "I"),
        ("Ò", "O"), ("Ù", "U"), ("'", " "), (".", " "),
    ]:
        out = out.replace(a, b)
    return " ".join(out.split())


def load_camera(clean: Path) -> list[tuple[int, str, str]]:
    rows = CON.execute(f"""
        SELECT DISTINCT persona_id, nome, cognome
        FROM read_parquet('{clean}')
        WHERE persona_id IS NOT NULL
          AND nome IS NOT NULL AND cognome IS NOT NULL
          AND TRIM(nome) != '' AND TRIM(cognome) != ''
    """).fetchall()
    return [(int(pid), nome or "", cognome or "") for pid, nome, cognome in rows]


def load_senato(clean: Path) -> list[tuple[int, str, str, int]]:
    """Carica senatori da un file clean. Ritorna (senatore_id, nome, cognome, legislatura)."""
    rows = CON.execute(f"""
        SELECT senatore_id, nome, cognome, legislatura
        FROM read_parquet('{clean}')
        WHERE senatore_id IS NOT NULL
          AND nome IS NOT NULL AND cognome IS NOT NULL
          AND TRIM(nome) != '' AND TRIM(cognome) != ''
    """).fetchall()
    return [(int(sid), nome or "", cognome or "", int(leg) if leg else 0)
            for sid, nome, cognome, leg in rows]


def load_senato_all(clean_dir: Path) -> list[tuple[int, str, str, int]]:
    """Carica senatori da TUTTE le legislature disponibili.
    
    Prima leggeva solo l'ultima legislatura (Leg19). Ora legge tutte
    le cartelle Legislature (13-19) per estendere la copertura del ponte.
    """
    files = sorted(
        clean_dir.glob("*/*_clean.parquet"),
        key=lambda p: int(p.parent.name) if p.parent.name.isdigit() else -1,
    )
    if not files:
        return []
    
    all_senato: list[tuple[int, str, str, int]] = []
    for f in files:
        leg_rows = load_senato(f)
        all_senato.extend(leg_rows)
        print(f"  carica Leg {f.parent.name}: {len(leg_rows)} senatori")
    
    # Dedup per senatore_id (può apparire in più legislature)
    seen: set[int] = set()
    deduped: list[tuple[int, str, str, int]] = []
    for sid, nome, cognome, leg in all_senato:
        if sid not in seen:
            seen.add(sid)
            deduped.append((sid, nome, cognome, leg))
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="../../out",
                        help="Output root (default: ../../out, relativo alla dir del dataset)")
    parser.add_argument("--out", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    camera_clean = root / "data/clean/camera_deputati_legislature/2026/camera_deputati_legislature_2026_clean.parquet"
    # senato_anagrafica è multi-legislature (Leg13–19): legge TUTTE le cartelle
    senato_clean_dir = root / "data/clean/senato_anagrafica"

    if not camera_clean.exists():
        print(f"ERRORE: {camera_clean} non trovato — camera_deputati_legislature deve essere processato prima")
        return 1
    if not senato_clean_dir.exists():
        print(f"ERRORE: {senato_clean_dir} non trovato — senato_anagrafica deve essere processato prima")
        return 1

    camera = load_camera(camera_clean)
    senato = load_senato_all(senato_clean_dir)
    print(f"deputati (persone distinte): {len(camera)}")
    print(f"senatori (tutte legislature): {len(senato)}")

    by_name: dict[tuple[str, str], list[int]] = defaultdict(list)
    for pid, nome, cognome in camera:
        by_name[(norm_name(cognome), norm_name(nome))].append(pid)

    # indici ausiliari per il fallback su nome multi-parola
    cam_by_cogn: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for pid, nome, cognome in camera:
        cam_by_cogn[norm_name(cognome)].append((pid, norm_name(nome)))

    def match_camera(nome: str, cognome: str) -> list[int]:
        """Camera personas candidate per un senatore."""
        n_cogn = norm_name(cognome)
        n_nome = norm_name(nome)
        # 1) match esatto cognome+nome
        if (n_cogn, n_nome) in by_name:
            return by_name[(n_cogn, n_nome)]
        # 2) cognome esatto + parole del nome contenute nel nome Camera
        #    (Camera: "IGNAZIO BENITO MARIA"; Senato: "Ignazio")
        words = n_nome.split()
        hits = [
            pid for pid, cam_nome in cam_by_cogn.get(n_cogn, [])
            if words and all(w in cam_nome.split() for w in words)
        ]
        return hits

    matched: list[tuple[int, int, str]] = []  # senatore_id, persona_id, tipo
    stats = {"match_1to1": 0, "ambigui": 0, "senza_match": 0}
    for sid, nome, cognome, _leg in senato:
        pids = match_camera(nome, cognome)
        if len(pids) == 1:
            matched.append((sid, pids[0], "1to1"))
            stats["match_1to1"] += 1
        elif len(pids) > 1:
            for p in pids:
                matched.append((sid, p, "ambiguo"))
            stats["ambigui"] += 1
        else:
            stats["senza_match"] += 1

    matched_personas = len({p for _, p, _ in matched if _})
    print(f"--- match ---")
    print(f"senatori 1:1 con un deputato: {stats['match_1to1']}  "
          f"({100.0 * stats['match_1to1'] / len(senato):.1f}%)")
    print(f"senatori ambigui (più deputati): {stats['ambigui']}")
    print(f"senatori senza match:            {stats['senza_match']}  "
          f"({100.0 * stats['senza_match'] / len(senato):.1f}%)")
    print(f"deputati (persona_id) coperti:   {matched_personas} / {len(camera)}")

    # verifica nota: Salvini
    salv = [r for r in matched if r[1] == 302741 or r[0] == 25407]
    print(f"--- check Salvini: {salv}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ponte_persona.parquet"
    table = pa.table(
        {
            "senatore_id": [r[0] for r in matched],
            "persona_id": [r[1] for r in matched],
            "tipo_match": [r[2] for r in matched],
        }
    )
    pq.write_table(table, out_path)
    print(f"OK → {out_path} ({len(matched)} righe)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
