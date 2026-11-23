"""Motor puro da escada constitucional de transição da Reforma Tributária (EC 132/2023 + LC 214/2025).

Sem acesso a banco de dados. Toda aritmética utiliza Decimal + ROUND_HALF_EVEN.

Escada de transição (ICMS/ISS antigos vs. IBS/CBS novos):
  - <= 2025 : 100% ICMS/ISS | 0% IBS | 0% CBS | 100% PIS/COFINS
  - 2026    : 100% ICMS/ISS | 0,10% IBS (teste) | 0,90% CBS (teste) | 100% PIS/COFINS (compensáveis)
  - 2027-28 : 100% ICMS/ISS | 0,10% IBS (transição) | 100% CBS cheia | PIS/COFINS extintos
  - 2029    :  90% ICMS/ISS (9/10) |  10% IBS (1/10) | 100% CBS | PIS/COFINS extintos
  - 2030    :  80% ICMS/ISS (8/10) |  20% IBS (2/10) | 100% CBS | PIS/COFINS extintos
  - 2031    :  70% ICMS/ISS (7/10) |  30% IBS (3/10) | 100% CBS | PIS/COFINS extintos
  - 2032    :  60% ICMS/ISS (6/10) |  40% IBS (4/10) | 100% CBS | PIS/COFINS extintos
  - >= 2033 :   0% ICMS/ISS (extintos) | 100% IBS | 100% CBS | PIS/COFINS extintos
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN

from app.core.rounding import ESCALA_ALIQUOTA_MAX, formatar_moeda

_ZERO = Decimal("0.00")
_UM = Decimal("1.00")
_CEM = Decimal("100")

# Alíquotas fixas de teste / transição inicial (LC 214/2025, arts. 343 a 348)
ALIQUOTA_IBS_TESTE_2026 = Decimal("0.10")
ALIQUOTA_CBS_TESTE_2026 = Decimal("0.90")
ALIQUOTA_IBS_TRANSICAO_2027_2028 = Decimal("0.10")


def _quant_aliq(valor: Decimal) -> Decimal:
    return valor.quantize(ESCALA_ALIQUOTA_MAX, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class RegraTransicaoRTC:
    """Parâmetros constitucionais vigentes para uma data de fato gerador."""

    ano: int
    data_referencia: date
    fase: str
    titulo_curto: str
    descricao: str
    fator_icms_iss: Decimal
    fator_ibs: Decimal
    fator_cbs: Decimal
    aliquota_ibs_fixa: Decimal | None
    aliquota_cbs_fixa: Decimal | None
    pis_cofins_vigente: bool
    ibs_cbs_compensaveis_teste: bool

    def to_dict(self) -> dict[str, object]:
        """Serialização padronizada para respostas JSON da API."""
        return {
            "ano": self.ano,
            "data_referencia": self.data_referencia.isoformat(),
            "fase": self.fase,
            "titulo_curto": self.titulo_curto,
            "descricao": self.descricao,
            "percentual_icms_iss": formatar_moeda(self.fator_icms_iss * _CEM),
            "percentual_ibs": formatar_moeda(self.fator_ibs * _CEM),
            "percentual_cbs": formatar_moeda(self.fator_cbs * _CEM),
            "aliquota_ibs_fixa": str(self.aliquota_ibs_fixa) if self.aliquota_ibs_fixa is not None else None,
            "aliquota_cbs_fixa": str(self.aliquota_cbs_fixa) if self.aliquota_cbs_fixa is not None else None,
            "pis_cofins_vigente": self.pis_cofins_vigente,
            "ibs_cbs_compensaveis_teste": self.ibs_cbs_compensaveis_teste,
        }


@dataclass(frozen=True)
class AliquotasTransicaoAno:
    """Alíquotas efetivas resultantes da aplicação da escada constitucional em uma data."""

    regra: RegraTransicaoRTC
    aliquota_local_efetiva: Decimal
    aliquota_ibs_efetiva: Decimal
    aliquota_cbs_efetiva: Decimal
    aliquota_total_efetiva: Decimal
    ignorou_tabela_local_simples_das: bool = False


_ESCALA_GRADUAL_IBS: dict[int, tuple[Decimal, Decimal]] = {
    2029: (Decimal("0.90"), Decimal("0.10")),
    2030: (Decimal("0.80"), Decimal("0.20")),
    2031: (Decimal("0.70"), Decimal("0.30")),
    2032: (Decimal("0.60"), Decimal("0.40")),
}


def obter_regra_transicao(data_fato_gerador: date | None = None) -> RegraTransicaoRTC:
    """Retorna a regra constitucional da EC 132 / LC 214 vigente para a data informada."""
    ref = data_fato_gerador or date.today()
    ano = ref.year

    if ano <= 2025:
        return RegraTransicaoRTC(
            ano=ano,
            data_referencia=ref,
            fase="pre_reforma",
            titulo_curto=f"{ano}: Pré-Reforma (100% ICMS/ISS)",
            descricao="Sistema anterior à Reforma Tributária: ICMS/ISS e PIS/COFINS integrais, sem IBS/CBS.",
            fator_icms_iss=_UM,
            fator_ibs=_ZERO,
            fator_cbs=_ZERO,
            aliquota_ibs_fixa=_ZERO,
            aliquota_cbs_fixa=_ZERO,
            pis_cofins_vigente=True,
            ibs_cbs_compensaveis_teste=False,
        )

    if ano == 2026:
        return RegraTransicaoRTC(
            ano=ano,
            data_referencia=ref,
            fase="ano_teste_2026",
            titulo_curto="2026: Ano-Teste (100% ICMS/ISS + CBS 0,9% / IBS 0,1%)",
            descricao=(
                "ICMS/ISS e PIS/COFINS integrais. Alíquotas-teste de CBS (0,90%) e IBS (0,10%) "
                "compensáveis com PIS/COFINS (LC 214/2025, art. 348)."
            ),
            fator_icms_iss=_UM,
            fator_ibs=_ZERO,
            fator_cbs=_ZERO,
            aliquota_ibs_fixa=ALIQUOTA_IBS_TESTE_2026,
            aliquota_cbs_fixa=ALIQUOTA_CBS_TESTE_2026,
            pis_cofins_vigente=True,
            ibs_cbs_compensaveis_teste=True,
        )

    if ano in (2027, 2028):
        return RegraTransicaoRTC(
            ano=ano,
            data_referencia=ref,
            fase="transicao_cbs_cheia",
            titulo_curto=f"{ano}: 100% ICMS/ISS + CBS cheia + IBS 0,1%",
            descricao=(
                "PIS/COFINS extintos e substituídos pela CBS cheia (100%). ICMS e ISS seguem "
                "integrais (100%) com IBS de transição em 0,10% (EC 132/2023)."
            ),
            fator_icms_iss=_UM,
            fator_ibs=_ZERO,
            fator_cbs=_UM,
            aliquota_ibs_fixa=ALIQUOTA_IBS_TRANSICAO_2027_2028,
            aliquota_cbs_fixa=None,
            pis_cofins_vigente=False,
            ibs_cbs_compensaveis_teste=False,
        )

    if ano in _ESCALA_GRADUAL_IBS:
        fator_local, fator_ibs = _ESCALA_GRADUAL_IBS[ano]
        pct_local = int(fator_local * _CEM)
        pct_ibs = int(fator_ibs * _CEM)
        return RegraTransicaoRTC(
            ano=ano,
            data_referencia=ref,
            fase="transicao_gradual_ibs",
            titulo_curto=f"{ano}: {pct_local}% ICMS/ISS + {pct_ibs}% IBS + CBS cheia",
            descricao=(
                f"Redução gradual do ICMS/ISS para {pct_local}% ({pct_local // 10}/10) com "
                f"substituição proporcional pelo IBS ({pct_ibs}%) e CBS integral (100%)."
            ),
            fator_icms_iss=fator_local,
            fator_ibs=fator_ibs,
            fator_cbs=_UM,
            aliquota_ibs_fixa=None,
            aliquota_cbs_fixa=None,
            pis_cofins_vigente=False,
            ibs_cbs_compensaveis_teste=False,
        )

    return RegraTransicaoRTC(
        ano=ano,
        data_referencia=ref,
        fase="reforma_plena",
        titulo_curto=f"{ano}: Reforma Plena (0% ICMS/ISS + 100% IBS/CBS)",
        descricao="ICMS, ISS e PIS/COFINS integralmente extintos. Vigência plena de IBS (100%) e CBS (100%).",
        fator_icms_iss=_ZERO,
        fator_ibs=_UM,
        fator_cbs=_UM,
        aliquota_ibs_fixa=None,
        aliquota_cbs_fixa=None,
        pis_cofins_vigente=False,
        ibs_cbs_compensaveis_teste=False,
    )


def aplicar_transicao_aliquotas(
    data_fato_gerador: date | None,
    aliquota_local_cheia: Decimal,
    aliquota_ibs_cheia: Decimal,
    aliquota_cbs_cheia: Decimal,
    *,
    simples_tradicional: bool = False,
) -> AliquotasTransicaoAno:
    """Calcula alíquotas efetivas (ICMS/ISS residual, IBS e CBS) conforme a data do fato gerador.

    Regra de Ouro do Simples Nacional:
      - Se `simples_tradicional=True` (recolhimento unificado no DAS / LC 123), a tabela
        municipal de ISS e a tabela modal de ICMS NÃO são aplicadas (`aliquota_local_efetiva = 0`).
      - Caso contrário (Lucro Presumido, Lucro Real, Regime Regular ou Simples Híbrido por fora),
        aplica integralmente a escada constitucional da EC 132 / LC 214 para o ano da data.
    """
    regra = obter_regra_transicao(data_fato_gerador)

    if simples_tradicional:
        return AliquotasTransicaoAno(
            regra=regra,
            aliquota_local_efetiva=_ZERO,
            aliquota_ibs_efetiva=_ZERO,
            aliquota_cbs_efetiva=_ZERO,
            aliquota_total_efetiva=_ZERO,
            ignorou_tabela_local_simples_das=True,
        )

    aliq_local = _quant_aliq(aliquota_local_cheia * regra.fator_icms_iss)

    if regra.aliquota_ibs_fixa is not None:
        aliq_ibs = _quant_aliq(regra.aliquota_ibs_fixa)
    else:
        aliq_ibs = _quant_aliq(aliquota_ibs_cheia * regra.fator_ibs)

    if regra.aliquota_cbs_fixa is not None:
        aliq_cbs = _quant_aliq(regra.aliquota_cbs_fixa)
    else:
        aliq_cbs = _quant_aliq(aliquota_cbs_cheia * regra.fator_cbs)

    total = _quant_aliq(aliq_local + aliq_ibs + aliq_cbs)
    return AliquotasTransicaoAno(
        regra=regra,
        aliquota_local_efetiva=aliq_local,
        aliquota_ibs_efetiva=aliq_ibs,
        aliquota_cbs_efetiva=aliq_cbs,
        aliquota_total_efetiva=total,
        ignorou_tabela_local_simples_das=False,
    )
