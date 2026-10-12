"""
db_snapshot.py — Version-controllable snapshot of mgg.db.

mgg.db is a 73 MB SQLite binary: too large to keep in git (GitHub hard-blocks
files over 100 MB, and every committed version is stored in full forever), and
not diffable. This script exports it as gzipped CSVs that live in the repo and
rebuilds an identical database from them.

    data/       MGG source data the pipeline reads. Changes only if MGG's own
                records are corrected.
    results/    What this pipeline produced (venue_assignments). Re-export after
                each `assign_ids.py {STATE} --commit`.

Each directory holds one <table>.csv.gz per table, a schema.sql with the exact
CREATE TABLE statements, and a manifest.json with row counts and checksums.

Not exported: split_logging and split_location_details, an audit trail of a
one-time August 2025 amenity-code cleanup. The pipeline never reads them, and
they are MGG curation history rather than data.

Format: UTF-8 CSV, header row, rows in primary-key order. NULL is written as
\\N so it stays distinct from the empty string (both occur: text columns use ''
while coordinates and foreign keys use NULL). Floats are written with Python's
shortest round-trip repr, so they reload bit-for-bit. Gzip headers carry no
timestamp, so re-exporting unchanged data produces byte-identical files.

Usage:
    python3 db_snapshot.py export            # mgg.db -> data/ + results/
    python3 db_snapshot.py build             # data/ + results/ -> mgg.db
    python3 db_snapshot.py build --force     # overwrite an existing mgg.db
    python3 db_snapshot.py verify            # rebuild in a temp dir, compare to mgg.db
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile

import config

DATA_DIR = os.path.join(config.BASE_DIR, "data")
RESULTS_DIR = os.path.join(config.BASE_DIR, "results")

# Insert order respects foreign keys (referenced tables first).
SOURCE_TABLES = [
    "unique_locations",
    "locations",
    "amenity_features",
    "location_types",
    "location_amenity_assignments",
    "location_type_assignments",
]
RESULT_TABLES = ["venue_assignments"]

NULL = r"\N"
csv.field_size_limit(2**31 - 1)  # long descriptions exceed the 128 KB default


def _columns(conn, table):
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _table_sql(conn, table):
    """CREATE TABLE plus any explicit (non-auto) indexes, verbatim from sqlite_master."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if row is None:
        raise SystemExit(f"Table {table!r} not found in {config.DB_PATH}")
    stmts = [row[0] + ";"]
    for (sql,) in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? "
        "AND sql IS NOT NULL ORDER BY name", (table,)
    ):
        stmts.append(sql + ";")
    return "\n".join(stmts)


def _encode(value):
    if value is None:
        return NULL
    if isinstance(value, bytes):
        raise SystemExit("BLOB values are not supported by this snapshot format")
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str) and value == NULL:
        raise SystemExit(f"A stored value equals the NULL sentinel {NULL!r}; cannot export losslessly")
    return str(value)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_bytes(path, data):
    tmp = f"{path}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def export_tables(conn, tables, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    manifest = {}
    schema = []
    for table in tables:
        cols = _columns(conn, table)
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(cols)
        n = 0
        for row in conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
            writer.writerow([_encode(v) for v in row])
            n += 1

        raw = io.BytesIO()
        # filename="" and mtime=0 keep the gzip header free of names/timestamps.
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(buf.getvalue().encode("utf-8"))
        path = os.path.join(out_dir, f"{table}.csv.gz")
        _atomic_write_bytes(path, raw.getvalue())

        manifest[table] = {"rows": n, "columns": cols, "sha256": _sha256(path)}
        schema.append(_table_sql(conn, table))
        print(f"  {table:32} {n:>9,} rows  {os.path.getsize(path) / 1048576:>6.2f} MB")

    _atomic_write_bytes(os.path.join(out_dir, "schema.sql"),
                        ("\n\n".join(schema) + "\n").encode("utf-8"))
    _atomic_write_bytes(os.path.join(out_dir, "manifest.json"),
                        (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))


def cmd_export(args):
    if not os.path.exists(config.DB_PATH):
        raise SystemExit(f"{config.DB_PATH} not found")
    conn = sqlite3.connect(config.DB_PATH)
    try:
        print(f"Source data -> {os.path.relpath(DATA_DIR, config.BASE_DIR)}/")
        export_tables(conn, SOURCE_TABLES, DATA_DIR)
        print(f"Results -> {os.path.relpath(RESULTS_DIR, config.BASE_DIR)}/")
        export_tables(conn, RESULT_TABLES, RESULTS_DIR)
    finally:
        conn.close()


