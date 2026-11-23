"""Cálculo unificado de bases de cálculo (RG/IBS-CBS, IS e SN) para NF-e (55) e NFC-e (65).

Port fiel de `BaseCalculoUnificadaService.java` e `ElementoBaseCalculo.java` da RFB.
Motor puro sem acesso a banco de dados (Decimal + ROUND_HALF_EVEN via `app.core.rounding`).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.core.rounding import formatar_moeda, subtrair

NaturezaOperacao = Literal["bem", "servico"]


@dataclass(frozen=True)
class _RegraElementoBC:
    tag: str
    operacao: Literal["SOMA", "SUBTRAI"]
    bases: frozenset[str]
    natureza: Optional[NaturezaOperacao]
    ano_inicio: int
    ano_fim: int
    modelos_validos: frozenset[int]

    def campo_compoe_base(self, ano: int, natureza: Optional[NaturezaOperacao], tp_doc: int) -> bool:
        ano_ok = self.ano_inicio <= ano <= self.ano_fim
        nat_ok = (self.natureza is None) or (natureza is not None and self.natureza == natureza)
        mod_ok = tp_doc in self.modelos_validos
        return ano_ok and nat_ok and mod_ok

    def motivo_nao_composicao(
        self, ano: int, natureza: Optional[NaturezaOperacao], tp_doc: int
    ) -> Optional[str]:
        if not (self.ano_inicio <= ano <= self.ano_fim):
            return (
                f"Campo {self.tag} não compõe as bases para o ano {ano} "
                f"(vigência {self.ano_inicio}–{self.ano_fim}) e foi ignorado no cálculo"
            )
        if self.natureza is not None and self.natureza != natureza:
            return (
                f"Campo {self.tag} não compõe as bases para a natureza {natureza} "
                f"(aplicável apenas a {self.natureza}) e foi ignorado no cálculo"
            )
        if tp_doc not in self.modelos_validos:
            return (
                f"Campo {self.tag} não compõe as bases para o documento modelo {tp_doc} "
                "e foi ignorado no cálculo"
            )
        return None


CATALOGO_ELEMENTOS_BC: tuple[_RegraElementoBC, ...] = (
    _RegraElementoBC("vProd", "SOMA", frozenset({"RG", "IS", "SN"}), None, 2026, 2033, frozenset({55, 65})),
    _RegraElementoBC("vFrete", "SOMA", frozenset({"RG", "IS", "SN"}), None, 2026, 2033, frozenset({55, 65})),
    _RegraElementoBC("vSeg", "SOMA", frozenset({"RG", "IS", "SN"}), None, 2026, 2033, frozenset({55, 65})),
    _RegraElementoBC("vOutro", "SOMA", frozenset({"RG", "IS", "SN"}), None, 2026, 2033, frozenset({55, 65})),
    _RegraElementoBC("vII", "SOMA", frozenset({"RG", "IS"}), "bem", 2026, 2033, frozenset({55})),
    _RegraElementoBC("vIS", "SOMA", frozenset({"RG", "SN"}), None, 2027, 2033, frozenset({55, 65})),
    _RegraElementoBC("vDesc", "SUBTRAI", frozenset({"RG", "IS", "SN"}), None, 2026, 2033, frozenset({55, 65})),
    _RegraElementoBC("vPIS", "SUBTRAI", frozenset({"RG", "IS"}), None, 2026, 2026, frozenset({55, 65})),
    _RegraElementoBC("vCOFINS", "SUBTRAI", frozenset({"RG", "IS"}), None, 2026, 2026, frozenset({55, 65})),
    _RegraElementoBC("vICMS", "SUBTRAI", frozenset({"RG", "IS"}), "bem", 2026, 2032, frozenset({55, 65})),
    _RegraElementoBC("vICMSUFDest", "SUBTRAI", frozenset({"RG", "IS"}), "bem", 2026, 2032, frozenset({55})),
    _RegraElementoBC("vFCP", "SUBTRAI", frozenset({"RG", "IS"}), "bem", 2026, 2032, frozenset({55, 65})),
    _RegraElementoBC("vFCPUFDest", "SUBTRAI", frozenset({"RG", "IS"}), "bem", 2026, 2032, frozenset({55})),
    _RegraElementoBC("vICMSMono", "SUBTRAI", frozenset({"RG", "IS"}), "bem", 2026, 2032, frozenset({55, 65})),
    _RegraElementoBC("vISSQN", "SUBTRAI", frozenset({"RG", "IS"}), "servico", 2026, 2032, frozenset({55, 65})),
)


class ComponentesBaseCalculoInput(BaseModel):
    """Componentes padronizados de base de cálculo (NF-e 55 / NFC-e 65)."""

    vProd: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vFrete: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vSeg: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vOutro: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vII: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vIS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vDesc: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vPIS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vCOFINS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vICMS: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vICMSUFDest: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vFCP: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vFCPUFDest: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vICMSMono: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    vISSQN: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class BaseCalculoUnificadaRequest(BaseModel):
    """Payload do endpoint de Base de Cálculo Unificada (RG/IBS-CBS, IS e SN)."""

    ano_fato_gerador: int = Field(default=2026, ge=2026, le=2033)
    natureza: Optional[NaturezaOperacao] = Field(default="bem")
    tipo_documento: int = Field(default=55, description="Modelo do DF-e: 55 (NF-e) ou 65 (NFC-e).")
    componentes: ComponentesBaseCalculoInput = Field(default_factory=ComponentesBaseCalculoInput)


class BaseCalculoUnificadaResponse(BaseModel):
    """Resultado unificado com as três bases calculadas e avisos de vigência/natureza/modelo."""

    ano_fato_gerador: int
    natureza: Optional[NaturezaOperacao]
    tipo_documento: int
    baseRG: str
    baseIS: str
    baseSN: str
    avisos: list[str]


def calcular_base_unificada(payload: BaseCalculoUnificadaRequest) -> BaseCalculoUnificadaResponse:
    """Calcula simultaneamente `baseRG`, `baseIS` e `baseSN` conforme catálogo RFB."""
    if payload.tipo_documento not in (55, 65):
        raise ValueError("Tipo de documento deve ser 55 (NF-e) ou 65 (NFC-e).")

    somas = {"RG": Decimal("0"), "IS": Decimal("0"), "SN": Decimal("0")}
    subtracoes = {"RG": Decimal("0"), "IS": Decimal("0"), "SN": Decimal("0")}
    avisos: list[str] = []

    for elem in CATALOGO_ELEMENTOS_BC:
        valor: Decimal = getattr(payload.componentes, elem.tag, Decimal("0"))
        if valor == Decimal("0"):
            continue

        if not elem.campo_compoe_base(payload.ano_fato_gerador, payload.natureza, payload.tipo_documento):
            motivo = elem.motivo_nao_composicao(
                payload.ano_fato_gerador, payload.natureza, payload.tipo_documento
            )
            if motivo:
                avisos.append(motivo)
            continue

        alvo = somas if elem.operacao == "SOMA" else subtracoes
        for base in elem.bases:
            alvo[base] = alvo[base] + valor

    base_rg = subtrair(somas["RG"], subtracoes["RG"])
    base_is = subtrair(somas["IS"], subtracoes["IS"])
    base_sn = subtrair(somas["SN"], subtracoes["SN"])

    return BaseCalculoUnificadaResponse(
        ano_fato_gerador=payload.ano_fato_gerador,
        natureza=payload.natureza,
        tipo_documento=payload.tipo_documento,
        baseRG=formatar_moeda(base_rg),
        baseIS=formatar_moeda(base_is),
        baseSN=formatar_moeda(base_sn),
        avisos=avisos,
    )
