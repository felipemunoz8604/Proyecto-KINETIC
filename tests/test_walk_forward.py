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


CANDIDATOS_REALES = [2.0, 3.0, 4.0, 5.0, 6.0]


def resultado_falso(elegidos, candidatos=None):
    """Un ResultadoWalkForward con solo lo que la estabilidad necesita mirar."""
    t = pd.Timestamp("2020-01-01", tz="UTC")
    ventanas = [
        wf.Ventana(
            numero=i, entrena_desde=t, entrena_hasta=t, prueba_desde=t,
            prueba_hasta=t, elegido=v, resultado_entrenamiento=0.0,
            metricas_prueba=wf.motor.Metricas(), operaciones_prueba=[],
        )
        for i, v in enumerate(elegidos)
    ]
    return wf.ResultadoWalkForward(
        ventanas, [], 500.0, 500.0,
        CANDIDATOS_REALES if candidatos is None else candidatos,
    )


# ---------------------------------------------------------------------------
# La estabilidad, con los cuatro casos reales del 29-ago-2026
# ---------------------------------------------------------------------------

def test_elegir_siempre_lo_mismo_es_estable():
    """BTCUSDT 15m: 6.0x en las seis ventanas."""
    r = resultado_falso([6.0] * 6)
    assert r.dispersion_pct == 0.0
    assert r.estabilidad == wf.ESTABLE
    assert r.el_elegido_es_estable


def test_moverse_de_punta_a_punta_del_menu_es_inestable():
    """
    ETHUSDT 1h: elegidos [5, 5, 2, 6, 6, 6]. Es el caso que rompio el criterio
    anterior, que decia "estable" porque 6.0 ganaba exactamente 3 de 6.

    Un anio el entrenamiento apunto a 2 y otro a 6: recorrio el menu entero.
    """
    r = resultado_falso([5.0, 5.0, 2.0, 6.0, 6.0, 6.0])
    assert r.dispersion_pct == 100.0
    assert r.estabilidad == wf.INESTABLE
    assert not r.el_elegido_es_estable


def test_una_mayoria_minima_ya_no_alcanza_para_declarar_estable():
    """
    El defecto exacto del criterio viejo: 6.0 gana 3 de 6 -- "al menos la
    mitad" -- pero las elecciones van de 2 a 6. Antes daba estable.
    """
    elegidos = [5.0, 5.0, 2.0, 6.0, 6.0, 6.0]
    assert elegidos.count(6.0) == len(elegidos) / 2, "el caso perdio su gracia"
    assert not resultado_falso(elegidos).el_elegido_es_estable


def test_un_grupo_apretado_pero_no_identico_queda_en_duda():
    """
    BTCUSDT 1h: elegidos [4, 6, 5, 4, 5, 5]. Nunca toco 2 ni 3, pero abarca
    la mitad del menu. Ni un si ni un no: DUDOSA.
    """
    r = resultado_falso([4.0, 6.0, 5.0, 4.0, 5.0, 5.0])
    assert r.dispersion_pct == 50.0
    assert r.estabilidad == wf.DUDOSA
    assert not r.el_elegido_es_estable, "DUDOSA no es un si tibio"


def test_un_solo_paso_de_diferencia_sigue_siendo_estable():
    """ETHUSDT 15m: [6,6,6,6,5,6]. Un vecino de distancia no es inestabilidad."""
    r = resultado_falso([6.0, 6.0, 6.0, 6.0, 5.0, 6.0])
    assert r.dispersion_pct == 25.0
    assert r.estabilidad == wf.ESTABLE


def test_la_dispersion_se_mide_contra_el_menu_no_contra_lo_elegido():
    """
    Elegir entre 4 y 5 es afinar si el menu iba de 2 a 6, y es recorrerlo
    entero si el menu eran solo 4 y 5. El mismo par de elecciones tiene que
    dar veredictos distintos.
    """
    apretado = resultado_falso([4.0, 5.0, 4.0, 5.0], candidatos=[2.0, 3.0, 4.0, 5.0, 6.0])
    suelto = resultado_falso([4.0, 5.0, 4.0, 5.0], candidatos=[4.0, 5.0])

    assert apretado.dispersion_pct == 25.0
    assert apretado.estabilidad == wf.ESTABLE
    assert suelto.dispersion_pct == 100.0
    assert suelto.estabilidad == wf.INESTABLE


def test_sin_candidatos_numericos_se_cae_al_criterio_por_conteo():
    """
    Para un parametro categorico la distancia entre dos valores no significa
    nada, asi que no se puede medir dispersion. No tiene que explotar.
    """
    r = resultado_falso(["adx", "adx", "adx", "pendiente"],
                        candidatos=["adx", "pendiente"])
    assert r.dispersion_pct is None
    assert r.estabilidad == wf.ESTABLE   # 3 de 4 es mayoria estricta

    disparejo = resultado_falso(["adx", "adx", "pendiente", "pendiente"],
                                candidatos=["adx", "pendiente"])
    assert disparejo.estabilidad == wf.INESTABLE, "un empate no es una eleccion"


