"""Schemas Pydantic para o Comparador Tributário (Simples vs. Híbrido vs. Regime Regular)."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.simples.schemas import AnexoSimples


class ComparadorRequest(BaseModel):
    """Parâmetros de entrada para simulação comparativa lado a lado entre regimes RTC."""

    receita_bruta_12m: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("4800000.00"),
        description="Receita Bruta acumulada nos últimos 12 meses (RBT12) em reais.",
    )
    valor_operacao: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        description="Valor da operação / venda simulada em reais (R$).",
    )
    anexo: AnexoSimples = Field(
        default=AnexoSimples.ANEXO_I,
        description="Anexo de enquadramento na LC 123/2006 (I a V). Sobrescrito por III/V quando aplicar_fator_r=True.",
    )
    aplicar_fator_r: bool = Field(
        default=False,
        description="Ativa simulação do Fator R (LC 123/2006: Folha 12m / RBT12 >= 28% → Anexo III, senão Anexo V).",
    )
    folha_salarios_12m: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Folha de salários, encargos e pró-labore dos últimos 12 meses (FS12) em reais.",
    )
    data_fato_gerador: date = Field(
        default=date(2026, 1, 1),
        description="Data do fato gerador para resolução de alíquotas e reduções no SQLite.",
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
    creditos_anteriores: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Créditos de IBS/CBS sobre insumos e compras anteriores (R$).",
    )
    percentual_vendas_b2b: Decimal = Field(
        default=Decimal("100.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Percentual de vendas para clientes PJ/B2B que aproveitam crédito de IBS/CBS.",
    )


class AnaliseFatorR(BaseModel):
    """Diagnóstico gerencial do Fator R (Anexo III vs. Anexo V — regra dos 28%)."""

    aplicado: bool
    folha_salarios_12m: Decimal
    percentual_fator_r: Decimal
    atingiu_minimo_28_pct: bool
    anexo_definido: AnexoSimples
    folha_minima_anexo_iii: Decimal
    folha_faltante_anexo_iii: Decimal
    folha_faltante_mensal: Decimal
    das_anexo_iii: Decimal
    das_anexo_v: Decimal
    economia_das_fator_r: Decimal
    recomendacao: str


class CenarioComparativo(BaseModel):
    """Detalhamento financeiro e de crédito tributário de um cenário simulado."""

    id: str
    nome: str
    subtitulo: str
    carga_tributaria_total: Decimal
    aliquota_efetiva_percentual: Decimal
    valor_das: Decimal
    valor_ibs_cbs_bruto: Decimal
    valor_ibs_cbs_liquido: Decimal
    valor_is: Decimal
    creditos_aproveitados: Decimal
    credito_gerado_cliente_b2b: Decimal
    custo_efetivo_cliente_b2b: Decimal
    observacoes: str


class ComparadorResponse(BaseModel):
    """Resultado consolidado da comparação lado a lado entre os três regimes."""

    valor_operacao: Decimal
    receita_bruta_12m: Decimal
    anexo: AnexoSimples
    fator_r: Optional[AnaliseFatorR] = None
    uf: Optional[str]
    c_class_trib: Optional[str]
    aliquota_ibs_uf_aplicada: Decimal
    aliquota_ibs_mun_aplicada: Decimal
    aliquota_cbs_aplicada: Decimal
    reducao_ibs_percentual: Decimal
    reducao_cbs_percentual: Decimal
    percentual_vendas_b2b: Decimal
    cenarios: list[CenarioComparativo]
    melhor_cenario_carga_propria: str
    economia_maxima_reais: Decimal
    melhor_cenario_competitividade_b2b: str
    resumo_executivo: str
