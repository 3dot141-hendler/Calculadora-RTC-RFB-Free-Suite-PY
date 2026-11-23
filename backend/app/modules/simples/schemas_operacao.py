"""Schemas Pydantic da operação multi-itens e observabilidade do Simples Nacional.

Espelha os contratos oficiais da Receita Federal (`OperacaoSimplesInput`,
`ItemSimplesInput`, `ObjetoSimplesDomain`, `TotalSimplesDomain`,
`ObservabilidadeSimplesDomain` — NT 2026.005 v1.00).
"""

from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .engine import EstadoItemSimples


def _coerce_optional_str(value: Any) -> Optional[str]:
    """Converte entradas numéricas ou textuais para string para validação VSN-* tolerante."""
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    return str(value)


class ItemSimplesInput(BaseModel):
    """Item de entrada de uma operação em lote do Simples Nacional (NT 2026.005)."""

    model_config = ConfigDict(populate_by_name=True)

    numero: Optional[int] = Field(default=None, description="Número sequencial do item na operação.")
    cAtivSN: Optional[str] = Field(
        default=None,
        description="Código oficial de Atividade do Simples Nacional (2 dígitos; ex.: '01', '04').",
    )
    cClassTrib: Optional[str] = Field(
        default=None,
        description="Código de Classificação Tributária do IBS/CBS (6 dígitos; resolve o tpRBSN).",
    )
    baseCalculo: Optional[Union[str, int, float, Decimal]] = Field(
        default=None,
        description="Base de cálculo do item sem Imposto Seletivo (ex.: '1000.00').",
    )
    valorImpostoSeletivo: Optional[Union[str, int, float, Decimal]] = Field(
        default="0.00",
        description="Valor do Imposto Seletivo já calculado (vIS; padrão '0.00').",
    )
    pIBSSN: Optional[Union[str, int, float, Decimal]] = Field(
        default=None,
        description="Alíquota efetiva do Simples Nacional para o IBS (%).",
    )
    pCBSSN: Optional[Union[str, int, float, Decimal]] = Field(
        default=None,
        description="Alíquota efetiva do Simples Nacional para a CBS (%).",
    )

    @field_validator(
        "cAtivSN",
        "cClassTrib",
        "baseCalculo",
        "valorImpostoSeletivo",
        "pIBSSN",
        "pCBSSN",
        mode="before",
    )
    @classmethod
    def _normalizar_para_texto(cls, value: Any) -> Optional[str]:
        return _coerce_optional_str(value)


class OperacaoSimplesInput(BaseModel):
    """Entrada da operação multi-itens do Simples Nacional com observabilidade VSN-*."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(default=None, description="Identificador único da operação.")
    versao: Optional[str] = Field(default="2.0.0", description="Versão do contrato da operação.")
    data: Optional[str] = Field(
        default=None,
        description="Data do fato gerador da operação no formato YYYY-MM-DD.",
    )
    tpDoc: Optional[Union[str, int]] = Field(
        default=None,
        description="Tipo de documento fiscal eletrônico (ex.: '55' NF-e, '65' NFC-e).",
    )
    CRT: Optional[Union[str, int]] = Field(
        default=None,
        description="Código de Regime Tributário do emitente (1, 2, 3 ou 4).",
    )
    tpRegimeIBSCBS: Optional[Union[str, int]] = Field(
        default=None,
        description="Regime de apuração do IBS/CBS (1=Regular, 2=Apuração por fora com CRT=3).",
    )
    tpEnteGov: Optional[Union[str, int]] = Field(
        default=None,
        description="Tipo de ente governamental adquirente (1=União, 2=Estado, 3=DF, 4=Município).",
    )
    itens: Optional[list[ItemSimplesInput]] = Field(
        default=None,
        description="Lista de itens da operação.",
    )

    @field_validator(
        "id",
        "versao",
        "data",
        "tpDoc",
        "CRT",
        "tpRegimeIBSCBS",
        "tpEnteGov",
        mode="before",
    )
    @classmethod
    def _normalizar_campos_globais(cls, value: Any) -> Optional[str]:
        return _coerce_optional_str(value)


class ErroDetalheSimples(BaseModel):
    """Detalhe de erro de validação/observabilidade com código VSN-* e JSON Pointer."""

    type: str
    title: str
    codigo: str
    pointer: str
    detail: str


class ErroDescricaoSimples(BaseModel):
    """Entrada do catálogo oficial de erros do Simples Nacional (VSN-*)."""

    codigo: str
    titulo: str
    descricao: str


class OperacaoSimplesDomain(BaseModel):
    """Repasse dos metadados globais da operação na resposta."""

    data: str
    tpDoc: str
    CRT: str
    tpRegimeIBSCBS: Optional[str] = None
    tpEnteGov: Optional[str] = None


class ImpostoSeletivoSimplesDomain(BaseModel):
    """Repasse do Imposto Seletivo (vIS) no item do Simples Nacional."""

    valor: str


class TributosSimplesDomain(BaseModel):
    """Tributos calculados do item no formato oficial NT 2026.005."""

    vRBSNitem: str
    tpRBSN: int
    tpRBSNDescricao: str
    vBC: Optional[str] = None
    pIBSSN: Optional[str] = None
    vIBSSN: Optional[str] = None
    vIBSPendSusp: Optional[str] = None
    pCBSSN: Optional[str] = None
    vCBSSN: Optional[str] = None
    vCBSPendSusp: Optional[str] = None
    IS: Optional[ImpostoSeletivoSimplesDomain] = None
    totalItem: Optional[str] = None


class ObjetoSimplesDomain(BaseModel):
    """Resultado individual de um item na operação multi-itens."""

    nObj: int
    estadoItem: EstadoItemSimples
    tribCalc: Optional[TributosSimplesDomain] = None
    erros: Optional[list[ErroDetalheSimples]] = None


class TotalSimplesDomain(BaseModel):
    """Totais consolidados da operação (espelhando TotalSimplesDomain.java)."""

    vRBSNtot: Optional[str] = None
    vBC: Optional[str] = None
    vIBSSNtot: Optional[str] = None
    vIBSSNtotPendSusp: Optional[str] = None
    vCBSSNtot: Optional[str] = None
    vCBSSNtotPendSusp: Optional[str] = None
    totalIs: Optional[str] = None
    totalTributos: Optional[str] = None


class ObservabilidadeSimplesDomain(BaseModel):
    """Resposta consolidada da operação em lote com observabilidade do Simples Nacional."""

    oper: OperacaoSimplesDomain
    objetos: list[ObjetoSimplesDomain]
    total: Optional[TotalSimplesDomain] = None
