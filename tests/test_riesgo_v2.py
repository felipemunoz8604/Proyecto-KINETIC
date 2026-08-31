"""
Pruebas de Riesgo v2: pesos, escalar de volatilidad, stop y cortacircuito.

Las cuatro que valen mas que el resto:

1. `test_pedir_apalancamiento_levanta` -- k_max > 1 es un cerrojo del
   MEGAPROMPT, no un default que se pisa pasando otro numero.
2. `test_el_tope_se_respeta_aunque_haga_falta_repartir_dos_veces` -- recortar
   y renormalizar de una pasada deja el tope violado en silencio.
3. `test_la_cartera_es_menos_volatil_que_sus_partes` -- si sigma_cartera
   fuera el promedio ponderado, `k` bajaria de mas para siempre.
4. `test_el_peso_liberado_por_un_stop_no_se_reparte` -- repartirlo mejora el
   resultado y es exactamente lo que no hay que hacer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk import catastrofe as cat  # noqa: E402
from risk import pesos as pz  # noqa: E402


def _dias(n: int, desde: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _serie_con_volatilidad(sigma_diaria: float, n: int, semilla: int
                           ) -> np.ndarray:
    rng = np.random.default_rng(semilla)
    return 100 * np.exp(np.cumsum(rng.normal(0, sigma_diaria, n)))


# --- Pesos por inversa de volatilidad -------------------------------------

def test_el_que_menos_se_mueve_pesa_mas():
    sigmas = pd.Series({"QUIETO": 0.20, "MEDIO": 0.40, "LOCO": 0.80})
    w = pz.pesos_inversa_volatilidad(sigmas)
    assert w["QUIETO"] > w["MEDIO"] > w["LOCO"]
    assert w.sum() == pytest.approx(1.0)


def test_dos_activos_con_la_misma_volatilidad_pesan_igual():
    sigmas = pd.Series({"A": 0.5, "B": 0.5, "C": 0.5, "D": 0.5})
    w = pz.pesos_inversa_volatilidad(sigmas)
    assert w.std() == pytest.approx(0.0, abs=1e-12)


def test_el_tope_del_cuarenta_por_ciento_se_respeta():
    sigmas = pd.Series({"A": 0.01, "B": 1.0, "C": 1.0})   # A dominaria todo
    w = pz.pesos_inversa_volatilidad(sigmas)
    assert w.max() <= pz.TOPE_POR_ACTIVO + 1e-9
    assert w.sum() == pytest.approx(1.0)


def test_el_tope_se_respeta_aunque_haga_falta_repartir_dos_veces():
    """
    Recortar al tope y renormalizar de UNA pasada no alcanza: el que recibe el
    excedente puede pasarse del tope y quedar violado sin que nada avise.
    """
    sigmas = pd.Series({"A": 0.01, "B": 0.02, "C": 1.0, "D": 1.0})
    w = pz.pesos_inversa_volatilidad(sigmas)
    assert w.max() <= pz.TOPE_POR_ACTIVO + 1e-9
    assert w.sum() == pytest.approx(1.0)
    assert (w > 0).all()


def test_con_dos_activos_el_tope_es_imposible_y_se_reparte_parejo():
    """
    Dos activos al 40% suman 0,80, no 1. No hay reparto que cumpla el tope, y
    lo mas cerca que se puede estar es mitad y mitad.
    """
    w = pz.pesos_inversa_volatilidad(pd.Series({"A": 0.2, "B": 0.9}))
    assert w.sum() == pytest.approx(1.0)
    assert w["A"] == pytest.approx(0.5)
    assert w["B"] == pytest.approx(0.5)


def test_sin_sigmas_validas_no_hay_pesos():
    assert pz.pesos_inversa_volatilidad(pd.Series({"A": 0.0})).empty


# --- Volatilidad ----------------------------------------------------------

def test_la_volatilidad_solo_mira_el_pasado():
    """
    Romper el futuro despues de la fecha no puede cambiar el sigma de hoy.
    Es la misma prueba que protege al universo y a los indicadores.
    """
    idx = _dias(200)
    cierres = pd.DataFrame({"A": _serie_con_volatilidad(0.02, 200, 1),
                            "B": _serie_con_volatilidad(0.04, 200, 2)},
                           index=idx)
    fecha = idx[150]
    original = pz.volatilidad_anualizada(cierres, fecha, ["A", "B"])

    roto = cierres.copy()
    roto.loc[roto.index >= fecha] *= 10.0
    despues = pz.volatilidad_anualizada(roto, fecha, ["A", "B"])
    pd.testing.assert_series_equal(original, despues)


def test_la_volatilidad_anualizada_usa_365_y_no_252():
    """Cripto opera los domingos. Anualizar con 252 la subestima un 12%."""
    idx = _dias(100)
    sigma_diaria = 0.02
    rng = np.random.default_rng(3)
    serie = 100 * np.exp(np.cumsum(rng.normal(0, sigma_diaria, 100)))
    cierres = pd.DataFrame({"A": serie}, index=idx)
    sigma = pz.volatilidad_anualizada(cierres, idx[-1], ["A"])["A"]
    # Con 30 dias de muestra hay ruido, pero el factor tiene que ser sqrt(365).
    assert sigma == pytest.approx(sigma_diaria * np.sqrt(365), rel=0.45)


def test_la_cartera_es_menos_volatil_que_sus_partes():
    """
    Con correlacion menor que 1, sigma_cartera < promedio ponderado de los
    sigmas. Esa diferencia es la diversificacion, y la medicion 5.2 mostro que
    en este universo existe (correlacion media 0,59).

    Si alguien calculara sigma_cartera como promedio ponderado, `k` bajaria de
    mas todos los dias y la cartera quedaria cronicamente chica.
    """
    idx = _dias(200)
    cierres = pd.DataFrame(
        {f"S{i}": _serie_con_volatilidad(0.03, 200, i) for i in range(6)},
        index=idx)
    fecha = idx[-1]
    simbolos = list(cierres.columns)
    sigmas = pz.volatilidad_anualizada(cierres, fecha, simbolos)
    w = pz.pesos_inversa_volatilidad(sigmas)
    sigma_p = pz.volatilidad_de_cartera(cierres, fecha, w)
    assert sigma_p < float((sigmas * w).sum())


def test_activos_identicos_no_diversifican_nada():
    """El caso limite: correlacion 1, sigma_cartera = sigma individual."""
    idx = _dias(200)
    base = _serie_con_volatilidad(0.03, 200, 42)
    cierres = pd.DataFrame({"A": base, "B": base * 7}, index=idx)
    fecha = idx[-1]
    sigmas = pz.volatilidad_anualizada(cierres, fecha, ["A", "B"])
    w = pz.pesos_inversa_volatilidad(sigmas)
    sigma_p = pz.volatilidad_de_cartera(cierres, fecha, w)
    assert sigma_p == pytest.approx(float(sigmas.mean()), rel=1e-6)


# --- Escalar de volatilidad -----------------------------------------------

def test_pedir_apalancamiento_levanta():
    """
    MEGAPROMPT v2.0, regla 7. Los perpetuos entraron para la pata corta y
    para bajar comisiones, no para apalancar. Es un cerrojo, no un default.
    """
    with pytest.raises(pz.SinApalancamiento):
        pz.escalar_de_volatilidad(0.10, k_max=1.5)


def test_una_cartera_tranquila_no_pasa_de_uno():
    """Aunque el objetivo permita mas, k se corta en 1,0."""
    assert pz.escalar_de_volatilidad(0.05) == pytest.approx(1.0)


def test_una_cartera_agitada_reduce_la_exposicion():
    k = pz.escalar_de_volatilidad(0.70)   # el doble del objetivo
    assert k == pytest.approx(0.5)


def test_sin_poder_medir_el_riesgo_no_se_toma():
    assert pz.escalar_de_volatilidad(float("nan")) == 0.0
    assert pz.escalar_de_volatilidad(0.0) == 0.0


# --- La formula completa --------------------------------------------------

def test_con_la_compuerta_cerrada_no_hay_ninguna_posicion():
    idx = _dias(200)
    cierres = pd.DataFrame(
        {f"S{i}": _serie_con_volatilidad(0.03, 200, i) for i in range(5)},
        index=idx)
    e = pz.exposiciones(cierres, idx[-1], list(cierres.columns), compuerta=0)
    assert (e == 0).all()


def test_la_exposicion_bruta_nunca_pasa_de_uno():
    """Sin apalancamiento. Es la consecuencia visible de k_max = 1,0."""
    idx = _dias(300)
    for semilla in range(8):
        cierres = pd.DataFrame(
            {f"S{i}": _serie_con_volatilidad(0.005 * (semilla + 1), 300, i)
             for i in range(6)}, index=idx)
        e = pz.exposiciones(cierres, idx[-1], list(cierres.columns),
                            compuerta=1)
        assert e.sum() <= 1.0 + 1e-9, f"semilla {semilla}: bruta {e.sum()}"


def test_un_simbolo_sin_datos_recibe_cero_y_no_rompe():
    idx = _dias(200)
    cierres = pd.DataFrame(
        {f"S{i}": _serie_con_volatilidad(0.03, 200, i) for i in range(4)},
        index=idx)
    e = pz.exposiciones(cierres, idx[-1],
                        list(cierres.columns) + ["FANTASMAUSDT"], compuerta=1)
    assert e["FANTASMAUSDT"] == 0.0
    assert e.sum() > 0


# --- Stop de catastrofe ---------------------------------------------------

def test_el_stop_esta_cuatro_atr_abajo():
    assert cat.precio_de_stop(100.0, 0.05) == pytest.approx(80.0)


def test_el_stop_nunca_baja_de_cero():
    """Un ATR del 30% por 4 daria -20% del precio. Cero es el piso."""
    assert cat.precio_de_stop(100.0, 0.30) == 0.0


def test_el_stop_es_mas_ancho_cuando_el_activo_se_mueve_mas():
    quieto = cat.precio_de_stop(100.0, 0.02)
    agitado = cat.precio_de_stop(100.0, 0.08)
    assert agitado < quieto


def test_el_stop_se_evalua_sobre_el_cierre_no_intradia():
    """
    Si toco el stop durante el dia y cerro arriba, no dispara. Con velas
    diarias no hay forma de saber en que orden pasaron el minimo y el cierre.
    """
    assert cat.se_disparo(cierre=81.0, stop=80.0) is False
    assert cat.se_disparo(cierre=80.0, stop=80.0) is True
    assert cat.se_disparo(cierre=79.0, stop=80.0) is True


def test_una_posicion_sin_precio_hoy_no_dispara():
    posiciones = [cat.Posicion("AUSDT", 100.0, 80.0),
                  cat.Posicion("BUSDT", 100.0, 80.0)]
    cierres = pd.Series({"AUSDT": 70.0, "BUSDT": np.nan})
    assert cat.revisar_stops(posiciones, cierres) == ["AUSDT"]


def test_el_peso_liberado_por_un_stop_no_se_reparte():
    """
    La especificacion es explicita: "el resto de la cartera no se toca". El
    peso del que salio se va a efectivo.

    Repartirlo entre los que quedan mejora el resultado del backtest y es
    exactamente lo que no hay que hacer: seria aumentar la exposicion justo
    despues de que algo se derrumbo.
    """
    exposicion = pd.Series({"A": 0.3, "B": 0.3, "C": 0.3})
    quedan = exposicion.drop("C")
    assert quedan.sum() == pytest.approx(0.6)   # y NO 0,9
    assert quedan["A"] == pytest.approx(0.3)


def test_un_atr_invalido_levanta():
    with pytest.raises(ValueError):
        cat.precio_de_stop(100.0, float("nan"))
    with pytest.raises(ValueError):
        cat.precio_de_stop(0.0, 0.05)


# --- Cortacircuito diario -------------------------------------------------

def test_cuenta_los_dias_bajo_el_umbral():
    patrimonio = pd.Series([100.0, 99.0, 95.0, 96.0, 90.0], index=_dias(5))
    disparos = cat.disparos_del_cortacircuito(patrimonio, umbral_pct=3.0)
    assert len(disparos) == 2   # -4,04% y -6,25%


def test_una_subida_fuerte_no_dispara_nada():
    patrimonio = pd.Series([100.0, 130.0, 170.0], index=_dias(3))
    assert len(cat.disparos_del_cortacircuito(patrimonio, 3.0)) == 0


def test_el_umbral_es_obligatorio_y_positivo():
    """
    Sin default a proposito: el 3% de la Fase 1 se medía sobre operaciones
    cerradas y no se puede trasladar a patrimonio a precio de mercado sin
    medirlo de nuevo.
    """
    patrimonio = pd.Series([100.0, 95.0], index=_dias(2))
    with pytest.raises(TypeError):
        cat.disparos_del_cortacircuito(patrimonio)   # type: ignore[call-arg]
    with pytest.raises(ValueError):
        cat.disparos_del_cortacircuito(patrimonio, -3.0)


def test_la_frecuencia_reporta_lo_que_hace_falta_para_decidir():
    rng = np.random.default_rng(20260830)
    retornos = rng.normal(0, 0.03, 730)
    patrimonio = pd.Series(1000 * np.exp(np.cumsum(retornos)), index=_dias(730))
    info = cat.frecuencia_de_disparo(patrimonio, 3.0)
    assert info["dias"] == 729
    assert info["disparos"] > 0
    assert info["por_anio"] == pytest.approx(info["disparos"] / (729 / 365))
    assert info["peor_dia_pct"] < 0


def test_el_patrimonio_desordenado_levanta():
    patrimonio = pd.Series([100.0, 95.0], index=_dias(2)[::-1])
    with pytest.raises(ValueError):
        cat.perdidas_diarias_pct(patrimonio)
