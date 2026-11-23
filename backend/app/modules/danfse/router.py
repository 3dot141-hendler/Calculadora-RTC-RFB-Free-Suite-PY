"""Rotas FastAPI para o módulo Gerador DANFSE (/danfse)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .schemas import DanfsePreviewRequest, DanfsePreviewResponse
from .service import gerar_pdf_danfse_preview, gerar_pdf_danfse_xml, gerar_preview_danfse
from .xml_parser import DanfseXmlSummary, XmlDanfseInvalidoError, parse_nfse_xml


class DanfseXmlRequest(BaseModel):
    """Payload contendo o XML bruto da NFS-e padrão nacional."""

    xml_content: str = Field(..., min_length=1, description="Conteúdo XML da NFS-e.")


router = APIRouter(prefix="/danfse", tags=["Gerador DANFSE"])


@router.get("/info", summary="Metadados do módulo Gerador DANFSE")
def info_danfse() -> dict[str, str]:
    """Retorna informações de status e referência do módulo DANFSE."""
    return {
        "modulo": "danfse",
        "status": "ready",
        "pdf_engine": "reportlab-qr-v2",
        "referencia_rfb": "https://github.com/ReceitaFederal/calculadora-rtc-gerador-danfse",
    }


@router.post(
    "/preview",
    response_model=DanfsePreviewResponse,
    summary="Gerar prévia estruturada do DANFSE",
)
def endpoint_preview_danfse(payload: DanfsePreviewRequest) -> DanfsePreviewResponse:
    """Valida dados da NFS-e com campos IBS/CBS e gera prévia estruturada."""
    return gerar_preview_danfse(payload)


@router.post(
    "/pdf",
    summary="Gerar PDF binário oficial do DANFSe v2.0 com QR Code",
    responses={200: {"content": {"application/pdf": {}}}},
)
def endpoint_pdf_danfse(payload: DanfsePreviewRequest) -> Response:
    """Renderiza e retorna o DANFSe v2.0 em PDF binário (`application/pdf`) com QR Code."""
    pdf_bytes, filename = gerar_pdf_danfse_preview(payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/parse-xml",
    response_model=DanfseXmlSummary,
    summary="Validar e extrair dados de XML NFS-e padrão nacional",
)
def endpoint_parse_xml_danfse(payload: DanfseXmlRequest) -> DanfseXmlSummary:
    """Analisa XML oficial da NFS-e com proteção XXE e retorna resumo estruturado."""
    try:
        return parse_nfse_xml(payload.xml_content)
    except XmlDanfseInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/pdf-from-xml",
    summary="Gerar PDF binário DANFSe v2.0 + QR Code a partir de XML NFS-e",
    responses={200: {"content": {"application/pdf": {}}}},
)
def endpoint_pdf_from_xml_danfse(payload: DanfseXmlRequest) -> Response:
    """Valida XML oficial (proteção XXE) e devolve o DANFSe v2.0 em PDF binário."""
    try:
        pdf_bytes, filename = gerar_pdf_danfse_xml(payload.xml_content)
    except XmlDanfseInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
