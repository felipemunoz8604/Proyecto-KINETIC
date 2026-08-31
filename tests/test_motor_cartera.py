"""
Pruebas del motor de cartera.

Las cuatro que sostienen todo lo demas:

1. `test_el_futuro_no_cambia_el_pasado` -- la prueba de causalidad del motor.
2. `test_exposicion_uno_replica_comprar_y_mantener` -- ancla el motor contra
   un calculo que se puede hacer a mano.
3. `test_el_costo_total_es_exactamente_lo_cobrado` -- si el ledger no cierra,
   el criterio 6 mide cualquier cosa.
4. `test_pedir_apalancamiento_levanta` -- k_max = 1,0 tambien se defiende acá.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtesting import motor_cartera as mc  # noqa: E402
from execution.costos import ModeloDeCostos  # noqa: E402
from execution.filtros import FiltroSimbolo, TablaDeFiltros  # noqa: E402

MODELO = ModeloDeCostos()          # Spot, taker, sin BNB
SIN_FRICCION = ModeloDeCostos(con_bnb=False)


def _dias(n: int, desde: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _mercado(precios: np.ndarray, simbolo: str = "AUSDT"):
    """Un mercado sin hueco: la apertura de hoy es el cierre de ayer."""
    idx = _dias(len(precios))
    cierres = pd.DataFrame({simbolo: precios}, index=idx)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = precios[0]
    return aperturas, cierres, idx


def test_sin_exposicion_el_patrimonio_no_se_mueve():
    aperturas, cierres, idx = _mercado(np.linspace(100, 300, 50))
    exp = pd.DataFrame(0.0, index=idx, columns=["AUSDT"])
    r = mc.simular(aperturas, cierres, exp, 500.0, MODELO)
    assert (r.patrimonio == 500.0).all()
    assert r.costo_total == 0.0


def test_exposicion_uno_replica_comprar_y_mantener():
    """
    Con exposicion 1 todo el tiempo, el patrimonio tiene que seguir al precio,
    descontado el costo de entrada. Es el ancla contra un calculo a mano.
    """
    precios = np.array([100.0] * 3 + [200.0] * 3)
    aperturas, cierres, idx = _mercado(precios)
    exp = pd.DataFrame(1.0, index=idx, columns=["AUSDT"])
    r = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                   rangos={"AUSDT": 1})

    peaje = MODELO.peaje_por_lado_pct(1) / 100.0
    # 1/(1+p) y no (1-p): el peaje se paga con efectivo, asi que se compra
    # un poquito menos de lo que el patrimonio permitiria en bruto.
    esperado_dia0 = 1_000.0 / (1 + peaje)
    assert r.patrimonio.iloc[0] == pytest.approx(esperado_dia0, rel=1e-6)
    # El precio se duplica: el patrimonio tambien, salvo el peaje ya pagado.
    assert r.patrimonio.iloc[-1] == pytest.approx(2 * esperado_dia0, rel=1e-3)


def test_el_futuro_no_cambia_el_pasado():
    """
    Cortar la serie a la mitad tiene que dar exactamente el mismo patrimonio
    en esa primera mitad. Si no, el motor esta mirando adelante.
    """
    rng = np.random.default_rng(20260830)
    precios = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 300)))
    aperturas, cierres, idx = _mercado(precios)
    exp = pd.DataFrame(0.7, index=idx, columns=["AUSDT"])

    entera = mc.simular(aperturas, cierres, exp, 500.0, MODELO)
    mitad = mc.simular(aperturas.iloc[:150], cierres.iloc[:150],
                       exp.iloc[:150], 500.0, MODELO)
    pd.testing.assert_series_equal(entera.patrimonio.iloc[:150],
                                   mitad.patrimonio)


def test_el_costo_total_es_exactamente_lo_cobrado():
    """
    Nocional movido x peaje = costo pagado. Si el ledger no cierra, el
    criterio 6 ("el costo no se come el resultado") mide cualquier cosa.
    """
    rng = np.random.default_rng(4)
    precios = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 120)))
    aperturas, cierres, idx = _mercado(precios)
    exp = pd.DataFrame(rng.uniform(0.2, 0.9, 120), index=idx,
                       columns=["AUSDT"])
    r = mc.simular(aperturas, cierres, exp, 10_000.0, MODELO,
                   rangos={"AUSDT": 6})

    peaje = MODELO.peaje_por_lado_pct(6) / 100.0
    assert r.costo_total == pytest.approx(r.negociado.sum() * peaje, rel=1e-9)
    assert r.costo_total > 0


def test_pedir_apalancamiento_levanta():
    aperturas, cierres, idx = _mercado(np.full(10, 100.0))
    exp = pd.DataFrame({"AUSDT": 0.7, "BUSDT": 0.7}, index=idx)
    aperturas["BUSDT"] = 100.0
    cierres["BUSDT"] = 100.0
    with pytest.raises(ValueError, match="apalancamiento"):
        mc.simular(aperturas, cierres, exp, 500.0, MODELO)


def test_el_nocional_minimo_frena_las_ordenes_chicas():
    """
    Con 500 USDT, un ajuste de exposicion del 0,5% son 2,50 USDT: por debajo
    del minimo de 5. Binance lo rechaza y el motor tambien.

    Esto crea una banda de no-operar sin que nadie la haya inventado: es el
    minimo del intercambio haciendo de amortiguador.
    """
    aperturas, cierres, idx = _mercado(np.full(40, 100.0))
    objetivo = np.full(40, 0.50)
    objetivo[20:] = 0.505          # un ajuste de 2,50 USDT sobre 500
    exp = pd.DataFrame(objetivo, index=idx, columns=["AUSDT"])
    filtros = TablaDeFiltros({"AUSDT": FiltroSimbolo(
        paso_cantidad=0.001, cantidad_minima=0.001, nocional_minimo=5.0)})
    r = mc.simular(aperturas, cierres, exp, 500.0, MODELO, filtros=filtros)
    # Solo se ejecuta la compra inicial; el ajuste de 2,50 USDT no pasa.
    assert (r.negociado > 0).sum() == 1
    assert r.ordenes_rechazadas > 0


def test_un_deslistado_se_liquida_con_penalizacion():
    idx = _dias(20)
    precios = np.full(20, 100.0)
    precios[10:] = np.nan
    cierres = pd.DataFrame({"AUSDT": precios}, index=idx)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = 100.0
    exp = pd.DataFrame(1.0, index=idx, columns=["AUSDT"])

    r = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                   rangos={"AUSDT": 1}, penalizacion_deslistado_pct=20.0)
    assert len(r.deslistados) == 1
    # Quedo ~80% del valor, menos peajes. Y despues no se mueve mas.
    assert 780 < r.patrimonio.iloc[-1] < 800
    assert r.patrimonio.iloc[-1] == pytest.approx(r.patrimonio.iloc[-2])


def test_un_muerto_no_se_vuelve_a_comprar():
    """
    Regresion de un error real: si un simbolo tiene apertura pero ya no tiene
    cierre, el motor lo recompraba a la apertura y lo reliquidaba al dia
    siguiente, pagando la penalizacion por deslistado UNA VEZ POR DIA hasta el
    final de la serie.

    La regla que lo evita: no se compra lo que no se va a poder valuar al
    cierre de hoy.
    """
    idx = _dias(30)
    cierres = pd.DataFrame({"AUSDT": [100.0] * 10 + [np.nan] * 20}, index=idx)
    aperturas = pd.DataFrame({"AUSDT": 100.0}, index=idx)   # apertura siempre
    exp = pd.DataFrame(1.0, index=idx, columns=["AUSDT"])

    r = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                   rangos={"AUSDT": 1}, penalizacion_deslistado_pct=20.0)
    assert len(r.deslistados) == 1


def test_sin_penalizacion_el_deslistado_recupera_casi_todo():
    """La sensibilidad de la especificacion: el numero cambia el resultado."""
    idx = _dias(20)
    precios = np.full(20, 100.0)
    precios[10:] = np.nan
    cierres = pd.DataFrame({"AUSDT": precios}, index=idx)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = 100.0
    exp = pd.DataFrame(1.0, index=idx, columns=["AUSDT"])

    suave = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                       rangos={"AUSDT": 1}, penalizacion_deslistado_pct=0.0)
    duro = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                      rangos={"AUSDT": 1}, penalizacion_deslistado_pct=50.0)
    assert suave.patrimonio.iloc[-1] > duro.patrimonio.iloc[-1] * 1.9


def test_no_se_puede_vender_mas_de_lo_que_se_tiene():
    aperturas, cierres, idx = _mercado(np.full(10, 100.0))
    exp = pd.DataFrame(0.0, index=idx, columns=["AUSDT"])
    exp.iloc[3:6] = 0.5
    r = mc.simular(aperturas, cierres, exp, 500.0, MODELO)
    assert (r.efectivo >= -1e-9).all()
    assert (r.exposicion["AUSDT"] >= -1e-9).all()


def test_el_rango_por_defecto_es_el_peor():
    """Suponer que todo es tan liquido como BTC seria regalarse el slippage."""
    aperturas, cierres, idx = _mercado(np.full(5, 100.0))
    exp = pd.DataFrame(1.0, index=idx, columns=["AUSDT"])
    barato = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO,
                        rangos={"AUSDT": 1})
    caro = mc.simular(aperturas, cierres, exp, 1_000.0, MODELO)
    assert caro.costo_total > barato.costo_total


def test_la_rotacion_y_el_costo_anual_se_calculan_sobre_el_patrimonio_medio():
    aperturas, cierres, idx = _mercado(np.full(730, 100.0))
    exp = pd.DataFrame(0.0, index=idx, columns=["AUSDT"])
    exp.iloc[::2] = 1.0              # entra y sale dia por medio
    r = mc.simular(aperturas, cierres, exp, 10_000.0, MODELO,
                   rangos={"AUSDT": 1})
    assert r.rotacion_anual > 100     # muchisimas vueltas al año
    assert r.costo_anual_pct > 0
    assert 40 < r.tiempo_en_mercado_pct < 60


def test_las_exposiciones_desordenadas_levantan():
    aperturas, cierres, idx = _mercado(np.full(5, 100.0))
    exp = pd.DataFrame(1.0, index=idx[::-1], columns=["AUSDT"])
    with pytest.raises(ValueError):
        mc.simular(aperturas, cierres, exp, 500.0, MODELO)
