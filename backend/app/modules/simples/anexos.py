"""Derivação de disponibilidade e Fator R para atividades do Simples Nacional.

Port fiel de `DerivacaoAnexosSimples.java` (RFB) e regra legal do Fator R
(LC 123/2006, art. 18, §§ 5º-J a 5º-M: Folha 12m / RBT12 >= 28% → Anexo III).
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
from typing import Optional

ANEXOS_VALIDOS: tuple[str, ...] = ("I", "II", "III", "IV", "V")
FATOR_R_LIMIAR_FRACAO = Decimal("0.28")
FATOR_R_LIMIAR_PERCENTUAL = Decimal("28.00")


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


@dataclass(frozen=True, slots=True)
class AvaliacaoFatorR:
    """Resultado puro da avaliação do Fator R (Anexo III vs. Anexo V)."""

    folha_salarios_12m: Decimal
    receita_bruta_12m: Decimal
    percentual_fator_r: Decimal
    atingiu_minimo_28_pct: bool
    anexo_definido: str
    folha_minima_anexo_iii: Decimal
    folha_faltante_anexo_iii: Decimal


def avaliar_fator_r(
    folha_salarios_12m: Decimal,
    receita_bruta_12m: Decimal,
) -> AvaliacaoFatorR:
    """Avalia o Fator R conforme LC 123/2006 (>= 28% enquadra Anexo III; < 28% Anexo V)."""
    if folha_salarios_12m < Decimal("0") or receita_bruta_12m < Decimal("0"):
        raise ValueError("Folha de salários e receita bruta 12m não podem ser negativas.")

    folha_q = folha_salarios_12m.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    rbt12_q = receita_bruta_12m.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    if rbt12_q == Decimal("0.00"):
        atingiu = folha_q > Decimal("0.00")
        percentual = Decimal("100.00") if atingiu else Decimal("0.00")
        folha_minima = Decimal("0.00")
        folha_faltante = Decimal("0.00")
    else:
        atingiu = (folha_q * Decimal("100")) >= (rbt12_q * Decimal("28"))
        percentual = ((folha_q / rbt12_q) * Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        folha_minima = (rbt12_q * FATOR_R_LIMIAR_FRACAO).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )
        folha_faltante = max(Decimal("0.00"), folha_minima - folha_q)

    return AvaliacaoFatorR(
        folha_salarios_12m=folha_q,
        receita_bruta_12m=rbt12_q,
        percentual_fator_r=percentual,
        atingiu_minimo_28_pct=atingiu,
        anexo_definido="III" if atingiu else "V",
        folha_minima_anexo_iii=folha_minima,
        folha_faltante_anexo_iii=folha_faltante,
    )


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
