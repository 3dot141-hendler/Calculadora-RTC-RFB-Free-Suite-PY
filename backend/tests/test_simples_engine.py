"""Testes unitários do motor puro do Simples Nacional (NT 2026.005 v1.00)."""

from decimal import Decimal
import pytest

from app.core.rounding import formatar_moeda
from app.modules.simples.engine import (
    DestinoValorSimples,
    EstadoItemSimples,
    InsumoCalculoSimples,
    RegimeApuracaoConfig,
    RegimeCalculoSimples,
    TipoReceitaBrutaConfig,
    calcular_item_simples,
)

REGIME_CRT_1 = RegimeApuracaoConfig(
    regime=RegimeCalculoSimples.CRT_1,
    gera_ibs=True,
    destino_devido=DestinoValorSimples.DEVIDO,
    destino_pendente_suspenso=DestinoValorSimples.PENDENTE_SUSPENSO,
)

REGIME_CRT_2 = RegimeApuracaoConfig(
    regime=RegimeCalculoSimples.CRT_2,
    gera_ibs=False,
    destino_devido=DestinoValorSimples.DEVIDO,
    destino_pendente_suspenso=DestinoValorSimples.PENDENTE_SUSPENSO,
)

REGIME_CRT_3 = RegimeApuracaoConfig(
    regime=RegimeCalculoSimples.CRT_3_TPREGIME_2,
    gera_ibs=True,
    destino_devido=DestinoValorSimples.PENDENTE_SUSPENSO,
    destino_pendente_suspenso=DestinoValorSimples.ZERO,
)

RECEITA_TRIBUTADA = TipoReceitaBrutaConfig(
    codigo=1,
    descricao="Receita tributada integralmente",
    compoe_receita=True,
    imposto_seletivo_compoe_receita=False,
    fator_receita=Decimal("1.0"),
    pendente_suspenso=False,
)

RECEITA_EXPORTACAO_INDIRETA = TipoReceitaBrutaConfig(
    codigo=4,
    descricao="Exportação indireta",
    compoe_receita=True,
    imposto_seletivo_compoe_receita=False,
    fator_receita=Decimal("1.0"),
    pendente_suspenso=True,
)


def test_item_nao_calculado_quando_cativ_invalido() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_1,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=False,
        base_calculo=Decimal("1000.00"),
        valor_imposto_seletivo=Decimal("50.00"),
    )
    res = calcular_item_simples(insumo)
    assert res.estado_item == EstadoItemSimples.NAO_CALCULADO
    assert res.trib_calc.v_rbsn_item == Decimal("1000.00")
    assert res.trib_calc.v_bc is None
    assert res.trib_calc.total_item is None


def test_crt1_calculo_padrao() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_1,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.50"),
        p_cbs_sn=Decimal("2.00"),
    )
    res = calcular_item_simples(insumo)
    assert res.estado_item == EstadoItemSimples.CALCULADO
    assert formatar_moeda(res.trib_calc.v_ibs_sn) == "15.00"
    assert formatar_moeda(res.trib_calc.v_cbs_sn) == "20.00"
    assert formatar_moeda(res.trib_calc.total_item) == "35.00"


def test_crt2_suprime_campos_ibs() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_2,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.50"),
        p_cbs_sn=Decimal("2.00"),
    )
    res = calcular_item_simples(insumo)
    assert res.trib_calc.p_ibs_sn is None
    assert res.trib_calc.v_ibs_sn is None
    assert res.trib_calc.v_ibs_pend_susp is None
    assert formatar_moeda(res.trib_calc.v_cbs_sn) == "20.00"
    assert formatar_moeda(res.trib_calc.total_item) == "20.00"


def test_compra_governamental_uniao_desloca_ibs_para_cbs() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_1,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.50"),
        p_cbs_sn=Decimal("2.00"),
        tp_ente_gov=1,
    )
    res = calcular_item_simples(insumo)
    assert res.trib_calc.p_ibs_sn == Decimal("0")
    assert res.trib_calc.p_cbs_sn == Decimal("3.50")
    assert formatar_moeda(res.trib_calc.v_ibs_sn) == "0.00"
    assert formatar_moeda(res.trib_calc.v_cbs_sn) == "35.00"


def test_compra_governamental_estadual_com_fator_transicao() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_1,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.00"),
        p_cbs_sn=Decimal("2.00"),
        tp_ente_gov=3,
        fator_transicao_compra_gov=Decimal("0.25"),
    )
    res = calcular_item_simples(insumo)
    assert res.trib_calc.p_ibs_sn == Decimal("1.50000000")
    assert res.trib_calc.p_cbs_sn == Decimal("1.50000000")


def test_compra_governamental_sem_fator_lanca_erro() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_1,
        tipo_receita_bruta=RECEITA_TRIBUTADA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.00"),
        p_cbs_sn=Decimal("2.00"),
        tp_ente_gov=2,
    )
    with pytest.raises(ValueError, match="Fator de transição"):
        calcular_item_simples(insumo)


def test_crt3_exportacao_indireta_zera_tributos() -> None:
    insumo = InsumoCalculoSimples(
        regime=REGIME_CRT_3,
        tipo_receita_bruta=RECEITA_EXPORTACAO_INDIRETA,
        c_ativ_sn_valido=True,
        base_calculo=Decimal("1000.00"),
        p_ibs_sn=Decimal("1.50"),
        p_cbs_sn=Decimal("2.00"),
    )
    res = calcular_item_simples(insumo)
    assert res.trib_calc.v_ibs_sn == Decimal("0")
    assert res.trib_calc.v_ibs_pend_susp == Decimal("0")
    assert res.trib_calc.v_cbs_sn == Decimal("0")
    assert res.trib_calc.v_cbs_pend_susp == Decimal("0")
    assert res.trib_calc.total_item == Decimal("0")
