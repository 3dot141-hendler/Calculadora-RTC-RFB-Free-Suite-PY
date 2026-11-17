"""Serviço de geração e validação de prévia DANFSE (esqueleto para port da RFB)."""

from decimal import Decimal, ROUND_HALF_EVEN
import hashlib

from .domain import SituacaoNotaTipo, formatar_cpf_cnpj
from .schemas import DanfsePreviewRequest, DanfsePreviewResponse


def gerar_preview_danfse(payload: DanfsePreviewRequest) -> DanfsePreviewResponse:
    """Valida e gera prévia estruturada do DANFSE com destaque de IBS e CBS.

    A renderização PDF/HTML fiel ao layout nacional será portada a partir de
    `originals:references/danfse`.
    """
    total_rtc = (payload.valor_ibs + payload.valor_cbs).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_EVEN
    )
    seed = f"{payload.prestador_cnpj}:{payload.numero_nfse}:{payload.valor_servicos}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:44].upper()
    situacao, _ = SituacaoNotaTipo.por_stc(payload.situacao_stc)

    return DanfsePreviewResponse(
        numero_nfse=payload.numero_nfse,
        chave_acesso_simulada=digest,
        prestador_cnpj=payload.prestador_cnpj,
        prestador_cnpj_formatado=formatar_cpf_cnpj(payload.prestador_cnpj),
        tomador_documento=payload.tomador_documento,
        tomador_documento_formatado=formatar_cpf_cnpj(payload.tomador_documento),
        valor_servicos=payload.valor_servicos.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN),
        valor_total_tributos_rtc=total_rtc,
        valor_liquido_nota=payload.valor_servicos.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        ),
        situacao=situacao,
        marca_dagua=situacao.marca_dagua(),
        status_validacao="VALIDO_PARA_PREVIA",
    )

