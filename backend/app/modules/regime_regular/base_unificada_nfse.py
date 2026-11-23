"""Cálculo unificado de bases de cálculo NFS-e (IBS/CBS + Simples Nacional + Locação 99.03).

Port fiel de `BaseCalculoUnificadaNfseService.java`, `TipoAjusteNfse.java`,
`OpcaoSimplesNacional.java`, `RegimeApuracaoIbsCbsSN.java` e `SituacaoOperacaoNfse.java` da RFB.
Motor puro sem acesso a banco de dados (Decimal + ROUND_HALF_EVEN via `app.core.rounding`).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.core.rounding import dividir_por_cem, formatar_moeda, multiplicar, subtrair

ANO_EXTINCAO_PIS_COFINS = 2027
ANO_EXTINCAO_ISSQN = 2033

SituacaoNfse = Literal["comum", "salaoParceiro", "locacao9903"]

# codigo -> (repercute_ibs_cbs, repercute_sn, requer_descricao)
TIPOS_AJUSTE_NFSE: dict[str, tuple[bool, bool, bool]] = {
    "101": (True, False, False),   # Subcontratação
    "102": (True, False, False),   # Consórcio
    "103": (True, False, False),   # Intermediação
    "104": (True, False, False),   # Cessão de mão de obra
    "105": (True, False, False),   # Ressarcimento
    "199": (True, False, True),    # Outros (exige xTpAjusteBC)
    "9": (False, True, False),     # Profissional Parceiro (Salão Parceiro)
}


class DocumentoAjusteNfseInput(BaseModel):
    """Documento de ajuste/dedução da base de cálculo NFS-e."""

    tpAjusteBC: str = Field(..., min_length=1, max_length=10)
    xTpAjusteBC: Optional[str] = Field(default=None, max_length=255)
    vAjusteAplic: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class LocacaoNfseInput(BaseModel):
    """Dados de locação de imóveis (subitem 99.03) com copropriedade."""

    pCopropriedade: Decimal = Field(default=Decimal("100.00"), gt=Decimal("0.00"), le=Decimal("100.00"))
    vTotOper: Decimal = Field(..., ge=Decimal("0.00"))
    vDescIncondTot: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    somaAjustesLocImoveis: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class BaseCalculoUnificadaNfseRequest(BaseModel):
    """Payload oficial de Base de Cálculo Unificada NFS-e / Locação 99.03."""

    ano_fato_gerador: int = Field(default=2026, ge=2026, le=2035)
    opSimpNac: int = Field(
        default=1,
        ge=1,
        le=4,
        description="1=Não Optante, 2=MEI, 3=Optante ME/EPP, 4=Optante Pendente.",
    )
    regApIBSCBSSN: Optional[int] = Field(
        default=None,
        ge=1,
        le=3,
        description="1=IBS+CBS pelo SN, 2=CBS pelo SN + IBS regular, 3=Ambos regulares.",
    )
    situacao: SituacaoNfse = Field(default="comum")
    vServ: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vDescIncond: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vISSQN: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vPIS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vCOFINS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    locacao: Optional[LocacaoNfseInput] = None
    documentos: list[DocumentoAjusteNfseInput] = Field(default_factory=list)


class ErroBaseCalculoNfse(BaseModel):
    """Erro estruturado retornado na validação de negócio NFS-e."""

    codigo: str
    mensagem: str


class BaseCalculoUnificadaNfseResponse(BaseModel):
    """Resultado do cálculo unificado NFS-e (baseRG, baseSN, avisos e erros)."""

    baseRG: Optional[str] = None
    baseSN: Optional[str] = None
    vCalcAjusteBCIBSCBS: str = "0.00"
    avisos: list[str] = Field(default_factory=list)
    erros: list[ErroBaseCalculoNfse] = Field(default_factory=list)


def _validar_negocio(
    payload: BaseCalculoUnificadaNfseRequest,
    erros: list[ErroBaseCalculoNfse],
) -> None:
    op = payload.opSimpNac
    reg = payload.regApIBSCBSSN

    if op in (3, 4) and reg is None:
        erros.append(
            ErroBaseCalculoNfse(
                codigo="EXXX-REGAP-OBRIG",
                mensagem="Campo regApIBSCBSSN obrigatório para optante do Simples Nacional",
            )
        )
    if op == 1 and reg is not None:
        erros.append(
            ErroBaseCalculoNfse(
                codigo="EXXX-REGAP-PROIB",
                mensagem="Campo regApIBSCBSSN proibido para não optante do Simples Nacional",
            )
        )
    if op in (2, 3) and payload.situacao == "locacao9903":
        erros.append(
            ErroBaseCalculoNfse(
                codigo="EXXX-LOC-SN",
                mensagem="Locação de imóveis incompatível com optante do Simples Nacional",
            )
        )


def _varrer_documentos(
    documentos: list[DocumentoAjusteNfseInput],
    avisos: list[str],
    erros: list[ErroBaseCalculoNfse],
) -> list[DocumentoAjusteNfseInput]:
    validos: list[DocumentoAjusteNfseInput] = []
    for doc in documentos:
        meta = TIPOS_AJUSTE_NFSE.get(doc.tpAjusteBC)
        if meta is None:
            avisos.append(f"Tipo de ajuste '{doc.tpAjusteBC}' desconhecido: documento ignorado")
            continue
        _, _, requer_desc = meta
        if requer_desc and not (doc.xTpAjusteBC and doc.xTpAjusteBC.strip()):
            erros.append(
                ErroBaseCalculoNfse(
                    codigo="LEIAUTE-XTP",
                    mensagem="Campo xTpAjusteBC obrigatório para tipo de ajuste 199",
                )
            )
            continue
        validos.append(doc)
    return validos


def _calcular_base_rg(
    payload: BaseCalculoUnificadaNfseRequest,
    v_calc_ajuste_ibs_cbs: Decimal,
) -> Decimal:
    ano = payload.ano_fato_gerador
    deduz_pis = payload.vPIS if ano < ANO_EXTINCAO_PIS_COFINS else Decimal("0")
    deduz_cofins = payload.vCOFINS if ano < ANO_EXTINCAO_PIS_COFINS else Decimal("0")

    if payload.situacao == "locacao9903":
        assert payload.locacao is not None
        fator = dividir_por_cem(payload.locacao.pCopropriedade)
        v_serv_efet = multiplicar(fator, payload.locacao.vTotOper)
        v_desc_efet = multiplicar(fator, payload.locacao.vDescIncondTot)
        v_ajustes_loc = multiplicar(fator, payload.locacao.somaAjustesLocImoveis)
        res = subtrair(v_serv_efet, v_desc_efet)
        res = subtrair(res, v_ajustes_loc)
        res = subtrair(res, deduz_pis)
        return subtrair(res, deduz_cofins)

    deduz_issqn = payload.vISSQN if ano < ANO_EXTINCAO_ISSQN else Decimal("0")
    res = subtrair(payload.vServ, payload.vDescIncond)
    res = subtrair(res, v_calc_ajuste_ibs_cbs)
    res = subtrair(res, deduz_issqn)
    res = subtrair(res, deduz_pis)
    return subtrair(res, deduz_cofins)


def _calcular_base_sn(
    payload: BaseCalculoUnificadaNfseRequest,
    v_calc_ajuste_ibs_cbs: Decimal,
    soma_prof_parceiro: Decimal,
) -> Optional[Decimal]:
    if payload.opSimpNac in (1, 2) or payload.regApIBSCBSSN is None:
        return None

    if payload.situacao == "locacao9903":
        assert payload.locacao is not None
        fator = dividir_por_cem(payload.locacao.pCopropriedade)
        v_serv_efet = multiplicar(fator, payload.locacao.vTotOper)
        v_desc_efet = multiplicar(fator, payload.locacao.vDescIncondTot)
        base = subtrair(v_serv_efet, v_desc_efet)
    else:
        base = subtrair(payload.vServ, payload.vDescIncond)

    base = subtrair(base, v_calc_ajuste_ibs_cbs)

    # Profissional parceiro: deduz da baseSN se salaoParceiro e regAp != AMBOS_REGULARES (3)
    if payload.situacao == "salaoParceiro" and payload.regApIBSCBSSN != 3:
        base = subtrair(base, soma_prof_parceiro)
    return base


def calcular_base_unificada_nfse(
    payload: BaseCalculoUnificadaNfseRequest,
) -> BaseCalculoUnificadaNfseResponse:
    """Executa o algoritmo completo de Base de Cálculo Unificada NFS-e / Locação (RFB)."""
    if payload.situacao == "locacao9903" and payload.locacao is None:
        raise ValueError("Campo locacao obrigatório quando situacao é locacao9903.")

    avisos: list[str] = []
    erros: list[ErroBaseCalculoNfse] = []

    _validar_negocio(payload, erros)
    docs_validos = _varrer_documentos(payload.documentos, avisos, erros)

    # MEI (2) — retorno antecipado fiel à RFB
    if payload.opSimpNac == 2:
        avisos.append("E1302: Operação MEI: bases de cálculo não aplicáveis")
        if payload.documentos:
            erros.append(
                ErroBaseCalculoNfse(
                    codigo="E0436",
                    mensagem="Documentos de ajuste não são permitidos para MEI",
                )
            )
        return BaseCalculoUnificadaNfseResponse(
            baseRG=None, baseSN=None, vCalcAjusteBCIBSCBS="0.00", avisos=avisos, erros=erros
        )

    is_locacao = payload.situacao == "locacao9903"
    v_calc_ajuste_ibs_cbs = Decimal("0")
    soma_prof_parceiro = Decimal("0")
    if not is_locacao:
        for doc in docs_validos:
            rep_ibscbs, rep_sn, _ = TIPOS_AJUSTE_NFSE[doc.tpAjusteBC]
            if rep_ibscbs:
                v_calc_ajuste_ibs_cbs += doc.vAjusteAplic
            if rep_sn:
                soma_prof_parceiro += doc.vAjusteAplic

    if v_calc_ajuste_ibs_cbs > Decimal("0") and v_calc_ajuste_ibs_cbs >= payload.vServ:
        erros.append(
            ErroBaseCalculoNfse(
                codigo="E1534",
                mensagem=(
                    f"Soma dos ajustes ({formatar_moeda(v_calc_ajuste_ibs_cbs)}) "
                    f"excede ou iguala o valor do serviço ({formatar_moeda(payload.vServ)})"
                ),
            )
        )

    if is_locacao and payload.documentos:
        avisos.append("Documentos de ajuste ignorados em contexto de locação de imóveis")
    if not is_locacao and payload.locacao is not None:
        avisos.append("Grupo locacao ignorado fora de contexto de locação de imóveis")

    base_rg = _calcular_base_rg(payload, v_calc_ajuste_ibs_cbs)
    base_sn = _calcular_base_sn(payload, v_calc_ajuste_ibs_cbs, soma_prof_parceiro)

    if payload.opSimpNac == 4:
        avisos.append("Optante pendente: cálculo realizado com ressalva")

    base_rg_str = formatar_moeda(base_rg)
    base_sn_str = formatar_moeda(base_sn) if base_sn is not None else None

    if Decimal(base_rg_str) < Decimal("0"):
        erros.append(
            ErroBaseCalculoNfse(
                codigo="BASE-NEGATIVA",
                mensagem=f"Base de cálculo RG negativa: {base_rg_str}",
            )
        )
    if base_sn_str is not None and Decimal(base_sn_str) < Decimal("0"):
        erros.append(
            ErroBaseCalculoNfse(
                codigo="BASE-NEGATIVA",
                mensagem=f"Base de cálculo SN negativa: {base_sn_str}",
            )
        )

    return BaseCalculoUnificadaNfseResponse(
        baseRG=base_rg_str,
        baseSN=base_sn_str,
        vCalcAjusteBCIBSCBS=formatar_moeda(v_calc_ajuste_ibs_cbs),
        avisos=avisos,
        erros=erros,
    )
