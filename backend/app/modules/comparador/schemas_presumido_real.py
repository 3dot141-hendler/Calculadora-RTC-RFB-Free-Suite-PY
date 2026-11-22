"""Schemas Pydantic para o comparador Lucro Presumido vs. Lucro Real (com IBS/CBS)."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AtividadePresumido(str, Enum):
    """Atividades com percentuais oficiais de presunção (Lei nº 9.249/1995)."""

    COMERCIO_INDUSTRIA = "COMERCIO_INDUSTRIA"
    SERVICOS_GERAIS = "SERVICOS_GERAIS"
    SERVICOS_HOSPITALARES = "SERVICOS_HOSPITALARES"
    TRANSPORTE_CARGA = "TRANSPORTE_CARGA"
    TRANSPORTE_PASSAGEIROS = "TRANSPORTE_PASSAGEIROS"


class ComparadorPresumidoRealRequest(BaseModel):
    """Parâmetros mensais para comparação entre Lucro Presumido e Lucro Real no Regime Regular."""

    receita_bruta_mensal: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        description="Faturamento bruto mensal (R$). Sem teto de R$ 4,8 mi; teto do Presumido é R$ 78 mi/ano.",
    )
    despesas_dedutiveis_mensais: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Custos e despesas operacionais dedutíveis no mês (R$) para apuração do Lucro Real.",
    )
    atividade: AtividadePresumido = Field(
        default=AtividadePresumido.COMERCIO_INDUSTRIA,
        description="Ramo de atividade que define os percentuais de presunção de IRPJ e CSLL.",
    )
    data_fato_gerador: date = Field(
        default=date(2026, 6, 1),
        description="Data do fato gerador para resolução de alíquotas IBS/CBS e reduções no SQLite.",
    )
    uf: Optional[str] = Field(
        default="SP",
        min_length=2,
        max_length=2,
        description="UF de destino para resolver alíquotas oficiais IBS/CBS no SQLite.",
    )
    c_class_trib: Optional[str] = Field(
        default="000001",
        description="Código cClassTrib para aplicar redução oficial de IBS/CBS do SQLite.",
    )
    aliquota_ibs_uf: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Override opcional da alíquota IBS Estadual (%).",
    )
    aliquota_ibs_mun: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Alíquota IBS Municipal (%).",
    )
    aliquota_cbs: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Override opcional da alíquota CBS Federal (%).",
    )
    aliquota_is: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Alíquota do Imposto Seletivo (%).",
    )
    creditos_ibs_cbs: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Créditos mensais de IBS/CBS sobre insumos e compras (R$).",
    )


class CenarioLucroComparativo(BaseModel):
    """Detalhamento mensal de tributos sobre lucro (IRPJ/CSLL) e consumo (IBS/CBS/IS)."""

    id: str
    nome: str
    subtitulo: str
    elegivel: bool
    base_calculo_irpj: Decimal
    base_calculo_csll: Decimal
    irpj_basico: Decimal
    adicional_irpj: Decimal
    csll: Decimal
    total_irpj_csll: Decimal
    ibs_cbs_is_liquido: Decimal
    carga_tributaria_total: Decimal
    aliquota_efetiva_percentual: Decimal
    observacoes: str


class ComparadorPresumidoRealResponse(BaseModel):
    """Resultado consolidado da comparação Lucro Presumido vs. Lucro Real."""

    receita_bruta_mensal: Decimal
    receita_anualizada_estimada: Decimal
    despesas_dedutiveis_mensais: Decimal
    lucro_contabil_mensal: Decimal
    margem_lucro_real_percentual: Decimal
    atividade: AtividadePresumido
    presuncao_irpj_percentual: Decimal
    presuncao_csll_percentual: Decimal
    uf: Optional[str]
    c_class_trib: Optional[str]
    aliquota_ibs_uf_aplicada: Decimal
    aliquota_cbs_aplicada: Decimal
    reducao_ibs_percentual: Decimal
    ibs_cbs_bruto: Decimal
    creditos_ibs_cbs_aproveitados: Decimal
    excede_limite_presumido: bool
    cenarios: list[CenarioLucroComparativo]
    melhor_regime: str
    economia_mensal_reais: Decimal
    economia_anual_estimada_reais: Decimal
    resumo_executivo: str
