"""Serviço de regras de negócio do Simples Nacional (esqueleto para port da RFB)."""

from decimal import Decimal, ROUND_HALF_UP

from app.core.rounding import formatar_aliquota, formatar_moeda
from app.modules.tabelas_oficiais.repository import (
    listar_atividades_simples,
    obter_fator_compra_gov_simples,
)
from .engine import (
    DestinoValorSimples,
    InsumoCalculoSimples,
    RegimeApuracaoConfig,
    RegimeCalculoSimples,
    TipoReceitaBrutaConfig,
    calcular_item_simples,
)
from .schemas import (
    AnexoSimples,
    SimplesCalculoRequest,
    SimplesCalculoResponse,
    SimplesItemCalculoRequest,
    SimplesItemCalculoResponse,
    SimplesItemTributosResponse,
)

# Tabela simplificada de alíquota nominal base por anexo (referência inicial para TDD)
_ALIQUOTA_BASE_ANEXO: dict[AnexoSimples, Decimal] = {
    AnexoSimples.ANEXO_I: Decimal("0.0400"),
    AnexoSimples.ANEXO_II: Decimal("0.0450"),
    AnexoSimples.ANEXO_III: Decimal("0.0600"),
    AnexoSimples.ANEXO_IV: Decimal("0.0450"),
    AnexoSimples.ANEXO_V: Decimal("0.1550"),
}

_ALIQUOTA_TRANSICAO_IBS_CBS = Decimal("0.0100")  # 1,0% referência inicial de transição


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_simples(payload: SimplesCalculoRequest) -> SimplesCalculoResponse:
    """Executa o cálculo estimado do Simples Nacional com parametrização RTC.

    As faixas progressivas completas e deduções por partilha de tributos serão
    portadas a partir do código de referência em `originals:references/simples`.
    """
    aliquota_base = _ALIQUOTA_BASE_ANEXO[payload.anexo]
    fator_faixa = (payload.receita_bruta_12m / Decimal("4800000.00")) * Decimal("0.05")
    aliquota_efetiva = (aliquota_base + fator_faixa).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    valor_das = _round_money(payload.valor_operacao * aliquota_efetiva)

    if payload.recolher_ibs_cbs_por_fora:
        valor_ibs_cbs = _round_money(payload.valor_operacao * _ALIQUOTA_TRANSICAO_IBS_CBS)
        obs = "Cálculo com IBS/CBS destacado por fora do DAS (opção regime regular)."
    else:
        valor_ibs_cbs = _round_money(valor_das * Decimal("0.20"))
        obs = "Cálculo unificado via DAS com parcela estimada de IBS/CBS."

    valor_total = (
        valor_das + valor_ibs_cbs if payload.recolher_ibs_cbs_por_fora else valor_das
    )

    return SimplesCalculoResponse(
        anexo=payload.anexo,
        aliquota_efetiva_das=(aliquota_efetiva * Decimal("100")).quantize(Decimal("0.01")),
        valor_das=valor_das,
        valor_ibs_cbs_estimado=valor_ibs_cbs,
        valor_total_tributos=_round_money(valor_total),
        observacoes=obs,
    )


_REGIMES_PADRAO: dict[RegimeCalculoSimples, RegimeApuracaoConfig] = {
    RegimeCalculoSimples.CRT_1: RegimeApuracaoConfig(
        regime=RegimeCalculoSimples.CRT_1,
        gera_ibs=True,
        destino_devido=DestinoValorSimples.DEVIDO,
        destino_pendente_suspenso=DestinoValorSimples.PENDENTE_SUSPENSO,
    ),
    RegimeCalculoSimples.CRT_2: RegimeApuracaoConfig(
        regime=RegimeCalculoSimples.CRT_2,
        gera_ibs=False,
        destino_devido=DestinoValorSimples.DEVIDO,
        destino_pendente_suspenso=DestinoValorSimples.PENDENTE_SUSPENSO,
    ),
    RegimeCalculoSimples.CRT_3_TPREGIME_2: RegimeApuracaoConfig(
        regime=RegimeCalculoSimples.CRT_3_TPREGIME_2,
        gera_ibs=True,
        destino_devido=DestinoValorSimples.PENDENTE_SUSPENSO,
        destino_pendente_suspenso=DestinoValorSimples.ZERO,
    ),
}

