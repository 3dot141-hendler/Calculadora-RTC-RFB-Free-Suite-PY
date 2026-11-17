"""Schemas Pydantic para o módulo Simples Nacional (RTC)."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from .engine import DestinoValorSimples, EstadoItemSimples, RegimeCalculoSimples


class AnexoSimples(str, Enum):
    """Anexos previstos na LC 123/2006 adaptados para a transição RTC."""

    ANEXO_I = "I"
    ANEXO_II = "II"
    ANEXO_III = "III"
    ANEXO_IV = "IV"
    ANEXO_V = "V"


class SimplesCalculoRequest(BaseModel):
    """Payload de entrada para simulação de cálculo no Simples Nacional."""

    receita_bruta_12m: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        le=Decimal("4800000.00"),
        description="Receita Bruta acumulada nos últimos 12 meses (RBT12).",
    )
    valor_operacao: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        description="Valor da operação/faturamento do período em reais (R$).",
    )
    anexo: AnexoSimples = Field(
        default=AnexoSimples.ANEXO_I,
        description="Anexo de enquadramento no Simples Nacional.",
    )
    recolher_ibs_cbs_por_fora: bool = Field(
        default=False,
        description="Indica opção pelo recolhimento de IBS/CBS pelo regime regular (por fora do DAS).",
    )


class SimplesCalculoResponse(BaseModel):
    """Resultado detalhado do cálculo do Simples Nacional com transição IBS/CBS."""

    anexo: AnexoSimples
    aliquota_efetiva_das: Decimal = Field(..., description="Alíquota efetiva total no DAS (%).")
    valor_das: Decimal = Field(..., description="Valor estimado do DAS em reais (R$).")
    valor_ibs_cbs_estimado: Decimal = Field(
        ..., description="Parcela ou valor de referência de IBS + CBS (R$)."
    )
    valor_total_tributos: Decimal = Field(..., description="Carga tributária total estimada (R$).")
    observacoes: str


class SimplesItemCalculoRequest(BaseModel):
    """Payload de entrada para cálculo por item conforme NT 2026.005 v1.00."""

    regime: RegimeCalculoSimples = Field(
        default=RegimeCalculoSimples.CRT_1,
        description="Combinação CRT × tpRegimeIBSCBS.",
    )
    data_fato_gerador: date = Field(
        default=date(2026, 1, 1),
        description="Data do fato gerador para resolução automática de vigências no SQLite.",
    )
    tp_rbsn: int = Field(default=1, ge=0, le=9, description="Código do Tipo de Receita Bruta (tpRBSN).")
    c_ativ_sn: Optional[str] = Field(
        default=None,
        description="Código de atividade cAtivSN (quando informado, é validado na tabela oficial).",
    )
    c_ativ_sn_valido: bool = Field(
        default=True,
        description="Indica se o código de atividade cAtivSN está válido e vigente.",
    )
    base_calculo: Decimal = Field(..., ge=Decimal("0.00"), description="Base de cálculo do item (R$).")
    valor_imposto_seletivo: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Valor do Imposto Seletivo (vIS)."
    )
    p_ibs_sn: Optional[Decimal] = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota IBS Simples (%)."
    )
    p_cbs_sn: Optional[Decimal] = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota CBS Simples (%)."
    )
    tp_ente_gov: Optional[int] = Field(
        default=None, ge=1, le=4, description="Tipo de ente governamental (1=União, 2/3/4=Outros)."
    )
    fator_transicao_compra_gov: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("1.00"),
        description="Fator de transição CBS→IBS para tpEnteGov ∈ {2, 3, 4} (opcional se vigente no banco).",
    )


class SimplesItemTributosResponse(BaseModel):
    """Tributos calculados do item com formatação fiscal oficial."""

    v_rbsn_item: str
    tp_rbsn: int
    tp_rbsn_descricao: str
    v_bc: Optional[str] = None
    p_ibs_sn: Optional[str] = None
    v_ibs_sn: Optional[str] = None
    v_ibs_pend_susp: Optional[str] = None
    p_cbs_sn: Optional[str] = None
    v_cbs_sn: Optional[str] = None
    v_cbs_pend_susp: Optional[str] = None
    valor_is: Optional[str] = None
    total_item: Optional[str] = None


class SimplesItemCalculoResponse(BaseModel):
    """Resposta oficial do cálculo por item do Simples Nacional (NT 2026.005)."""

    estado_item: EstadoItemSimples
    regime: RegimeCalculoSimples
    destino_devido: DestinoValorSimples
    trib_calc: SimplesItemTributosResponse

