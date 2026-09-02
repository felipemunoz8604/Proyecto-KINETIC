"""
Pruebas de C-A (captura) y C-B (proteccion).

Las tres que sostienen el resto:

1. `test_la_clasificacion_no_usa_el_mes_que_clasifica` -- sin ese rezago, un
   mes malo se clasificaria como bajista usando su propio resultado, y la
   proteccion daria perfecta siempre.
2. `test_el_benchmark_contra_si_mismo_da_uno_exacto` -- el invariante que fija
   la escala de las dos metricas.
3. `test_no_se_pierde_el_tramo_inicial` -- el mismo error que costo una prueba
   roja en la curva de retiro top-k.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import regimen  # noqa: E402


def _dias(n: int, desde: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _curva(retornos_diarios: np.ndarray, desde: str = "2019-01-01"
           ) -> pd.Series:
    return pd.Series(1000 * np.cumprod(1.0 + retornos_diarios),
                     index=_dias(len(retornos_diarios), desde))


# --- Clasificacion de regimen ---------------------------------------------

def test_una_serie_que_sube_siempre_da_meses_alcistas():
    precios = pd.Series(np.linspace(100, 500, 900), index=_dias(900))
    marca = regimen.clasificar_meses(precios)
    assert marca.sum() > 0
    assert marca.iloc[-1]


def test_una_serie_que_baja_siempre_da_meses_bajistas():
    precios = pd.Series(np.linspace(500, 100, 900), index=_dias(900))
    marca = regimen.clasificar_meses(precios)
    assert not marca.any()


def test_la_clasificacion_no_usa_el_mes_que_clasifica():
    """
    El rezago es lo que impide que un mes se clasifique con su propio
    resultado. Sin el, la proteccion daria perfecta siempre: se estaria
    marcando como bajista justo lo que ya se sabe que salio mal.
    """
    # Sube 18 meses y despues se derrumba de golpe.
    valores = np.concatenate([np.linspace(100, 300, 550),
                              np.linspace(300, 60, 60)])
    precios = pd.Series(valores, index=_dias(len(valores)))
    marca = regimen.clasificar_meses(precios)
    # El mes del derrumbe todavia se clasifica alcista: los 12 meses PREVIOS
    # venian subiendo. Recien despues cambia.
    mes_del_derrumbe = precios.index[555].to_period("M")
    assert marca.loc[mes_del_derrumbe]


def test_agregar_datos_del_futuro_no_cambia_la_clasificacion():
    rng = np.random.default_rng(20260901)
    precios = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, 1200))),
                        index=_dias(1200))
    entera = regimen.clasificar_meses(precios)
    cortada = regimen.clasificar_meses(precios.iloc[:800])
    comunes = entera.index.intersection(cortada.index)
    pd.testing.assert_series_equal(entera.loc[comunes], cortada.loc[comunes])


# --- Captura y proteccion --------------------------------------------------

def _escenario(n: int = 1200, semilla: int = 7):
    rng = np.random.default_rng(semilla)
    btc = 100 * np.exp(np.cumsum(rng.normal(0.0015, 0.03, n)))
    precios = pd.Series(btc, index=_dias(n))
    b1 = pd.Series(1000 * btc / btc[0], index=_dias(n))
    return precios, b1


def test_el_benchmark_contra_si_mismo_da_uno_exacto():
    """
    El invariante que fija la escala: si la estrategia ES el benchmark,
    captura y proteccion valen 1,000 exacto. Si esto se corre, las dos
    metricas estan midiendo cosas distintas de lo que dicen.
    """
    precios, b1 = _escenario()
    marca = regimen.clasificar_meses(precios)
    p = regimen.puntuar(b1, b1, marca, "B1")
    assert p.captura == pytest.approx(1.0)
    assert p.proteccion == pytest.approx(1.0)


def test_media_exposicion_captura_menos_y_protege_mas():
    """
    Media posicion en BTC y el resto quieto: captura ~la mitad de la subida y
    cae ~la mitad. Es el caso que la descomposicion dice que NO puede mover el
    cociente, y sirve de ancla.
    """
    precios, b1 = _escenario()
    diarios = b1.pct_change().fillna(0.0)
    mitad = pd.Series(1000 * np.cumprod(1.0 + 0.5 * diarios.to_numpy()),
                      index=b1.index)
    marca = regimen.clasificar_meses(precios)
    p = regimen.puntuar(mitad, b1, marca, "mitad")
    assert 0.3 < p.captura < 0.8
    assert 0.3 < p.proteccion < 0.8


def test_estar_afuera_en_los_bajistas_protege_del_todo():
    """El caso ideal: cero exposicion en meses bajistas, caida cero."""
    precios, b1 = _escenario()
    marca = regimen.clasificar_meses(precios)
    diarios = b1.pct_change().fillna(0.0)
    por_mes = pd.Series(b1.index.to_period("M"), index=b1.index)
    dentro = por_mes.map(marca).fillna(False).astype(bool)
    filtrados = diarios.where(dentro, 0.0)
    perfecta = pd.Series(1000 * np.cumprod(1.0 + filtrados.to_numpy()),
                         index=b1.index)
    p = regimen.puntuar(perfecta, b1, marca, "perfecta")
    assert p.proteccion == pytest.approx(0.0, abs=1e-9)
    assert p.captura > 0.9


def test_no_se_pierde_el_tramo_inicial():
    """
    `resample("ME").last().pct_change()` descarta el primer valor y con el se
    pierde el tramo del inicio al primer fin de mes. Es el mismo error que ya
    costo una prueba roja en la curva de retiro top-k.
    """
    # Sube fuerte en enero y despues queda plano: si el tramo inicial se
    # perdiera, el retorno acumulado daria cero.
    diarios = np.concatenate([np.full(20, 0.02), np.zeros(400)])
    curva = _curva(diarios)
    mensual = regimen._mensual(curva)
    total = float(np.prod(1.0 + mensual.to_numpy()) - 1.0)
    assert total == pytest.approx(curva.iloc[-1] / curva.iloc[0] - 1.0,
                                  rel=1e-9)


def test_se_reporta_tambien_el_peor_tramo_contiguo():
    """
    Encadenar meses bajistas no contiguos arma una curva que nunca existio.
    El control es el peor tramo contiguo, que si es real: si los dos dieran
    veredictos distintos, el criterio dependeria de esa eleccion.
    """
    precios, b1 = _escenario()
    marca = regimen.clasificar_meses(precios)
    diarios = b1.pct_change().fillna(0.0)
    mitad = pd.Series(1000 * np.cumprod(1.0 + 0.5 * diarios.to_numpy()),
                      index=b1.index)
    p = regimen.puntuar(mitad, b1, marca, "mitad")
    assert p.caida_bajista_peor_tramo <= 0
    assert np.isfinite(p.proteccion_por_tramo)


def test_el_intervalo_de_captura_contiene_uno_si_es_el_benchmark():
    precios, b1 = _escenario()
    marca = regimen.clasificar_meses(precios)
    bajo, alto = regimen.intervalo_de_captura(b1, b1, marca)
    assert bajo <= 1.0 <= alto
