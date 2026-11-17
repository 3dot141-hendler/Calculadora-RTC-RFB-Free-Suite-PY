"""Schemas Pydantic para o módulo Simples Nacional (RTC)."""

from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field


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

