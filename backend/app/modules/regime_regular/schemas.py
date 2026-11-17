"""Schemas Pydantic para o módulo Regime Regular (IBS/CBS/IS)."""

from decimal import Decimal
from pydantic import BaseModel, Field


class RegimeRegularCalculoRequest(BaseModel):
    """Payload de entrada para cálculo no Regime Regular da Reforma Tributária."""

    valor_operacao: Decimal = Field(..., gt=Decimal("0.00"), description="Valor base da operação (R$).")
    aliquota_ibs_uf: Decimal = Field(
        default=Decimal("10.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota IBS Estadual (%)."
    )
    aliquota_ibs_mun: Decimal = Field(
        default=Decimal("7.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota IBS Municipal (%)."
    )
    aliquota_cbs: Decimal = Field(
        default=Decimal("8.80"), ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota CBS Federal (%)."
    )
    aliquota_is: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="Alíquota Imposto Seletivo (%)."
    )
    percentual_reducao: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Redução de alíquota prevista em regime diferenciado (%).",
    )
    creditos_anteriores: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Créditos acumulados de etapas anteriores (R$).",
    )


class RegimeRegularCalculoResponse(BaseModel):
    """Resultado detalhado do cálculo de IBS, CBS e Imposto Seletivo."""

    base_calculo: Decimal
    valor_ibs_uf: Decimal
    valor_ibs_mun: Decimal
    valor_cbs: Decimal
    valor_is: Decimal
    total_bruto_tributos: Decimal
    creditos_aproveitados: Decimal
    valor_liquido_a_recolher: Decimal

