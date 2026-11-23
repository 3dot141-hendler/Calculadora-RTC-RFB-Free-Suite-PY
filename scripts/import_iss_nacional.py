"""Importa alíquotas municipais de ISS (Portal Nacional NFS-e) para 5 shards SQLite regionais.

Particionamento determinístico pelo 1º dígito do código IBGE:
  1 -> database/iss_norte.db
  2 -> database/iss_nordeste.db
  3 -> database/iss_sudeste.db
  4 -> database/iss_sul.db
  5 -> database/iss_centro_oeste.db

Também popula `iss_servicos_catalogo` em `database/rtc_referencias.db` cruzando
as descrições oficiais da `LISTA_SERVICOS_LC_116` (branch `originals`).
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from pathlib import Path
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TXT = (
    ROOT_DIR
    / "docs"
    / "personal"
    / "aliquotas-municipios-20260903-extr1"
    / "aliquotas-municipios-20260903.txt"
)
DATABASE_DIR = ROOT_DIR / "database"
REF_DB_PATH = DATABASE_DIR / "rtc_referencias.db"
SCHEMA_PATH = ROOT_DIR / "backend" / "app" / "modules" / "tabelas_oficiais" / "schema.sql"

REGION_SHARDS: dict[str, str] = {
    "1": "iss_norte.db",
    "2": "iss_nordeste.db",
    "3": "iss_sudeste.db",
    "4": "iss_sul.db",
    "5": "iss_centro_oeste.db",
}

_SHARD_SCHEMA = """
CREATE TABLE iss_aliquotas (
    codigo_ibge INTEGER NOT NULL,
    servico_id INTEGER NOT NULL,
    aliquota_bps INTEGER NOT NULL,
    inicio_vigencia TEXT NOT NULL,
    fim_vigencia TEXT,
    PRIMARY KEY (codigo_ibge, servico_id, inicio_vigencia)
) WITHOUT ROWID;

