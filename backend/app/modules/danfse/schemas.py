"""Schemas Pydantic para o módulo Gerador DANFSE."""

from decimal import Decimal
from pydantic import BaseModel, Field

from .domain import SituacaoNotaTipo


class DanfsePreviewRequest(BaseModel):
    """Payload de entrada para geração de prévia estruturada de DANFSE."""

    numero_nfse: str = Field(..., min_length=1, max_length=32, description="Número da NFS-e.")
    prestador_cnpj: str = Field(
        ...,
        pattern=r"^\d{14}$",
        description="CNPJ do prestador (14 dígitos numéricos).",
    )
    tomador_documento: str = Field(
        ...,
        pattern=r"^\d{11}|\d{14}$",
        description="CPF (11 dígitos) ou CNPJ (14 dígitos) do tomador.",
    )
    discriminacao_servico: str = Field(..., min_length=3, max_length=500)
    valor_servicos: Decimal = Field(..., gt=Decimal("0.00"))
    valor_ibs: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    valor_cbs: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    situacao_stc: int = Field(default=0, ge=0, le=2, description="0=Válida, 1=Substituída, 2=Cancelada.")


class DanfsePreviewResponse(BaseModel):
    """Resposta estruturada com chave simulada e resumo para renderização do DANFSE."""

    numero_nfse: str
    chave_acesso_simulada: str
    prestador_cnpj: str
    prestador_cnpj_formatado: str
    tomador_documento: str
    tomador_documento_formatado: str
    valor_servicos: Decimal
    valor_total_tributos_rtc: Decimal
    valor_liquido_nota: Decimal
    situacao: SituacaoNotaTipo
    marca_dagua: str
    status_validacao: str

