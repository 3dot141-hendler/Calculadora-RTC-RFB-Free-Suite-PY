"""Avaliador seguro de expressões aritméticas tributárias (ADR001 — RFB).

Port fiel de `AvaliadorExpressaoAritmetica.java` usando AST Python em sandbox
restrita (sem `eval()`): permite apenas literais numéricos (`Decimal`),
variáveis previamente mapeadas e operadores aritméticos (`+`, `-`, `*`, `/`).
"""

from __future__ import annotations

import ast
from decimal import Decimal, InvalidOperation
from pydantic import BaseModel, Field

from app.core.rounding import arredondar_interno, formatar_moeda

MAX_EXPRESSION_LENGTH = 500
MAX_AST_NODES = 128

FORMULAS_OFICIAIS_REFERENCIA: dict[str, dict[str, str]] = {
    "aliquota_efetiva_padrao": {
        "expressao": "aliquota * (1 - percentualReducao)",
        "descricao": "Alíquota efetiva padrão com redução por cClassTrib (LC 214/2025).",
    },
    "aliquota_efetiva_compra_gov": {
        "expressao": "aliquota * (1 - percentualReducao) * (1 - percentualReducaoCompraGov)",
        "descricao": "Alíquota efetiva em operação de compra governamental com redutor (V0019).",
    },
    "base_calculo_cibs_com_is": {
        "expressao": "baseCalculoInformada - impostoSeletivoInformado + impostoSeletivoCalculado",
        "descricao": "Base de cálculo CBS/IBS substituindo IS informado pelo IS calculado.",
    },
    "tributo_devido_diferimento": {
        "expressao": "tributoCalculado * (1 - percentualDiferimento)",
        "descricao": "Tributo devido após dedução do percentual de diferimento.",
    },
}


class ExpressaoInvalidaError(ValueError):
    """Erro lançado quando a expressão tributária é sintaticamente ou semanticamente inválida."""


class ExpressaoAvaliacaoRequest(BaseModel):
    """Payload para avaliação segura de expressão aritmética tributária (ADR001)."""

    expressao: str = Field(..., min_length=1, max_length=MAX_EXPRESSION_LENGTH)
    variaveis: dict[str, Decimal] = Field(default_factory=dict)


class ExpressaoAvaliacaoResponse(BaseModel):
    """Resultado da avaliação da expressão tributária com precisão interna e monetária."""

    expressao: str
    resultado_interno: str
    resultado_monetario: str
    variaveis_utilizadas: list[str]


def _parse_decimal_constant(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExpressaoInvalidaError(f"Constante não numérica não permitida: {value!r}")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ExpressaoInvalidaError(f"Número inválido na expressão: {value!r}") from exc


def _eval_node(node: ast.AST, variaveis: dict[str, Decimal], usadas: set[str]) -> Decimal:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, variaveis, usadas)

    if isinstance(node, ast.Constant):
        return _parse_decimal_constant(node.value)

    if isinstance(node, ast.Name):
        if node.id not in variaveis:
            raise ExpressaoInvalidaError(f"Variável não mapeada no contexto: '{node.id}'")
        valor = variaveis[node.id]
        if valor is None:
            raise ExpressaoInvalidaError(f"Valor nulo para a variável: '{node.id}'")
        usadas.add(node.id)
        return Decimal(str(valor))

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, variaveis, usadas)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise ExpressaoInvalidaError(f"Operador unário não permitido: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, variaveis, usadas)
        right = _eval_node(node.right, variaveis, usadas)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            if right == Decimal("0"):
                raise ExpressaoInvalidaError("Divisão por zero na avaliação da expressão.")
            return left / right
        raise ExpressaoInvalidaError(f"Operador binário não permitido: {type(node.op).__name__}")

    raise ExpressaoInvalidaError(
        f"Construção não permitida pela sandbox aritmética (ADR001): {type(node).__name__}"
    )


def avaliar_expressao_tributaria(
    expressao: str,
    variaveis: dict[str, Decimal] | None = None,
) -> tuple[Decimal, list[str]]:
    """Avalia expressão aritmética em sandbox AST com `Decimal` e arredondamento interno (8 casas)."""
    expr = (expressao or "").strip()
    if not expr:
        raise ExpressaoInvalidaError("Expressão tributária vazia.")
    if len(expr) > MAX_EXPRESSION_LENGTH:
        raise ExpressaoInvalidaError(f"Expressão excede o limite de {MAX_EXPRESSION_LENGTH} caracteres.")

    ctx = {k: Decimal(str(v)) for k, v in (variaveis or {}).items()}

    # Atalho fiel à RFB: expressão é exatamente o nome de uma variável
    if expr in ctx:
        return arredondar_interno(ctx[expr]), [expr]

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ExpressaoInvalidaError(f"Erro de sintaxe na expressão: {exc.msg}") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise ExpressaoInvalidaError(f"Expressão excede o limite de {MAX_AST_NODES} nós AST.")

    usadas: set[str] = set()
    resultado = _eval_node(tree, ctx, usadas)
    return arredondar_interno(resultado), sorted(usadas)


def executar_avaliacao_expressao(payload: ExpressaoAvaliacaoRequest) -> ExpressaoAvaliacaoResponse:
    """Executa a avaliação de expressão para o endpoint REST de auditoria ADR001."""
    resultado, usadas = avaliar_expressao_tributaria(payload.expressao, payload.variaveis)
    return ExpressaoAvaliacaoResponse(
        expressao=payload.expressao.strip(),
        resultado_interno=str(resultado),
        resultado_monetario=formatar_moeda(resultado),
        variaveis_utilizadas=usadas,
    )
