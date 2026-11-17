"""Gerenciador de conexão SQLite somente-leitura (ADR004 RFB).

Em runtime, todas as consultas às tabelas de referência usam `mode=ro`
para impedir qualquer escrita acidental pela aplicação.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator

from app.core.config import get_settings


def get_readonly_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Abre conexão SQLite estritamente em modo somente-leitura (`mode=ro`)."""
    target = db_path or get_settings().resolved_reference_db_path
    uri = f"file:{target.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def readonly_session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager para consultas somente-leitura nas tabelas oficiais."""
    conn = get_readonly_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
