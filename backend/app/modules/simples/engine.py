"""Motor puro de cálculo do Simples Nacional (NT 2026.005 v1.00).

Port fiel de `SimplesNacionalCalculoService.java` da Receita Federal
(LC 123/2006, LC 214/2025, LC 227/2026).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from app.core.rounding import (
    dividir_por_cem,
    multiplicar,
    subtrair,
    totalizar,
)


class DestinoValorSimples(str, Enum):
    """Destino de um valor de tributo calculado pelo Simples Nacional."""

    DEVIDO = "DEVIDO"
    PENDENTE_SUSPENSO = "PENDENTE_SUSPENSO"
    ZERO = "ZERO"


class EstadoItemSimples(str, Enum):
    """Estados possíveis de um item processado pelo Simples Nacional."""

    CALCULADO = "CALCULADO"
    NAO_CALCULADO = "NAO_CALCULADO"
    NAO_IMPLEMENTADO = "NAO_IMPLEMENTADO"
    INCONSISTENCIA_ENTRADA = "INCONSISTENCIA_ENTRADA"
    FALHA_TECNICA = "FALHA_TECNICA"


class RegimeCalculoSimples(str, Enum):
    """Combinações válidas CRT × tpRegimeIBSCBS (NT 2026.005, seção 5.3.4)."""

    CRT_1 = "CRT_1"
    CRT_2 = "CRT_2"
    CRT_3_TPREGIME_2 = "CRT_3_TPREGIME_2"


@dataclass(frozen=True)
class RegimeApuracaoConfig:
    """Parâmetros da matriz de regime de apuração do Simples Nacional."""

    regime: RegimeCalculoSimples
    gera_ibs: bool
    destino_devido: DestinoValorSimples
    destino_pendente_suspenso: DestinoValorSimples


@dataclass(frozen=True)
class TipoReceitaBrutaConfig:
    """Efeito parametrizado do tipo de receita bruta (tpRBSN)."""

    codigo: int
    descricao: str
    compoe_receita: bool
    imposto_seletivo_compoe_receita: bool
    fator_receita: Decimal
    pendente_suspenso: bool


@dataclass(frozen=True)
class InsumoCalculoSimples:
    """Insumos resolvidos e validados de um item do Simples Nacional."""

    regime: RegimeApuracaoConfig
    tipo_receita_bruta: TipoReceitaBrutaConfig
    c_ativ_sn_valido: bool
    base_calculo: Decimal
    valor_imposto_seletivo: Decimal = Decimal("0.00")
    p_ibs_sn: Optional[Decimal] = None
    p_cbs_sn: Optional[Decimal] = None
    tp_ente_gov: Optional[int] = None
    fator_transicao_compra_gov: Optional[Decimal] = None


@dataclass(frozen=True)
class TributosSimplesResult:
    """Tributos calculados para um item do Simples Nacional."""

    v_rbsn_item: Decimal
    tp_rbsn: int
    tp_rbsn_descricao: str
    v_bc: Optional[Decimal] = None
    p_ibs_sn: Optional[Decimal] = None
    v_ibs_sn: Optional[Decimal] = None
    v_ibs_pend_susp: Optional[Decimal] = None
    p_cbs_sn: Optional[Decimal] = None
    v_cbs_sn: Optional[Decimal] = None
    v_cbs_pend_susp: Optional[Decimal] = None
    valor_is: Optional[Decimal] = None
    total_item: Optional[Decimal] = None


@dataclass(frozen=True)
class ResultadoCalculoSimples:
    """Estado e tributos calculados do item."""

    estado_item: EstadoItemSimples
    trib_calc: TributosSimplesResult


def _aplicar_deslocamento_cbs_ibs(
    p_ibs_sn: Optional[Decimal],
    p_cbs_sn: Optional[Decimal],
    tp_ente_gov: Optional[int],
    fator: Optional[Decimal],
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Passo 2 do pipeline: deslocamento CBS↔IBS em compras governamentais."""
    if tp_ente_gov is None or (p_ibs_sn is None and p_cbs_sn is None):
        return p_ibs_sn, p_cbs_sn

    p_ibs = p_ibs_sn if p_ibs_sn is not None else Decimal("0")
    p_cbs = p_cbs_sn if p_cbs_sn is not None else Decimal("0")

    if tp_ente_gov == 1:
        # União: pCBS' = pCBS + pIBS; pIBS' = 0
        return Decimal("0"), totalizar((p_cbs, p_ibs))

    if fator is None:
        raise ValueError(
            f"Fator de transição de compra governamental obrigatório para tpEnteGov={tp_ente_gov}."
        )

    # pIBS' = pIBS + f × pCBS; pCBS' = (1 − f) × pCBS
    p_ibs_transf = totalizar((p_ibs, multiplicar(fator, p_cbs)))
    p_cbs_transf = multiplicar(subtrair(Decimal("1"), fator), p_cbs)
    return p_ibs_transf, p_cbs_transf