_TIPOS_RECEITA_PADRAO: dict[int, TipoReceitaBrutaConfig] = {
    0: TipoReceitaBrutaConfig(0, "Não compõe receita bruta", False, False, Decimal("0.0"), False),
    1: TipoReceitaBrutaConfig(1, "Receita tributada integralmente", True, False, Decimal("1.0"), False),
    2: TipoReceitaBrutaConfig(2, "Receita imune/isenta", True, False, Decimal("0.0"), False),
    4: TipoReceitaBrutaConfig(4, "Exportação indireta", True, False, Decimal("1.0"), True),
    5: TipoReceitaBrutaConfig(5, "Redução de 50% na receita tributada", True, False, Decimal("0.5"), False),
}


def calcular_item_simples_api(payload: SimplesItemCalculoRequest) -> SimplesItemCalculoResponse:
    """Resolve parâmetros vigentes no SQLite e executa o motor puro NT 2026.005 v1.00."""
    regime_cfg = _REGIMES_PADRAO[payload.regime]
    tipo_receita_cfg = _TIPOS_RECEITA_PADRAO.get(
        payload.tp_rbsn,
        TipoReceitaBrutaConfig(
            payload.tp_rbsn,
            f"Tipo de receita {payload.tp_rbsn}",
            True,
            False,
            Decimal("1.0"),
            False,
        ),
    )

    c_ativ_valido = payload.c_ativ_sn_valido
    if payload.c_ativ_sn is not None:
        atividades = listar_atividades_simples(payload.data_fato_gerador)
        c_ativ_valido = any(a["codigo"] == payload.c_ativ_sn for a in atividades)

    fator_gov = payload.fator_transicao_compra_gov
    if (
        payload.tp_ente_gov in {2, 3, 4}
        and (payload.p_ibs_sn is not None or payload.p_cbs_sn is not None)
        and fator_gov is None
    ):
        registro = obter_fator_compra_gov_simples(payload.data_fato_gerador)
        if registro is None:
            raise ValueError(
                f"Fator de transição compra gov não vigente para {payload.data_fato_gerador.isoformat()}."
            )
        fator_gov = Decimal(registro["fator"])

    resultado = calcular_item_simples(
        InsumoCalculoSimples(
            regime=regime_cfg,
            tipo_receita_bruta=tipo_receita_cfg,
            c_ativ_sn_valido=c_ativ_valido,
            base_calculo=payload.base_calculo,
            valor_imposto_seletivo=payload.valor_imposto_seletivo,
            p_ibs_sn=payload.p_ibs_sn,
            p_cbs_sn=payload.p_cbs_sn,
            tp_ente_gov=payload.tp_ente_gov,
            fator_transicao_compra_gov=fator_gov,
        )
    )

    tc = resultado.trib_calc
    trib_response = SimplesItemTributosResponse(
        v_rbsn_item=formatar_moeda(tc.v_rbsn_item),
        tp_rbsn=tc.tp_rbsn,
        tp_rbsn_descricao=tc.tp_rbsn_descricao,
        v_bc=formatar_moeda(tc.v_bc) if tc.v_bc is not None else None,
        p_ibs_sn=formatar_aliquota(tc.p_ibs_sn) if tc.p_ibs_sn is not None else None,
        v_ibs_sn=formatar_moeda(tc.v_ibs_sn) if tc.v_ibs_sn is not None else None,
        v_ibs_pend_susp=formatar_moeda(tc.v_ibs_pend_susp) if tc.v_ibs_pend_susp is not None else None,
        p_cbs_sn=formatar_aliquota(tc.p_cbs_sn) if tc.p_cbs_sn is not None else None,
        v_cbs_sn=formatar_moeda(tc.v_cbs_sn) if tc.v_cbs_sn is not None else None,
        v_cbs_pend_susp=formatar_moeda(tc.v_cbs_pend_susp) if tc.v_cbs_pend_susp is not None else None,
        valor_is=formatar_moeda(tc.valor_is) if tc.valor_is is not None else None,
        total_item=formatar_moeda(tc.total_item) if tc.total_item is not None else None,
    )

    return SimplesItemCalculoResponse(
        estado_item=resultado.estado_item,
        regime=regime_cfg.regime,
        destino_devido=regime_cfg.destino_devido,
        trib_calc=trib_response,
    )

