"""
Indicadores tecnicos de KINETIC, calculados a mano.

Por que a mano y no con una libreria: el MEGAPROMPT prohibe `pandas_ta`
(bug de compatibilidad con numpy reciente al importar `NaN`), y las
alternativas obligan a fijar una dependencia mas para hacer unas cuentas
que caben en un archivo. Ademas, un indicador escrito aca es un indicador
que se puede leer y probar.

LA REGLA QUE GOBIERNA ESTE ARCHIVO: NADA MIRA AL FUTURO
-------------------------------------------------------
El valor de cualquier indicador en la vela `i` puede usar la vela `i` y
todas las anteriores. Nunca la `i+1`. Si se rompe esa regla, el backtest da
un resultado espectacular y el bot en vivo pierde, porque en vivo el futuro
no existe todavia. No es un error que se vea leyendo el codigo: se ve
cuando el numero es demasiado bueno.

`tests/test_indicators.py` lo verifica de la unica forma que sirve: calcula
cada indicador sobre la serie completa, despues la corta en cada punto y
recalcula. Si algun valor cambia, algo estaba espiando adelante.

CALENTAMIENTO
-------------
Un indicador de periodo 14 no tiene un valor valido antes de la vela 14.
Las funciones de aca devuelven `NaN` en ese tramo en vez de un numero
inventado con datos insuficientes. Es a proposito: el backtest debe
saltearse esas velas, no operarlas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Promedios
# ---------------------------------------------------------------------------

def sma(serie: pd.Series, periodo: int) -> pd.Series:
    """Promedio simple de las ultimas `periodo` velas."""
    return serie.rolling(window=periodo, min_periods=periodo).mean()


def ema(serie: pd.Series, periodo: int) -> pd.Series:
    """
    Promedio exponencial: pesa mas lo reciente.

    Se anulan las primeras `periodo - 1` velas. Pandas devolveria un numero
    ahi igual, pero seria una EMA calculada con menos datos de los que su
    periodo pide, y en las primeras velas eso se parece mas al precio que a
    un promedio.
    """
    valores = serie.ewm(span=periodo, adjust=False).mean()
    valores.iloc[: periodo - 1] = np.nan
    return valores


def _suavizado_wilder(serie: pd.Series, periodo: int) -> pd.Series:
    """
    El suavizado de Wilder, que es lo que usan ATR y ADX de verdad.

    No es la EMA comun: usa alpha = 1/periodo en vez de 2/(periodo+1). Es la
    confusion mas frecuente al programar estos dos indicadores, y da valores
    parecidos pero distintos a los de cualquier plataforma.
    """
    return serie.ewm(alpha=1.0 / periodo, adjust=False).mean()


# ---------------------------------------------------------------------------
# Volatilidad
# ---------------------------------------------------------------------------

def rango_verdadero(df: pd.DataFrame) -> pd.Series:
    """
    True Range: cuanto se movio el precio en la vela, contando el hueco
    contra el cierre anterior.

    Es el mayor de: (alto - bajo), |alto - cierre previo|, |bajo - cierre previo|.
    """
    cierre_previo = df["close"].shift(1)
    return pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - cierre_previo).abs(),
            (df["low"] - cierre_previo).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """
    Average True Range: cuanto se mueve el precio en promedio.

    De aca sale la distancia del stop loss (entrada - 2 x ATR). Un stop fijo
    en porcentaje trata igual a un mercado tranquilo y a uno enloquecido; el
    ATR se adapta solo.
    """
    tr = rango_verdadero(df)
    valores = _suavizado_wilder(tr, periodo)
    valores.iloc[:periodo] = np.nan  # la primera TR no tiene cierre previo
    return valores


def atr_porcentual(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """ATR expresado como % del precio. Sirve para comparar entre pares."""
    return atr(df, periodo) / df["close"] * 100.0


def desviacion_porcentual(serie: pd.Series, periodo: int) -> pd.Series:
    """
    Desviacion estandar de los cierres, como % del precio.

    Es la otra forma de medir consolidacion: cuando este numero esta bajo,
    el precio lleva rato quieto y una ruptura significa algo.
    """
    return serie.rolling(window=periodo, min_periods=periodo).std(ddof=0) / serie * 100.0


def desviacion_relativa(
    df: pd.DataFrame, periodo_cons: int, periodo_atr: int
) -> pd.Series:
    """
    Consolidacion SIN UNIDADES: dispersion de N velas / rango tipico de UNA.

    POR QUE EXISTE ESTA FUNCION
    ---------------------------
    `desviacion_porcentual` devuelve un numero en % del precio, y compararlo
    contra un umbral fijo (0,75%) parece razonable hasta que se cambia de
    temporalidad. **La volatilidad escala con la temporalidad**: 0,75% es un
    umbral sensato para velas de 15 minutos y absurdamente estricto para
    velas de 4 horas, que se mueven mucho mas. Con el umbral absoluto, 4h
    daba 0-3 operaciones y parecia que no habia señales; en realidad se las
    estaba midiendo con una regla calibrada para otra escala.

    Dividir por el ATR% cancela las unidades: numerador y denominador escalan
    juntos. El resultado se lee como "cuantas velas tipicas de ancho tiene la
    dispersion de la ventana". Un valor bajo es consolidacion de verdad, en
    cualquier temporalidad y en cualquier par.

    Es causal: los dos ingredientes miran solo hacia atras.

    (Es el mismo error que TITAN tenia con `MAX_SPREAD = 2.0`, una constante
    pensada para EURUSD que no significa nada para GOLD. Preferir umbrales
    relativos a la estadistica propia del instrumento sobre constantes
    absolutas.)
    """
    dispersion = desviacion_porcentual(df["close"], periodo_cons)
    tipico = atr_porcentual(df, periodo_atr)
    # Sin ATR valido no hay con que normalizar: NaN, que aguas abajo se lee
    # como "todavia calentando" y no como "consolido".
    return dispersion / tipico.where(tipico > 0)


def bollinger(
    serie: pd.Series, periodo: int = 20, desviaciones: float = 2.0
) -> pd.DataFrame:
    """Banda central (SMA) y las dos bandas a N desviaciones estandar."""
    centro = sma(serie, periodo)
    desv = serie.rolling(window=periodo, min_periods=periodo).std(ddof=0)
    return pd.DataFrame(
        {
            "bb_centro": centro,
            "bb_superior": centro + desviaciones * desv,
            "bb_inferior": centro - desviaciones * desv,
        }
    )


# ---------------------------------------------------------------------------
# Regimen: hay tendencia o esto es lateral
# ---------------------------------------------------------------------------

def adx(df: pd.DataFrame, periodo: int = 14) -> pd.DataFrame:
    """
    ADX y sus dos componentes direccionales (+DI y -DI).

    Que mide: la FUERZA de la tendencia, no su direccion. Un ADX alto con
    -DI arriba es una tendencia bajista fuerte. Por convencion, por debajo de
    20 se considera mercado lateral -- y ahi las rupturas suelen ser falsas,
    que es exactamente por lo que este filtro existe.
    """
    alto, bajo = df["high"], df["low"]

    subida = alto.diff()
    bajada = -bajo.diff()

    # Solo cuenta el movimiento que domina: si el maximo subio mas de lo que
    # el minimo bajo, es +DM, y viceversa. Nunca los dos a la vez.
    dm_mas = pd.Series(
        np.where((subida > bajada) & (subida > 0), subida, 0.0), index=df.index
    )
    dm_menos = pd.Series(
        np.where((bajada > subida) & (bajada > 0), bajada, 0.0), index=df.index
    )

    tr_suave = _suavizado_wilder(rango_verdadero(df), periodo)
    di_mas = 100.0 * _suavizado_wilder(dm_mas, periodo) / tr_suave
    di_menos = 100.0 * _suavizado_wilder(dm_menos, periodo) / tr_suave

    suma = di_mas + di_menos
    dx = 100.0 * (di_mas - di_menos).abs() / suma.replace(0.0, np.nan)
    adx_valores = _suavizado_wilder(dx.fillna(0.0), periodo)

    # ADX necesita dos calentamientos encadenados: uno para los DI y otro
    # para suavizar el DX. Antes de 2*periodo el numero no significa nada.
    calentamiento = 2 * periodo
    adx_valores.iloc[:calentamiento] = np.nan
    di_mas.iloc[:periodo] = np.nan
    di_menos.iloc[:periodo] = np.nan

    return pd.DataFrame({"adx": adx_valores, "di_mas": di_mas, "di_menos": di_menos})


def pendiente_sma(serie: pd.Series, periodo: int = 200, ventana: int = 20) -> pd.Series:
    """
    Cuanto subio o bajo la SMA en las ultimas `ventana` velas, en %.

    Es la alternativa al ADX como filtro de regimen: positiva = la media
    apunta hacia arriba.
    """
    media = sma(serie, periodo)
    return (media / media.shift(ventana) - 1.0) * 100.0


# ---------------------------------------------------------------------------
# Rango de consolidacion y volumen
# ---------------------------------------------------------------------------

def rango_previo(df: pd.DataFrame, velas: int) -> pd.DataFrame:
    """
    Techo y piso de las `velas` ANTERIORES, sin contar la vela actual.

    El `shift(1)` es la linea mas importante de este archivo. Sin el, la vela
    que rompe el rango forma parte del rango que esta rompiendo: su propio
    maximo seria el techo, y ningun cierre podria quedar por encima. El
    backtest no fallaria -- simplemente no encontraria ninguna ruptura, o
    peor, encontraria las equivocadas.
    """
    techo = df["high"].rolling(window=velas, min_periods=velas).max().shift(1)
    piso = df["low"].rolling(window=velas, min_periods=velas).min().shift(1)
    return pd.DataFrame({"techo": techo, "piso": piso})


def volumen_promedio(df: pd.DataFrame, periodo: int = 50) -> pd.Series:
    """
    Volumen promedio de las `periodo` velas anteriores, sin contar la actual.

    Mismo motivo que en `rango_previo`: la vela de ruptura suele traer un
    volumen enorme. Si entra en su propio promedio, se compara contra si
    misma y el filtro se ablanda justo cuando tiene que ser exigente.
    """
    return (
        df["volume"].rolling(window=periodo, min_periods=periodo).mean().shift(1)
    )


# ---------------------------------------------------------------------------
# Conveniencia
# ---------------------------------------------------------------------------

def agregar_indicadores(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Devuelve una copia del DataFrame con todos los indicadores que pide la
    configuracion. No modifica el original.
    """
    est = cfg["estrategia"]
    salida = df.copy()

    salida["ema_rapida"] = ema(df["close"], est["tendencia"]["ema_rapida"])
    salida["ema_lenta"] = ema(df["close"], est["tendencia"]["ema_lenta"])

    periodo_atr = cfg["stops"]["atr_periodo"]
    salida["atr"] = atr(df, periodo_atr)
    salida["atr_pct"] = atr_porcentual(df, periodo_atr)

    velas_cons = est["consolidacion"]["velas"]
    salida["desv_pct"] = desviacion_porcentual(df["close"], velas_cons)
    # La version sin unidades, que es la que permite comparar temporalidades.
    # Se calcula siempre: cuesta nada y tenerla al lado de `desv_pct` hace
    # visible la diferencia entre las dos formas de medir.
    salida["desv_rel"] = desviacion_relativa(df, velas_cons, periodo_atr)
    rango = rango_previo(df, velas_cons)
    salida["techo"] = rango["techo"]
    salida["piso"] = rango["piso"]

    salida["vol_promedio"] = volumen_promedio(df, est["volumen"]["periodo_promedio"])

    indicadores_adx = adx(df, est["regimen"]["adx_periodo"])
    salida["adx"] = indicadores_adx["adx"]
    salida["di_mas"] = indicadores_adx["di_mas"]
    salida["di_menos"] = indicadores_adx["di_menos"]

    salida["sma_macro"] = sma(df["close"], est["portfolio_guard"]["sma_periodo"])

    return salida
