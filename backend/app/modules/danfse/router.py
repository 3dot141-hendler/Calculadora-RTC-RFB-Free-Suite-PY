"""Rotas FastAPI para o módulo Gerador DANFSE (/danfse)."""

from fastapi import APIRouter

from .schemas import DanfsePreviewRequest, DanfsePreviewResponse
from .service import gerar_preview_danfse

router = APIRouter(prefix="/danfse", tags=["Gerador DANFSE"])


@router.get("/info", summary="Metadados do módulo Gerador DANFSE")
def info_danfse() -> dict[str, str]:
    """Retorna informações de status e referência do módulo DANFSE."""
    return {
        "modulo": "danfse",
        "status": "ready",
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

