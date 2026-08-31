"""
Pruebas de E0.

La central es `test_los_dos_caminos_coinciden`: el camino rapido y el de
referencia tienen que dar exactamente lo mismo. Es el mismo arreglo que en la
Fase 1 con `mascara_de_senales` contra `evaluar_vela`, y esta por la misma
razon -- el rapido es el que se corre y el lento es el que se entiende.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk import pesos as pz  # noqa: E402
from strategy import e0  # noqa: E402


def _dias(n: int, desde: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _serie(n: int, semilla: int, sigma: float = 0.03) -> pd.Series:
    rng = np.random.default_rng(semilla)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0005, sigma, n))),
                     index=_dias(n))


def test_los_dos_caminos_coinciden():
    """
    Vectorizado contra dia a dia. Si alguien cambia una condicion en uno solo
    de los dos, se cae aca y no en un resultado raro seis meses despues.
    """
    cierres = _serie(500, 20260830)
    rapido = e0.exposicion_objetivo(cierres)
    lento = e0.exposicion_objetivo_lenta(cierres)
    pd.testing.assert_series_equal(rapido, lento, check_names=False,
                                   rtol=1e-12, atol=1e-12)


def test_coinciden_tambien_con_otra_volatilidad():
    """Un solo mercado sintetico no alcanza para creerle a una equivalencia."""
    for semilla, sigma in ((1, 0.01), (2, 0.06), (3, 0.10)):
        cierres = _serie(400, semilla, sigma)
        pd.testing.assert_series_equal(
            e0.exposicion_objetivo(cierres),
            e0.exposicion_objetivo_lenta(cierres),
            check_names=False, rtol=1e-12, atol=1e-12)


def test_antes_de_los_doscientos_dias_no_hay_exposicion():
    """Sin media de 200 dias no hay señal, y sin señal no se toma nada."""
    cierres = _serie(500, 5)
    e = e0.exposicion_objetivo(cierres)
    assert (e.iloc[:200] == 0).all()


def test_con_la_señal_en_falso_la_exposicion_es_cero():
    """Una serie que solo baja nunca esta sobre su media de 200 dias."""
    cierres = pd.Series(np.linspace(1000, 100, 400), index=_dias(400))
    assert (e0.exposicion_objetivo(cierres) == 0).all()


def test_la_exposicion_nunca_pasa_de_uno():
    for semilla in range(6):
        e = e0.exposicion_objetivo(_serie(400, semilla, 0.005))
        assert e.max() <= pz.K_MAX + 1e-12


def test_un_mercado_mas_agitado_recibe_menos_exposicion():
    """
    Es el nucleo de la volatilidad objetivo: a igual señal, mas movimiento
    significa menos plata adentro.
    """
    # El MISMO camino escalado, no dos caminos distintos: asi la señal se
    # enciende en los mismos dias y lo unico que cambia es la volatilidad.
    rng = np.random.default_rng(7)
    ruido = rng.normal(0, 1, 500)

    def con_sigma(s: float) -> pd.Series:
        return pd.Series(100 * np.exp(np.cumsum(0.003 + s * ruido)),
                         index=_dias(500))

    tranquilo = e0.exposicion_objetivo(con_sigma(0.01))
    agitado = e0.exposicion_objetivo(con_sigma(0.04))
    juntos = (tranquilo > 0) & (agitado > 0)
    assert juntos.sum() > 50
    assert tranquilo[juntos].mean() > agitado[juntos].mean()


def test_agregar_datos_del_futuro_no_cambia_el_pasado():
    """
    La prueba de no-anticipacion. Cortar la serie no puede cambiar ni una
    exposicion de los dias que quedaron.
    """
    cierres = _serie(600, 99)
    entera = e0.exposicion_objetivo(cierres)
    cortada = e0.exposicion_objetivo(cierres.iloc[:400])
    pd.testing.assert_series_equal(entera.iloc[:400], cortada)


def test_la_señal_de_hoy_usa_el_cierre_de_ayer():
    """
    El dia del salto la exposicion todavia es cero: la decision se toma con el
    cierre de ayer, porque cuando conoces el cierre de hoy el dia ya termino.
    """
    # Baja 250 dias (siempre debajo de su propia media) y despues salta.
    valores = np.concatenate([np.linspace(200.0, 100.0, 250),
                              np.full(60, 400.0)])
    cierres = pd.Series(valores, index=_dias(310))
    e = e0.exposicion_objetivo(cierres)

    dia_del_salto = cierres.index[250]
    primer_dia_dentro = e[e > 0].index[0]
    assert primer_dia_dentro == dia_del_salto + pd.Timedelta(days=1)


def test_pedir_apalancamiento_levanta():
    with pytest.raises(pz.SinApalancamiento):
        e0.exposicion_objetivo(_serie(400, 1), k_max=2.0)


def test_el_formato_para_el_motor_es_una_columna():
    marco = e0.exposiciones(_serie(300, 2))
    assert list(marco.columns) == [e0.SIMBOLO]
    assert len(marco) == 300
