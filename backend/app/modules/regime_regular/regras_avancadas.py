"""Regras puras avançadas do Regime Regular: redução de base, crédito presumido e compra governamental.

Motor puro sem acesso a banco de dados (Decimal + ROUND_HALF_EVEN via `app.core.rounding`).
Referências oficiais RFB:
- `CreditoPresumidoOperacaoDomain.java` (`gIBSCredPres`, `gCBSCredPres`)
- `TributacaoCompraGovernamentalDomain.java` + migração `V0019` (`REDUTOR_COMPRA_GOVERNAMENTAL`, `TRANSFERENCIA_CBS_ENTE_GOV`)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from app.core.rounding import (
    dividir_por_cem,
    formatar_aliquota,
    formatar_moeda,
    multiplicar,
    subtrair,
)
from .expressao_engine import avaliar_expressao_tributaria

NOMES_ENTE_GOV: dict[int, str] = {
    1: "União",
    2: "Estado",
    3: "Distrito Federal",
    4: "Município",
}


class CreditoPresumidoInput(BaseModel):
    """Configuração de crédito presumido aplicável ao item da operação (LC 214/2025)."""

    codigo_credito_presumido: Optional[int] = Field(
        default=None, ge=1, description="Código cCredPres oficial da classificação de crédito presumido."
    )
    percentual_ibs: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="pCredPres IBS (%)."
    )
    percentual_cbs: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="pCredPres CBS (%)."
    )
    condicao_suspensiva: bool = Field(
        default=False,
        description="Se verdadeiro, classifica o valor em vCredPresCondSus (condição suspensiva).",
    )


class CreditoPresumidoItemResponse(BaseModel):
    """Detalhamento do crédito presumido apurado para o item (espelho de CreditoPresumidoOperacaoDomain)."""

    vBCCredPres: str
    cCredPres: Optional[int] = None
    pCredPresIBS: str
    vCredPresIBS: str
    vCredPresCondSusIBS: str
    pCredPresCBS: str
    vCredPresCBS: str
    vCredPresCondSusCBS: str


class TributacaoCompraGovItemResponse(BaseModel):
    """Detalhamento de compra governamental no Regime Geral (TributacaoCompraGovernamentalDomain)."""

    tpEnteGov: int
    ente_governamental: str
    pRedutor: str
    pAliqIBSUF: str
    vTribIBSUF: str
    pAliqIBSMun: str
    vTribIBSMun: str
    pAliqCBS: str
    vTribCBS: str
    pTransferenciaCBS: str
    vCBSTransferidaEnte: str


def aplicar_reducao_base_calculo(
    valor_base_original: Decimal,
    percentual_reducao_base: Decimal,
) -> tuple[Decimal, Decimal]:
    """Aplica redução percentual sobre a base de cálculo retornando (base_efetiva, valor_reducao)."""
    if percentual_reducao_base <= Decimal("0"):
        return valor_base_original, Decimal("0")
    fator_reducao = dividir_por_cem(percentual_reducao_base)
    valor_reducao = multiplicar(valor_base_original, fator_reducao)
    base_efetiva = subtrair(valor_base_original, valor_reducao)
    return base_efetiva, valor_reducao


def calcular_credito_presumido_item(
    base_efetiva: Decimal,
    cfg: CreditoPresumidoInput,
) -> tuple[CreditoPresumidoItemResponse, Decimal, Decimal]:
    """Apura crédito presumido de IBS e CBS sobre a base efetiva do item.

    Retorna `(dto_resposta, valor_credito_ibs_ativo, valor_credito_cbs_ativo)`.
    Quando `condicao_suspensiva=True`, o valor vai para `vCredPresCondSus*` e o ativo é `0`.
    """
    bruto_ibs = multiplicar(base_efetiva, dividir_por_cem(cfg.percentual_ibs))
    bruto_cbs = multiplicar(base_efetiva, dividir_por_cem(cfg.percentual_cbs))

    if cfg.condicao_suspensiva:
        val_ibs, susp_ibs = Decimal("0"), bruto_ibs
        val_cbs, susp_cbs = Decimal("0"), bruto_cbs
    else:
        val_ibs, susp_ibs = bruto_ibs, Decimal("0")
        val_cbs, susp_cbs = bruto_cbs, Decimal("0")

    dto = CreditoPresumidoItemResponse(
        vBCCredPres=formatar_moeda(base_efetiva),
        cCredPres=cfg.codigo_credito_presumido,
        pCredPresIBS=formatar_aliquota(cfg.percentual_ibs),
        vCredPresIBS=formatar_moeda(val_ibs),
        vCredPresCondSusIBS=formatar_moeda(susp_ibs),
        pCredPresCBS=formatar_aliquota(cfg.percentual_cbs),
        vCredPresCBS=formatar_moeda(val_cbs),
        vCredPresCondSusCBS=formatar_moeda(susp_cbs),
    )
    return dto, val_ibs, val_cbs


def calcular_aliquota_efetiva_com_regras(
    aliquota_nominal_pct: Decimal,
    percentual_reducao_aliq_pct: Decimal,
    percentual_redutor_compra_gov_pct: Decimal = Decimal("0"),
) -> Decimal:
    """Calcula alíquota efetiva (%) usando o avaliador seguro de expressões (ADR001)."""
    aliquota_dec = dividir_por_cem(aliquota_nominal_pct)
    red_dec = dividir_por_cem(percentual_reducao_aliq_pct)
    gov_dec = dividir_por_cem(percentual_redutor_compra_gov_pct)
    efetiva_dec, _ = avaliar_expressao_tributaria(
        "aliquota * (1 - percentualReducao) * (1 - percentualReducaoCompraGov)",
        {
            "aliquota": aliquota_dec,
            "percentualReducao": red_dec,
            "percentualReducaoCompraGov": gov_dec,
        },
    )
    return efetiva_dec * Decimal("100")


def montar_detalhe_compra_governamental(
    tp_ente_gov: int,
    p_redutor_pct: Decimal,
    aliq_ibs_uf_efet_pct: Decimal,
    val_ibs_uf: Decimal,
    aliq_ibs_mun_efet_pct: Decimal,
    val_ibs_mun: Decimal,
    aliq_cbs_efet_pct: Decimal,
    val_cbs: Decimal,
    p_transferencia_cbs_pct: Decimal,
) -> tuple[TributacaoCompraGovItemResponse, Decimal]:
    """Monta grupo `compra_governamental` do item e apura parcela de CBS transferida ao ente (UF/DF/Mun)."""
    # União (1) já é o titular da CBS; Estados (2), DF (3) e Municípios (4) recebem transferência conforme V0019
    if tp_ente_gov in (2, 3, 4) and p_transferencia_cbs_pct > Decimal("0"):
        cbs_transferida = multiplicar(val_cbs, dividir_por_cem(p_transferencia_cbs_pct))
        pct_transf_aplicado = p_transferencia_cbs_pct
    else:
        cbs_transferida = Decimal("0")
        pct_transf_aplicado = Decimal("0")

    dto = TributacaoCompraGovItemResponse(
        tpEnteGov=tp_ente_gov,
        ente_governamental=NOMES_ENTE_GOV.get(tp_ente_gov, f"Ente {tp_ente_gov}"),
        pRedutor=formatar_aliquota(p_redutor_pct),
        pAliqIBSUF=formatar_aliquota(aliq_ibs_uf_efet_pct),
        vTribIBSUF=formatar_moeda(val_ibs_uf),
        pAliqIBSMun=formatar_aliquota(aliq_ibs_mun_efet_pct),
        vTribIBSMun=formatar_moeda(val_ibs_mun),
        pAliqCBS=formatar_aliquota(aliq_cbs_efet_pct),
        vTribCBS=formatar_moeda(val_cbs),
        pTransferenciaCBS=formatar_aliquota(pct_transf_aplicado),
        vCBSTransferidaEnte=formatar_moeda(cbs_transferida),
    )
    return dto, cbs_transferida
