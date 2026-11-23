"""Parser seguro de XML da NFS-e padrão nacional (DANFSE).

Port baseado em `models.go` e `ADR006` (`calculadora-rtc-gerador-danfse`),
com bloqueio explícito de DOCTYPE/entidades externas (XXE).
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import xml.etree.ElementTree as ET
from pydantic import BaseModel

from app.modules.tabelas_oficiais.repository import buscar_localidades_ibge
from .domain import (
    DanfsePdfDocument,
    MAPA_CSTAT,
    SituacaoNotaTipo,
    formatar_cpf_cnpj,
    montar_url_qrcode_nfse,
)


class XmlDanfseInvalidoError(ValueError):
    """Erro levantado quando o XML da NFS-e é inválido ou inseguro."""


class DanfseXmlSummary(BaseModel):
    """Resumo extraído do XML oficial da NFS-e padrão nacional."""

    numero_nfse: str
    chave_id: str
    cstat: str
    cstat_descricao: str
    situacao: SituacaoNotaTipo
    marca_dagua: str
    prestador_nome: str
    prestador_documento: str
    tomador_nome: str
    tomador_documento: str
    valor_servicos: str
    discriminacao_servico: str
    municipio_emissao: str = "Não informado"
    valor_ibs: str = "0.00"
    valor_cbs: str = "0.00"
    cst_cclasstrib: str = "-"
    codigo_tributacao: str = "-"
    competencia: str = "-"
    data_emissao: str = "-"
    prestador_endereco: str = "-"
    tomador_endereco: str = "-"
    tomador_municipio: str = "-"
    informacoes_complementares: str = ""
    ambiente_homologacao: bool = False
    qrcode_url: str = ""


def _find_text(parent: ET.Element | None, path: str, default: str = "") -> str:
    if parent is None:
        return default
    # Ignora namespaces XML usando wildcard {*} quando necessário
    parts = [f"{{*}}{p}" for p in path.split("/")]
    node = parent.find("/".join(parts))
    if node is not None and node.text:
        return node.text.strip()
    return default


def _parse_decimal(raw: str) -> Decimal:
    try:
        return Decimal(raw or "0.00").quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        return Decimal("0.00")


def _resolver_municipio_ibge(codigo_raw: str, fallback: str = "-") -> str:
    if codigo_raw and codigo_raw.isdigit():
        locs = buscar_localidades_ibge(codigo=int(codigo_raw), limit=1)
        if locs:
            return f"{locs[0]['nome']} - {locs[0]['uf_sigla']}"
    return fallback


def _montar_endereco(parent: ET.Element | None, base_path: str) -> str:
    partes = [
        _find_text(parent, f"{base_path}/xLgr"),
        _find_text(parent, f"{base_path}/nro"),
        _find_text(parent, f"{base_path}/xBairro"),
        _find_text(parent, f"{base_path}/CEP"),
    ]
    filtradas = [p for p in partes if p]
    return ", ".join(filtradas) if filtradas else "-"


def parse_nfse_xml(xml_content: str) -> DanfseXmlSummary:
    """Valida e extrai os campos principais do XML da NFS-e padrão nacional."""
    if not xml_content or not xml_content.strip():
        raise XmlDanfseInvalidoError("Conteúdo XML vazio.")

    upper = xml_content.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        raise XmlDanfseInvalidoError("Declarações DOCTYPE/ENTITY não são permitidas por segurança.")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise XmlDanfseInvalidoError(f"XML malformado: {exc}") from exc

    local_name = root.tag.split("}")[-1]
    if local_name != "NFSe":
        raise XmlDanfseInvalidoError(f"Elemento raiz esperado 'NFSe', recebido '{local_name}'.")

    inf = root.find("{*}infNFSe")
    if inf is None:
        raise XmlDanfseInvalidoError("Elemento obrigatório 'infNFSe' ausente.")

    numero_nfse = _find_text(inf, "nNFSe", "0")
    chave_id = inf.attrib.get("Id", "")
    cstat = _find_text(inf, "cStat", "100")
    situacao_attr = inf.attrib.get("situacao", "").lower()

    if situacao_attr == "cancelada" or cstat == "101":
        situacao = SituacaoNotaTipo.CANCELADA
    elif situacao_attr == "substituida" or cstat == "102":
        situacao = SituacaoNotaTipo.SUBSTITUIDA
    else:
        situacao = SituacaoNotaTipo.VALIDA

    prest_doc = _find_text(inf, "emit/CNPJ") or _find_text(inf, "emit/CPF")
    toma_doc = _find_text(inf, "DPS/infDPS/toma/CNPJ") or _find_text(inf, "DPS/infDPS/toma/CPF")
    valor_dec = _parse_decimal(
        _find_text(inf, "DPS/infDPS/valores/vServPrest/vServ") or _find_text(inf, "valores/vLiq", "0.00")
    )

    valor_ibs = _parse_decimal(
        _find_text(inf, "IBSCBS/totCIBS/gIBS/vIBSTot")
        or _find_text(inf, "IBSCBS/valores/vIBS")
        or _find_text(inf, "DPS/infDPS/IBSCBS/valores/vIBS")
    )
    valor_cbs = _parse_decimal(
        _find_text(inf, "IBSCBS/totCIBS/gCBS/vCBS")
        or _find_text(inf, "IBSCBS/valores/vCBS")
        or _find_text(inf, "DPS/infDPS/IBSCBS/valores/vCBS")
    )
    cst = _find_text(inf, "DPS/infDPS/IBSCBS/gTribRegular/CST") or _find_text(inf, "IBSCBS/CST")
    c_class = _find_text(inf, "DPS/infDPS/IBSCBS/gTribRegular/cClassTrib") or _find_text(inf, "IBSCBS/cClassTrib")
    cst_cclasstrib = f"{cst or '-'} / {c_class or '-'}" if (cst or c_class) else "-"

    codigo_ibge_raw = _find_text(inf, "DPS/infDPS/cLocEmi") or _find_text(inf, "cLocIncid")
    municipio_emissao = _resolver_municipio_ibge(
        codigo_ibge_raw, fallback=_find_text(inf, "xLocEmi", "Não informado")
    )
    tomador_mun = _resolver_municipio_ibge(
        _find_text(inf, "DPS/infDPS/toma/end/endNac/cMun"), fallback="-"
    )

    tp_amb = _find_text(inf, "DPS/infDPS/tpAmb") or _find_text(inf, "tpAmb")
    cod_trib = _find_text(inf, "DPS/infDPS/serv/cServ/cTribNac", "-")
    c_nbs = _find_text(inf, "DPS/infDPS/serv/cServ/cNBS")
    if c_nbs:
        cod_trib = f"{cod_trib} | NBS {c_nbs}"

    qrcode_url = montar_url_qrcode_nfse(chave_id or numero_nfse)

    return DanfseXmlSummary(
        numero_nfse=numero_nfse,
        chave_id=chave_id,
        cstat=cstat,
        cstat_descricao=MAPA_CSTAT.get(cstat, "Situação não mapeada"),
        situacao=situacao,
        marca_dagua=situacao.marca_dagua(),
        prestador_nome=_find_text(inf, "emit/xNome", "Não informado"),
        prestador_documento=formatar_cpf_cnpj(prest_doc) if prest_doc else "Não informado",
        tomador_nome=_find_text(inf, "DPS/infDPS/toma/xNome", "Não informado"),
        tomador_documento=formatar_cpf_cnpj(toma_doc) if toma_doc else "Não informado",
        valor_servicos=f"{valor_dec:f}",
        discriminacao_servico=_find_text(inf, "DPS/infDPS/serv/cServ/xDescServ", "Não informado"),
        municipio_emissao=municipio_emissao,
        valor_ibs=f"{valor_ibs:f}",
        valor_cbs=f"{valor_cbs:f}",
        cst_cclasstrib=cst_cclasstrib,
        codigo_tributacao=cod_trib,
        competencia=_find_text(inf, "DPS/infDPS/dCompet", datetime.now().strftime("%Y-%m-%d")),
        data_emissao=_find_text(inf, "dhProc") or _find_text(inf, "DPS/infDPS/dhEmi", datetime.now().strftime("%d/%m/%Y %H:%M")),
        prestador_endereco=_montar_endereco(inf, "emit/enderNac"),
        tomador_endereco=_montar_endereco(inf, "DPS/infDPS/toma/end"),
        tomador_municipio=tomador_mun,
        informacoes_complementares=_find_text(inf, "DPS/infDPS/serv/infoCompl/xInfComp", ""),
        ambiente_homologacao=(tp_amb == "2"),
        qrcode_url=qrcode_url,
    )


def xml_summary_to_pdf_document(summary: DanfseXmlSummary) -> DanfsePdfDocument:
    """Converte `DanfseXmlSummary` no modelo normalizado para o renderizador PDF."""
    valor_serv = _parse_decimal(summary.valor_servicos)
    valor_ibs = _parse_decimal(summary.valor_ibs)
    valor_cbs = _parse_decimal(summary.valor_cbs)
    total_rtc = (valor_ibs + valor_cbs).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    liquido_rtc = (valor_serv + total_rtc).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    obs_base = summary.informacoes_complementares.strip()
    obs_auth = (
        "A autenticidade desta NFS-e pode ser verificada pela leitura do código QR "
        "ou pela consulta da chave de acesso no portal nacional da NFS-e."
    )
    info_compl = f"{obs_base} | {obs_auth}" if obs_base else obs_auth

    return DanfsePdfDocument(
        numero_nfse=summary.numero_nfse,
        chave_acesso=summary.chave_id or summary.numero_nfse,
        qrcode_url=summary.qrcode_url or montar_url_qrcode_nfse(summary.chave_id or summary.numero_nfse),
        competencia=summary.competencia,
        data_hora_emissao=summary.data_emissao,
        situacao_texto=f"{summary.cstat} - {summary.cstat_descricao}",
        marca_dagua=summary.marca_dagua,
        sem_validade_juridica=summary.ambiente_homologacao,
        prestador_nome=summary.prestador_nome,
        prestador_documento=summary.prestador_documento,
        prestador_municipio=summary.municipio_emissao,
        prestador_endereco=summary.prestador_endereco,
        tomador_nome=summary.tomador_nome,
        tomador_documento=summary.tomador_documento,
        tomador_municipio=summary.tomador_municipio,
        tomador_endereco=summary.tomador_endereco,
        local_prestacao=summary.municipio_emissao,
        codigo_tributacao=summary.codigo_tributacao,
        discriminacao_servico=summary.discriminacao_servico,
        cst_cclasstrib=summary.cst_cclasstrib,
        valor_servicos=valor_serv,
        valor_ibs=valor_ibs,
        valor_cbs=valor_cbs,
        valor_total_ibs_cbs=total_rtc,
        valor_liquido_nota=valor_serv,
        valor_liquido_com_rtc=liquido_rtc,
        informacoes_complementares=info_compl,
    )
