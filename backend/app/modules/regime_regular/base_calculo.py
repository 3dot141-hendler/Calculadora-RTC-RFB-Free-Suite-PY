"""Serviço de apuração da Base de Cálculo (CBS/IBS e Imposto Seletivo).

Port fiel de `BaseCalculoService.java` (Regime Regular / RFB), validando:
- Ano de início de vigência (CBS/IBS >= 2026, IS >= 2027).
- Ano de extinção de tributos legados (PIS/COFINS >= 2027, ICMS/ISS >= 2033).
- Composição exata de parcelas que integram e não integram a base de cálculo.
"""

from decimal import Decimal
from pydantic import BaseModel, Field

from app.core.rounding import formatar_moeda

ANO_INICIO_CBS_IBS = 2026
ANO_INICIO_IS = 2027
ANO_EXTINCAO_PIS_COFINS = 2027
ANO_EXTINCAO_ICMS_ISS = 2033


class CampoInvalidoError(ValueError):
    """Erro de validação de regra fiscal ou vigência na base de cálculo."""


class BaseCalculoCibsRequest(BaseModel):
    """Payload de entrada para apuração da Base de Cálculo de CBS/IBS."""

    ano_fato_gerador: int = Field(default=2026, ge=2000, le=2100)
    valor_bem: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ajuste_acrescimos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    juros: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    multas: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    encargos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    frete: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    imposto_seletivo: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    outros_tributos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    demais_importancias: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    # Parcelas que não integram a base
    cosip: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ipi: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    desconto_incondicional: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    pis: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    pis_importacao: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    cofins: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    cofins_importacao: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    icms: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    iss: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class BaseCalculoISMercadoriasRequest(BaseModel):
    """Payload de entrada para apuração da Base de Cálculo do Imposto Seletivo (Mercadorias)."""

    ano_fato_gerador: int = Field(default=2027, ge=2000, le=2100)
    valor_bem: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ajuste_acrescimos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    juros: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    multas: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    encargos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    frete_cobrado: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    outros_tributos: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    demais_importancias: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    # Parcelas que não integram a base
    cosip: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ipi: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    desconto_incondicional: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    bonificacao: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    devolucao_vendas: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    icms: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    iss: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class BaseCalculoResponse(BaseModel):
    """Resultado da apuração de Base de Cálculo com formatação oficial."""

    base_calculo: str


def _valida_ano_inicio(ano_fato_gerador: int, ano_inicio: int, tributo: str) -> None:
    if ano_fato_gerador < ano_inicio:
        raise CampoInvalidoError(
            f"Para {tributo}, o ano do fato gerador deve ser {ano_inicio} ou superior"
        )


def _valida_extincao(campos: dict[str, Decimal], ano_fato_gerador: int, ano_extincao: int) -> None:
    if ano_fato_gerador >= ano_extincao:
        informados = sorted(nome for nome, val in campos.items() if val != Decimal("0"))
        if informados:
            raise CampoInvalidoError(
                f"Os seguintes campos não podem ser informados a partir de {ano_extincao}: "
                + ", ".join(informados)
            )


def _valida_base_nao_negativa(base_calculo: Decimal) -> None:
    if base_calculo < Decimal("0"):
        raise CampoInvalidoError(
            "Base de cálculo não pode ser negativa. A soma dos valores que não integram a base "
            "é maior que a soma dos valores que integram a base."
        )


def calcular_base_cibs(payload: BaseCalculoCibsRequest) -> BaseCalculoResponse:
    """Calcula a base de cálculo de CBS/IBS conforme regras de vigência da RFB."""
    _valida_ano_inicio(payload.ano_fato_gerador, ANO_INICIO_CBS_IBS, "CBS/IBS")
    _valida_extincao(
        {
            "PIS": payload.pis,
            "PIS Importação": payload.pis_importacao,
            "COFINS": payload.cofins,
            "COFINS Importação": payload.cofins_importacao,
        },
        payload.ano_fato_gerador,
        ANO_EXTINCAO_PIS_COFINS,
    )
    _valida_extincao(
        {"ICMS": payload.icms, "ISS": payload.iss},
        payload.ano_fato_gerador,
        ANO_EXTINCAO_ICMS_ISS,
    )

    integra = (
        payload.valor_bem
        + payload.ajuste_acrescimos
        + payload.juros
        + payload.multas
        + payload.encargos
        + payload.frete
        + payload.imposto_seletivo
        + payload.outros_tributos
        + payload.demais_importancias
    )
    nao_integra = (
        payload.cosip
        + payload.ipi
        + payload.desconto_incondicional
        + payload.pis
        + payload.pis_importacao
        + payload.cofins
        + payload.cofins_importacao
        + payload.icms
        + payload.iss
    )

    base = integra - nao_integra
    _valida_base_nao_negativa(base)
    return BaseCalculoResponse(base_calculo=formatar_moeda(base))


def calcular_base_is_mercadorias(payload: BaseCalculoISMercadoriasRequest) -> BaseCalculoResponse:
    """Calcula a base de cálculo do Imposto Seletivo sobre mercadorias."""
    _valida_ano_inicio(payload.ano_fato_gerador, ANO_INICIO_IS, "IS")
    _valida_extincao(
        {"ICMS": payload.icms, "ISS": payload.iss},
        payload.ano_fato_gerador,
        ANO_EXTINCAO_ICMS_ISS,
    )

    integra = (
        payload.valor_bem
        + payload.ajuste_acrescimos
        + payload.juros
        + payload.multas
        + payload.encargos
        + payload.frete_cobrado
        + payload.outros_tributos
        + payload.demais_importancias
    )
    nao_integra = (
        payload.cosip
        + payload.ipi
        + payload.desconto_incondicional
        + payload.bonificacao
        + payload.devolucao_vendas
        + payload.icms
        + payload.iss
    )

    base = integra - nao_integra
    _valida_base_nao_negativa(base)
    return BaseCalculoResponse(base_calculo=formatar_moeda(base))

