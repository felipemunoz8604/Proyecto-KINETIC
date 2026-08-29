"""
Pruebas del motor de backtest.

Cada prueba ataca una de las formas en que un backtest se regala plata. Se
arman velas a mano con los indicadores ya puestos, para poder controlar
exactamente cuando hay senal y cuando no.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from backtesting import backtest_engine as motor  # noqa: E402
from risk import position_sizing  # noqa: E402


@pytest.fixture
def cfg() -> dict:
    return {
        "capital": {"monto": 10_000.0},
        "riesgo": {
            "por_operacion_pct": 1.0,
            "perdida_diaria_max_pct": 50.0,   # holgado: no queremos que estorbe
            "max_posiciones_simultaneas": 1,
            "kill_switch": False,
        },
        "stops": {"atr_periodo": 14, "atr_multiplicador_sl": 2.0},
        "costos": {"comision_por_lado_pct": 0.1, "slippage_pct_por_lado": 0.05},
        "estrategia": {
            "tendencia": {"ema_rapida": 9, "ema_lenta": 21},
            "consolidacion": {"velas": 50, "umbral_desviacion_pct": 2.0},
            "volumen": {"periodo_promedio": 50, "multiplicador_minimo": 2.0},
            "regimen": {"metodo": "adx", "adx_periodo": 14, "adx_minimo": 20.0},
            "portfolio_guard": {
                "sma_periodo": 200,
                "distancia_maxima_bajo_sma_pct": None,   # guardia apagada
                "una_posicion_por_grupo": True,
            },
        },
        "backtest_motor": {
            "entrada_en_apertura_siguiente": True,
            "descartar_dias_iniciales": 0,
            "capital_compuesto": True,
        },
    }


SIN_SENAL = {
    "adx": 5.0,          # regimen no apto: corta en el primer filtro
    "desv_pct": 1.0, "techo": 1e9, "vol_promedio": 1000.0,
    "ema_rapida": 100.0, "ema_lenta": 100.0, "atr": 5.0,
}
CON_SENAL = {
    "adx": 30.0, "desv_pct": 1.0, "techo": 100.0, "vol_promedio": 1000.0,
    "ema_rapida": 105.0, "ema_lenta": 100.0, "atr": 5.0,
}


def construir(filas: list[dict]) -> pd.DataFrame:
    """Arma un DataFrame de velas con indicadores ya calculados."""
    df = pd.DataFrame(filas)
    df.index = pd.date_range("2026-01-01", periods=len(filas), freq="1h", tz="UTC")
    df["sma_macro"] = 1.0
    return df


def vela(o, h, l, c, v=3000.0, senal=False) -> dict:
    base = dict(CON_SENAL if senal else SIN_SENAL)
    base.update({"open": o, "high": h, "low": l, "close": c, "volume": v})
    return base


REGLAS = position_sizing.ReglasSimbolo(
    paso_cantidad=0.000001, cantidad_minima=0.000001, compra_minima=1.0
)


def correr(df, cfg):
    return motor.correr(df, cfg, par="TESTUSDT", temporalidad="1h", reglas_simbolo=REGLAS)


# ===========================================================================
# 1. La entrada va a la apertura de la vela SIGUIENTE
# ===========================================================================

def test_la_entrada_es_a_la_apertura_de_la_vela_siguiente(cfg):
    """
    Comprar al cierre de la vela de senal es imposible: recien ahi sabes
    cual fue el cierre. La vela de senal cierra en 110; la siguiente abre en
    130. El backtest tiene que pagar 130, no 110.
    """
    df = construir([
        vela(100, 101, 99, 110, senal=True),    # senal, cierra en 110
        vela(130, 140, 128, 135),               # abre en 130: aca se compra
        vela(135, 140, 130, 138),
        vela(138, 140, 60, 65),                 # se derrumba: salta el stop
    ])
    r = correr(df, cfg)

    assert len(r.operaciones) == 1
    op = r.operaciones[0]
    esperado = 130 * 1.0005   # apertura + slippage
    assert op.entrada_precio == pytest.approx(esperado)
    assert op.entrada_momento == df.index[1]


def test_sin_vela_siguiente_no_se_abre_nada(cfg):
    """Si la senal cae en la ultima vela, no hay donde ejecutarla."""
    df = construir([vela(100, 101, 99, 100), vela(100, 111, 99, 110, senal=True)])
    assert len(correr(df, cfg).operaciones) == 0


# ===========================================================================
# 2. El stop no siempre se ejecuta en su precio
# ===========================================================================

def test_si_la_vela_abre_debajo_del_stop_se_ejecuta_ahi(cfg):
    """
    Suponer que el stop siempre se cumple en su precio es regalarse plata.
    Entrada ~100, ATR 5, stop en ~90. La vela de derrumbe ABRE en 70: la
    orden se ejecuta en 70, no en 90.
    """
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),     # entra a 100 (+slippage), stop ~90,05
        vela(70, 72, 65, 68),        # abre en 70, ya debajo del stop
    ])
    r = correr(df, cfg)

    op = r.operaciones[0]
    assert op.salida_precio == pytest.approx(70 * 0.9995), "se ejecuto al stop y no a la apertura"
    assert "hueco" in op.motivo_salida


def test_si_la_vela_solo_TOCA_el_stop_se_ejecuta_en_el_stop(cfg):
    """
    Ojo con el stop esperado: el trailing YA se mueve en la propia vela de
    entrada. Se entra a 100,05 con stop inicial en 90,05, pero esa misma
    vela cierra en 101, asi que el chandelier lo sube a 101 - 10 = 91. Es
    correcto: la vela cerro por encima de la entrada.
    """
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),     # entra a 100,05; la vela cierra en 101
        vela(101, 102, 85, 95),      # el minimo perfora el stop, pero abre arriba
    ])
    op = correr(df, cfg).operaciones[0]

    assert op.stop_inicial == pytest.approx(100 * 1.0005 - 10.0)
    assert op.stop_final == pytest.approx(91.0)
    assert op.salida_precio == pytest.approx(91.0 * 0.9995)
    assert op.motivo_salida == "stop"


def test_una_posicion_puede_abrirse_y_morir_en_la_misma_vela(cfg):
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 101, 50, 55),      # abre en 100 y se desploma en la misma vela
    ])
    r = correr(df, cfg)
    assert len(r.operaciones) == 1
    assert r.operaciones[0].entrada_momento == r.operaciones[0].salida_momento


# ===========================================================================
# 3. Los costos
# ===========================================================================

def test_se_cobran_los_costos_de_entrada_y_de_salida(cfg):
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 102, 85, 95),
    ])
    op = correr(df, cfg).operaciones[0]

    valor_entrada = op.entrada_precio * op.cantidad
    valor_salida = op.salida_precio * op.cantidad
    esperado = (valor_entrada + valor_salida) * 0.001
    assert op.costos == pytest.approx(esperado, rel=1e-9)
    assert op.resultado_neto == pytest.approx(op.resultado_bruto - op.costos)


def test_sin_costos_el_resultado_es_mejor(cfg):
    """Comprobacion de cordura: si los costos no cambiaran nada, no se cobran."""
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 130, 100, 128),
        vela(128, 130, 60, 65),
    ])
    con = correr(df, cfg).metricas.capital_final

    cfg["costos"] = {"comision_por_lado_pct": 0.0, "slippage_pct_por_lado": 0.0}
    sin = correr(df, cfg).metricas.capital_final
    assert sin > con


def test_el_slippage_empeora_los_dos_lados(cfg):
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 102, 85, 95),
    ])
    cfg["costos"]["slippage_pct_por_lado"] = 0.0
    sin = correr(df, cfg).operaciones[0]
    cfg["costos"]["slippage_pct_por_lado"] = 0.5
    con = correr(df, cfg).operaciones[0]

    assert con.entrada_precio > sin.entrada_precio, "se deberia comprar mas caro"
    assert con.salida_precio < sin.salida_precio, "se deberia vender mas barato"


# ===========================================================================
# 4. Datos que no significan nada
# ===========================================================================

def test_se_descartan_los_primeros_dias(cfg):
    cfg["backtest_motor"]["descartar_dias_iniciales"] = 1   # 24 velas de 1h
    filas = [vela(100, 101, 99, 110, senal=True)] + [vela(100, 102, 99, 101)] * 40
    r = correr(construir(filas), cfg)

    assert r.metricas.desde == construir(filas).index[24]
    assert len(r.operaciones) == 0, "la senal estaba en el tramo descartado"


# ===========================================================================
# 5. El trailing dentro del backtest
# ===========================================================================

def test_el_trailing_convierte_una_subida_en_ganancia_asegurada(cfg):
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),      # entra ~100, stop ~90
        vela(101, 141, 100, 140),     # sube: stop pasa a 130
        vela(140, 141, 100, 105),     # cae y toca 130 -> sale ganando
    ])
    op = correr(df, cfg).operaciones[0]

    assert op.gano, "con el trailing en 130 y entrada en 100 tendria que ganar"
    assert op.stop_final > op.stop_inicial
    assert op.stop_final > op.entrada_precio


# ===========================================================================
# 6. Nada mira al futuro
# ===========================================================================

def test_agregar_velas_al_final_no_cambia_las_operaciones_ya_cerradas(cfg):
    """
    La prueba mas fuerte del motor. Se corre sobre las primeras N velas, y
    despues sobre la serie entera. Las operaciones que ya habian cerrado
    tienen que salir identicas: si cambian, el motor estaba usando velas
    que en ese momento no existian.
    """
    filas = [
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 102, 85, 95),        # cierra la operacion 1
        vela(95, 96, 94, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 102, 80, 85),        # cierra la operacion 2
    ]
    futuras = [vela(85, 500, 84, 480), vela(480, 500, 10, 12)]

    cortas = correr(construir(filas), cfg).operaciones
    largas = correr(construir(filas + futuras), cfg).operaciones

    assert len(cortas) == 2
    for previa, posterior in zip(cortas, largas):
        assert previa.entrada_precio == pytest.approx(posterior.entrada_precio)
        assert previa.salida_precio == pytest.approx(posterior.salida_precio)
        assert previa.resultado_neto == pytest.approx(posterior.resultado_neto)


# ===========================================================================
# 7. Los limites de riesgo mandan tambien en el backtest
# ===========================================================================

def test_el_limite_diario_frena_las_entradas(cfg):
    """El portero tiene que aplicar igual en el backtest que en vivo."""
    cfg["riesgo"]["perdida_diaria_max_pct"] = 0.5   # medio punto: una perdida lo agota
    filas = []
    for _ in range(4):
        filas += [
            vela(100, 101, 99, 110, senal=True),
            vela(100, 102, 99, 101),
            vela(101, 102, 80, 85),
        ]
    r = correr(construir(filas), cfg)

    assert len(r.operaciones) == 1, "el limite diario deberia frenar las siguientes"
    assert any(k.startswith("riesgo:") for k in r.metricas.rechazos)


def test_el_kill_switch_impide_toda_entrada(cfg):
    cfg["riesgo"]["kill_switch"] = True
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 102, 85, 95),
    ])
    assert len(correr(df, cfg).operaciones) == 0


# ===========================================================================
# 8. Metricas
# ===========================================================================

def test_las_metricas_se_calculan_bien():
    m = motor.Metricas(
        operaciones=10, ganadoras=4, perdedoras=6,
        capital_inicial=1000.0, capital_final=1200.0,
        ganancia_bruta=500.0, perdida_bruta=300.0,
    )
    assert m.profit_factor == pytest.approx(500 / 300)
    assert m.tasa_acierto_pct == pytest.approx(40.0)
    assert m.retorno_total_pct == pytest.approx(20.0)
    assert m.esperanza_por_operacion == pytest.approx(20.0)


def test_profit_factor_sin_perdidas_es_infinito():
    m = motor.Metricas(operaciones=1, ganancia_bruta=100.0, perdida_bruta=0.0)
    assert m.profit_factor == float("inf")


def test_el_drawdown_mide_la_peor_caida_desde_un_pico():
    curva = pd.Series([100.0, 120, 90, 130, 110])
    # El peor tramo es 120 -> 90: una caida del 25%.
    assert motor._drawdown_maximo_pct(curva) == pytest.approx(25.0)


def test_sin_operaciones_el_informe_dice_donde_se_cayo_todo(cfg):
    df = construir([vela(100, 101, 99, 100)] * 5)
    r = correr(df, cfg)
    assert r.metricas.operaciones == 0
    assert "regimen" in r.metricas.rechazos
    assert "Sin operaciones" in r.metricas.informe()


def test_una_posicion_abierta_al_final_se_cierra_y_se_cuenta(cfg):
    df = construir([
        vela(100, 101, 99, 110, senal=True),
        vela(100, 102, 99, 101),
        vela(101, 105, 100, 104),   # termina el periodo con la posicion viva
    ])
    r = correr(df, cfg)
    assert len(r.operaciones) == 1
    assert r.operaciones[0].motivo_salida == "fin del periodo"
