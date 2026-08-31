r"""
La compuerta de regimen -- lo unico que decide si la cartera esta adentro.

QUE ES
------
Un interruptor de 0 o 1 sobre TODA la cartera:

    G(t) = 1 si cierre_BTC(t-1) > SMA(cierre_BTC, 200)(t-1), si no 0

Cuando vale 0 no hay posiciones. Ninguna. No es un filtro que reduce el
tamaño: apaga la cartera entera.

POR QUE ESTA EN risk/ Y NO EN strategy/
----------------------------------------
Porque no dice que comprar, dice **si se compra**. La estrategia propone y
`risk/` dispone -- es la regla 3 del proyecto, y la compuerta es el caso mas
claro: no mira ni un solo dato del activo que se va a operar.

EL DESFASE DE UN DIA NO ES UN DETALLE
--------------------------------------
`G(t)` usa el cierre de **t-1**. Decidir con el cierre de hoy y operar hoy es
imposible: cuando conoces el cierre, el dia ya termino. Sin ese `shift(1)`
la compuerta esquiva caidas que en vivo no habria esquivado, y el backtest
sale precioso.

LO QUE NO TIENE, Y ES A PROPOSITO: AMORTIGUADOR
------------------------------------------------
Un precio que oscila alrededor de la media de 200 dias hace entrar y salir
varias veces seguidas, y cada ida y vuelta cuesta una rotacion COMPLETA de la
cartera. La solucion habitual es una banda muerta o un minimo de dias.

**No esta implementado a proposito.** La especificacion dice que si hace
falta, es un parametro nuevo y se cuenta como tal. Primero se mide cuantos
latigazos hay de verdad (medicion 5.4) y despues se decide, con el numero
sobre la mesa. Al reves es agregar un parametro para arreglar un problema que
no se sabe si existe.
"""

from __future__ import annotations

import pandas as pd

from strategy.indicators import sma

PERIODO_SMA = 200


def media_movil(cierres: pd.Series, periodo: int = PERIODO_SMA) -> pd.Series:
    """
    La media movil de `strategy/indicators.py`, no una copia.

    Tener dos implementaciones de la misma media es como se rompen las cosas
    en este proyecto: se corrige una y la otra queda vieja. La de indicators
    ya tiene la prueba de no-anticipacion encima.
    """
    return sma(cierres, periodo)


def compuerta_de_regimen(cierres: pd.Series,
                         periodo: int = PERIODO_SMA) -> pd.Series:
    """
    La serie de 0 y 1, indexada por dia.

    Antes de tener `periodo` cierres la compuerta vale 0: sin dato no se
    opera. Es la eleccion conservadora y ademas la unica honesta -- lo otro
    seria suponer que estabamos adentro sin manera de saberlo.
    """
    if not cierres.index.is_monotonic_increasing:
        raise ValueError("los cierres tienen que venir ordenados por fecha")
    encendida = (cierres > media_movil(cierres, periodo))
    return encendida.shift(1).fillna(False).astype(int)


def cambios(compuerta: pd.Series) -> pd.Series:
    """Los dias en que la compuerta cambio de estado (el primero no cuenta)."""
    movio = compuerta.diff().fillna(0) != 0
    return compuerta[movio]


def tramos(compuerta: pd.Series) -> pd.DataFrame:
    """
    Un renglon por tramo de estado constante: desde, hasta, estado y dias.

    Sirve para dos cosas: ver cuanto dura un regimen y contar los latigazos,
    que son los tramos cortos.
    """
    grupo = (compuerta.diff().fillna(0) != 0).cumsum()
    filas = []
    for _, bloque in compuerta.groupby(grupo):
        filas.append({
            "desde": bloque.index[0],
            "hasta": bloque.index[-1],
            "estado": int(bloque.iloc[0]),
            "dias": len(bloque),
        })
    return pd.DataFrame(filas)


def latigazos(compuerta: pd.Series, dias_minimos: int = 10) -> pd.DataFrame:
    """
    Los tramos que duraron menos de `dias_minimos`: entrar y salir enseguida.

    Cada uno cuesta dos lados de rotacion completa de la cartera y no aporta
    nada, porque el regimen no llego a durar.
    """
    t = tramos(compuerta)
    if t.empty:
        return t
    # El ultimo tramo esta cortado por el final de los datos, no por el
    # mercado: contarlo como latigazo seria un artefacto de la ventana.
    return t.iloc[:-1][t.iloc[:-1]["dias"] < dias_minimos]