def _valor_tributo(
    v_rbsn_item: Decimal,
    fator_receita: Decimal,
    aliquota: Optional[Decimal],
) -> Decimal:
    """Valor bruto: vRBSNitem × fatorReceita × (alíquota / 100)."""
    if aliquota is None or fator_receita == 0:
        return Decimal("0")
    return multiplicar(multiplicar(v_rbsn_item, fator_receita), dividir_por_cem(aliquota))


def _repartir_por_regime(
    regime: RegimeApuracaoConfig,
    valor: Decimal,
    pendente_suspenso: bool,
) -> tuple[Decimal, Decimal]:
    """Reparte valor entre (devido, pendente_suspenso) conforme matriz do regime."""
    destino = regime.destino_pendente_suspenso if pendente_suspenso else regime.destino_devido
    if destino == DestinoValorSimples.DEVIDO:
        return valor, Decimal("0")
    if destino == DestinoValorSimples.PENDENTE_SUSPENSO:
        return Decimal("0"), valor
    return Decimal("0"), Decimal("0")


def calcular_item_simples(insumo: InsumoCalculoSimples) -> ResultadoCalculoSimples:
    """Ponto único de decisão de fluxo de cálculo do Simples Nacional (NT 2026.005)."""
    tipo_receita = insumo.tipo_receita_bruta

    if tipo_receita.compoe_receita:
        if tipo_receita.imposto_seletivo_compoe_receita:
            v_rbsn_item = totalizar((insumo.base_calculo, insumo.valor_imposto_seletivo))
        else:
            v_rbsn_item = totalizar((insumo.base_calculo,))
    else:
        v_rbsn_item = Decimal("0")

    if not insumo.c_ativ_sn_valido:
        return ResultadoCalculoSimples(
            estado_item=EstadoItemSimples.NAO_CALCULADO,
            trib_calc=TributosSimplesResult(
                v_rbsn_item=v_rbsn_item,
                tp_rbsn=tipo_receita.codigo,
                tp_rbsn_descricao=tipo_receita.descricao,
            ),
        )

    p_ibs_transf, p_cbs_transf = _aplicar_deslocamento_cbs_ibs(
        insumo.p_ibs_sn,
        insumo.p_cbs_sn,
        insumo.tp_ente_gov,
        insumo.fator_transicao_compra_gov,
    )

    fator_receita = tipo_receita.fator_receita
    v_bc = multiplicar(v_rbsn_item, fator_receita)

    valor_ibs = _valor_tributo(v_rbsn_item, fator_receita, p_ibs_transf)
    valor_cbs = _valor_tributo(v_rbsn_item, fator_receita, p_cbs_transf)

    gera_ibs = insumo.regime.gera_ibs
    ibs_devido, ibs_pend = (
        _repartir_por_regime(insumo.regime, valor_ibs, tipo_receita.pendente_suspenso)
        if gera_ibs
        else (None, None)
    )
    cbs_devido, cbs_pend = _repartir_por_regime(
        insumo.regime, valor_cbs, tipo_receita.pendente_suspenso
    )

    valor_is = insumo.valor_imposto_seletivo
    parcelas_devidas = [v for v in (ibs_devido, cbs_devido, valor_is) if v is not None]
    total_item = totalizar(parcelas_devidas)

    return ResultadoCalculoSimples(
        estado_item=EstadoItemSimples.CALCULADO,
        trib_calc=TributosSimplesResult(
            v_rbsn_item=v_rbsn_item,
            tp_rbsn=tipo_receita.codigo,
            tp_rbsn_descricao=tipo_receita.descricao,
            v_bc=v_bc,
            p_ibs_sn=p_ibs_transf if gera_ibs else None,
            v_ibs_sn=ibs_devido,
            v_ibs_pend_susp=ibs_pend,
            p_cbs_sn=p_cbs_transf,
            v_cbs_sn=cbs_devido,
            v_cbs_pend_susp=cbs_pend,
            valor_is=valor_is,
            total_item=total_item,
        ),
    )
