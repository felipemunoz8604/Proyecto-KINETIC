"""
Pruebas del modulo de metricas, benchmarks y la barrera del holdout.

Por que estas pruebas importan mas que la mayoria: este modulo es el que va a
decidir si E0, E1, E2 y E3 pasan o no pasan. Un error aca no produce un
resultado raro que alguien note -- produce un veredicto equivocado que nadie
cuestiona, porque el numero "se ve bien".

Casi todas usan curvas armadas a mano con el resultado calculable a mano. Es
a proposito: una prueba que compara contra lo que devuelve el propio codigo
no prueba nada.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from metrics import benchmarks, metricas, ventana


def curva(valores, desde="2019-01-01", freq="D") -> pd.Series:
    idx = pd.date_range(desde, periods=len(valores), freq=freq, tz="UTC")
    return pd.Series([float(v) for v in valores], index=idx)


# --- CAGR -----------------------------------------------------------------

def test_cagr_duplicar_en_un_anio_da_cien_por_ciento():
    # 366 puntos diarios = 365 dias de calendario transcurridos.
    valores = [100.0] * 365 + [200.0]
    assert metricas.cagr(curva(valores)) == pytest.approx(1.0, abs=1e-9)


def test_cagr_usa_dias_de_calendario_no_cantidad_de_filas():
    """
    Dos curvas con el mismo principio y fin, una diaria y otra semanal.

    Si el CAGR contara filas, la semanal daria un numero absurdo. Tiene que
    dar lo mismo: lo que importa es cuanto TARDO en crecer.
    """
    diaria = curva([100.0] * 730 + [200.0])
    semanal = curva([100.0] * 104 + [200.0], freq="7D")
    # Ambas cubren ~2 anios, asi que duplicar da ~41,4% anual.
    assert metricas.cagr(diaria) == pytest.approx(0.414, abs=0.01)
    assert metricas.cagr(semanal) == pytest.approx(0.414, abs=0.01)


def test_cagr_de_una_curva_plana_es_cero():
    assert metricas.cagr(curva([100.0] * 100)) == pytest.approx(0.0)


# --- Caida maxima ---------------------------------------------------------

def test_caida_maxima_toma_la_peor_no_la_ultima():
    # Sube a 200, cae a 100 (-50%), recupera a 300, cae a 240 (-20%).
    peor, _, _, _ = metricas.caida_maxima(curva([100, 200, 100, 300, 240]))
    assert peor == pytest.approx(-0.5)


def test_caida_maxima_mide_desde_el_pico_hasta_la_recuperacion():
    """La duracion va del maximo previo al dia que lo recupera, no al fondo."""
    # dia 0: 100 | dia 1: 200 (pico) | dia 2: 100 (fondo) | dia 3: 150
    # dia 4: 200 (recupera)
    peor, dias, desde, hasta = metricas.caida_maxima(
        curva([100, 200, 100, 150, 200])
    )
    assert peor == pytest.approx(-0.5)
    assert desde == pd.Timestamp("2019-01-02", tz="UTC")
    assert hasta == pd.Timestamp("2019-01-05", tz="UTC")
    assert dias == 3


def test_caida_que_nunca_se_recupera_cuenta_hasta_el_final():
    """
    Devolver 0 o None seria mentir en la direccion comoda.

    Una caida abierta es peor que una cerrada, no mejor.
    """
    _, dias, _, hasta = metricas.caida_maxima(curva([100, 200, 100, 110, 120]))
    assert hasta == pd.Timestamp("2019-01-05", tz="UTC")
    assert dias == 3


def test_curva_que_solo_sube_no_tiene_caida():
    peor, dias, desde, hasta = metricas.caida_maxima(curva([100, 110, 120, 130]))
    assert peor == 0.0
    assert dias == 0
    assert desde is None and hasta is None


# --- Calmar ---------------------------------------------------------------

def test_calmar_es_cagr_sobre_caida():
    m = metricas.calcular(curva([100.0] * 365 + [200.0] + [150.0]), "prueba")
    assert m.calmar == pytest.approx(m.cagr / abs(m.caida_maxima))


def test_calmar_sin_caida_y_ganando_es_infinito():
    """
    Ganar sin caer nunca es Calmar infinito de verdad, no cero.

    Pasa casi siempre porque la serie es demasiado corta, y devolver 0 lo
    disimularia: un infinito se ve y obliga a mirar.
    """
    m = metricas.calcular(curva([100.0] * 365 + [200.0]), "sube siempre")
    assert m.calmar == float("inf")


# --- Sortino --------------------------------------------------------------

def test_sortino_castiga_solo_la_volatilidad_de_abajo():
    m_inf = metricas.sortino(curva([100, 101, 102, 103, 104]))
    assert m_inf == float("inf")  # ningun dia negativo: no hay denominador

    con_bajones = metricas.sortino(curva([100, 90, 110, 95, 120]))
    assert math.isfinite(con_bajones)


# --- Errores y bordes -----------------------------------------------------

def test_una_curva_de_un_solo_punto_no_se_puede_medir():
    with pytest.raises(ValueError, match="al menos dos"):
        metricas.calcular(curva([100.0]), "muy corta")


def test_tiempo_en_mercado_sale_de_la_exposicion():
    patrimonio = curva([100, 101, 102, 103])
    exposicion = pd.Series([0.0, 1.0, 1.0, 0.0], index=patrimonio.index)
    m = metricas.calcular(patrimonio, "con compuerta", exposicion=exposicion)
    assert m.tiempo_en_mercado_pct == pytest.approx(50.0)


# --- La barrera del holdout -----------------------------------------------

def test_la_barrera_corta_datos_del_holdout():
    del_holdout = curva([100.0] * 10, desde="2025-06-01")
    with pytest.raises(ventana.HoldoutBloqueado, match="ventana de diseño"):
        ventana.verificar(del_holdout)


def test_la_barrera_deja_pasar_la_ventana_de_diseno():
    ventana.verificar(curva([100.0] * 10, desde="2024-01-01"))  # no levanta


def test_la_barrera_se_abre_solo_si_se_pide_explicitamente():
    del_holdout = curva([100.0] * 10, desde="2025-06-01")
    ventana.verificar(del_holdout, permitir_holdout=True)  # no levanta


def test_recortar_a_diseno_deja_exactamente_la_ventana():
    larga = curva([100.0] * 3000, desde="2018-01-01")
    corta = ventana.recortar_a_diseno(larga)
    assert corta.index[0] >= ventana.DISENO_DESDE
    assert corta.index[-1] <= ventana.DISENO_HASTA
    ventana.verificar(corta)  # y por lo tanto ya no levanta


# --- B1 -------------------------------------------------------------------

def _velas(precios, desde="2019-01-01") -> pd.DataFrame:
    idx = pd.date_range(desde, periods=len(precios), freq="D", tz="UTC")
    return pd.DataFrame({"close": [float(p) for p in precios]}, index=idx)


def test_b1_cobra_el_costo_de_entrada_una_sola_vez():
    curva_b1 = benchmarks.b1(_velas([100, 200, 400]), 1000.0)
    esperado = 1000.0 * (1 - benchmarks.COSTO_ENTRADA_PCT / 100.0)
    assert curva_b1.iloc[0] == pytest.approx(esperado)
    # Cuadruplicar el precio cuadruplica el patrimonio: no hay mas costos.
    assert curva_b1.iloc[-1] == pytest.approx(esperado * 4)


def test_b1_sigue_al_precio_sin_tocar_nada():
    precios = [100, 150, 75, 300]
    curva_b1 = benchmarks.b1(_velas(precios), 500.0)
    for i, p in enumerate(precios):
        assert curva_b1.iloc[i] / curva_b1.iloc[0] == pytest.approx(p / precios[0])


def test_b1_respeta_la_barrera_del_holdout():
    with pytest.raises(ventana.HoldoutBloqueado):
        benchmarks.b1(_velas([100, 200], desde="2025-06-01"), 500.0)


def test_b1_necesita_al_menos_dos_velas():
    with pytest.raises(ValueError, match="al menos dos"):
        benchmarks.b1(_velas([100]), 500.0)
