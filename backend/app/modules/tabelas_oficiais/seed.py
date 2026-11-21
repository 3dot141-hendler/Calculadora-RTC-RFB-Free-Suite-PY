"""Inicializador e carga de dados de referência no banco SQLite."""

from pathlib import Path
import sqlite3

from app.core.config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def ensure_reference_db(db_path: Path | None = None) -> Path:
    """Cria e popula o banco SQLite de referência se ainda não existir."""
    target = db_path or get_settings().resolved_reference_db_path
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _seed_initial_data(conn)
        conn.commit()
    finally:
        conn.close()
    return target


def _seed_initial_data(conn: sqlite3.Connection) -> None:
    """Popula registros iniciais de vigência baseados nas NTs da RFB."""
    conn.executemany(
        """
        INSERT INTO cst_classificacao
            (cst, c_class_trib, descricao, aliquota_reducao_ibs, aliquota_reducao_cbs, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("000", "000001", "Tributação integral", "0.00", "0.00", "2026-01-01", None),
            ("200", "200003", "Cesta básica nacional (alíquota zero)", "100.00", "100.00", "2026-01-01", None),
            ("200", "200028", "Serviços de educação/saúde (redução 60%)", "60.00", "60.00", "2026-01-01", None),
            ("410", "410001", "Imunidade ou não incidência", "100.00", "100.00", "2026-01-01", None),
        ],
    )

    conn.executemany(
        """
        INSERT INTO atividade_simples
            (codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("01", "Comércio em geral", "I", None, "2026-01-01", None),
            ("02", "Indústria em geral", "II", None, "2026-01-01", None),
            ("03", "Prestação de serviços sem Fator R", "III", None, "2026-01-01", None),
            ("04", "Serviços de engenharia e TI sujeitos ao Fator R", "V", "III", "2026-01-01", None),
            ("90", "Atividade sem enquadramento por anexo", None, None, "2026-01-01", None),
        ],
    )

    conn.executemany(
        """
        INSERT INTO transicao_compra_gov_simples (id, fator, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "0.10", "2026-01-01", "2026-12-31"),
            (2, "0.20", "2027-01-01", "2027-12-31"),
            (3, "0.50", "2028-01-01", None),
        ],
    )

    conn.executemany(
        """
        INSERT INTO uf_aliquota_referencia
            (uf, nome, aliquota_ibs_uf, aliquota_cbs, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("RS", "Rio Grande do Sul", "10.00", "8.80", "2026-01-01", None),
            ("SP", "São Paulo", "10.00", "8.80", "2026-01-01", None),
            ("RJ", "Rio de Janeiro", "10.00", "8.80", "2026-01-01", None),
            ("MG", "Minas Gerais", "10.00", "8.80", "2026-01-01", None),
            ("DF", "Distrito Federal", "10.00", "8.80", "2026-01-01", None),
        ],
    )

    conn.executemany(
        """
        INSERT INTO localidades_ibge (codigo_ibge, nome, uf_codigo, uf_sigla)
        VALUES (?, ?, ?, ?)
        """,
        [
            (4314902, "Porto Alegre", 43, "RS"),
            (4307609, "Esteio", 43, "RS"),
            (3550308, "São Paulo", 35, "SP"),
            (3304557, "Rio de Janeiro", 33, "RJ"),
            (5300108, "Brasília", 53, "DF"),
        ],
    )

