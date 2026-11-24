"""Resolução unificada de ICMS estadual / ISS municipal e transição constitucional (EC 132 / LC 214).

Centraliza o lookup read-only no SQLite (27 UFs ICMS + 5 shards regionais de ISS) e aplica
o motor puro `transicao_rtc.py` para manter os motores de cálculo livres de acesso a banco.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.core.rounding import ESCALA_ALIQUOTA_MAX
from app.core.transicao_rtc import RegraTransicaoRTC, obter_regra_transicao
from .repository_iss import obter_icms_uf, obter_iss_municipal

_ZERO = Decimal("0.00")


def _q4(val: Decimal) -> Decimal:
    return val.quantize(ESCALA_ALIQUOTA_MAX, rounding=ROUND_HALF_EVEN)


class ResumoTransicaoLocal(BaseModel):
    """Metadados da transição constitucional e do tributo local (ICMS/ISS) aplicados na simulação."""

    aplicar_transicao_ano: bool
    ano: int
    data_fato_gerador: str
    fase: str
    titulo_fase: str
    descricao_fase: str
    percentual_icms_iss_vigente: Decimal
    percentual_ibs_vigente: Decimal
    percentual_cbs_vigente: Decimal
    tipo_tributo_local: Optional[str] = None
    origem_aliquota_local: str = "nao_aplicavel"
    aliquota_local_cheia: Decimal = _ZERO
    aliquota_local_efetiva: Decimal = _ZERO
    aliquota_ibs_uf_efetiva: Decimal = _ZERO
    aliquota_ibs_mun_efetiva: Decimal = _ZERO
    aliquota_cbs_efetiva: Decimal = _ZERO
    municipio_nome: Optional[str] = None
    codigo_servico_iss: Optional[str] = None
    mensagem_aliquota_local: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ContextoTransicaoLocal:
    """Resultado interno com alíquotas efetivas pós-transição e resumo serializável."""

    aliquota_local_efetiva: Decimal
    aliquota_ibs_uf_efetiva: Decimal
    aliquota_ibs_mun_efetiva: Decimal
    aliquota_cbs_efetiva: Decimal
    resumo: ResumoTransicaoLocal


def _resolver_tributo_local_cheio(
    *,
    data_fato_gerador: date,
    uf: Optional[str],
    tipo_tributo_local: Optional[Literal["icms", "iss"]],
    codigo_ibge: Optional[int],
    codigo_servico_iss: Optional[str],
    aliquota_icms_manual: Optional[Decimal],
    aliquota_iss_manual: Optional[Decimal],
) -> tuple[Optional[str], Decimal, str, Optional[str], Optional[str], Optional[str]]:
    """Retorna (tipo, aliq_cheia, origem, mun_nome, cod_servico, mensagem)."""
    tipo = tipo_tributo_local
    if tipo is None:
        if aliquota_iss_manual is not None or (codigo_ibge is not None and codigo_servico_iss):
            tipo = "iss"
        elif aliquota_icms_manual is not None:
            tipo = "icms"

    if tipo == "iss":
        if aliquota_iss_manual is not None:
            return (
                "iss",
                aliquota_iss_manual,
                "manual",
                None,
                codigo_servico_iss,
                "Alíquota de ISS informada manualmente pelo usuário.",
            )
        if codigo_ibge is not None and codigo_servico_iss:
            resp: dict[str, Any] = obter_iss_municipal(
                codigo_ibge=codigo_ibge,
                codigo_servico=codigo_servico_iss,
                data_fato_gerador=data_fato_gerador,
            )
            if resp["encontrado"] and resp["aliquota_iss"] is not None:
                return (
                    "iss",
                    Decimal(resp["aliquota_iss"]),
                    resp["origem"],
                    resp["municipio_nome"],
                    resp["codigo_ctribnac"],
                    resp["mensagem"],
                )
            return (
                "iss",
                _ZERO,
                resp["origem"],
                resp["municipio_nome"],
                codigo_servico_iss,
                resp["mensagem"],
            )
        return (
            "iss",
            _ZERO,
            "nao_informado",
            None,
            codigo_servico_iss,
            "Selecione o município IBGE e o serviço LC 116 ou informe a alíquota de ISS manualmente.",
        )

    if tipo == "icms":
        if aliquota_icms_manual is not None:
            return (
                "icms",
                aliquota_icms_manual,
                "manual",
                None,
                None,
                "Alíquota de ICMS informada manualmente pelo usuário.",
            )
        if uf:
            reg = obter_icms_uf(uf=uf, data_fato_gerador=data_fato_gerador)
            if reg:
                return (
                    "icms",
                    Decimal(reg["aliquota_total"]),
                    "tabela_icms_uf",
                    None,
                    None,
                    f"ICMS modal {reg['uf']}: {reg['aliquota_interna']}% + FCP {reg['aliquota_fcp']}% ({reg['fundamentacao']}).",
                )
        return ("icms", _ZERO, "nao_informado", None, None, "UF não encontrada na tabela de ICMS modal.")

    return (None, _ZERO, "nao_aplicavel", None, None, None)


def _aplicar_escada_ibs_cbs(
    regra: RegraTransicaoRTC,
    aliq_local_cheia: Decimal,
    aliq_ibs_uf_cheia: Decimal,
    aliq_ibs_mun_cheia: Decimal,
    aliq_cbs_cheia: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Aplica fatores da EC 132 / LC 214 separando IBS UF, IBS Mun, CBS e ICMS/ISS."""
    local_efet = _q4(aliq_local_cheia * regra.fator_icms_iss)

    if regra.aliquota_ibs_fixa is not None:
        # Em 2026-2028 a alíquota-teste/transição de IBS é 0,10% (alocada na parcela UF para soma exata)
        ibs_uf_efet = _q4(regra.aliquota_ibs_fixa)
        ibs_mun_efet = _ZERO
    else:
        ibs_uf_efet = _q4(aliq_ibs_uf_cheia * regra.fator_ibs)
        ibs_mun_efet = _q4(aliq_ibs_mun_cheia * regra.fator_ibs)

    if regra.aliquota_cbs_fixa is not None:
        cbs_efet = _q4(regra.aliquota_cbs_fixa)
    else:
        cbs_efet = _q4(aliq_cbs_cheia * regra.fator_cbs)

    return local_efet, ibs_uf_efet, ibs_mun_efet, cbs_efet


