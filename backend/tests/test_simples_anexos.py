"""Testes unitários para derivação de anexos e Fator R (port de DerivacaoAnexosSimples)."""

import pytest

from app.modules.simples.anexos import ModoFatorR, derivar_anexos_simples


def test_atividade_sem_anexo_sempre_disponivel() -> None:
    res = derivar_anexos_simples(None, None, set())
    assert res.disponivel is True
    assert res.anexos_faltantes == ()
    assert res.modo_fator_r == ModoFatorR.NAO_APLICAVEL


def test_atividade_com_fator_r_sem_anexo_base_lanca_erro() -> None:
    with pytest.raises(ValueError, match="Atividade inconsistente"):
        derivar_anexos_simples(None, "III")


def test_fator_r_opcional_quando_ambos_configurados() -> None:
    res = derivar_anexos_simples("V", "III", {"III", "V"})
    assert res.disponivel is True
    assert res.anexos_faltantes == ()
    assert res.modo_fator_r == ModoFatorR.OPCIONAL


def test_fator_r_obrigatorio_quando_apenas_anexo_com_fator_configurado() -> None:
    res = derivar_anexos_simples("V", "III", {"III"})
    assert res.disponivel is True
    assert res.anexos_faltantes == ("V",)
    assert res.modo_fator_r == ModoFatorR.OBRIGATORIO


def test_fator_r_indisponivel_quando_anexo_com_fator_nao_configurado() -> None:
    res = derivar_anexos_simples("V", "III", {"V"})
    assert res.disponivel is True
    assert res.anexos_faltantes == ("III",)
    assert res.modo_fator_r == ModoFatorR.INDISPONIVEL
