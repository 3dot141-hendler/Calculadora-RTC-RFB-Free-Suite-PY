"""Sincroniza o catálogo completo de municípios IBGE de `originals` para o SQLite."""

import json
from pathlib import Path
import sqlite3
import subprocess

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "backend" / "app" / "modules" / "tabelas_oficiais" / "schema.sql"
DB_PATH = ROOT_DIR / "database" / "rtc_referencias.db"


def sync_localidades() -> int:
    """Lê localidades.json da branch `originals` e atualiza `localidades_ibge`."""
    raw = subprocess.check_output(
        [
            "git",
            "show",
            "originals:references/danfse/cmd/gen-localidades/data/localidades.json",
        ],
        cwd=ROOT_DIR,
    )
    data = json.loads(raw.decode("utf-8"))
    uf_por_codigo = {est["codigo"]: est["sigla"] for est in data["estados"]}

    registros = [
        (m["codigo"], m["nome"], m["ufCodigo"], uf_por_codigo.get(m["ufCodigo"], ""))
        for m in data["municipios"]
    ]

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM localidades_ibge")
        conn.executemany(
            "INSERT INTO localidades_ibge (codigo_ibge, nome, uf_codigo, uf_sigla) VALUES (?, ?, ?, ?)",
            registros,
        )
        conn.commit()
    finally:
        conn.close()
    return len(registros)


if __name__ == "__main__":
    total = sync_localidades()
    print(f"Sincronizados {total} municípios IBGE em {DB_PATH}")
