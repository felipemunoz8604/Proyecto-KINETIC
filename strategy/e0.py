r"""
E0 -- la linea base barata: BTC con compuerta de tendencia y volatilidad
objetivo.

QUE ES Y POR QUE VA PRIMERO
----------------------------
Un solo activo, un solo indicador, cero seleccion. La especificacion es
tajante: **"es obligatoria y se implementa primero. No es un descarte: es la
vara."** Si nada la supera, se implementa E0 y se cierra la investigacion.

    señal(t)      = cierre_BTC(t-1) > SMA200(t-1)
    exposicion(t) = min(35% / sigma_BTC(30d, hasta t-1), 1,0)  si la señal
                    0                                          si no

Se ejecuta a la **apertura del dia t**. Todo lo que entra en la decision se
conocia al cierre de t-1.

LA HIPOTESIS QUE PONE A PRUEBA
--------------------------------
Que la mayor parte del beneficio de "igualar al mercado con la mitad de la
caida" viene de **estar afuera en los tramos bajistas**, no de elegir activos.
Si E0 alcanza eso sola, E1 y E2 tienen que justificar su complejidad contra
ella, no contra comprar y esperar.

Y al reves: **su falsacion es un hallazgo mayor.** Si E0 no llega a Calmar
>= 1,3 x Calmar(B1), la compuerta de regimen no funciona en este mercado, y E1
y E2 -- que usan la misma compuerta -- quedan debilitadas antes de probarse.

DOS CAMINOS QUE TIENEN QUE DAR LO MISMO
-----------------------------------------
`exposicion_objetivo` es el camino rapido (vectorizado) y
`exposicion_objetivo_lenta` es el de referencia, que recalcula dia por dia
pasando por `risk/`. Hay una prueba que exige que coincidan.

Es el mismo arreglo que en la Fase 1 con `mascara_de_senales` contra
`evaluar_vela`, y esta por la misma razon: el camino rapido es el que se corre
y el lento es el que se entiende. **Si cambias una condicion, cambiala en los
dos lados.**

EL REBALANCEO ES DIARIO -- DECISION DE FELIPE, 30-ago-2026
------------------------------------------------------------
La especificacion no lo fijaba. Sigma cambia todos los dias y el precio
tambien, asi que la exposicion real se desvia sola del objetivo. Felipe eligio
volver al objetivo todos los dias: es la lectura literal de una exposicion
definida dia a dia, y es la mas cara de las tres opciones, o sea la mas dificil
de aprobar.

El minimo de 5 USDT de Binance frena las ordenes chicas y termina haciendo de
amortiguador sin que nadie lo haya inventado como parametro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from risk.compuerta import PERIODO_SMA, compuerta_de_regimen
from risk.pesos import (
    DIAS_POR_ANIO,
    K_MAX,
    MINIMO_DE_OBSERVACIONES,
    SIGMA_OBJETIVO,
    VENTANA_VOLATILIDAD_DIAS,
    escalar_de_volatilidad,
    volatilidad_anualizada,
)

SIMBOLO = "BTCUSDT"


def exposicion_objetivo(cierres: pd.Series,
                        *,
                        objetivo: float = SIGMA_OBJETIVO,
                        k_max: float = K_MAX,
                        periodo_sma: int = PERIODO_SMA,
                        dias_vol: int = VENTANA_VOLATILIDAD_DIAS,
                        con_compuerta: bool = True) -> pd.Series:
    """
    La fraccion del patrimonio que E0 quiere tener en BTC cada dia.

    Camino rapido. Todo lo que se usa para el dia t esta desplazado un dia:
    `shift(1)` sobre la volatilidad y sobre la señal.

    `con_compuerta=False` es la **referencia B4**: solo objetivo de
    volatilidad, siempre dentro. Es una bandera y no un archivo aparte a
    proposito -- B4 se define como "E0 sin la compuerta", asi que todo lo
    demas tiene que ser identico por construccion y no por disciplina.
    """
    if k_max > K_MAX:
        # Se delega el mensaje completo, que explica por que es un cerrojo.
        escalar_de_volatilidad(1.0, objetivo, k_max)

    g = (compuerta_de_regimen(cierres, periodo_sma) if con_compuerta
         else pd.Series(1, index=cierres.index))

    retornos = np.log(cierres / cierres.shift(1))
    sigma = (retornos.rolling(dias_vol, min_periods=MINIMO_DE_OBSERVACIONES)
             .std(ddof=1) * np.sqrt(DIAS_POR_ANIO)).shift(1)

    k = (objetivo / sigma).clip(upper=k_max)
    # Sin sigma no hay medida del riesgo, y sin medida no se toma. Es el mismo
    # criterio que la compuerta antes del dia 200.
    k = k.where(np.isfinite(sigma) & (sigma > 0), 0.0)

    return (g * k).fillna(0.0).rename(SIMBOLO)


def exposicion_objetivo_lenta(cierres: pd.Series,
                              *,
                              objetivo: float = SIGMA_OBJETIVO,
                              k_max: float = K_MAX,
                              periodo_sma: int = PERIODO_SMA,
                              dias_vol: int = VENTANA_VOLATILIDAD_DIAS,
                              con_compuerta: bool = True,
                              simbolo: str = SIMBOLO) -> pd.Series:
    """
    El mismo calculo, dia por dia, pasando por `risk/`. Es la referencia.

    Mucho mas lento y mucho mas facil de leer. Su valor esta en que usa
    exactamente las mismas funciones que van a usar E1 y E2, asi que si el
    camino rapido se desvia, la prueba de equivalencia lo agarra.
    """
    marco = cierres.to_frame(name=simbolo)
    g = (compuerta_de_regimen(cierres, periodo_sma) if con_compuerta
         else pd.Series(1, index=cierres.index))
    salida = {}
    for fecha in cierres.index:
        if int(g.get(fecha, 0)) == 0:
            salida[fecha] = 0.0
            continue
        sigmas = volatilidad_anualizada(marco, fecha, [simbolo], dias_vol)
        if simbolo not in sigmas.index:
            salida[fecha] = 0.0
            continue
        salida[fecha] = escalar_de_volatilidad(float(sigmas[simbolo]),
                                               objetivo, k_max)
    return pd.Series(salida, index=cierres.index, name=simbolo)


def exposiciones(cierres: pd.Series, **kwargs) -> pd.DataFrame:
    """La misma serie en el formato que espera `backtesting/motor_cartera.py`."""
    return exposicion_objetivo(cierres, **kwargs).to_frame()
