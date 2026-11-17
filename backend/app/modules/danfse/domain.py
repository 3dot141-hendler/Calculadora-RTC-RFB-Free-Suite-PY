"""Domínio, enumerações e tabelas oficiais de apresentação do DANFSE.

Port de `internal/domain/enums/situacao.go` e `internal/domain/presentation/danfse_format.go`
do repositório oficial `calculadora-rtc-gerador-danfse` (Receita Federal).
"""

from enum import Enum
import re


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
