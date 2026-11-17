"""Parser seguro de XML da NFS-e padrão nacional (DANFSE).

Port baseado em `models.go` e `ADR006` (`calculadora-rtc-gerador-danfse`),
com bloqueio explícito de DOCTYPE/entidades externas (XXE).
"""

from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET
from pydantic import BaseModel

from app.modules.tabelas_oficiais.repository import buscar_localidades_ibge
from .domain import MAPA_CSTAT, SituacaoNotaTipo, formatar_cpf_cnpj


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


def _find_text(parent: ET.Element | None, path: str, default: str = "") -> str:
    if parent is None:
        return default
    # Ignora namespaces XML usando wildcard {*} quando necessário
    parts = [f"{{*}}{p}" for p in path.split("/")]
    node = parent.find("/".join(parts))
    if node is not None and node.text:
        return node.text.strip()
    return default


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
    valor_raw = _find_text(inf, "DPS/infDPS/valores/vServPrest/vServ") or _find_text(
        inf, "valores/vLiq", "0.00"
    )
    try:
        valor_dec = Decimal(valor_raw).quantize(Decimal("0.01"))
    except InvalidOperation:
        valor_dec = Decimal("0.00")

    codigo_ibge_raw = _find_text(inf, "DPS/infDPS/cLocEmi") or _find_text(inf, "cLocIncid")
    municipio_emissao = _find_text(inf, "xLocEmi", "Não informado")
    if codigo_ibge_raw.isdigit():
        locs = buscar_localidades_ibge(codigo=int(codigo_ibge_raw), limit=1)
        if locs:
            municipio_emissao = f"{locs[0]['nome']} - {locs[0]['uf_sigla']}"

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
    )

