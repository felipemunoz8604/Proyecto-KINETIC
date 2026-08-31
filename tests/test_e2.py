"""
Pruebas de E2.

Las tres que sostienen el resto:

1. `test_la_bruta_nunca_pasa_de_uno` -- con cortos, sumar con signo dejaria
   pasar apalancamiento disfrazado de neutralidad.
2. `test_solo_se_shortea_lo_que_tiene_perpetuo` -- shortear en Spot no existe;
   dejarlo pasar seria simular una operacion imposible.
3. `test_una_moneda_no_puede_estar_larga_y_corta_a_la_vez` -- se cancelaria
   sola y pagaria dos peajes por nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategy import e2  # noqa: E402


def _dias(n: int, desde: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _panel(n: int, nombres: list[str], semilla_base: int = 0) -> pd.DataFrame:
    idx = _dias(n)
    datos = {}
    for i, nombre in enumerate(nombres):
        rng = np.random.default_rng(semilla_base + i)
        datos[nombre] = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
    return pd.DataFrame(datos, index=idx)


def _escenario(n: int = 400, shorteables: list[str] | None = None):
    nombres = [f"S{i}USDT" for i in range(1, 13)]
    spot = _panel(n, nombres)
    ap_spot = spot.shift(1)
    ap_spot.iloc[0] = spot.iloc[0]
    cols = shorteables if shorteables is not None else nombres
    # El perpetuo sigue de cerca al Spot pero no es identico: eso es la base.
    rng = np.random.default_rng(99)
    perp = spot[cols] * (1 + rng.normal(0, 0.001, (n, len(cols))))
    ap_perp = perp.shift(1)
    ap_perp.iloc[0] = perp.iloc[0]
    atr_spot = pd.DataFrame(0.05, index=spot.index, columns=spot.columns)
    atr_perp = pd.DataFrame(0.05, index=perp.index, columns=perp.columns)
    universo = {spot.index[i]: nombres for i in range(60, n, 30)}
    return (spot, ap_spot, perp, ap_perp, atr_spot, atr_perp, universo,
            spot.index)


def _armar(**kwargs):
    (spot, ap_spot, perp, ap_perp, atr_spot, atr_perp, universo,
     idx) = _escenario(**kwargs)
    return e2.construir_exposiciones(spot, ap_spot, perp, ap_perp,
                                     atr_spot, atr_perp, universo, idx)


# --- Seleccion ------------------------------------------------------------

def test_la_pata_corta_toma_los_peores():
    fila = pd.Series({f"S{i}": float(i) for i in range(10)})
    assert e2.seleccionar_cortos(fila, list(fila.index), 3) == ["S0", "S1", "S2"]


def test_la_pata_corta_no_exige_puntaje_negativo():
    """
    La especificacion dice "los 5 de menor s_i", sin condicion de signo -- al
    reves que la larga, que exige s_i > 0. Se respeta la asimetria porque
    estaba preregistrada; queda anotado que es asimetria y no descuido.
    """
    fila = pd.Series({"A": 5.0, "B": 3.0, "C": 1.0})
    assert e2.seleccionar_cortos(fila, list(fila.index), 2) == ["C", "B"]


# --- Armado ---------------------------------------------------------------

def test_la_bruta_nunca_pasa_de_uno():
    """
    Se mide en valores absolutos. +0,6 y -0,6 no son exposicion cero: son 1,2
    de bruta, o sea apalancamiento
    """
    a = _armar()
    assert a.exposiciones.abs().sum(axis=1).max() <= 1.0 + 1e-9


def test_hay_las_dos_patas():
    a = _armar()
    assert (a.exposiciones > 0).any().any()
    assert (a.exposiciones < 0).any().any()


def test_cada_pata_no_pasa_de_la_mitad():
    a = _armar()
    positivos = a.exposiciones.clip(lower=0).sum(axis=1)
    negativos = (-a.exposiciones.clip(upper=0)).sum(axis=1)
    assert positivos.max() <= e2.FRACCION_POR_PATA + 1e-9
    assert negativos.max() <= e2.FRACCION_POR_PATA + 1e-9


def test_nunca_hay_mas_de_cinco_por_pata():
    a = _armar()
    assert (a.exposiciones > 0).sum(axis=1).max() <= e2.CUANTAS_POSICIONES
    assert (a.exposiciones < 0).sum(axis=1).max() <= e2.CUANTAS_POSICIONES


def test_solo_se_shortea_lo_que_tiene_perpetuo():
    """
    Shortear en Spot no existe. Si un simbolo sin perpetuo apareciera en la
    pata corta, el backtest estaria simulando una operacion imposible.
    """
    con_perp = ["S1USDT", "S2USDT", "S3USDT", "S4USDT", "S5USDT", "S6USDT"]
    a = _armar(shorteables=con_perp)
    cortos = a.exposiciones.columns[(a.exposiciones < 0).any()]
    assert set(e2.simbolo_base(c) for c in cortos) <= set(con_perp)


def test_la_pata_corta_es_otro_instrumento():
    """
    Spot y perpetuo de la misma moneda NO comparten columna. Si la
    compartieran, cada cambio de venue le meteria al motor un salto de precio
    que no ocurrio, y ese salto aparece como ganancia de la nada.
    """
    a = _armar()
    cortos = a.exposiciones.columns[(a.exposiciones < 0).any()]
    largos = a.exposiciones.columns[(a.exposiciones > 0).any()]
    assert all(e2.es_perpetuo(c) for c in cortos)
    assert not any(e2.es_perpetuo(c) for c in largos)


def test_el_nombre_base_se_recupera():
    assert e2.simbolo_base("BTCUSDT.P") == "BTCUSDT"
    assert e2.simbolo_base("BTCUSDT") == "BTCUSDT"


def test_una_moneda_no_puede_estar_larga_y_corta_a_la_vez():
    """Se cancelaria sola y pagaria dos peajes por nada."""
    a = _armar()
    for _, fila in a.exposiciones.iterrows():
        en_largo = {e2.simbolo_base(c) for c in fila[fila > 0].index}
        en_corto = {e2.simbolo_base(c) for c in fila[fila < 0].index}
        assert not (en_largo & en_corto)


def test_agregar_datos_del_futuro_no_cambia_el_pasado():
    (spot, ap_spot, perp, ap_perp, atr_spot, atr_perp, universo,
     idx) = _escenario(500)
    corte = 300
    entero = e2.construir_exposiciones(spot, ap_spot, perp, ap_perp,
                                       atr_spot, atr_perp, universo, idx)
    universo_corto = {f: v for f, v in universo.items() if f < idx[corte]}
    parcial = e2.construir_exposiciones(
        spot.iloc[:corte], ap_spot.iloc[:corte], perp.iloc[:corte],
        ap_perp.iloc[:corte], atr_spot.iloc[:corte], atr_perp.iloc[:corte],
        universo_corto, idx[:corte])
    pd.testing.assert_frame_equal(
        entero.exposiciones.iloc[:corte][parcial.exposiciones.columns],
        parcial.exposiciones)


def test_sin_ningun_perpetuo_queda_solo_la_pata_larga():
    """
    No se fuerza la neutralidad rellenando con otro nombre: la cartera queda
    desbalanceada y eso se ve, en vez de esconderse.
    """
    (spot, ap_spot, _, _, atr_spot, _, universo, idx) = _escenario()
    vacio = pd.DataFrame(index=spot.index)
    a = e2.construir_exposiciones(spot, ap_spot, vacio, vacio,
                                  atr_spot, vacio, universo, idx)
    assert (a.exposiciones >= -1e-12).all().all()
    assert a.dias_sin_cortos > 0


def test_el_stop_de_un_corto_mira_el_precio_del_perpetuo():
    """
    Si mirara el de Spot, un corto podria seguir abierto mientras el perpetuo
    se le fue en contra -- o cerrarse sin que el instrumento que se opera se
    haya movido.
    """
    idx = _dias(200)
    nombres = ["BUENAUSDT", "MALAUSDT"]
    spot = pd.DataFrame({
        "BUENAUSDT": np.linspace(100, 200, 200),
        "MALAUSDT": np.linspace(100, 90, 200),      # en Spot casi no se mueve
    }, index=idx)
    ap_spot = spot.shift(1); ap_spot.iloc[0] = spot.iloc[0]
    # En el perpetuo, MALA se dispara para arriba: el corto tiene que saltar.
    perp = pd.DataFrame({
        "BUENAUSDT": np.linspace(100, 200, 200),
        "MALAUSDT": np.concatenate([np.linspace(100, 90, 100),
                                    np.linspace(90, 400, 100)]),
    }, index=idx)
    ap_perp = perp.shift(1); ap_perp.iloc[0] = perp.iloc[0]
    atr = pd.DataFrame(0.02, index=idx, columns=nombres)
    universo = {idx[60]: nombres}

    a = e2.construir_exposiciones(spot, ap_spot, perp, ap_perp, atr, atr,
                                  universo, idx, cuantas=1)
    cortos = [d for d in a.stops_disparados if d["pata"] == "corta"]
    assert cortos, "el corto tenia que saltar por el precio del perpetuo"


def test_el_peso_del_que_salio_por_stop_no_se_reparte():
    a = _armar()
    if not a.stops_disparados:
        pytest.skip("sin stops en este escenario")
    salto = a.stops_disparados[0]["fecha"]
    i = a.exposiciones.index.get_loc(salto)
    antes = a.exposiciones.iloc[i - 1].abs().sum()
    despues = a.exposiciones.iloc[i].abs().sum()
    assert despues < antes + 1e-12
