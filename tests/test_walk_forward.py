"""
Pruebas del walk-forward.

La propiedad que hay que blindar es UNA: el parametro se elige mirando solo
el tramo de entrenamiento. Si el proceso llegara a ver el tramo de prueba
aunque sea de refilon, el resultado "fuera de muestra" seria mentira y no
habria forma de darse cuenta mirando el numero final.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backtesting import walk_forward as wf  # noqa: E402
from risk import position_sizing  # noqa: E402
from strategy import indicators as ind  # noqa: E402


@pytest.fixture
def cfg() -> dict:
    return {
        "capital": {"monto": 1_000.0},
        "riesgo": {
            "por_operacion_pct": 1.0, "perdida_diaria_max_pct": 100.0,
            "max_posiciones_simultaneas": 1, "kill_switch": False,
        },
        "stops": {
            "atr_periodo": 14, "atr_multiplicador_sl": 2.0,
            "trailing_atr_multiplicador": 2.0,
        },
        "costos": {"comision_por_lado_pct": 0.1, "slippage_pct_por_lado": 0.05},
        "estrategia": {
            "tendencia": {"ema_rapida": 9, "ema_lenta": 21},
            "consolidacion": {"velas": 20, "umbral_desviacion_pct": 100.0},
            "volumen": {"periodo_promedio": 20, "multiplicador_minimo": 1.0},
            "regimen": {"metodo": "adx", "adx_periodo": 14, "adx_minimo": 0.0},
            "portfolio_guard": {
                "sma_periodo": 50, "distancia_maxima_bajo_sma_pct": None,
                "una_posicion_por_grupo": True,
            },
        },
        "backtest_motor": {"descartar_dias_iniciales": 0, "capital_compuesto": True},
    }


@pytest.fixture
def velas() -> pd.DataFrame:
    """Seis anios de velas diarias sinteticas."""
    generador = np.random.default_rng(2026)
    n = 365 * 6
    cierre = 100 + np.cumsum(generador.normal(0.05, 1.5, n))
    cierre = np.maximum(cierre, 5.0)
    return pd.DataFrame(
        {
            "open": np.concatenate([[cierre[0]], cierre[:-1]]),
            "high": cierre + np.abs(generador.normal(1.0, 0.6, n)),
            "low": cierre - np.abs(generador.normal(1.0, 0.6, n)),
            "close": cierre,
            "volume": np.abs(generador.normal(1000, 500, n)),
        },
        index=pd.date_range("2018-01-01", periods=n, freq="1D", tz="UTC"),
    )


def aplicar_trailing(cfg: dict, valor: float) -> None:
    cfg["stops"]["trailing_atr_multiplicador"] = valor


REGLAS = position_sizing.ReglasSimbolo(0.000001, 0.000001, 1.0)


def correr(velas, cfg, candidatos=(2.0, 4.0), **kwargs):
    d = ind.agregar_indicadores(velas, cfg)
    return wf.correr(
        d, cfg, "TESTUSDT", "1D", list(candidatos), aplicar_trailing,
        reglas_simbolo=REGLAS, **kwargs
    )


# ===========================================================================
# La propiedad central
# ===========================================================================

def test_la_eleccion_no_puede_ver_el_tramo_de_prueba(velas, cfg):
    """
    Se espia que datos recibe el criterio de seleccion. Cada vez que se
    evalua un candidato, el ultimo dato disponible tiene que ser anterior al
    primer dato del tramo de prueba de esa misma ventana.
    """
    vistos: list[pd.Timestamp] = []

    original = wf.motor.correr

    def espia(df, *args, **kwargs):
        vistos.append(df.index[-1])
        return original(df, *args, **kwargs)

    wf.motor.correr = espia
    try:
        resultado = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)
    finally:
        wf.motor.correr = original

    assert resultado.ventanas, "no se genero ninguna ventana"

    # Por cada ventana hubo N evaluaciones de entrenamiento + 1 de prueba.
    candidatos = 2
    indice = 0
    for v in resultado.ventanas:
        for _ in range(candidatos):
            assert vistos[indice] < v.prueba_desde, (
                f"la ventana {v.numero} evaluo un candidato con datos hasta "
                f"{vistos[indice]}, que ya entra en el tramo de prueba "
                f"(empieza {v.prueba_desde})"
            )
            indice += 1
        indice += 1   # la corrida de prueba, esa si ve el tramo de prueba


def test_los_tramos_no_se_recortan_una_segunda_vez(velas, cfg):
    """
    El descarte de los primeros dias tras el listado va UNA vez, sobre el
    historico entero. Si el motor lo repitiera en cada tramo, cada ventana
    perderia sus primeros 30 dias: el entrenamiento elegiria el parametro con
    datos mutilados y la prueba dejaria sin medir casi el 9% del periodo,
    ademas de un mes ciego justo despues de cada costura.

    Se verifico en datos reales el 29-ago-2026: eran 4.609 velas de prueba de
    BTCUSDT 1h que el motor nunca miraba, y la ultima ventana quedaba vacia
    entera por ser mas corta que el recorte.
    """
    cfg["backtest_motor"]["descartar_dias_iniciales"] = 30

    vistos: list[tuple] = []
    original = wf.motor.correr

    def espia(df, *args, **kwargs):
        vistos.append((df.index[0], kwargs.get("recortar_inicio", True)))
        return original(df, *args, **kwargs)

    wf.motor.correr = espia
    try:
        r = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)
    finally:
        wf.motor.correr = original

    assert r.ventanas, "no se genero ninguna ventana"

    # Ningun tramo puede llegar al motor con el recorte encendido.
    assert all(not recorta for _, recorta in vistos), (
        "algun tramo se paso con recortar_inicio=True: el motor le va a "
        "morder los primeros 30 dias"
    )

    # Y el tramo de prueba tiene que empezar donde dice la ventana, no un mes
    # despues. Esta es la parte que fallaba.
    candidatos = 2
    indice = 0
    for v in r.ventanas:
        indice += candidatos          # las corridas de entrenamiento
        arranque_prueba = vistos[indice][0]
        assert arranque_prueba == v.prueba_desde, (
            f"la ventana {v.numero} dice probar desde {v.prueba_desde} pero el "
            f"motor recibio datos desde {arranque_prueba}: hay un hueco"
        )
        indice += 1


def test_el_recorte_del_listado_se_aplica_igual_una_vez(velas, cfg):
    """Apagarlo por tramo no puede hacer que el listado deje de descartarse."""
    cfg["backtest_motor"]["descartar_dias_iniciales"] = 30
    r = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)

    assert r.ventanas
    assert r.ventanas[0].entrena_desde >= velas.index[0] + pd.Timedelta(days=30), (
        "el primer tramo de entrenamiento arranca dentro de los dias que "
        "habia que descartar por listado reciente"
    )


def test_los_tramos_de_prueba_no_se_pisan_entre_si(velas, cfg):
    r = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)
    for anterior, siguiente in zip(r.ventanas, r.ventanas[1:]):
        assert anterior.prueba_hasta < siguiente.prueba_desde


def test_el_entrenamiento_siempre_precede_a_su_prueba(velas, cfg):
    r = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)
    for v in r.ventanas:
        assert v.entrena_hasta < v.prueba_desde


def test_el_capital_se_arrastra_entre_ventanas(velas, cfg):
    """
    Cada ventana de prueba arranca con lo que dejo la anterior. Si cada una
    empezara con los 1.000 iniciales, una perdida temprana no pesaria en el
    resto y el resultado seria mas optimista que la realidad.
    """
    r = correr(velas, cfg, anios_entrenamiento=2, anios_prueba=1)
    suma = sum(v.metricas_prueba.resultado_neto for v in r.ventanas)
    assert r.capital_final == pytest.approx(r.capital_inicial + suma)


# ===========================================================================
# Diagnostico
# ===========================================================================

def test_se_registran_todos_los_candidatos_evaluados(velas, cfg):
    r = correr(velas, cfg, candidatos=(2.0, 3.0, 4.0), anios_entrenamiento=2)
    for v in r.ventanas:
        assert set(v.candidatos_evaluados) == {2.0, 3.0, 4.0}
        assert v.elegido in {2.0, 3.0, 4.0}


def test_el_elegido_es_el_mejor_del_entrenamiento(velas, cfg):
    r = correr(velas, cfg, candidatos=(2.0, 3.0, 4.0), anios_entrenamiento=2)
    for v in r.ventanas:
        mejor = max(v.candidatos_evaluados.values())
        assert v.candidatos_evaluados[v.elegido] == pytest.approx(mejor)


def test_detecta_cuando_el_elegido_no_es_estable():
    """Si cada ventana elige un valor distinto, no hay optimo: hay ruido."""
    def ventana_falsa(n, elegido):
        return wf.Ventana(
            numero=n,
            entrena_desde=pd.Timestamp("2020-01-01", tz="UTC"),
            entrena_hasta=pd.Timestamp("2021-01-01", tz="UTC"),
            prueba_desde=pd.Timestamp("2021-01-02", tz="UTC"),
            prueba_hasta=pd.Timestamp("2022-01-01", tz="UTC"),
            elegido=elegido, resultado_entrenamiento=0.0,
            metricas_prueba=wf.motor.Metricas(), operaciones_prueba=[],
        )

    inestable = wf.ResultadoWalkForward(
        [ventana_falsa(i, v) for i, v in enumerate([2, 3, 4, 5])], [], 1000.0, 1000.0
    )
    assert not inestable.el_elegido_es_estable

    estable = wf.ResultadoWalkForward(
        [ventana_falsa(i, v) for i, v in enumerate([3, 3, 3, 5])], [], 1000.0, 1000.0
    )
    assert estable.el_elegido_es_estable


def test_la_concentracion_se_calcula_sobre_las_operaciones_de_prueba():
    def op(resultado):
        return wf.motor.Operacion(
            par="X", temporalidad="1h",
            entrada_momento=pd.Timestamp("2020-01-01", tz="UTC"), entrada_precio=1.0,
            salida_momento=pd.Timestamp("2020-01-02", tz="UTC"), salida_precio=1.0,
            cantidad=1.0, motivo_salida="stop", stop_inicial=0.9, stop_final=0.9,
            velas_abierta=1, riesgo_pct_planeado=1.0, costos=0.0,
            resultado_bruto=resultado, resultado_neto=resultado, capital_antes=1000.0,
        )

    # Neto = 100. La mejor sola aporta 90.
    r = wf.ResultadoWalkForward(
        [], [op(90.0), op(20.0), op(-10.0)], 1000.0, 1100.0
    )
    assert r.concentracion_pct == pytest.approx(90.0)


def test_sin_datos_no_explota(cfg):
    vacio = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    vacio.index = pd.DatetimeIndex([], tz="UTC")
    r = wf.correr(vacio, cfg, "X", "1h", [2.0], aplicar_trailing)
    assert r.ventanas == []
    assert r.metricas.operaciones == 0
