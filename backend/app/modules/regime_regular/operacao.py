"""Motor de cálculo por operação (múltiplos itens) do Regime Regular (IBS/CBS/IS).

Aplica redução via CST/cClassTrib do SQLite, diferimento de IBS/CBS e
totalização fiscal sem arredondamento intermediário (LC 214/2025).
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from app.core.rounding import (
    dividir_por_cem,
    formatar_moeda,
    multiplicar,
    subtrair,
    totalizar,
)
from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
)


class ItemOperacaoRequest(BaseModel):
    """Item individual de uma operação no Regime Regular."""

    codigo_item: str = Field(..., min_length=1, max_length=60)
    valor_base: Decimal = Field(..., gt=Decimal("0.00"))
    c_class_trib: Optional[str] = Field(default=None)
    aliquota_ibs_uf: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    aliquota_ibs_mun: Decimal = Field(default=Decimal("7.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    aliquota_cbs: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    aliquota_is: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    percentual_diferimento: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00")
    )


class OperacaoRegimeRegularRequest(BaseModel):
    """Payload de operação com múltiplos itens no Regime Regular."""

    data_fato_gerador: date = Field(default=date(2026, 1, 1))
    uf: str = Field(default="RS", min_length=2, max_length=2)
    itens: list[ItemOperacaoRequest] = Field(..., min_length=1)


class ItemOperacaoResponse(BaseModel):
    """Resultado tributário individual do item."""

    codigo_item: str
    valor_base: str
    valor_ibs_uf: str
    valor_ibs_mun: str
    valor_cbs: str
    valor_is: str
    valor_diferido: str
    total_devido_item: str


class OperacaoRegimeRegularResponse(BaseModel):
    """Resultado consolidado da operação no Regime Regular."""

    uf: str
    quantidade_itens: int
    itens: list[ItemOperacaoResponse]
    total_base_calculo: str
    total_ibs: str
    total_cbs: str
    total_is: str
    total_diferido: str
    total_geral_operacao: str


def calcular_operacao_regime_regular(
    payload: OperacaoRegimeRegularRequest,
) -> OperacaoRegimeRegularResponse:
    """Calcula múltiplos itens com vigência no SQLite e totaliza sem arredondamento intermediário."""
    ufs = listar_ufs_referencia(payload.data_fato_gerador)
    uf_upper = payload.uf.upper()
    uf_match = next((u for u in ufs if u["uf"] == uf_upper), None)
    aliq_uf_padrao = Decimal(uf_match["aliquota_ibs_uf"]) if uf_match else Decimal("10.00")
    aliq_cbs_padrao = Decimal(uf_match["aliquota_cbs"]) if uf_match else Decimal("8.80")

    csts = listar_cst_classificacao(payload.data_fato_gerador)
    cst_map = {c["c_class_trib"]: c for c in csts}

    itens_resp: list[ItemOperacaoResponse] = []
    acc_base: list[Decimal] = []
    acc_ibs: list[Decimal] = []
    acc_cbs: list[Decimal] = []
    acc_is: list[Decimal] = []
    acc_dif: list[Decimal] = []

    for item in payload.itens:
        aliq_uf = item.aliquota_ibs_uf if item.aliquota_ibs_uf is not None else aliq_uf_padrao
        aliq_cbs = item.aliquota_cbs if item.aliquota_cbs is not None else aliq_cbs_padrao

        cst_info = cst_map.get(item.c_class_trib) if item.c_class_trib else None
        red_ibs = Decimal(cst_info["aliquota_reducao_ibs"]) if cst_info else Decimal("0.00")
        red_cbs = Decimal(cst_info["aliquota_reducao_cbs"]) if cst_info else Decimal("0.00")

        fator_red_ibs = subtrair(Decimal("1"), dividir_por_cem(red_ibs))
        fator_red_cbs = subtrair(Decimal("1"), dividir_por_cem(red_cbs))
        fator_dif = dividir_por_cem(item.percentual_diferimento)
        fator_devido = subtrair(Decimal("1"), fator_dif)

        bruto_ibs_uf = multiplicar(multiplicar(item.valor_base, dividir_por_cem(aliq_uf)), fator_red_ibs)
        bruto_ibs_mun = multiplicar(multiplicar(item.valor_base, dividir_por_cem(item.aliquota_ibs_mun)), fator_red_ibs)
        bruto_cbs = multiplicar(multiplicar(item.valor_base, dividir_por_cem(aliq_cbs)), fator_red_cbs)

        dev_ibs_uf = multiplicar(bruto_ibs_uf, fator_devido)
        dev_ibs_mun = multiplicar(bruto_ibs_mun, fator_devido)
        dev_cbs = multiplicar(bruto_cbs, fator_devido)
        dev_is = multiplicar(item.valor_base, dividir_por_cem(item.aliquota_is))

        diferido_item = totalizar((
            multiplicar(bruto_ibs_uf, fator_dif),
            multiplicar(bruto_ibs_mun, fator_dif),
            multiplicar(bruto_cbs, fator_dif),
        ))
        total_item = totalizar((dev_ibs_uf, dev_ibs_mun, dev_cbs, dev_is))

        acc_base.append(item.valor_base)
        acc_ibs.append(totalizar((dev_ibs_uf, dev_ibs_mun)))
        acc_cbs.append(dev_cbs)
        acc_is.append(dev_is)
        acc_dif.append(diferido_item)

        itens_resp.append(
            ItemOperacaoResponse(
                codigo_item=item.codigo_item,
                valor_base=formatar_moeda(item.valor_base),
                valor_ibs_uf=formatar_moeda(dev_ibs_uf),
                valor_ibs_mun=formatar_moeda(dev_ibs_mun),
                valor_cbs=formatar_moeda(dev_cbs),
                valor_is=formatar_moeda(dev_is),
                valor_diferido=formatar_moeda(diferido_item),
                total_devido_item=formatar_moeda(total_item),
            )
        )

    tot_ibs = totalizar(acc_ibs)
    tot_cbs = totalizar(acc_cbs)
    tot_is = totalizar(acc_is)
    tot_geral = totalizar((tot_ibs, tot_cbs, tot_is))

    return OperacaoRegimeRegularResponse(
        uf=uf_upper,
        quantidade_itens=len(itens_resp),
        itens=itens_resp,
        total_base_calculo=formatar_moeda(totalizar(acc_base)),
        total_ibs=formatar_moeda(tot_ibs),
        total_cbs=formatar_moeda(tot_cbs),
        total_is=formatar_moeda(tot_is),
        total_diferido=formatar_moeda(totalizar(acc_dif)),
        total_geral_operacao=formatar_moeda(tot_geral),
    )
