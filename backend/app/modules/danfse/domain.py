"""Domínio, enumerações e tabelas oficiais de apresentação do DANFSE.

Port de `internal/domain/enums/situacao.go`, `danfse_preparation.go` e
`internal/domain/presentation/danfse_format.go` do repositório oficial
`calculadora-rtc-gerador-danfse` (Receita Federal).
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
import re
from urllib.parse import quote

CONSULTA_PUBLICA_NFSE_URL = "https://www.nfse.gov.br/ConsultaPublica/"


class SituacaoNotaTipo(str, Enum):
    """Situação da NFS-e no padrão nacional."""

    VALIDA = "valida"
    SUBSTITUIDA = "substituida"
    CANCELADA = "cancelada"

    @classmethod
    def por_stc(cls, stc: int) -> tuple["SituacaoNotaTipo", bool]:
        """Converte código numérico cStat/STC para SituacaoNotaTipo."""
        mapping = {
            0: cls.VALIDA,
            1: cls.SUBSTITUIDA,
            2: cls.CANCELADA,
        }
        if stc in mapping:
            return mapping[stc], True
        return cls.VALIDA, False

    def marca_dagua(self) -> str:
        """Retorna texto de marca d'água para renderização do DANFSE."""
        if self == SituacaoNotaTipo.CANCELADA:
            return "CANCELADA"
        if self == SituacaoNotaTipo.SUBSTITUIDA:
            return "SUBSTITUÍDA"
        return ""

    def rotulo_situacao(self) -> str:
        """Retorna rótulo legível da situação da nota."""
        if self == SituacaoNotaTipo.CANCELADA:
            return "101 - NFS-e Cancelada"
        if self == SituacaoNotaTipo.SUBSTITUIDA:
            return "102 - NFS-e Substituída"
        return "100 - NFS-e Regular"


MAPA_CSTAT: dict[str, str] = {
    "100": "NFS-e Regular",
    "101": "NFS-e Cancelada",
    "102": "NFS-e Substituída",
    "103": "NFS-e de Decisão Judicial ou Administrativa",
    "104": "NFS-e Emitida em Contingência",
    "105": "NFS-e de Ajuste",
}

MAPA_OPCAO_SIMPLES_NACIONAL: dict[int, str] = {
    1: "1 - Não Optante",
    2: "2 - Optante - MEI",
    3: "3 - Optante - ME/EPP",
}

MAPA_TRIBUTACAO_ISSQN: dict[int, str] = {
    1: "Operação Tributável",
    2: "Imunidade",
    3: "Exportação de Serviço",
    4: "Não Incidência",
}


def formatar_cpf_cnpj(documento: str) -> str:
    """Formata CPF (11 dígitos) ou CNPJ (14 dígitos) no padrão brasileiro."""
    digits = re.sub(r"\D", "", documento)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    return documento


def formatar_moeda_br(valor: Decimal) -> str:
    """Formata Decimal no padrão monetário brasileiro (R$ 1.234,56)."""
    quant = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    sinal = "-" if quant < 0 else ""
    inteiro, frac = f"{abs(quant):.2f}".split(".")
    inteiro_fmt = f"{int(inteiro):,}".replace(",", ".")
    return f"{sinal}R$ {inteiro_fmt},{frac}"


def montar_url_qrcode_nfse(chave_acesso: str) -> str:
    """Monta URL oficial de consulta pública da NFS-e Nacional (NT 008)."""
    chave_limpa = chave_acesso.strip().replace("NFS", "")
    return f"{CONSULTA_PUBLICA_NFSE_URL}?tpc=1&chave={quote(chave_limpa, safe='')}"


def sanitizar_nome_arquivo_nfse(numero_nfse: str) -> str:
    """Sanitiza número da NFS-e para uso seguro em Content-Disposition."""
    limpo = re.sub(r"[^A-Za-z0-9_-]", "", numero_nfse.strip())
    return f"DANFSE_{limpo or 'documento'}.pdf"


@dataclass(frozen=True)
class DanfsePdfDocument:
    """Modelo normalizado e imutável para renderização do PDF DANFSe v2.0."""

    numero_nfse: str
    chave_acesso: str
    qrcode_url: str
    competencia: str
    data_hora_emissao: str
    situacao_texto: str
    marca_dagua: str
    sem_validade_juridica: bool
    prestador_nome: str
    prestador_documento: str
    prestador_municipio: str
    prestador_endereco: str
    tomador_nome: str
    tomador_documento: str
    tomador_municipio: str
    tomador_endereco: str
    local_prestacao: str
    codigo_tributacao: str
    discriminacao_servico: str
    cst_cclasstrib: str
    valor_servicos: Decimal
    valor_ibs: Decimal
    valor_cbs: Decimal
    valor_total_ibs_cbs: Decimal
    valor_liquido_nota: Decimal
    valor_liquido_com_rtc: Decimal
    informacoes_complementares: str
    intermediario_nome: str = ""
    intermediario_documento: str = ""
    intermediario_municipio: str = ""
    intermediario_endereco: str = ""
    chave_nfse_substituida: str = ""
    motivo_substituicao: str = ""
