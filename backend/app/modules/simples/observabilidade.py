"""Orquestrador multi-itens e observabilidade VSN-* do Simples Nacional.

Port fiel de `SimplesNacionalObservabilidadeService.java` e
`TotalSimplesDomain.java` (NT 2026.005 v1.00).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Optional

from app.core.rounding import formatar_aliquota, formatar_moeda, totalizar
from app.modules.tabelas_oficiais.repository import (
    listar_atividades_simples,
    listar_cst_classificacao,
    obter_fator_compra_gov_simples,
)
from .codigos_erro import (
    CodigoValidacaoSimples,
    ErroDetalheData,
    ItemCollectorSimples,
    build_erro_global,
)
from .engine import (
    InsumoCalculoSimples,
    RegimeApuracaoConfig,
    RegimeCalculoSimples,
    TributosSimplesResult,
    calcular_item_simples,
)
from .schemas_operacao import (
    ErroDetalheSimples,
    ImpostoSeletivoSimplesDomain,
    ItemSimplesInput,
    ObjetoSimplesDomain,
    ObservabilidadeSimplesDomain,
    OperacaoSimplesDomain,
    OperacaoSimplesInput,
    TotalSimplesDomain,
    TributosSimplesDomain,
)
from .validacao_escopo import (
    CATIV_NAO_TRIBUTAVEL,
    REGIMES_MATRIZ,
    TIPOS_RECEITA,
    TipoReceitaParametro,
    parse_int,
    resolver_tp_rbsn_por_cst,
    validar_aliquota_item,
    validar_campos_globais,
    validar_decimal_item,
)


class OperacaoSimplesInvalidaError(Exception):
    """Exceção lançada quando a operação falha nas validações globais (HTTP 422)."""

    def __init__(self, erros: list[ErroDetalheSimples]) -> None:
        super().__init__("Operação do Simples Nacional inválida.")
        self.erros = erros


@dataclass(frozen=True, slots=True)
class _ContextoOperacao:
    data: date
    tp_doc: int
    regime: RegimeApuracaoConfig
    tp_ente_gov: Optional[int]
    fator_compra_gov: Optional[Decimal]
    csts_por_codigo: dict[str, dict]
    atividades_por_codigo: dict[str, dict]


def _to_erro_schema(err: ErroDetalheData) -> ErroDetalheSimples:
    return ErroDetalheSimples(
        type=err.type,
        title=err.title,
        codigo=err.codigo,
        pointer=err.pointer,
        detail=err.detail,
    )


def _converter_tributos_domain(tc: TributosSimplesResult) -> TributosSimplesDomain:
    is_domain = (
        ImpostoSeletivoSimplesDomain(valor=formatar_moeda(tc.valor_is))
        if tc.valor_is is not None
        else None
    )
    return TributosSimplesDomain(
        vRBSNitem=formatar_moeda(tc.v_rbsn_item),
        tpRBSN=tc.tp_rbsn,
        tpRBSNDescricao=tc.tp_rbsn_descricao,
        vBC=formatar_moeda(tc.v_bc) if tc.v_bc is not None else None,
        pIBSSN=formatar_aliquota(tc.p_ibs_sn) if tc.p_ibs_sn is not None else None,
        vIBSSN=formatar_moeda(tc.v_ibs_sn) if tc.v_ibs_sn is not None else None,
        vIBSPendSusp=formatar_moeda(tc.v_ibs_pend_susp) if tc.v_ibs_pend_susp is not None else None,
        pCBSSN=formatar_aliquota(tc.p_cbs_sn) if tc.p_cbs_sn is not None else None,
        vCBSSN=formatar_moeda(tc.v_cbs_sn) if tc.v_cbs_sn is not None else None,
        vCBSPendSusp=formatar_moeda(tc.v_cbs_pend_susp) if tc.v_cbs_pend_susp is not None else None,
        IS=is_domain,
        totalItem=formatar_moeda(tc.total_item) if tc.total_item is not None else None,
    )


def _processar_item(
    item: ItemSimplesInput,
    index: int,
    ctx: _ContextoOperacao,
    base_url: str,
) -> tuple[ObjetoSimplesDomain, Optional[TributosSimplesResult]]:
    collector = ItemCollectorSimples(index, base_url)

    n_obj = item.numero
    if n_obj is None:
        collector.add_erro_validacao(
            CodigoValidacaoSimples.NUMERO_AUSENTE, "numero", "O número do item é obrigatório."
        )
    n_obj_efetivo = n_obj if n_obj is not None else index + 1

    base_calculo = validar_decimal_item(
        item.baseCalculo,
        collector,
        "baseCalculo",
        CodigoValidacaoSimples.BASE_AUSENTE,
        CodigoValidacaoSimples.BASE_INVALIDA,
    )
    valor_is = validar_decimal_item(
        item.valorImpostoSeletivo,
        collector,
        "valorImpostoSeletivo",
        CodigoValidacaoSimples.IS_INVALIDO,
        CodigoValidacaoSimples.IS_INVALIDO,
    )

    tipo_param: Optional[TipoReceitaParametro] = None
    if not item.cClassTrib or not item.cClassTrib.strip():
        collector.add_erro_validacao(
            CodigoValidacaoSimples.CCLASSTRIB_AUSENTE,
            "cClassTrib",
            "O código de classificação tributária (cClassTrib) é obrigatório.",
        )
    else:
        codigo_cst = item.cClassTrib.strip()
        cst_row = ctx.csts_por_codigo.get(codigo_cst)
        if cst_row is None:
            collector.add_erro_validacao(
                CodigoValidacaoSimples.CCLASSTRIB_DESCONHECIDO,
                "cClassTrib",
                f"cClassTrib '{codigo_cst}' desconhecido ou fora de vigência em {ctx.data.isoformat()}.",
            )
        else:
            tipo_param = TIPOS_RECEITA[resolver_tp_rbsn_por_cst(cst_row)]

    c_ativ_valido = False
    if item.cAtivSN and item.cAtivSN.strip():
        codigo_ativ = item.cAtivSN.strip()
        if codigo_ativ in ctx.atividades_por_codigo:
            c_ativ_valido = True
            if (
                codigo_ativ == CATIV_NAO_TRIBUTAVEL
                and tipo_param is not None
                and tipo_param.vedado_nao_tributavel
            ):
                collector.add_erro_validacao(
                    CodigoValidacaoSimples.CATIVSN_INCOMPATIVEL_CCLASSTRIB,
                    "cAtivSN",
                    f"O código de atividade '{codigo_ativ}' (Operações não Tributáveis) é incompatível com cClassTrib de tpRBSN={tipo_param.config.codigo}.",
                )

    aliquotas_exigidas = c_ativ_valido and tipo_param is not None and tipo_param.exige_aliquota
    p_ibs_exigida = aliquotas_exigidas and ctx.regime.gera_ibs

    p_cbs = validar_aliquota_item(
        item.pCBSSN,
        aliquotas_exigidas,
        collector,
        "pCBSSN",
        CodigoValidacaoSimples.ALIQUOTA_CBS_AUSENTE,
        CodigoValidacaoSimples.ALIQUOTA_CBS_INVALIDA,
    )
    p_ibs = validar_aliquota_item(
        item.pIBSSN,
        p_ibs_exigida,
        collector,
        "pIBSSN",
        CodigoValidacaoSimples.ALIQUOTA_IBS_AUSENTE,
        CodigoValidacaoSimples.ALIQUOTA_IBS_INVALIDA,
    )

    if collector.has_erros or base_calculo is None or valor_is is None or tipo_param is None:
        return (
            ObjetoSimplesDomain(
                nObj=n_obj_efetivo,
                estadoItem=collector.estado,
                tribCalc=None,
                erros=[_to_erro_schema(e) for e in collector.erros],
            ),
            None,
        )

    try:
        resultado = calcular_item_simples(
            InsumoCalculoSimples(
                regime=ctx.regime,
                tipo_receita_bruta=tipo_param.config,
                c_ativ_sn_valido=c_ativ_valido,
                base_calculo=base_calculo,
                valor_imposto_seletivo=valor_is,
                p_ibs_sn=p_ibs,
                p_cbs_sn=p_cbs,
                tp_ente_gov=ctx.tp_ente_gov,
                fator_transicao_compra_gov=ctx.fator_compra_gov,
            )
        )
        return (
            ObjetoSimplesDomain(
                nObj=n_obj_efetivo,
                estadoItem=resultado.estado_item,
                tribCalc=_converter_tributos_domain(resultado.trib_calc),
                erros=None,
            ),
            resultado.trib_calc,
        )
    except Exception as exc:
        collector.add_falha_tecnica(exc)
        return (
            ObjetoSimplesDomain(
                nObj=n_obj_efetivo,
                estadoItem=collector.estado,
                tribCalc=None,
                erros=[_to_erro_schema(e) for e in collector.erros],
            ),
            None,
        )


def _somar_presentes(
    resultados: list[TributosSimplesResult],
    extrator: Callable[[TributosSimplesResult], Optional[Decimal]],
) -> Optional[Decimal]:
    valores = [v for r in resultados if (v := extrator(r)) is not None]
    return totalizar(valores) if valores else None


def consolidar_totais_simples(resultados: list[TributosSimplesResult]) -> Optional[TotalSimplesDomain]:
    """Consolida totais a partir dos itens com tribCalc (CALCULADO e NAO_CALCULADO)."""
    if not resultados:
        return None

    v_rbsn_tot = _somar_presentes(resultados, lambda r: r.v_rbsn_item)
    v_bc = _somar_presentes(resultados, lambda r: r.v_bc)
    v_ibs_tot = _somar_presentes(resultados, lambda r: r.v_ibs_sn)
    v_ibs_pend = _somar_presentes(resultados, lambda r: r.v_ibs_pend_susp)
    v_cbs_tot = _somar_presentes(resultados, lambda r: r.v_cbs_sn)
    v_cbs_pend = _somar_presentes(resultados, lambda r: r.v_cbs_pend_susp)
    total_is = _somar_presentes(resultados, lambda r: r.valor_is)

    parcelas_devidas = [v for v in (v_ibs_tot, v_cbs_tot, total_is) if v is not None]
    total_tributos = totalizar(parcelas_devidas) if parcelas_devidas else None

    return TotalSimplesDomain(
        vRBSNtot=formatar_moeda(v_rbsn_tot) if v_rbsn_tot is not None else None,
        vBC=formatar_moeda(v_bc) if v_bc is not None else None,
        vIBSSNtot=formatar_moeda(v_ibs_tot) if v_ibs_tot is not None else None,
        vIBSSNtotPendSusp=formatar_moeda(v_ibs_pend) if v_ibs_pend is not None else None,
        vCBSSNtot=formatar_moeda(v_cbs_tot) if v_cbs_tot is not None else None,
        vCBSSNtotPendSusp=formatar_moeda(v_cbs_pend) if v_cbs_pend is not None else None,
        totalIs=formatar_moeda(total_is) if total_is is not None else None,
        totalTributos=formatar_moeda(total_tributos) if total_tributos is not None else None,
    )


def calcular_operacao_simples_observabilidade(
    operacao: OperacaoSimplesInput,
    base_url: str = "",
) -> ObservabilidadeSimplesDomain:
    """Valida escopo global, processa todos os itens com ItemCollectorSimples e totaliza."""
    data_fg, erros_globais = validar_campos_globais(operacao, base_url)
    if erros_globais:
        raise OperacaoSimplesInvalidaError([_to_erro_schema(e) for e in erros_globais])

    crt = int(operacao.CRT.strip())  # type: ignore[union-attr]
    regime_enum = (
        RegimeCalculoSimples.CRT_1
        if crt == 1
        else RegimeCalculoSimples.CRT_2
        if crt == 2
        else RegimeCalculoSimples.CRT_3_TPREGIME_2
    )
    regime_cfg = REGIMES_MATRIZ[regime_enum]

    tp_ente_gov = parse_int(operacao.tpEnteGov)
    fator_gov: Optional[Decimal] = None
    if tp_ente_gov in (2, 3, 4):
        registro = obter_fator_compra_gov_simples(data_fg)
        if registro is None:
            err = build_erro_global(
                CodigoValidacaoSimples.COMPRA_GOV_SEM_VIGENCIA,
                "tpEnteGov",
                f"Fator de transição de compra governamental não vigente para {data_fg.isoformat()}.",
                base_url,
            )
            raise OperacaoSimplesInvalidaError([_to_erro_schema(err)])
        fator_gov = Decimal(registro["fator"])

    csts = {row["c_class_trib"]: row for row in listar_cst_classificacao(data_fg)}
    atividades = {row["codigo"]: row for row in listar_atividades_simples(data_fg)}

    ctx = _ContextoOperacao(
        data=data_fg,
        tp_doc=int(operacao.tpDoc.strip()),  # type: ignore[union-attr]
        regime=regime_cfg,
        tp_ente_gov=tp_ente_gov,
        fator_compra_gov=fator_gov,
        csts_por_codigo=csts,
        atividades_por_codigo=atividades,
    )

    pares = [
        _processar_item(item, idx, ctx, base_url)
        for idx, item in enumerate(operacao.itens or [])
    ]
    pares.sort(key=lambda par: par[0].nObj)

    objetos = [par[0] for par in pares]
    resultados_brutos = [par[1] for par in pares if par[1] is not None]
    total = consolidar_totais_simples(resultados_brutos)

    oper_out = OperacaoSimplesDomain(
        data=data_fg.isoformat(),
        tpDoc=operacao.tpDoc.strip(),  # type: ignore[union-attr]
        CRT=operacao.CRT.strip(),  # type: ignore[union-attr]
        tpRegimeIBSCBS=(
            operacao.tpRegimeIBSCBS.strip()
            if operacao.tpRegimeIBSCBS and operacao.tpRegimeIBSCBS.strip()
            else None
        ),
        tpEnteGov=(
            operacao.tpEnteGov.strip()
            if operacao.tpEnteGov and operacao.tpEnteGov.strip()
            else None
        ),
    )
    return ObservabilidadeSimplesDomain(oper=oper_out, objetos=objetos, total=total)