def load_dir(conn, src_dir):
    manifest_path = os.path.join(src_dir, "manifest.json")
    schema_path = os.path.join(src_dir, "schema.sql")
    if not (os.path.exists(manifest_path) and os.path.exists(schema_path)):
        raise SystemExit(f"{src_dir} is missing manifest.json or schema.sql — run `export` first")
    with open(manifest_path) as f:
        manifest = json.load(f)

    conn.executescript(open(schema_path).read())
    for table, meta in manifest.items():
        path = os.path.join(src_dir, f"{table}.csv.gz")
        if _sha256(path) != meta["sha256"]:
            raise SystemExit(f"Checksum mismatch for {path} — file changed or is corrupt")
        with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            placeholders = ",".join("?" * len(header))
            col_list = ",".join(f'"{c}"' for c in header)
            # Values go in as strings; SQLite column affinity converts them back
            # to INTEGER / REAL per the original schema.
            conn.executemany(
                f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})',
                ([None if v == NULL else v for v in row] for row in reader),
            )
        n = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        if n != meta["rows"]:
            raise SystemExit(f"{table}: loaded {n:,} rows, manifest expects {meta['rows']:,}")
        print(f"  {table:32} {n:>9,} rows")


def build(out_path, include_results=True):
    tmp = f"{out_path}.building"
    if os.path.exists(tmp):
        os.remove(tmp)
    conn = sqlite3.connect(tmp)
    try:
        load_dir(conn, DATA_DIR)
        if include_results and os.path.exists(os.path.join(RESULTS_DIR, "manifest.json")):
            load_dir(conn, RESULTS_DIR)
        conn.execute("ANALYZE")
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp, out_path)


def cmd_build(args):
    out = args.out or config.DB_PATH
    if os.path.exists(out) and not args.force:
        raise SystemExit(f"{out} already exists. Use --force to replace it.")
    if args.force:
        # A stale WAL from the old database would be replayed onto the new file.
        for suffix in ("-wal", "-shm"):
            if os.path.exists(out + suffix):
                os.remove(out + suffix)
    build(out, include_results=not args.no_results)
    print(f"Built {out}")


def _snapshot(conn, table):
    cols = _columns(conn, table)
    select = ", ".join(f'typeof("{c}"), "{c}"' for c in cols)
    return conn.execute(f'SELECT {select} FROM "{table}" ORDER BY rowid').fetchall()


def cmd_verify(args):
    if not os.path.exists(config.DB_PATH):
        raise SystemExit(f"{config.DB_PATH} not found")
    with tempfile.TemporaryDirectory() as d:
        rebuilt = os.path.join(d, "rebuilt.db")
        print("Rebuilding from snapshot...")
        build(rebuilt)
        orig = sqlite3.connect(config.DB_PATH)
        new = sqlite3.connect(rebuilt)
        ok = True
        print("Comparing every row and value type against mgg.db...")
        for table in SOURCE_TABLES + RESULT_TABLES:
            same_schema = _table_sql(orig, table) == _table_sql(new, table)
            a, b = _snapshot(orig, table), _snapshot(new, table)
            same_rows = a == b
            ok &= same_schema and same_rows
            status = "identical" if (same_schema and same_rows) else "DIFFERS"
            detail = "" if same_rows else f" ({len(a):,} vs {len(b):,} rows)"
            print(f"  {table:32} {status}{'' if same_schema else ' [schema]'}{detail}")
        orig.close()
        new.close()
    if not ok:
        raise SystemExit("Verification FAILED — snapshot does not reproduce mgg.db")
    print("Verification passed: snapshot reproduces mgg.db exactly.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("export", help="mgg.db -> data/ + results/")
    b = sub.add_parser("build", help="data/ + results/ -> mgg.db")
    b.add_argument("--out", help=f"output path (default: {config.DB_PATH})")
    b.add_argument("--force", action="store_true", help="overwrite an existing database")
    b.add_argument("--no-results", action="store_true", help="source data only, no venue_assignments")
    sub.add_parser("verify", help="rebuild in a temp dir and compare against mgg.db")
    args = p.parse_args()
    {"export": cmd_export, "build": cmd_build, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    main()
