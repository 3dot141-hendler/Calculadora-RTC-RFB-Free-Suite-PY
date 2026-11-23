"""Validação global de escopo (CRT × tpRegimeIBSCBS × tpDoc) e parametrização SN.

Implementa as regras C21a-10/20/30 da NT 2026.005 v1.00 e helpers de validação
tolerante com emissão dos códigos VSN-*.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from .codigos_erro import (
    CodigoValidacaoSimples,
    ErroDetalheData,
    ItemCollectorSimples,
    build_erro_global,
)
from .engine import (
    DestinoValorSimples,
    RegimeApuracaoConfig,
    RegimeCalculoSimples,
    TipoReceitaBrutaConfig,
)
from .schemas_operacao import OperacaoSimplesInput

TPDOCS_SUPORTADOS: frozenset[int] = frozenset({55, 65})
TPDOCS_SEM_TRATAMENTO: frozenset[int] = frozenset({77, 94})
CATIV_NAO_TRIBUTAVEL = "90"

REGIMES_MATRIZ: dict[RegimeCalculoSimples, RegimeApuracaoConfig] = {
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


@dataclass(frozen=True, slots=True)
class TipoReceitaParametro:
    """Parametrização estendida de tpRBSN (efeito + exigências de validação)."""

    config: TipoReceitaBrutaConfig
    exige_aliquota: bool
    vedado_nao_tributavel: bool


TIPOS_RECEITA: dict[int, TipoReceitaParametro] = {
    0: TipoReceitaParametro(
        TipoReceitaBrutaConfig(0, "Não é receita bruta", False, False, Decimal("0.0"), False),
        exige_aliquota=False,
        vedado_nao_tributavel=False,
    ),
    1: TipoReceitaParametro(
        TipoReceitaBrutaConfig(1, "Receita bruta - interna", True, False, Decimal("1.0"), False),
        exige_aliquota=True,
        vedado_nao_tributavel=True,
    ),
    2: TipoReceitaParametro(
        TipoReceitaBrutaConfig(
            2, "Receita bruta - interna sem cálculo de IBS e CBS", True, False, Decimal("0.0"), False
        ),
        exige_aliquota=False,
        vedado_nao_tributavel=True,
    ),
    3: TipoReceitaParametro(
        TipoReceitaBrutaConfig(3, "Receita bruta - exportação direta", True, False, Decimal("0.0"), False),
        exige_aliquota=False,
        vedado_nao_tributavel=True,
    ),
    4: TipoReceitaParametro(
        TipoReceitaBrutaConfig(4, "Receita bruta - exportação indireta", True, False, Decimal("1.0"), True),
        exige_aliquota=True,
        vedado_nao_tributavel=True,
    ),
    5: TipoReceitaParametro(
        TipoReceitaBrutaConfig(
            5, "Receita bruta - mercado interno e exportação", True, False, Decimal("0.5"), False
        ),
        exige_aliquota=True,
        vedado_nao_tributavel=True,
    ),
    9: TipoReceitaParametro(
        TipoReceitaBrutaConfig(9, "Fornecimento incompatível com SN", True, False, Decimal("0.0"), False),
        exige_aliquota=False,
        vedado_nao_tributavel=False,
    ),
}


def parse_int(valor: Optional[str]) -> Optional[int]:
    if valor is None or not valor.strip():
        return None
    try:
        return int(valor.strip())
    except ValueError:
        return None


def _validar_data(valor: Optional[str], erros: list[ErroDetalheData], base_url: str) -> Optional[date]:
    if valor is None or not valor.strip():
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.DATA_INVALIDA,
                "data",
                "A data do fato gerador é obrigatória.",
                base_url,
            )
        )
        return None
    try:
        return date.fromisoformat(valor.strip())
    except ValueError:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.DATA_INVALIDA,
                "data",
                f"Data inválida, recebido: '{valor}' (esperado YYYY-MM-DD).",
                base_url,
            )
        )
        return None


def _validar_escopo(
    operacao: OperacaoSimplesInput,
    data_fg: Optional[date],
    erros: list[ErroDetalheData],
    base_url: str,
) -> None:
    """Validação cruzada CRT × tpRegimeIBSCBS × tpDoc (NT 2026.005, regras C21a-10/20/30)."""
    if not operacao.tpDoc or not operacao.tpDoc.strip():
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.TPDOC_AUSENTE,
                "tpDoc",
                "O tipo de documento fiscal (tpDoc) é obrigatório e não foi informado.",
                base_url,
            )
        )
    else:
        tp_doc = parse_int(operacao.tpDoc)
        if tp_doc is None:
            erros.append(
                build_erro_global(
                    CodigoValidacaoSimples.TPDOC_NAO_SUPORTADO,
                    "tpDoc",
                    f"Tipo de documento não suportado pelo cálculo do Simples Nacional, recebido: '{operacao.tpDoc}'.",
                    base_url,
                )
            )
        elif tp_doc in TPDOCS_SEM_TRATAMENTO:
            erros.append(
                build_erro_global(
                    CodigoValidacaoSimples.TPDOC_NAO_SUPORTADO,
                    "tpDoc",
                    f"Tipo de documento fiscal (tpDoc) de código {tp_doc} ainda não possui tratamento implementado.",
                    base_url,
                )
            )
        elif data_fg is not None and tp_doc not in TPDOCS_SUPORTADOS:
            erros.append(
                build_erro_global(
                    CodigoValidacaoSimples.TPDOC_NAO_SUPORTADO,
                    "tpDoc",
                    f"Tipo de documento não suportado pelo cálculo do Simples Nacional, recebido: '{operacao.tpDoc}' (suportados: 55, 65).",
                    base_url,
                )
            )

    crt = parse_int(operacao.CRT)
    if crt is None or crt < 1 or crt > 4:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.CRT_INVALIDO,
                "CRT",
                f"O CRT é obrigatório e deve ser 1, 2, 3 ou 4, recebido: '{operacao.CRT}'.",
                base_url,
            )
        )
        return

    tp_regime_informado = bool(operacao.tpRegimeIBSCBS and operacao.tpRegimeIBSCBS.strip())
    tp_regime: Optional[int] = None
    if tp_regime_informado:
        tp_regime = parse_int(operacao.tpRegimeIBSCBS)
        if tp_regime not in (1, 2):
            erros.append(
                build_erro_global(
                    CodigoValidacaoSimples.TPREGIMEIBSCBS_INVALIDO,
                    "tpRegimeIBSCBS",
                    f"tpRegimeIBSCBS inválido, recebido: '{operacao.tpRegimeIBSCBS}' (esperado 1 ou 2).",
                    base_url,
                )
            )
            return

    if crt == 4 and tp_regime_informado:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.TPREGIMEIBSCBS_INCOMPATIVEL,
                "tpRegimeIBSCBS",
                "CRT=4 (MEI) não admite tpRegimeIBSCBS algum (regra C21a-30 da NT 2026.005).",
                base_url,
            )
        )
    elif crt in (1, 2) and tp_regime == 2:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.TPREGIMEIBSCBS_INCOMPATIVEL,
                "tpRegimeIBSCBS",
                f"CRT={crt} não admite tpRegimeIBSCBS=2 (regra C21a-10 da NT 2026.005).",
                base_url,
            )
        )
    elif crt == 3 and tp_regime == 1:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.TPREGIMEIBSCBS_INCOMPATIVEL,
                "tpRegimeIBSCBS",
                "CRT=3 não admite tpRegimeIBSCBS=1 (regra C21a-20 da NT 2026.005).",
                base_url,
            )
        )

    if crt == 4:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.OPERACAO_FORA_ESCOPO,
                "CRT",
                "Operação fora do escopo do cálculo assistido do Simples Nacional: MEI (CRT=4).",
                base_url,
            )
        )
    if tp_regime == 1:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.OPERACAO_FORA_ESCOPO,
                "tpRegimeIBSCBS",
                "Operação fora do escopo: optante pelo regime regular do IBS/CBS (tpRegimeIBSCBS=1).",
                base_url,
            )
        )
    if crt == 3 and not tp_regime_informado:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.OPERACAO_FORA_ESCOPO,
                "CRT",
                "Operação fora do escopo: CRT=3 sem tpRegimeIBSCBS=2 (regime normal puro).",
                base_url,
            )
        )


def validar_campos_globais(operacao: OperacaoSimplesInput, base_url: str) -> tuple[date, list[ErroDetalheData]]:
    """Executa todas as validações globais da operação e acumula erros VSN-*."""
    erros: list[ErroDetalheData] = []

    if not operacao.id or not operacao.id.strip():
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.DADO_GLOBAL_AUSENTE,
                "id",
                "O identificador da operação (id) é obrigatório.",
                base_url,
            )
        )
    if not operacao.versao or not operacao.versao.strip():
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.DADO_GLOBAL_AUSENTE,
                "versao",
                "A versão do payload (versao) é obrigatória.",
                base_url,
            )
        )

    data_fg = _validar_data(operacao.data, erros, base_url)
    _validar_escopo(operacao, data_fg, erros, base_url)

    if operacao.tpEnteGov and operacao.tpEnteGov.strip():
        tp_gov = parse_int(operacao.tpEnteGov)
        if tp_gov is None or tp_gov < 1 or tp_gov > 4:
            erros.append(
                build_erro_global(
                    CodigoValidacaoSimples.TPENTEGOV_INVALIDO,
                    "tpEnteGov",
                    f"Tipo de ente governamental inválido, recebido: '{operacao.tpEnteGov}' (esperado 1, 2, 3 ou 4).",
                    base_url,
                )
            )

    if not operacao.itens:
        erros.append(
            build_erro_global(
                CodigoValidacaoSimples.ITENS_VAZIOS,
                "itens",
                "A lista de itens é obrigatória e não pode estar vazia.",
                base_url,
            )
        )

    return data_fg or date(2026, 1, 1), erros


def resolver_tp_rbsn_por_cst(cst_row: dict) -> int:
    """Deriva o tpRBSN (NT 2026.005) a partir do CST/cClassTrib vigente no SQLite."""
    cst = str(cst_row.get("cst", ""))
    descricao = str(cst_row.get("descricao", "")).lower()
    red_ibs = Decimal(str(cst_row.get("aliquota_reducao_ibs", "0.00")))

    if "exportação indireta" in descricao or cst == "550":
        return 4
    if "exportação" in descricao and cst in ("410", "400"):
        return 3
    if cst == "410" and ("não onerosa" in descricao or "não incidência" in descricao):
        return 0
    if cst in ("400", "410") or red_ibs >= Decimal("100.00"):
        return 2
    if red_ibs == Decimal("50.00"):
        return 5
    return 1


def validar_decimal_item(
    valor: Optional[str],
    collector: ItemCollectorSimples,
    campo: str,
    codigo_ausente: CodigoValidacaoSimples,
    codigo_invalido: CodigoValidacaoSimples,
) -> Optional[Decimal]:
    """Valida e converte valor decimal obrigatório não negativo de um item."""
    if valor is None or not valor.strip():
        collector.add_erro_validacao(codigo_ausente, campo, "O campo é obrigatório e não foi informado.")
        return None
    try:
        num = Decimal(valor.strip())
    except InvalidOperation:
        collector.add_erro_validacao(
            codigo_invalido, campo, f"O valor não é um número decimal válido, recebido: '{valor}'."
        )
        return None
    if num < 0:
        collector.add_erro_validacao(
            codigo_invalido, campo, f"O valor não pode ser negativo, recebido: '{valor}'."
        )
        return None
    return num


def validar_aliquota_item(
    valor: Optional[str],
    exigida: bool,
    collector: ItemCollectorSimples,
    campo: str,
    codigo_ausente: CodigoValidacaoSimples,
    codigo_invalido: CodigoValidacaoSimples,
) -> Optional[Decimal]:
    """Valida e converte alíquota condicional (exigida somente quando o cálculo a utiliza)."""
    if valor is None or not valor.strip():
        if exigida:
            collector.add_erro_validacao(
                codigo_ausente, campo, "A alíquota é exigida para o cálculo do item e não foi informada."
            )
        return None
    try:
        num = Decimal(valor.strip())
    except InvalidOperation:
        collector.add_erro_validacao(
            codigo_invalido, campo, f"O valor não é um número decimal válido, recebido: '{valor}'."
        )
        return None
    if num < 0:
        collector.add_erro_validacao(
            codigo_invalido, campo, f"O valor não pode ser negativo, recebido: '{valor}'."
        )
        return None
    return num