def test_el_walk_forward_de_verdad_recuerda_su_menu(velas, cfg):
    """Si no guardara los candidatos, la dispersion no se podria calcular."""
    r = correr(velas, cfg, candidatos=(2.0, 4.0, 6.0), anios_entrenamiento=2)
    assert r.candidatos == [2.0, 4.0, 6.0]
    assert r.dispersion_pct is not None


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


# ===========================================================================
# El respaldo: cuanta evidencia habia detras de cada eleccion
# ===========================================================================

def ventana_con_respaldo(puntajes, ops, elegido):
    t = pd.Timestamp("2020-01-01", tz="UTC")
    return wf.Ventana(
        numero=1, entrena_desde=t, entrena_hasta=t, prueba_desde=t,
        prueba_hasta=t, elegido=elegido, resultado_entrenamiento=puntajes[elegido],
        metricas_prueba=wf.motor.Metricas(), operaciones_prueba=[],
        candidatos_evaluados=puntajes, operaciones_entrenamiento=ops,
    )


def test_el_respaldo_son_las_operaciones_del_valor_elegido():
    v = ventana_con_respaldo({2.0: 10.0, 6.0: 50.0}, {2.0: 80, 6.0: 31}, 6.0)
    assert v.respaldo == 31, "cuenta las del elegido, no las del que mas opero"


def test_sin_operaciones_detras_la_eleccion_es_arbitraria():
    """
    Un candidato que no opero nunca puede ganar igual: si todos dan 0.00, el
    max() devuelve el primero de la lista. Eso no es haber elegido.
    """
    v = ventana_con_respaldo({2.0: 0.0, 6.0: 0.0}, {2.0: 0, 6.0: 0}, 2.0)
    assert v.respaldo == 0
    assert v.la_eleccion_fue_arbitraria


def test_un_empate_perfecto_tambien_es_arbitrario():
    """Con operaciones pero puntajes identicos, gano el orden de la lista."""
    v = ventana_con_respaldo({2.0: 25.0, 6.0: 25.0}, {2.0: 40, 6.0: 40}, 2.0)
    assert v.margen == 0.0
    assert v.la_eleccion_fue_arbitraria


def test_con_margen_y_operaciones_la_eleccion_no_es_arbitraria():
    v = ventana_con_respaldo({2.0: 10.0, 6.0: 50.0}, {2.0: 80, 6.0: 31}, 6.0)
    assert v.margen == 40.0
    assert not v.la_eleccion_fue_arbitraria


def test_el_margen_se_mide_contra_el_segundo_no_contra_el_peor():
    """Contra el peor siempre parece holgado y esconde un empate arriba."""
    v = ventana_con_respaldo(
        {2.0: -100.0, 4.0: 49.9, 6.0: 50.0}, {2.0: 5, 4.0: 30, 6.0: 31}, 6.0
    )
    assert v.margen == pytest.approx(0.1)


def test_la_bandera_de_arbitraria_NO_agarra_una_muestra_diminuta():
    """
    Deja constancia de una limitacion, no de una virtud.

    El 29-ago-2026 una ventana de ETHUSDT 1h eligio 2.0x -- el extremo
    opuesto del menu -- sobre NUEVE operaciones de entrenamiento. Elegir
    sobre nueve operaciones es basura, y esta bandera dice que no pasa nada,
    porque hay operaciones y hay margen.

    Es a proposito: poner un umbral ("menos de N operaciones") habria sido
    inventar un numero mirando estos mismos datos. El precio es que la
    bandera casi nunca sirve y hay que leer la columna cruda de respaldo.
    Si algun dia se le agrega un umbral, esta prueba tiene que cambiar --
    y esa discusion es justamente la que no hay que saltearse.
    """
    v = ventana_con_respaldo({2.0: 18.0, 6.0: 10.7}, {2.0: 9, 6.0: 11}, 2.0)
    assert v.respaldo == 9
    assert not v.la_eleccion_fue_arbitraria


def test_el_resultado_reporta_la_ventana_peor_respaldada(velas, cfg):
    r = correr(velas, cfg, candidatos=(2.0, 4.0), anios_entrenamiento=2)
    assert r.respaldo_minimo == min(v.respaldo for v in r.ventanas)
    for v in r.ventanas:
        assert v.operaciones_entrenamiento.keys() == {2.0, 4.0}


def test_el_informe_avisa_cuando_una_eleccion_fue_arbitraria():
    r = wf.ResultadoWalkForward(
        [ventana_con_respaldo({2.0: 0.0, 6.0: 0.0}, {2.0: 0, 6.0: 0}, 2.0)],
        [], 500.0, 500.0, [2.0, 6.0],
    )
    assert "ARBITRARIA" in r.informe()
    assert len(r.ventanas_arbitrarias) == 1
