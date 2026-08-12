#!/usr/bin/env python3
"""Ponte persona_id (Camera) ↔ senator_id (Senato).

Unifica l'identità di una persona tra i due rami del Parlamento tramite
match esatto su cognome+nome normalizzati (UPPER, senza accenti).

Il sistema parlamentare non espone una chiave condivisa Camera↔Senato:
la stessa persona ha un `persona_id` (dati.camera.it) e un `senatore_id`
(dati.senato.it) diversi. Questo ponte produce la mappa 1:1 quando il
match è univoco e segnala i casi ambigui o non risolti.

Uso:
    python3 scripts/build_ponte_persona.py
    python3 scripts/build_ponte_persona.py --out out/data/derived/ponte_persona
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
    """).fetchall()
    return [(int(pid), nome or "", cognome or "") for pid, nome, cognome in rows]


def load_senato(clean: Path) -> list[tuple[int, str, str]]:
    rows = CON.execute(f"""
        SELECT senatore_id, nome, cognome
        FROM read_parquet('{clean}')
        WHERE senatore_id IS NOT NULL
    """).fetchall()
    return [(int(sid), nome or "", cognome or "") for sid, nome, cognome in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-clean",
                        default="out/data/clean/camera_deputati_legislature/2026/camera_deputati_legislature_2026_clean.parquet")
    parser.add_argument("--senato-clean",
                        default="out/data/clean/senato_anagrafica/2026/senato_anagrafica_2026_clean.parquet")
    parser.add_argument("--out", default="out/data/derived/ponte_persona")
    args = parser.parse_args()

    camera = load_camera(Path(args.camera_clean))
    senato = load_senato(Path(args.senato_clean))
    print(f"deputati (persone distinte): {len(camera)}")
    print(f"senatori:                    {len(senato)}")

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
    for sid, nome, cognome in senato:
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
