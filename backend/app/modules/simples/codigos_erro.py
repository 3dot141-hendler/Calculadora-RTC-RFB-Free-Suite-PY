"""Catálogo de códigos de erro VSN-* e coletor por item do Simples Nacional.

Port fiel de `CodigoValidacaoSimples.java`, `ItemCollectorSimples.java` e
`SimplesNacionalErroService.java` da Receita Federal (NT 2026.005 v1.00).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .engine import EstadoItemSimples


class CodigoValidacaoSimples(Enum):
    """Catálogo oficial de códigos de validação do Simples Nacional (prefixo VSN-)."""

    # VSN-008 e VSN-009: APOSENTADOS pela RFB (nunca reutilizados).
    BASE_AUSENTE = (
        "VSN-001",
        "Base de cálculo do Simples ausente",
        "A base de cálculo do Simples Nacional é obrigatória e não foi informada.",
    )
    BASE_INVALIDA = (
        "VSN-002",
        "Base de cálculo do Simples inválida (negativa/não numérica)",
        "A base de cálculo informada não é um número decimal válido ou é negativa.",
    )
    IS_INVALIDO = (
        "VSN-003",
        "Valor do Imposto Seletivo inválido (negativo/não numérico)",
        "O valor do Imposto Seletivo (vIS) informado não é um número decimal válido ou é negativo.",
    )
    ALIQUOTA_CBS_AUSENTE = (
        "VSN-004",
        "Alíquota pCBSSN ausente",
        "A alíquota efetiva de CBS do Simples Nacional (pCBSSN) é exigida para o cálculo do item e não foi informada.",
    )
    ALIQUOTA_CBS_INVALIDA = (
        "VSN-005",
        "Alíquota pCBSSN inválida (negativa/não numérica)",
        "A alíquota efetiva de CBS do Simples Nacional (pCBSSN) informada não é um número decimal válido ou é negativa.",
    )
    ALIQUOTA_IBS_AUSENTE = (
        "VSN-006",
        "Alíquota pIBSSN ausente",
        "A alíquota efetiva de IBS do Simples Nacional (pIBSSN) é exigida para o cálculo do item e não foi informada.",
    )
    ALIQUOTA_IBS_INVALIDA = (
        "VSN-007",
        "Alíquota pIBSSN inválida (negativa/não numérica)",
        "A alíquota efetiva de IBS do Simples Nacional (pIBSSN) informada não é um número decimal válido ou é negativa.",
    )
    NUMERO_AUSENTE = (
        "VSN-010",
        "Número do item ausente",
        "O número (identificador) do item é obrigatório e não foi informado.",
    )
    ITENS_VAZIOS = (
        "VSN-011",
        "Lista de itens vazia",
        "A lista de itens da operação é obrigatória e não pode estar vazia.",
    )
    DATA_INVALIDA = (
        "VSN-012",
        "Data do fato gerador ausente/inválida",
        "A data do fato gerador é obrigatória e deve estar no formato de data (YYYY-MM-DD).",
    )
    DADO_GLOBAL_AUSENTE = (
        "VSN-013",
        "Dado global obrigatório ausente",
        "Um campo global obrigatório da operação (id ou versao) não foi informado.",
    )
    TPDOC_AUSENTE = (
        "VSN-014",
        "Tipo de documento fiscal (tpDoc) ausente",
        "O tipo de documento fiscal (tpDoc) é obrigatório e não foi informado.",
    )
    TPDOC_NAO_SUPORTADO = (
        "VSN-015",
        "Tipo de documento fiscal (tpDoc) não suportado",
        "O tipo de documento fiscal (tpDoc) informado não está habilitado para o cálculo do Simples Nacional na data do fato gerador.",
    )
    CRT_INVALIDO = (
        "VSN-016",
        "Código de Regime Tributário (CRT) ausente/inválido",
        "O Código de Regime Tributário (CRT) é obrigatório e deve ser 1, 2, 3 ou 4.",
    )
    TPREGIMEIBSCBS_INVALIDO = (
        "VSN-017",
        "Tipo de regime do IBS/CBS (tpRegimeIBSCBS) inválido",
        "O tipo de regime de apuração do IBS/CBS (tpRegimeIBSCBS), quando informado, deve ser 1 ou 2.",
    )
    TPREGIMEIBSCBS_INCOMPATIVEL = (
        "VSN-018",
        "tpRegimeIBSCBS incompatível com o CRT",
        "A combinação de CRT e tpRegimeIBSCBS informada é incoerente (regras C21a-10/20/30 da NT 2026.005): "
        "CRT 1, 2 ou 4 não admite tpRegimeIBSCBS=2; CRT 3 não admite tpRegimeIBSCBS=1; CRT 4 não admite tpRegimeIBSCBS algum.",
    )
    OPERACAO_FORA_ESCOPO = (
        "VSN-019",
        "Operação fora do escopo do cálculo assistido do Simples Nacional",
        "A operação não é calculada por este endpoint: optante pelo regime regular do IBS/CBS (tpRegimeIBSCBS=1), "
        "MEI (CRT=4) ou regime normal puro (CRT=3 sem tpRegimeIBSCBS=2).",
    )
    CCLASSTRIB_AUSENTE = (
        "VSN-020",
        "Código de Classificação Tributária (cClassTrib) ausente",
        "O código de classificação tributária do IBS/CBS (cClassTrib) é obrigatório e não foi informado.",
    )
    CCLASSTRIB_DESCONHECIDO = (
        "VSN-021",
        "cClassTrib desconhecido ou fora de vigência",
        "O cClassTrib informado não existe ou não está vigente na data do fato gerador: o Tipo de Receita Bruta (tpRBSN) não pôde ser determinado.",
    )
    CCLASSTRIB_INCOMPATIVEL_TPDOC = (
        "VSN-022",
        "cClassTrib incompatível com o tpDoc",
        "O cClassTrib informado não é admissível para o tipo de documento fiscal (tpDoc) da operação.",
    )
    CATIVSN_INCOMPATIVEL_CCLASSTRIB = (
        "VSN-023",
        "Código de Atividade do Simples Nacional incompatível com cClassTrib",
        "O código de atividade cAtivSN='90' (Operações não Tributáveis) é incompatível com cClassTrib cujo tpRBSN esteja entre 1 e 5 (regra UB14-90 da NT 2026.005).",
    )
    TPENTEGOV_INVALIDO = (
        "VSN-024",
        "Tipo de ente governamental (tpEnteGov) inválido",
        "O tipo de ente governamental (tpEnteGov), quando informado, deve ser 1 (União), 2 (Estado), 3 (Distrito Federal) ou 4 (Município).",
    )
    COMPRA_GOV_SEM_VIGENCIA = (
        "VSN-025",
        "Parametrização de compra governamental indisponível para a data",
        "A data do fato gerador está fora das vigências do fator de transição de compra governamental do Simples Nacional (NT 2026.005, seção 5.3.3).",
    )
    PARAMETRIZACAO_INDISPONIVEL = (
        "VSN-026",
        "Parametrização do cálculo do Simples Nacional indisponível para a data",
        "Não há linha vigente na data do fato gerador para a tabela de parametrização do Simples Nacional.",
    )
    CCLASSTRIB_NAO_IMPLEMENTADO = (
        "VSN-027",
        "cClassTrib sem tratamento implementado no cálculo do Simples Nacional",
        "A classificação tributária informada está vinculada a tratamento ainda não implementado; o item é reportado como NAO_IMPLEMENTADO.",
    )
    DESCONHECIDO = (
        "VSN-000",
        "Erro de validação não categorizado",
        "O tipo de validação aplicado não possui uma categoria específica.",
    )
    FALHA_TECNICA = (
        "VSN-999",
        "Falha técnica no cálculo do item",
        "Ocorreu uma falha técnica inesperada durante o cálculo do item.",
    )

    def __init__(self, code: str, titulo: str, descricao: str) -> None:
        self.code = code
        self.titulo = titulo
        self.descricao = descricao

    @classmethod
    def from_codigo(cls, codigo: Optional[str]) -> Optional["CodigoValidacaoSimples"]:
        """Resolve o enum pelo código textual (ex.: 'VSN-018')."""
        if not codigo:
            return None
        return _CODE_INDEX.get(codigo.strip().upper())


_CODE_INDEX: dict[str, CodigoValidacaoSimples] = {
    item.code: item for item in CodigoValidacaoSimples
}


@dataclass(frozen=True, slots=True)
class ErroDetalheData:
    """Estrutura de detalhe de erro conforme padrão RFC 7807 / RFB."""

    type: str
    title: str
    codigo: str
    pointer: str
    detail: str


def build_type_uri(base_url: str, codigo: str) -> str:
    """Monta a URI de documentação do catálogo de erros VSN-*."""
    base = base_url.rstrip("/")
    return f"{base}/api/v1/simples/observabilidade/erros?codigo={codigo}"


def build_erro_global(
    codigo: CodigoValidacaoSimples,
    campo: str,
    detail: str,
    base_url: str = "",
) -> ErroDetalheData:
    """Cria um detalhe de erro em nível de operação (#/<campo>)."""
    return ErroDetalheData(
        type=build_type_uri(base_url, codigo.code),
        title=codigo.titulo,
        codigo=codigo.code,
        pointer=f"#/{campo}",
        detail=detail,
    )


class ItemCollectorSimples:
    """Coletor de erros e estado por item do Simples Nacional."""

    def __init__(self, index: int, base_url: str = "") -> None:
        self._index = index
        self._base_url = base_url
        self._erros: list[ErroDetalheData] = []
        self._estado: EstadoItemSimples = EstadoItemSimples.CALCULADO

    def add_erro_validacao(
        self,
        codigo: CodigoValidacaoSimples,
        campo: Optional[str],
        detail: str,
    ) -> None:
        """Acumula erro de validação promovendo CALCULADO → INCONSISTENCIA_ENTRADA."""
        if self._estado == EstadoItemSimples.CALCULADO:
            self._estado = EstadoItemSimples.INCONSISTENCIA_ENTRADA
        self._erros.append(
            ErroDetalheData(
                type=build_type_uri(self._base_url, codigo.code),
                title=codigo.titulo,
                codigo=codigo.code,
                pointer=self._build_pointer(campo),
                detail=detail,
            )
        )

    def add_nao_implementado(
        self,
        codigo: CodigoValidacaoSimples,
        campo: Optional[str],
        detail: str,
    ) -> None:
        """Define incondicionalmente o item como NAO_IMPLEMENTADO (VSN-027)."""
        self._estado = EstadoItemSimples.NAO_IMPLEMENTADO
        self._erros.append(
            ErroDetalheData(
                type=build_type_uri(self._base_url, codigo.code),
                title=codigo.titulo,
                codigo=codigo.code,
                pointer=self._build_pointer(campo),
                detail=detail,
            )
        )

    def add_falha_tecnica(self, exc: Exception) -> None:
        """Registra falha técnica inesperada (VSN-999) e estado FALHA_TECNICA."""
        self._estado = EstadoItemSimples.FALHA_TECNICA
        codigo = CodigoValidacaoSimples.FALHA_TECNICA
        self._erros.append(
            ErroDetalheData(
                type=build_type_uri(self._base_url, codigo.code),
                title=codigo.titulo,
                codigo=codigo.code,
                pointer=f"#/itens/{self._index}",
                detail=str(exc) or codigo.descricao,
            )
        )

    def _build_pointer(self, campo: Optional[str]) -> str:
        if not campo:
            return f"#/itens/{self._index}"
        return f"#/itens/{self._index}/{campo}"

    @property
    def estado(self) -> EstadoItemSimples:
        return self._estado

    @property
    def erros(self) -> tuple[ErroDetalheData, ...]:
        return tuple(self._erros)

    @property
    def has_erros(self) -> bool:
        return bool(self._erros)


def listar_catalogo_erros_simples() -> list[dict[str, str]]:
    """Retorna o catálogo completo de códigos VSN-* ordenado pelo código."""
    return [
        {"codigo": item.code, "titulo": item.titulo, "descricao": item.descricao}
        for item in sorted(CodigoValidacaoSimples, key=lambda c: c.code)
    ]


def buscar_erro_simples_por_codigo(codigo: str) -> Optional[dict[str, str]]:
    """Consulta a descrição catalogada de um código VSN-* específico."""
    encontrado = CodigoValidacaoSimples.from_codigo(codigo)
    if encontrado is None:
        return None
    return {
        "codigo": encontrado.code,
        "titulo": encontrado.titulo,
        "descricao": encontrado.descricao,
    }
