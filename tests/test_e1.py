"""
Pruebas de E1.

Las cuatro que sostienen el resto:

1. `test_el_sigma_vectorizado_coincide_con_el_de_risk` -- E1 recalcula la
   volatilidad de forma vectorizada por velocidad; si se desvia del camino de
   `risk/`, E0 y E1 dejarian de ser comparables sin que nada avise.
2. `test_el_puntaje_saltea_el_ultimo_dia` -- el salto es la mitad de la
   hipotesis, y es invisible si esta mal.
3. `test_agregar_datos_del_futuro_no_cambia_el_pasado` -- causalidad.
4. `test_el_peso_del_que_salio_por_stop_no_se_reparte` -- repartirlo mejora el
   resultado y es exactamente lo que no hay que hacer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk import pesos as pz  # noqa: E402
from strategy import e1  # noqa: E402


def _dias(n: int, desde: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _panel(n: int, semillas: dict[str, int], sigma: float = 0.03
           ) -> pd.DataFrame:
    idx = _dias(n)
    datos = {}
    for nombre, semilla in semillas.items():
        rng = np.random.default_rng(semilla)
        datos[nombre] = 100 * np.exp(np.cumsum(rng.normal(0.001, sigma, n)))
    return pd.DataFrame(datos, index=idx)


# --- Volatilidad y puntaje ------------------------------------------------

def test_el_sigma_vectorizado_coincide_con_el_de_risk():
    """
    El camino rapido de E1 contra el de a un dia de `risk/`. Si se separan,
    E0 y E1 dejan de estar midiendo la misma volatilidad.
    """
    cierres = _panel(300, {"AUSDT": 1, "BUSDT": 2, "CUSDT": 3})
    rapido = e1.sigmas_diarias(cierres)
    for fecha in cierres.index[100::37]:
        lento = pz.volatilidad_anualizada(cierres, fecha,
                                          list(cierres.columns))
        for s in lento.index:
            assert rapido.at[fecha, s] == pytest.approx(lento[s], rel=1e-12)


def test_el_puntaje_saltea_el_ultimo_dia():
    """
    Con ventana 28 y salto 1, el retorno va de t-30 a t-2. El dia t-1 NO
    entra: se saltea para esquivar la reversion de muy corto plazo.
    """
    idx = _dias(40)
    # Precio plano salvo un salto enorme justo en t-1: si el puntaje lo
    # tomara, se notaria; como lo saltea, no cambia nada.
    base = np.full(40, 100.0)
    con_salto = base.copy()
    con_salto[38] = 1000.0        # t-1 respecto de la fila 39

    sigmas = pd.DataFrame(0.5, index=idx, columns=["AUSDT"])
    p_sin = e1.puntajes(pd.DataFrame({"AUSDT": base}, index=idx), sigmas)
    p_con = e1.puntajes(pd.DataFrame({"AUSDT": con_salto}, index=idx), sigmas)
    assert p_sin.iloc[39]["AUSDT"] == pytest.approx(p_con.iloc[39]["AUSDT"])


def test_el_puntaje_es_adimensional():
    """
    Multiplicar todos los precios por diez no puede cambiar el puntaje: es un
    retorno sobre una volatilidad, y los dos son relativos.
    """
    cierres = _panel(200, {"AUSDT": 5})
    s1 = e1.puntajes(cierres, e1.sigmas_diarias(cierres))
    s2 = e1.puntajes(cierres * 10, e1.sigmas_diarias(cierres * 10))
    pd.testing.assert_frame_equal(s1, s2)


def test_a_igual_retorno_gana_el_menos_volatil():
    """El puntaje divide por sigma: eso es todo lo que hace la division."""
    fila = pd.Series({"QUIETO": 2.0, "LOCO": 0.5})
    assert e1.seleccionar(fila, ["QUIETO", "LOCO"], 1) == ["QUIETO"]


# --- Seleccion ------------------------------------------------------------

def test_se_eligen_los_cinco_mejores():
    fila = pd.Series({f"S{i}": float(i) for i in range(10)})
    elegidos = e1.seleccionar(fila, list(fila.index), 5)
    assert elegidos == ["S9", "S8", "S7", "S6", "S5"]


def test_los_puntajes_negativos_no_entran_aunque_falten_posiciones():
    """
    Completar con los "menos malos" seria comprar momentum negativo, o sea
    hacer lo contrario de lo que dice la hipotesis.
    """
    fila = pd.Series({"A": 1.5, "B": 0.3, "C": -0.2, "D": -5.0})
    assert e1.seleccionar(fila, list(fila.index), 5) == ["A", "B"]


def test_si_nada_es_positivo_no_se_compra_nada():
    fila = pd.Series({"A": -0.1, "B": -2.0})
    assert e1.seleccionar(fila, list(fila.index), 5) == []


def test_solo_se_elige_dentro_del_universo():
    """Un simbolo con puntaje altisimo pero fuera del top-20 no entra."""
    fila = pd.Series({"DENTRO": 1.0, "AFUERA": 99.0})
    assert e1.seleccionar(fila, ["DENTRO"], 5) == ["DENTRO"]


# --- Armado completo ------------------------------------------------------

def _escenario(n: int = 400, sigma: float = 0.03):
    cierres = _panel(n, {f"S{i}USDT": i for i in range(1, 9)}, sigma)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = cierres.iloc[0]
    atr = pd.DataFrame(0.05, index=cierres.index, columns=cierres.columns)
    compuerta = pd.Series(1, index=cierres.index)
    universo = {cierres.index[i]: list(cierres.columns)
                for i in range(60, n, 30)}
    return cierres, aperturas, atr, compuerta, universo


def test_la_exposicion_bruta_nunca_pasa_de_uno():
    cierres, aperturas, atr, g, universo = _escenario()
    a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                  cierres.index)
    assert a.exposiciones.sum(axis=1).max() <= pz.K_MAX + 1e-9


def test_nunca_hay_mas_de_cinco_posiciones():
    cierres, aperturas, atr, g, universo = _escenario()
    a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                  cierres.index)
    assert (a.exposiciones > 0).sum(axis=1).max() <= e1.CUANTAS_POSICIONES


def test_con_la_compuerta_cerrada_no_hay_nada():
    cierres, aperturas, atr, _, universo = _escenario()
    cerrada = pd.Series(0, index=cierres.index)
    a = e1.construir_exposiciones(cierres, aperturas, atr, cerrada, universo,
                                  cierres.index)
    assert (a.exposiciones.sum(axis=1) == 0).all()


def test_agregar_datos_del_futuro_no_cambia_el_pasado():
    cierres, aperturas, atr, g, universo = _escenario(500)
    corte = 300
    entero = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                       cierres.index)
    universo_corto = {f: v for f, v in universo.items()
                      if f < cierres.index[corte]}
    parcial = e1.construir_exposiciones(
        cierres.iloc[:corte], aperturas.iloc[:corte], atr.iloc[:corte],
        g.iloc[:corte], universo_corto, cierres.index[:corte])
    pd.testing.assert_frame_equal(
        entero.exposiciones.iloc[:corte][parcial.exposiciones.columns],
        parcial.exposiciones)


def test_el_stop_saca_la_posicion_y_no_la_devuelve_hasta_el_mes_siguiente():
    """
    Un derrumbe de una sola moneda: sale, y no vuelve aunque el puntaje la
    siga favoreciendo, hasta el proximo rebalanceo.
    """
    idx = _dias(200)
    cierres = pd.DataFrame({
        "BUENAUSDT": np.linspace(100, 200, 200),
        "MALAUSDT": np.concatenate([np.linspace(100, 200, 120),
                                    np.linspace(200, 20, 80)]),
    }, index=idx)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = cierres.iloc[0]
    atr = pd.DataFrame(0.02, index=idx, columns=cierres.columns)
    g = pd.Series(1, index=idx)
    universo = {idx[60]: list(cierres.columns), idx[180]: list(cierres.columns)}

    a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo, idx)
    assert len(a.stops_disparados) >= 1
    salto = a.stops_disparados[0]["fecha"]
    # Entre el disparo y el rebalanceo siguiente no vuelve a tener peso.
    entre = a.exposiciones.loc[(a.exposiciones.index >= salto)
                               & (a.exposiciones.index < idx[180]), "MALAUSDT"]
    assert (entre == 0).all()


def test_el_peso_del_que_salio_por_stop_no_se_reparte():
    """
    "El resto de la cartera no se toca": el peso liberado se va a efectivo.
    Repartirlo seria aumentar la exposicion justo despues de un derrumbe.
    """
    idx = _dias(200)
    cierres = pd.DataFrame({
        "AUSDT": np.linspace(100, 160, 200),
        "BUSDT": np.linspace(100, 150, 200),
        "MALAUSDT": np.concatenate([np.linspace(100, 200, 120),
                                    np.linspace(200, 20, 80)]),
    }, index=idx)
    aperturas = cierres.shift(1)
    aperturas.iloc[0] = cierres.iloc[0]
    atr = pd.DataFrame(0.02, index=idx, columns=cierres.columns)
    g = pd.Series(1, index=idx)
    universo = {idx[60]: list(cierres.columns)}

    a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo, idx)
    assert a.stops_disparados
    salto = a.stops_disparados[0]["fecha"]
    i = a.exposiciones.index.get_loc(salto)
    antes = a.exposiciones.iloc[i - 1]
    despues = a.exposiciones.iloc[i]
    assert despues["MALAUSDT"] == 0.0
    # Los que quedan no reciben nada: la bruta baja.
    assert despues.sum() < antes.sum()


def test_los_rangos_de_liquidez_siguen_el_orden_del_universo():
    idx = _dias(60)
    universo = {idx[0]: ["BTCUSDT", "ETHUSDT", "XRPUSDT"]}
    r = e1.rangos_de_liquidez(universo, idx)
    assert r.iloc[-1]["BTCUSDT"] == 1
    assert r.iloc[-1]["ETHUSDT"] == 2
    assert r.iloc[-1]["XRPUSDT"] == 3


def test_los_rangos_cambian_cuando_cambia_el_universo():
    idx = _dias(60)
    universo = {idx[0]: ["AUSDT", "BUSDT"], idx[30]: ["BUSDT", "AUSDT"]}
    r = e1.rangos_de_liquidez(universo, idx)
    assert r.iloc[10]["AUSDT"] == 1
    assert r.iloc[40]["AUSDT"] == 2


# --- Las dos hipotesis de rescate preautorizadas (R1 y R2) ----------------

def test_la_ventana_de_momentum_es_un_parametro():
    """
    R1 cambia la ventana de 28 a 90 dias. Tiene que entrar por parametro y no
    por edicion del codigo: si hay que tocar el modulo para correrla, la
    corrida siguiente ya no mide lo mismo que la anterior.
    """
    cierres, aperturas, atr, g, universo = _escenario(500)
    corta = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                      cierres.index, dias_momentum=28)
    larga = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                      cierres.index, dias_momentum=90)
    assert not corta.exposiciones.equals(larga.exposiciones)


def test_con_ocho_posiciones_hay_hasta_ocho():
    """R2: ocho posiciones en vez de cinco."""
    cierres, aperturas, atr, g, universo = _escenario()
    a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                  cierres.index, cuantas=8)
    assert (a.exposiciones > 0).sum(axis=1).max() <= 8
    assert (a.exposiciones > 0).sum(axis=1).max() > e1.CUANTAS_POSICIONES


def test_los_rescates_no_pueden_apalancar():
    """Ni R1 ni R2 aflojan el tope de bruta: sigue siendo k_max = 1,0."""
    cierres, aperturas, atr, g, universo = _escenario()
    for kwargs in ({"dias_momentum": 90}, {"cuantas": 8}):
        a = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                      cierres.index, **kwargs)
        assert a.exposiciones.sum(axis=1).max() <= pz.K_MAX + 1e-9
