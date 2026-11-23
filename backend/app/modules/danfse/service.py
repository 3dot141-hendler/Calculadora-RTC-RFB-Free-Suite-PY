"""Serviço de geração de prévia estruturada e PDF binário (DANFSe v2.0 + QR Code)."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib

from .domain import (
    DanfsePdfDocument,
    SituacaoNotaTipo,
    formatar_cpf_cnpj,
    montar_url_qrcode_nfse,
    sanitizar_nome_arquivo_nfse,
)
from .pdf_renderer import renderizar_danfse_pdf
from .schemas import DanfsePreviewRequest, DanfsePreviewResponse
from .xml_parser import parse_nfse_xml, xml_summary_to_pdf_document


def gerar_preview_danfse(payload: DanfsePreviewRequest) -> DanfsePreviewResponse:
    """Valida e gera prévia estruturada do DANFSE com destaque de IBS e CBS."""
    total_rtc = (payload.valor_ibs + payload.valor_cbs).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_EVEN
    )
    seed = f"{payload.prestador_cnpj}:{payload.numero_nfse}:{payload.valor_servicos}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:44].upper()
    situacao, _ = SituacaoNotaTipo.por_stc(payload.situacao_stc)
    valor_serv = payload.valor_servicos.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

    return DanfsePreviewResponse(
        numero_nfse=payload.numero_nfse,
        chave_acesso_simulada=digest,
        prestador_cnpj=payload.prestador_cnpj,
        prestador_cnpj_formatado=formatar_cpf_cnpj(payload.prestador_cnpj),
        tomador_documento=payload.tomador_documento,
        tomador_documento_formatado=formatar_cpf_cnpj(payload.tomador_documento),
        valor_servicos=valor_serv,
        valor_total_tributos_rtc=total_rtc,
        valor_liquido_nota=valor_serv,
        situacao=situacao,
        marca_dagua=situacao.marca_dagua(),
        status_validacao="VALIDO_PARA_PREVIA",
    )


def gerar_pdf_danfse_preview(payload: DanfsePreviewRequest) -> tuple[bytes, str]:
    """Gera PDF binário DANFSe v2.0 (com QR Code) a partir do payload estruturado."""
    preview = gerar_preview_danfse(payload)
    agora = datetime.now()
    valor_ibs = payload.valor_ibs.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    valor_cbs = payload.valor_cbs.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    liquido_rtc = (preview.valor_liquido_nota + preview.valor_total_tributos_rtc).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_EVEN
    )

    doc = DanfsePdfDocument(
        numero_nfse=preview.numero_nfse,
        chave_acesso=preview.chave_acesso_simulada,
        qrcode_url=montar_url_qrcode_nfse(preview.chave_acesso_simulada),
        competencia=agora.strftime("%d/%m/%Y"),
        data_hora_emissao=agora.strftime("%d/%m/%Y %H:%M:%S"),
        situacao_texto=preview.situacao.rotulo_situacao(),
        marca_dagua=preview.marca_dagua,
        sem_validade_juridica=True,
        prestador_nome="Prestador de Serviços (Simulação Estruturada)",
        prestador_documento=preview.prestador_cnpj_formatado,
        prestador_municipio="Porto Alegre - RS",
        prestador_endereco="Informado na emissão definitiva",
        tomador_nome="Tomador / Adquirente (Simulação Estruturada)",
        tomador_documento=preview.tomador_documento_formatado,
        tomador_municipio="-",
        tomador_endereco="-",
        local_prestacao="Porto Alegre - RS",
        codigo_tributacao="Simulação RTC (LC 214/2025)",
        discriminacao_servico=payload.discriminacao_servico,
        cst_cclasstrib="000 / 000001",
        valor_servicos=preview.valor_servicos,
        valor_ibs=valor_ibs,
        valor_cbs=valor_cbs,
        valor_total_ibs_cbs=preview.valor_total_tributos_rtc,
        valor_liquido_nota=preview.valor_liquido_nota,
        valor_liquido_com_rtc=liquido_rtc,
        informacoes_complementares=(
            "Documento auxiliar gerado em modo de simulação/prévia pela Calculadora RTC RFB Free Suite PY. "
            "A autenticidade de NFS-e oficial pode ser verificada pela leitura do QR Code no portal nacional da NFS-e."
        ),
    )
    return renderizar_danfse_pdf(doc), sanitizar_nome_arquivo_nfse(preview.numero_nfse)


def gerar_pdf_danfse_xml(xml_content: str) -> tuple[bytes, str]:
    """Valida XML <NFSe> (proteção XXE) e gera PDF binário DANFSe v2.0 com QR Code."""
    summary = parse_nfse_xml(xml_content)
    doc = xml_summary_to_pdf_document(summary)
    return renderizar_danfse_pdf(doc), sanitizar_nome_arquivo_nfse(summary.numero_nfse)
