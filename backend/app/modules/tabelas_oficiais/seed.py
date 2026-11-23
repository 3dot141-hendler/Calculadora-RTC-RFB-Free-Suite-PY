"""Inicializador e carga de dados de referência no banco SQLite."""

from pathlib import Path
import sqlite3

from app.core.config import get_settings
from .icms_ufs_data import ICMS_MODAL_UFS_2026

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_UFS_BRASIL: tuple[tuple[str, str], ...] = (
    ("AC", "Acre"),
    ("AL", "Alagoas"),
    ("AM", "Amazonas"),
    ("AP", "Amapá"),
    ("BA", "Bahia"),
    ("CE", "Ceará"),
    ("DF", "Distrito Federal"),
    ("ES", "Espírito Santo"),
    ("GO", "Goiás"),
    ("MA", "Maranhão"),
    ("MG", "Minas Gerais"),
    ("MS", "Mato Grosso do Sul"),
    ("MT", "Mato Grosso"),
    ("PA", "Pará"),
    ("PB", "Paraíba"),
    ("PE", "Pernambuco"),
    ("PI", "Piauí"),
    ("PR", "Paraná"),
    ("RJ", "Rio de Janeiro"),
    ("RN", "Rio Grande do Norte"),
    ("RO", "Rondônia"),
    ("RR", "Roraima"),
    ("RS", "Rio Grande do Sul"),
    ("SC", "Santa Catarina"),
    ("SE", "Sergipe"),
    ("SP", "São Paulo"),
    ("TO", "Tocantins"),
)

_ATIVIDADES_SIMPLES_NT2026005: tuple[tuple[str, str, str | None, str | None], ...] = (
    ("01", "Revenda de mercadorias, venda de mercadorias industrializadas pelo contribuinte", "I", None),
    ("02", "Operações com os demais bens materiais, sem incidência de ICMS", "I", None),
    ("03", "Venda de mercadorias industrializadas pelo contribuinte (ZFM)", "II", None),
    ("04", "Operações com os demais bens materiais (ZFM), sem incidência de ICMS", "II", None),
    ("05", "Prestação de serviços de transporte intermunicipal e interestadual (LC 123)", "III", None),
    ("06", "Prestação de serviços de comunicação", "III", None),
    ("07", "Prestação de serviços e cessão de direitos tributados exclusivamente pelo Anexo III", "III", None),
    ("08", "Prestação de serviços contábeis com ISS fixo municipal", "III", None),
    ("09", 'Prestação de serviços – Sujeitos ao Fator "R"', "III", "V"),
    ("10", "Prestação de serviços de transporte municipal de passageiros (LC 116/2003)", "III", None),
    ("11", "Locação de bens móveis e operações com serviços sem incidência de ISS", "III", None),
    ("12", "Prestação de serviços da área da construção civil tributados pelo Anexo III", "III", None),
    ("13", "Prestação de serviços da área da construção civil tributados pelo Anexo IV", "IV", None),
    ("14", "Prestação de serviços tributados pelo Anexo IV", "IV", None),
    ("90", "Operações não Tributáveis", None, None),
)


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
    """Popula registros iniciais de vigência (fallback quando rtc_referencias.db não existe)."""
    conn.executemany(
        """
        INSERT INTO cst_classificacao
            (cst, c_class_trib, descricao, aliquota_reducao_ibs, aliquota_reducao_cbs, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("000", "000001", "Situações tributadas integralmente pelo IBS e CBS.", "0.00", "0.00", "2026-01-01", None),
            ("200", "200003", "Vendas de produtos destinados à alimentação humana (Anexo I)", "100.00", "100.00", "2026-01-01", None),
            ("200", "200028", "Fornecimento dos serviços de educação (Anexo II)", "60.00", "60.00", "2026-01-01", None),
            ("410", "410001", "Fornecimento de bonificações no documento fiscal", "100.00", "100.00", "2026-01-01", None),
        ],
    )

    conn.executemany(
        """
        INSERT INTO atividade_simples
            (codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (cod, desc, sem_r, com_r, "2026-01-01", None)
            for cod, desc, sem_r, com_r in _ATIVIDADES_SIMPLES_NT2026005
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
        INSERT INTO redutor_compra_governamental (id, percentual_redutor, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?)
        """,
        [(2, "0.00", "2026-01-01", None)],
    )

    conn.executemany(
        """
        INSERT INTO transferencia_cbs_ente_gov (id, percentual_transferencia, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "10.00", "2029-01-01", "2029-12-31"),
            (2, "20.00", "2030-01-01", "2030-12-31"),
            (3, "30.00", "2031-01-01", "2031-12-31"),
            (4, "40.00", "2032-01-01", "2032-12-31"),
            (5, "100.00", "2033-01-01", None),
            (6, "0.00", "2026-01-01", "2028-12-31"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO ncm_imposto_seletivo
            (ncm, descricao, aliquota_ad_valorem, aliquota_ad_rem, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            ("87032100", "Automóveis de cilindrada <= 1.000 cm3", "5.27", None, "2027-01-01", "2033-12-31"),
            ("24021000", "Charutos e cigarrilhas contendo tabaco", None, "21.30", "2027-01-01", "2033-12-31"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO nbs_aplicavel
            (nbs, descricao, item_lc116, c_class_trib, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [("122011", "Serviços de ensino pré-escolar", "08.01", "200028", "2026-01-01", None)],
    )

    conn.executemany(
        """
        INSERT INTO tratamento_tributario
            (id, descricao, expressao_aliquota, expressao_aliquota_efetiva, expressao_base_calculo,
             expressao_tributo_calculado, expressao_tributo_devido, possui_reducao, possui_monofasia,
             inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1, "Tributação pelo Imposto Seletivo - Com Cálculo", None, None,
                "baseCalculoInformada", "baseCalculo*aliquotaAdValorem+quantidade*aliquotaAdRem",
                "tributoCalculado", 1, 0, "2026-01-01", None,
            ),
        ],
    )

    conn.executemany(
        """
        INSERT INTO uf_aliquota_referencia
            (uf, nome, aliquota_ibs_uf, aliquota_cbs, inicio_vigencia, fim_vigencia)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(sigla, nome, "10.00", "8.80", "2026-01-01", None) for sigla, nome in _UFS_BRASIL],
    )

    conn.executemany(
        """
        INSERT INTO icms_aliquota_uf
            (uf, aliquota_interna, aliquota_fcp, inicio_vigencia, fim_vigencia, fundamentacao)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ICMS_MODAL_UFS_2026,
    )

    conn.executemany(
        """
        INSERT INTO iss_servicos_catalogo (id, codigo_ctribnac, subitem_lc116, descricao)
        VALUES (?, ?, ?, ?)
        """,
        [
            (1, "01.01.01.000", "01.01", "Análise e desenvolvimento de sistemas."),
            (2, "01.07.01.000", "01.07", "Suporte técnico em informática."),
            (3, "17.19.01.000", "17.19", "Contabilidade, inclusive serviços técnicos e auxiliares."),
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