CREATE TABLE iss_municipios_cobertura (
    codigo_ibge INTEGER PRIMARY KEY,
    total_regras INTEGER NOT NULL
) WITHOUT ROWID;
"""


def _load_lc116_descriptions(branch: str = "originals") -> dict[str, str]:
    """Lê descrições oficiais da LC 116 direto da branch `originals` (com fallback seguro)."""
    try:
        sys.path.insert(0, str(ROOT_DIR / "scripts"))
        from sync_rfb_sqlite import _load_rfb_memory_db  # noqa: PLC0415

        mem = _load_rfb_memory_db(branch=branch)
        try:
            rows = mem.execute("SELECT LSLC_CD, LSLC_DESCRICAO FROM LISTA_SERVICOS_LC_116").fetchall()
        finally:
            mem.close()
        desc_map: dict[str, str] = {}
        for code, desc in rows:
            clean_code = str(code).strip()
            clean_desc = str(desc).strip()
            desc_map[clean_code] = clean_desc
            if "." in clean_code:
                major, minor = clean_code.split(".", 1)
                desc_map[f"{int(major):02d}.{minor.zfill(2)}"] = clean_desc
        return desc_map
    except Exception:
        return {}


def _parse_aliquota_bps(raw: str) -> int | None:
    """Converte '5', '2,5' ou '4.99' em basis points inteiros (500, 250, 499)."""
    text = raw.strip().replace(",", ".")
    if not text:
        return None
    try:
        val = Decimal(text)
    except InvalidOperation:
        return None
    if val < 0 or val > Decimal("100"):
        return None
    return int((val * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))


def _normalize_iso_date(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    return text[:10]


def _init_shard(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = OFF;")
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA page_size = 4096;")
    conn.executescript(_SHARD_SCHEMA)
    return conn


def import_iss_nacional(
    source_txt: Path = DEFAULT_TXT,
    output_dir: Path = DATABASE_DIR,
    ref_db: Path = REF_DB_PATH,
    branch: str = "originals",
) -> dict[str, dict[str, float | int]]:
    """Importa o TXT oficial do Portal da NFS-e para os 5 shards regionais + catálogo."""
    if not source_txt.exists():
        raise FileNotFoundError(f"Arquivo TXT oficial não encontrado: {source_txt}")

    output_dir.mkdir(parents=True, exist_ok=True)
    lc116_desc = _load_lc116_descriptions(branch=branch)

    # 1ª passagem rápida: coletar catálogo único e ordenado dos códigos de serviço
    servicos_set: set[str] = set()
    with source_txt.open("r", encoding="utf-8-sig", errors="replace") as fh:
        fh.readline()
        for line in fh:
            parts = line.rstrip("\r\n").split(";")
            if len(parts) >= 6 and parts[3].strip():
                servicos_set.add(parts[3].strip())

    servicos_ordenados = sorted(servicos_set)
    servico_to_id = {cod: idx + 1 for idx, cod in enumerate(servicos_ordenados)}

    # Salvar catálogo de serviços no rtc_referencias.db
    ref_conn = sqlite3.connect(str(ref_db))
    try:
        ref_conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        ref_conn.execute("DELETE FROM iss_servicos_catalogo")
        cat_rows = []
        for cod, sid in servico_to_id.items():
            subitem = cod[:5]
            desc = lc116_desc.get(subitem) or lc116_desc.get(subitem.lstrip("0")) or f"Serviço LC 116 subitem {subitem}"
            cat_rows.append((sid, cod, subitem, desc))
        ref_conn.executemany(
            "INSERT INTO iss_servicos_catalogo (id, codigo_ctribnac, subitem_lc116, descricao) VALUES (?, ?, ?, ?)",
            cat_rows,
        )
        ref_conn.commit()
    finally:
        ref_conn.close()

    # 2ª passagem streaming: distribuir alíquotas pelos 5 shards regionais
    conns: dict[str, sqlite3.Connection] = {}
    buffers: dict[str, list[tuple[int, int, int, str, str | None]]] = {k: [] for k in REGION_SHARDS}
    mun_counts: dict[str, dict[int, int]] = {k: {} for k in REGION_SHARDS}
    skipped = 0

    for reg_key, filename in REGION_SHARDS.items():
        conns[reg_key] = _init_shard(output_dir / filename)

    insert_sql = (
        "INSERT OR REPLACE INTO iss_aliquotas "
        "(codigo_ibge, servico_id, aliquota_bps, inicio_vigencia, fim_vigencia) "
        "VALUES (?, ?, ?, ?, ?)"
    )

    try:
        with source_txt.open("r", encoding="utf-8-sig", errors="replace") as fh:
            fh.readline()
            for line in fh:
                parts = line.rstrip("\r\n").split(";")
                if len(parts) < 8:
                    skipped += 1
                    continue
                ibge_str = parts[0].strip()
                if len(ibge_str) != 7 or not ibge_str.isdigit() or ibge_str[0] not in REGION_SHARDS:
                    skipped += 1
                    continue
                bps = _parse_aliquota_bps(parts[5])
                dt_ini = _normalize_iso_date(parts[6])
                if bps is None or not dt_ini:
                    skipped += 1
                    continue
                sid = servico_to_id.get(parts[3].strip())
                if sid is None:
                    skipped += 1
                    continue
                dt_fim = _normalize_iso_date(parts[7])
                reg_key = ibge_str[0]
                ibge_int = int(ibge_str)
                buffers[reg_key].append((ibge_int, sid, bps, dt_ini, dt_fim))
                mun_counts[reg_key][ibge_int] = mun_counts[reg_key].get(ibge_int, 0) + 1

                if len(buffers[reg_key]) >= 25_000:
                    conns[reg_key].executemany(insert_sql, buffers[reg_key])
                    buffers[reg_key].clear()

        stats: dict[str, dict[str, float | int]] = {}
        for reg_key, filename in REGION_SHARDS.items():
            conn = conns[reg_key]
            if buffers[reg_key]:
                conn.executemany(insert_sql, buffers[reg_key])
                buffers[reg_key].clear()
            conn.executemany(
                "INSERT INTO iss_municipios_cobertura (codigo_ibge, total_regras) VALUES (?, ?)",
                list(mun_counts[reg_key].items()),
            )
            conn.commit()
            conn.execute("VACUUM;")
            conn.close()
            size_mb = (output_dir / filename).stat().st_size / (1024 * 1024)
            stats[filename] = {
                "municipios": len(mun_counts[reg_key]),
                "regras": sum(mun_counts[reg_key].values()),
                "size_mb": round(size_mb, 2),
            }
        stats["_meta"] = {"servicos_catalogo": len(servico_to_id), "linhas_ignoradas": skipped}
        return stats
    finally:
        for conn in conns.values():
            try:
                conn.close()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa ISS municipal do Portal Nacional NFS-e em 5 shards SQLite.")
    parser.add_argument("--source", type=Path, default=DEFAULT_TXT, help="Caminho do arquivo TXT oficial.")
    parser.add_argument("--branch", default="originals", help="Branch Git para descrições LC 116.")
    args = parser.parse_args()

    stats = import_iss_nacional(source_txt=args.source, branch=args.branch)
    meta = stats.pop("_meta")
    print(f"Catálogo gravado em {REF_DB_PATH}: {meta['servicos_catalogo']} códigos cTribNac | {meta['linhas_ignoradas']} linhas sem alíquota ignoradas")
    total_mb = 0.0
    for filename, info in stats.items():
        total_mb += float(info["size_mb"])
        print(f"  {filename:22s} | {info['municipios']:4d} muns | {info['regras']:7,d} regras | {info['size_mb']:5.2f} MB")
    print(f"Total 5 shards: {total_mb:.2f} MB")


if __name__ == "__main__":
    main()
