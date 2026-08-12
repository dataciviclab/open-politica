#!/usr/bin/env python3
"""Merge dei chunk camera_voti già estratti + date SPARQL → camera_voti.parquet."""
import sys
sys.path.insert(0, "scripts")
import glob
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import extract_camera_voti as ev

out_dir = "out/data/derived/camera_voti"
chunks = sorted(glob.glob(f"{out_dir}/chunks/chunk_*.parquet"))
print("chunk:", len(chunks))

dates = ev.fetch_votazione_dates(19)
print("date votazioni:", len(dates))
dates_path = f"{out_dir}/votazione_dates.parquet"
pq.write_table(
    pa.table({"votazione": [d["vr"] for d in dates], "data_raw": [d["d"] for d in dates]}),
    dates_path,
)

con = duckdb.connect()
globs = ", ".join(f"'{c}'" for c in chunks)
out = f"{out_dir}/camera_voti.parquet"
con.execute(f"""
    CREATE OR REPLACE TABLE finale AS
    SELECT DISTINCT
        v.voto AS voto_uri,
        TRY_CAST(REGEXP_EXTRACT(v.deputato, 'deputato\\.rdf/d(\\d+)_', 1) AS BIGINT) AS deputato_id,
        v.votazione,
        v.tipo AS voto,
        v.sigla,
        v.gruppo,
        TRY_CAST(
            CASE WHEN length(d.data_raw) = 8
                 THEN substr(d.data_raw,1,4)||'-'||substr(d.data_raw,5,2)||'-'||substr(d.data_raw,7,2)
            END AS DATE
        ) AS data
    FROM read_parquet([{globs}]) v
    LEFT JOIN read_parquet('{dates_path}') d ON v.votazione = d.votazione
""")
con.execute(f"COPY (SELECT * FROM finale) TO '{out}' (FORMAT PARQUET)")
n = con.execute("SELECT count(*) FROM finale").fetchone()[0]
nd = con.execute("SELECT count(DISTINCT deputato_id) FROM finale").fetchone()[0]
nv = con.execute("SELECT count(DISTINCT votazione) FROM finale").fetchone()[0]
null_data = con.execute("SELECT count(*) FROM finale WHERE data IS NULL").fetchone()[0]
print(f"OK: {n} voti, {nd} deputati, {nv} votazioni, NULL data {null_data}")
