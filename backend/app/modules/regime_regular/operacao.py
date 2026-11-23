"""Motor de cálculo por operação (múltiplos itens) do Regime Regular (IBS/CBS/IS).

Aplica redução de alíquota via CST/cClassTrib do SQLite, redução de base de cálculo,
crédito presumido, compra governamental (REDUTOR_COMPRA_GOVERNAMENTAL e
TRANSFERENCIA_CBS_ENTE_GOV), diferimento de IBS/CBS e totalização fiscal sem
arredondamento intermediário (LC 214/2025).
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field

from app.core.rounding import (
    dividir_por_cem,
    formatar_aliquota,
    formatar_moeda,
    multiplicar,
    subtrair,
    totalizar,
)
from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
    obter_redutor_compra_gov_regime_geral,
    obter_transferencia_cbs_ente_gov,
)
from .regras_avancadas import (
    CreditoPresumidoInput,
    CreditoPresumidoItemResponse,
    TributacaoCompraGovItemResponse,
    aplicar_reducao_base_calculo,
    calcular_aliquota_efetiva_com_regras,
    calcular_credito_presumido_item,
    montar_detalhe_compra_governamental,
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
    percentual_reducao_base: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Redução percentual aplicada diretamente sobre a base de cálculo (%).",
    )
    percentual_diferimento: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00")
    )
    credito_presumido: Optional[CreditoPresumidoInput] = Field(
        default=None,
        description="Parâmetros opcionais de crédito presumido (IBS/CBS) sobre o item.",
    )


class OperacaoRegimeRegularRequest(BaseModel):
    """Payload de operação com múltiplos itens no Regime Regular."""

    data_fato_gerador: date = Field(default=date(2026, 1, 1))
    uf: str = Field(default="RS", min_length=2, max_length=2)
    tp_ente_gov: Optional[int] = Field(
        default=None,
        ge=1,
        le=4,
        description="Tipo de ente em compra governamental: 1=União, 2=Estado, 3=DF, 4=Município.",
    )
    percentual_redutor_compra_gov: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Override opcional do redutor governamental (%); se omitido, resolve do SQLite.",
    )
    itens: list[ItemOperacaoRequest] = Field(..., min_length=1)


class ItemOperacaoResponse(BaseModel):
    """Resultado tributário individual do item."""

    codigo_item: str
    valor_base_original: str
    valor_reducao_base: str
    valor_base: str
    valor_ibs_uf: str
    valor_ibs_mun: str
    valor_cbs: str
    valor_is: str
    valor_diferido: str
    total_devido_item: str
    credito_presumido: Optional[CreditoPresumidoItemResponse] = None
    compra_governamental: Optional[TributacaoCompraGovItemResponse] = None


class OperacaoRegimeRegularResponse(BaseModel):
    """Resultado consolidado da operação no Regime Regular."""

    uf: str
    quantidade_itens: int
    itens: list[ItemOperacaoResponse]
    total_base_calculo: str
    total_reducao_base: str
    total_ibs: str
    total_cbs: str
    total_is: str
    total_diferido: str
    total_credito_presumido_ibs: str
    total_credito_presumido_cbs: str
    total_cbs_transferida_ente_gov: str
    percentual_redutor_compra_gov_aplicado: str
    percentual_transferencia_cbs_aplicado: str
    total_geral_operacao: str


def _resolver_parametros_compra_gov(
    payload: OperacaoRegimeRegularRequest,
) -> tuple[Decimal, Decimal]:
    """Resolve redutor governamental e transferência CBS do SQLite conforme vigência."""
    if payload.tp_ente_gov is None:
        return Decimal("0.00"), Decimal("0.00")

    if payload.percentual_redutor_compra_gov is not None:
        p_redutor = payload.percentual_redutor_compra_gov
    else:
        reg_redutor = obter_redutor_compra_gov_regime_geral(payload.data_fato_gerador)
        p_redutor = Decimal(reg_redutor["percentual_redutor"]) if reg_redutor else Decimal("0.00")

    reg_transf = obter_transferencia_cbs_ente_gov(payload.data_fato_gerador)
    p_transf = Decimal(reg_transf["percentual_transferencia"]) if reg_transf else Decimal("0.00")
    return p_redutor, p_transf


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
    p_redutor_gov, p_transf_cbs = _resolver_parametros_compra_gov(payload)

    itens_resp: list[ItemOperacaoResponse] = []
    acc_base: list[Decimal] = []
    acc_red_base: list[Decimal] = []
    acc_ibs: list[Decimal] = []
    acc_cbs: list[Decimal] = []
    acc_is: list[Decimal] = []
    acc_dif: list[Decimal] = []
    acc_cred_ibs: list[Decimal] = []
    acc_cred_cbs: list[Decimal] = []
    acc_cbs_transf: list[Decimal] = []

    for item in payload.itens:
        aliq_uf = item.aliquota_ibs_uf if item.aliquota_ibs_uf is not None else aliq_uf_padrao
        aliq_cbs = item.aliquota_cbs if item.aliquota_cbs is not None else aliq_cbs_padrao

        cst_info = cst_map.get(item.c_class_trib) if item.c_class_trib else None
        red_ibs = Decimal(cst_info["aliquota_reducao_ibs"]) if cst_info else Decimal("0.00")
        red_cbs = Decimal(cst_info["aliquota_reducao_cbs"]) if cst_info else Decimal("0.00")

        base_efetiva, val_red_base = aplicar_reducao_base_calculo(
            item.valor_base, item.percentual_reducao_base
        )

        aliq_uf_efet = calcular_aliquota_efetiva_com_regras(aliq_uf, red_ibs, p_redutor_gov)
        aliq_mun_efet = calcular_aliquota_efetiva_com_regras(item.aliquota_ibs_mun, red_ibs, p_redutor_gov)
        aliq_cbs_efet = calcular_aliquota_efetiva_com_regras(aliq_cbs, red_cbs, p_redutor_gov)

        fator_dif = dividir_por_cem(item.percentual_diferimento)
        fator_devido = subtrair(Decimal("1"), fator_dif)

        bruto_ibs_uf = multiplicar(base_efetiva, dividir_por_cem(aliq_uf_efet))
        bruto_ibs_mun = multiplicar(base_efetiva, dividir_por_cem(aliq_mun_efet))
        bruto_cbs = multiplicar(base_efetiva, dividir_por_cem(aliq_cbs_efet))

        dev_ibs_uf = multiplicar(bruto_ibs_uf, fator_devido)
        dev_ibs_mun = multiplicar(bruto_ibs_mun, fator_devido)
        dev_cbs = multiplicar(bruto_cbs, fator_devido)
        dev_is = multiplicar(base_efetiva, dividir_por_cem(item.aliquota_is))

        diferido_item = totalizar((
            multiplicar(bruto_ibs_uf, fator_dif),
            multiplicar(bruto_ibs_mun, fator_dif),
            multiplicar(bruto_cbs, fator_dif),
        ))
        total_item = totalizar((dev_ibs_uf, dev_ibs_mun, dev_cbs, dev_is))

        cred_dto = None
        if item.credito_presumido is not None:
            cred_dto, cred_ibs_val, cred_cbs_val = calcular_credito_presumido_item(
                base_efetiva, item.credito_presumido
            )
            acc_cred_ibs.append(cred_ibs_val)
            acc_cred_cbs.append(cred_cbs_val)

        compra_gov_dto = None
        if payload.tp_ente_gov is not None:
            compra_gov_dto, cbs_transf_item = montar_detalhe_compra_governamental(
                tp_ente_gov=payload.tp_ente_gov,
                p_redutor_pct=p_redutor_gov,
                aliq_ibs_uf_efet_pct=aliq_uf_efet,
                val_ibs_uf=dev_ibs_uf,
                aliq_ibs_mun_efet_pct=aliq_mun_efet,
                val_ibs_mun=dev_ibs_mun,
                aliq_cbs_efet_pct=aliq_cbs_efet,
                val_cbs=dev_cbs,
                p_transferencia_cbs_pct=p_transf_cbs,
            )
            acc_cbs_transf.append(cbs_transf_item)

        acc_base.append(base_efetiva)
        acc_red_base.append(val_red_base)
        acc_ibs.append(totalizar((dev_ibs_uf, dev_ibs_mun)))
        acc_cbs.append(dev_cbs)
        acc_is.append(dev_is)
        acc_dif.append(diferido_item)

        itens_resp.append(
            ItemOperacaoResponse(
                codigo_item=item.codigo_item,
                valor_base_original=formatar_moeda(item.valor_base),
                valor_reducao_base=formatar_moeda(val_red_base),
                valor_base=formatar_moeda(base_efetiva),
                valor_ibs_uf=formatar_moeda(dev_ibs_uf),
                valor_ibs_mun=formatar_moeda(dev_ibs_mun),
                valor_cbs=formatar_moeda(dev_cbs),
                valor_is=formatar_moeda(dev_is),
                valor_diferido=formatar_moeda(diferido_item),
                total_devido_item=formatar_moeda(total_item),
                credito_presumido=cred_dto,
                compra_governamental=compra_gov_dto,
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
        total_reducao_base=formatar_moeda(totalizar(acc_red_base)),
        total_ibs=formatar_moeda(tot_ibs),
        total_cbs=formatar_moeda(tot_cbs),
        total_is=formatar_moeda(tot_is),
        total_diferido=formatar_moeda(totalizar(acc_dif)),
        total_credito_presumido_ibs=formatar_moeda(totalizar(acc_cred_ibs)),
        total_credito_presumido_cbs=formatar_moeda(totalizar(acc_cred_cbs)),
        total_cbs_transferida_ente_gov=formatar_moeda(totalizar(acc_cbs_transf)),
        percentual_redutor_compra_gov_aplicado=formatar_aliquota(p_redutor_gov),
        percentual_transferencia_cbs_aplicado=formatar_aliquota(
            p_transf_cbs if payload.tp_ente_gov in (2, 3, 4) else Decimal("0.00")
        ),
        total_geral_operacao=formatar_moeda(tot_geral),
    )