def resolver_contexto_transicao_local(
    *,
    data_fato_gerador: date,
    uf: Optional[str],
    aliq_ibs_uf_cheia: Decimal,
    aliq_ibs_mun_cheia: Decimal,
    aliq_cbs_cheia: Decimal,
    aplicar_transicao_ano: bool = False,
    tipo_tributo_local: Optional[Literal["icms", "iss"]] = None,
    codigo_ibge: Optional[int] = None,
    codigo_servico_iss: Optional[str] = None,
    aliquota_icms_manual: Optional[Decimal] = None,
    aliquota_iss_manual: Optional[Decimal] = None,
) -> Optional[ContextoTransicaoLocal]:
    """Resolve contexto completo quando `aplicar_transicao_ano=True` ou há tributo local explícito.

    Retorna `None` se `aplicar_transicao_ano=False` e nenhum campo local foi informado,
    preservando 100% da retrocompatibilidade com chamadas legadas.
    """
    tem_local_explicito = any(
        x is not None
        for x in (tipo_tributo_local, codigo_ibge, codigo_servico_iss, aliquota_icms_manual, aliquota_iss_manual)
    )
    if not aplicar_transicao_ano and not tem_local_explicito:
        return None

    regra = obter_regra_transicao(data_fato_gerador)
    tipo, aliq_cheia, origem, mun_nome, cod_serv, msg = _resolver_tributo_local_cheio(
        data_fato_gerador=data_fato_gerador,
        uf=uf,
        tipo_tributo_local=tipo_tributo_local,
        codigo_ibge=codigo_ibge,
        codigo_servico_iss=codigo_servico_iss,
        aliquota_icms_manual=aliquota_icms_manual,
        aliquota_iss_manual=aliquota_iss_manual,
    )

    if aplicar_transicao_ano:
        local_efet, ibs_uf_efet, ibs_mun_efet, cbs_efet = _aplicar_escada_ibs_cbs(
            regra, aliq_cheia, aliq_ibs_uf_cheia, aliq_ibs_mun_cheia, aliq_cbs_cheia
        )
    else:
        local_efet = _q4(aliq_cheia)
        ibs_uf_efet = aliq_ibs_uf_cheia
        ibs_mun_efet = aliq_ibs_mun_cheia
        cbs_efet = aliq_cbs_cheia

    resumo = ResumoTransicaoLocal(
        aplicar_transicao_ano=aplicar_transicao_ano,
        ano=regra.ano,
        data_fato_gerador=regra.data_referencia.isoformat(),
        fase=regra.fase,
        titulo_fase=regra.titulo_curto,
        descricao_fase=regra.descricao,
        percentual_icms_iss_vigente=(regra.fator_icms_iss * Decimal("100")).quantize(Decimal("0.01")),
        percentual_ibs_vigente=(regra.fator_ibs * Decimal("100")).quantize(Decimal("0.01")),
        percentual_cbs_vigente=(regra.fator_cbs * Decimal("100")).quantize(Decimal("0.01")),
        tipo_tributo_local=tipo,
        origem_aliquota_local=origem,
        aliquota_local_cheia=aliq_cheia,
        aliquota_local_efetiva=local_efet,
        aliquota_ibs_uf_efetiva=ibs_uf_efet,
        aliquota_ibs_mun_efetiva=ibs_mun_efet,
        aliquota_cbs_efetiva=cbs_efet,
        municipio_nome=mun_nome,
        codigo_servico_iss=cod_serv,
        mensagem_aliquota_local=msg,
    )
    return ContextoTransicaoLocal(
        aliquota_local_efetiva=local_efet,
        aliquota_ibs_uf_efetiva=ibs_uf_efet,
        aliquota_ibs_mun_efetiva=ibs_mun_efet,
        aliquota_cbs_efetiva=cbs_efet,
        resumo=resumo,
    )
