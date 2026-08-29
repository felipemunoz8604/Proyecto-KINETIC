"""
Pruebas de los indicadores.

Dos clases de prueba, y la segunda es la que de verdad importa:

1. VALORES: que las cuentas den lo que tienen que dar, contra numeros
   calculados a mano.
2. NADA MIRA AL FUTURO: se calcula el indicador con la serie completa,
   despues se corta la serie en cada punto y se recalcula. Si algun valor
   cambia, el indicador estaba usando velas que en ese momento no existian.
   Ese es el error que hace que un backtest se vea hermoso y el bot en vivo
   pierda plata.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from strategy import indicators as ind  # noqa: E402


@pytest.fixture
def velas() -> pd.DataFrame:
    """200 velas sinteticas con tendencia y ruido reproducible."""
    generador = np.random.default_rng(20260828)
    n = 200
    cierre = 100 + np.cumsum(generador.normal(0.15, 1.2, n))
    alto = cierre + np.abs(generador.normal(0.6, 0.3, n))
    bajo = cierre - np.abs(generador.normal(0.6, 0.3, n))
    apertura = np.concatenate([[cierre[0]], cierre[:-1]])
    volumen = np.abs(generador.normal(1000, 250, n))
    return pd.DataFrame(
        {"open": apertura, "high": alto, "low": bajo, "close": cierre, "volume": volumen},
        index=pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC"),
    )


# ---------------------------------------------------------------------------
# 1. Valores
# ---------------------------------------------------------------------------

def test_sma_da_el_promedio_a_mano():
    serie = pd.Series([1.0, 2, 3, 4, 5, 6])
    resultado = ind.sma(serie, 3)
    assert pd.isna(resultado.iloc[0]) and pd.isna(resultado.iloc[1])
    assert resultado.iloc[2] == pytest.approx(2.0)   # (1+2+3)/3
    assert resultado.iloc[5] == pytest.approx(5.0)   # (4+5+6)/3


def test_ema_da_el_valor_a_mano():
    """EMA de 3: alpha = 2/(3+1) = 0.5. Se sigue la cuenta paso a paso."""
    serie = pd.Series([10.0, 20, 30, 40])
    resultado = ind.ema(serie, 3)
    # Arranca en 10; 0.5*20+0.5*10 = 15; 0.5*30+0.5*15 = 22.5; 0.5*40+0.5*22.5 = 31.25
    assert pd.isna(resultado.iloc[0]) and pd.isna(resultado.iloc[1])
    assert resultado.iloc[2] == pytest.approx(22.5)
    assert resultado.iloc[3] == pytest.approx(31.25)


def test_ema_reacciona_mas_rapido_que_la_sma():
    """
    Es la razon de ser de la EMA: si no, usariamos SMA y listo.

    Ojo con como se mide. La ventaja de la EMA esta en las primeras velas
    despues del cambio. Diez velas despues de un salto, una SMA de 10 ya
    absorbio el nivel nuevo por completo (vale exactamente 200) mientras la
    EMA todavia arrastra el pasado. Comparar ahi da lo contrario de lo que
    uno espera, y no prueba nada.
    """
    serie = pd.concat([pd.Series([100.0] * 50), pd.Series([200.0] * 3)], ignore_index=True)
    ema_3_velas = ind.ema(serie, 10).iloc[-1]
    sma_3_velas = ind.sma(serie, 10).iloc[-1]

    assert ema_3_velas > sma_3_velas, (
        f"a 3 velas del salto la EMA ({ema_3_velas:.1f}) deberia ir por delante "
        f"de la SMA ({sma_3_velas:.1f})"
    )
    assert ema_3_velas > 140.0  # ~145: ya recorrio casi la mitad del salto
    assert sma_3_velas == pytest.approx(130.0)  # (7*100 + 3*200)/10


def test_rango_verdadero_toma_el_hueco_en_cuenta():
    df = pd.DataFrame({"high": [10.0, 20.0], "low": [9.0, 19.0], "close": [9.5, 19.5]})
    tr = ind.rango_verdadero(df)
    assert tr.iloc[0] == pytest.approx(1.0)   # sin cierre previo: alto - bajo
    # Segunda vela: alto-bajo = 1, pero |20 - 9.5| = 10.5 por el hueco.
    assert tr.iloc[1] == pytest.approx(10.5)


def test_atr_usa_suavizado_de_wilder_no_ema_comun(velas):
    """
    El error clasico es usar alpha=2/(p+1) en vez de 1/p. Da un numero
    parecido, y por eso pasa desapercibido.
    """
    tr = ind.rango_verdadero(velas)
    wilder = tr.ewm(alpha=1 / 14, adjust=False).mean()
    ema_comun = tr.ewm(span=14, adjust=False).mean()

    resultado = ind.atr(velas, 14)
    assert resultado.iloc[-1] == pytest.approx(wilder.iloc[-1])
    assert resultado.iloc[-1] != pytest.approx(ema_comun.iloc[-1])


def test_atr_es_siempre_positivo(velas):
    valores = ind.atr(velas, 14).dropna()
    assert len(valores) > 0
    assert (valores > 0).all()


def test_adx_queda_entre_0_y_100(velas):
    resultado = ind.adx(velas, 14).dropna()
    assert len(resultado) > 0
    assert resultado["adx"].between(0, 100).all()
    assert resultado["di_mas"].between(0, 100).all()
    assert resultado["di_menos"].between(0, 100).all()


def test_adx_distingue_tendencia_de_lateral():
    """Una rampa limpia debe dar ADX mucho mas alto que un serrucho."""
    n = 200
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")

    subida = np.arange(n, dtype=float) + 100
    tendencia = pd.DataFrame(
        {"open": subida, "high": subida + 1, "low": subida - 1, "close": subida,
         "volume": np.full(n, 1000.0)}, index=idx)

    serrucho = 100 + np.tile([0.0, 1.0], n // 2)
    lateral = pd.DataFrame(
        {"open": serrucho, "high": serrucho + 1, "low": serrucho - 1, "close": serrucho,
         "volume": np.full(n, 1000.0)}, index=idx)

    adx_tendencia = ind.adx(tendencia, 14)["adx"].iloc[-1]
    adx_lateral = ind.adx(lateral, 14)["adx"].iloc[-1]

    assert adx_tendencia > 50, f"ADX en tendencia limpia deberia ser alto, dio {adx_tendencia}"
    assert adx_lateral < 25, f"ADX en serrucho deberia ser bajo, dio {adx_lateral}"


def test_bollinger_tiene_las_bandas_en_orden(velas):
    bandas = ind.bollinger(velas["close"], 20, 2.0).dropna()
    assert (bandas["bb_superior"] > bandas["bb_centro"]).all()
    assert (bandas["bb_centro"] > bandas["bb_inferior"]).all()


# ---------------------------------------------------------------------------
# El shift(1): la vela actual no puede estar en su propio rango
# ---------------------------------------------------------------------------

def test_rango_previo_excluye_la_vela_actual():
    """
    Sin el shift(1), la vela que rompe el rango forma parte del rango que
    esta rompiendo, y su cierre nunca puede superar su propio maximo.
    """
    df = pd.DataFrame(
        {
            "high": [10.0, 11, 12, 13, 99],   # la ultima es la ruptura
            "low": [9.0, 10, 11, 12, 50],
            "close": [9.5, 10.5, 11.5, 12.5, 98],
            "volume": [1.0] * 5,
        }
    )
    rango = ind.rango_previo(df, 3)

    # En la vela 4 (indice 4) el techo debe salir de las velas 1,2,3 -> 13.
    assert rango["techo"].iloc[4] == pytest.approx(13.0)
    # Y el cierre de esa vela SI puede superarlo. Ahi esta la ruptura.
    assert df["close"].iloc[4] > rango["techo"].iloc[4]


def test_volumen_promedio_excluye_la_vela_actual():
    """
    La vela de ruptura trae volumen enorme. Si entra en su propio promedio,
    el filtro se ablanda justo cuando tiene que ser exigente.
    """
    df = pd.DataFrame({"volume": [100.0, 100, 100, 100, 10_000]})
    promedio = ind.volumen_promedio(df, 4)
    assert promedio.iloc[4] == pytest.approx(100.0), "la vela de ruptura se colo en su promedio"


def test_el_filtro_de_volumen_se_dispara_como_corresponde():
    df = pd.DataFrame({"volume": [100.0] * 50 + [250.0]})
    promedio = ind.volumen_promedio(df, 50)
    assert df["volume"].iloc[-1] > 2.0 * promedio.iloc[-1]


# ---------------------------------------------------------------------------
# 2. Nada mira al futuro
# ---------------------------------------------------------------------------

INDICADORES_A_VERIFICAR = {
    "sma_20": lambda d: ind.sma(d["close"], 20),
    "ema_9": lambda d: ind.ema(d["close"], 9),
    "ema_21": lambda d: ind.ema(d["close"], 21),
    "atr_14": lambda d: ind.atr(d, 14),
    "atr_pct_14": lambda d: ind.atr_porcentual(d, 14),
    "desv_pct_50": lambda d: ind.desviacion_porcentual(d["close"], 50),
    "adx_14": lambda d: ind.adx(d, 14)["adx"],
    "di_mas_14": lambda d: ind.adx(d, 14)["di_mas"],
    "techo_50": lambda d: ind.rango_previo(d, 50)["techo"],
    "piso_50": lambda d: ind.rango_previo(d, 50)["piso"],
    "vol_prom_50": lambda d: ind.volumen_promedio(d, 50),
    "bb_superior": lambda d: ind.bollinger(d["close"], 20)["bb_superior"],
    "pendiente_sma": lambda d: ind.pendiente_sma(d["close"], 50, 10),
}


@pytest.mark.parametrize("nombre", sorted(INDICADORES_A_VERIFICAR))
def test_ningun_indicador_mira_al_futuro(nombre, velas):
    """
    Se calcula el indicador con toda la serie. Despues se corta la serie en
    varios puntos y se recalcula. El valor en el ultimo punto de cada corte
    tiene que ser identico: si cambia, el indicador estaba usando velas
    posteriores, que en vivo no existirian.
    """
    funcion = INDICADORES_A_VERIFICAR[nombre]
    completo = funcion(velas)

    for corte in (120, 150, 180, 199):
        parcial = funcion(velas.iloc[: corte + 1])
        esperado = completo.iloc[corte]
        obtenido = parcial.iloc[corte]

        if pd.isna(esperado) and pd.isna(obtenido):
            continue
        assert obtenido == pytest.approx(esperado, rel=1e-9), (
            f"{nombre} cambia de valor en la vela {corte} segun cuantas velas "
            f"posteriores existan: {obtenido} con la serie cortada contra "
            f"{esperado} con la serie completa. Esta mirando al futuro."
        )


# ---------------------------------------------------------------------------
# Calentamiento
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "nombre,minimo_nan",
    [("sma_20", 19), ("ema_9", 8), ("atr_14", 14), ("adx_14", 28), ("techo_50", 50)],
)
def test_los_indicadores_no_inventan_valores_antes_de_calentar(nombre, minimo_nan, velas):
    valores = INDICADORES_A_VERIFICAR[nombre](velas)
    assert valores.iloc[:minimo_nan].isna().all(), (
        f"{nombre} devuelve numeros antes de tener datos suficientes"
    )


def test_agregar_indicadores_no_toca_el_dataframe_original(velas):
    columnas_antes = list(velas.columns)
    cfg = {
        "estrategia": {
            "tendencia": {"ema_rapida": 9, "ema_lenta": 21},
            "consolidacion": {"velas": 50},
            "volumen": {"periodo_promedio": 50},
            "regimen": {"adx_periodo": 14},
            "portfolio_guard": {"sma_periodo": 100},
        },
        "stops": {"atr_periodo": 14},
    }
    salida = ind.agregar_indicadores(velas, cfg)

    assert list(velas.columns) == columnas_antes, "se modifico el DataFrame original"
    for esperada in ("ema_rapida", "ema_lenta", "atr", "techo", "piso", "adx", "sma_macro"):
        assert esperada in salida.columns
