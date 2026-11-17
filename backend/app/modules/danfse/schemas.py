"""Schemas Pydantic para o módulo Gerador DANFSE."""

from decimal import Decimal
from pydantic import BaseModel, Field


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


class DanfsePreviewResponse(BaseModel):
    """Resposta estruturada com chave simulada e resumo para renderização do DANFSE."""

    numero_nfse: str
    chave_acesso_simulada: str
    prestador_cnpj: str
    tomador_documento: str
    valor_servicos: Decimal
    valor_total_tributos_rtc: Decimal
    valor_liquido_nota: Decimal
    status_validacao: str

