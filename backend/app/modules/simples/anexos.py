"""Derivação de disponibilidade e Fator R para atividades do Simples Nacional.

Port fiel de `DerivacaoAnexosSimples.java` (RFB).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

ANEXOS_VALIDOS: tuple[str, ...] = ("I", "II", "III", "IV", "V")


class ModoFatorR(str, Enum):
    """Comportamento do Fator R frente aos anexos configurados pelo usuário."""

    NAO_APLICAVEL = "NAO_APLICAVEL"
    OPCIONAL = "OPCIONAL"
    OBRIGATORIO = "OBRIGATORIO"
    INDISPONIVEL = "INDISPONIVEL"


@dataclass(frozen=True)
class DerivacaoAnexoResult:
    """Resultado da derivação de disponibilidade de uma atividade do Simples."""

    disponivel: bool
    anexos_faltantes: tuple[str, ...]
    modo_fator_r: ModoFatorR


def derivar_anexos_simples(
    anexo_sem_fator_r: Optional[str],
    anexo_com_fator_r: Optional[str],
    anexos_configurados: Optional[set[str]] = None,
) -> DerivacaoAnexoResult:
    """Deriva disponibilidade, anexos faltantes e modo Fator R de uma atividade."""
    if anexo_com_fator_r is not None and anexo_sem_fator_r is None:
        raise ValueError(
            f"Atividade inconsistente: anexo_com_fator_r ({anexo_com_fator_r}) "
            "preenchido sem anexo_sem_fator_r."
        )

    configurados = set(ANEXOS_VALIDOS) if anexos_configurados is None else anexos_configurados

    anexos_possiveis = [
        anexo for anexo in ANEXOS_VALIDOS if anexo in (anexo_sem_fator_r, anexo_com_fator_r)
    ]
    anexos_faltantes = tuple(anexo for anexo in anexos_possiveis if anexo not in configurados)
    disponivel = len(anexos_possiveis) == 0 or any(
        anexo in configurados for anexo in anexos_possiveis
    )

    if anexo_com_fator_r is None:
        modo_fator_r = ModoFatorR.NAO_APLICAVEL
    elif anexo_com_fator_r in configurados:
        modo_fator_r = (
            ModoFatorR.OPCIONAL if anexo_sem_fator_r in configurados else ModoFatorR.OBRIGATORIO
        )
    else:
        modo_fator_r = ModoFatorR.INDISPONIVEL

    return DerivacaoAnexoResult(
        disponivel=disponivel,
        anexos_faltantes=anexos_faltantes,
        modo_fator_r=modo_fator_r,
    )
