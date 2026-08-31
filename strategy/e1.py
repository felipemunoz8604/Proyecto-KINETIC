r"""
E1 -- momentum transversal, solo largos, con volatilidad objetivo y compuerta.

LA CANDIDATA PRINCIPAL
-----------------------
Tres mecanismos con respaldo empirico separado, apilados:

1. **Seleccion transversal por momentum.** Liu, Tsyvinski y Wu encuentran que
   mercado, tamaño y momentum capturan el corte transversal de retornos en
   cripto, y que el efecto se concentra en la pata larga -- justo la que una
   cuenta Spot puede operar.
2. **Ponderacion por inversa de volatilidad**, para que una sola moneda no
   domine el riesgo aunque pese lo mismo en dinero.
3. **Compuerta de regimen agregado**, la misma de E0.

La advertencia de la misma literatura es igual de firme: el momentum en cripto
sufre desplomes severos y **una sola moneda puede anular el retorno de la
cartera**. De ahi la restriccion al top-20 y el stop de catastrofe.

    s_i(t) = r_i(28 dias, salteando el ultimo) / sigma_i(30 dias)

El puntaje es **adimensional por construccion**: es un retorno dividido por
una volatilidad. Eso respeta la restriccion 6.3 de la Fase 1 -- comparar
monedas con un numero que tiene unidades es comparar manzanas con metros.

EL SALTO DE UN DIA
-------------------
El retorno se mide hasta t-2, no hasta t-1. El dia mas reciente se saltea a
proposito para esquivar la reversion de muy corto plazo, que es un efecto
distinto y de signo contrario al momentum. Es el analogo del clasico "12-2"
de la literatura de acciones.

Como la decision de t solo puede usar datos hasta t-1, saltear uno mas deja la
ventana entre t-30 y t-2.

QUE PASA SI HAY MENOS DE CINCO CON PUNTAJE POSITIVO
-----------------------------------------------------
Se toman los que haya y el resto queda en USDT. La cartera puede quedar
parcialmente en efectivo **por señal**, ademas de por compuerta. No se
completa con los "menos malos": un puntaje negativo es momentum negativo, y
comprarlo seria hacer lo contrario de lo que dice la hipotesis.

LA FRECUENCIA: SELECCION MENSUAL, TAMAÑO DIARIO
-------------------------------------------------
La especificacion fija el rebalanceo de **seleccion** el primer dia de cada
mes, y la compuerta **diaria**. No dice nada del tamaño. Se aplica la misma
decision que Felipe tomo para E0 el 30-ago-2026: los pesos y el escalar `k` se
recalculan todos los dias sobre los cinco ya elegidos. La seleccion sigue
siendo mensual.

EL STOP DE CATASTROFE NECESITA MEMORIA
----------------------------------------
Es lo unico de E1 que no se puede calcular con una formula sobre la serie: hay
que acordarse a que precio se entro. Por eso el armado de exposiciones es un
bucle dia a dia y no una expresion vectorizada.

Cuando salta, esa posicion se cierra y **el activo queda excluido hasta el
proximo rebalanceo mensual**. Su peso se va a efectivo y no se reparte entre
los que quedan (ver `risk/catastrofe.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from risk import catastrofe as cat
from risk.pesos import (
    DIAS_POR_ANIO,
    K_MAX,
    MINIMO_DE_OBSERVACIONES,
    SIGMA_OBJETIVO,
    TOPE_POR_ACTIVO,
    VENTANA_VOLATILIDAD_DIAS,
    escalar_de_volatilidad,
    pesos_inversa_volatilidad,
)

# De la especificacion 6.2. Todos marcados [FIJO]: no se barren.
DIAS_MOMENTUM = 28
SALTO_DIAS = 1
CUANTAS_POSICIONES = 5


def sigmas_diarias(cierres: pd.DataFrame,
                   dias: int = VENTANA_VOLATILIDAD_DIAS) -> pd.DataFrame:
    """
    Volatilidad anualizada de cada simbolo, tal como se conocia en t-1.

    Vectorizado. Es el mismo calculo que `risk.pesos.volatilidad_anualizada`
    hace de a un dia; la prueba de equivalencia lo verifica.
    """
    retornos = np.log(cierres / cierres.shift(1))
    sigma = (retornos.rolling(dias, min_periods=MINIMO_DE_OBSERVACIONES)
             .std(ddof=1) * np.sqrt(DIAS_POR_ANIO))
    return sigma.shift(1)


def puntajes(cierres: pd.DataFrame,
             sigmas: pd.DataFrame,
             *,
             dias: int = DIAS_MOMENTUM,
             salto: int = SALTO_DIAS) -> pd.DataFrame:
    """
    s_i = retorno de `dias` salteando los ultimos `salto`, sobre sigma.

    Todo desplazado para que la fila de la fecha t use solo datos anteriores a
    t: el retorno va de t-(dias+salto+1) a t-(salto+1).
    """
    fin = cierres.shift(salto + 1)
    inicio = cierres.shift(dias + salto + 1)
    retorno = fin / inicio - 1.0
    return retorno / sigmas.replace(0.0, np.nan)


def seleccionar(fila_de_puntajes: pd.Series,
                candidatos: list[str],
                cuantos: int = CUANTAS_POSICIONES) -> list[str]:
    """
    Los `cuantos` de mayor puntaje entre los candidatos, exigiendo s_i > 0.

    Si hay menos, se devuelven los que haya. Completar con puntajes negativos
    seria comprar momentum negativo, o sea lo contrario de la hipotesis.
    """
    disponibles = [c for c in candidatos if c in fila_de_puntajes.index]
    validos = fila_de_puntajes[disponibles].dropna()
    positivos = validos[validos > 0]
    return list(positivos.sort_values(ascending=False).index[:cuantos])


@dataclass
class Armado:
    """Las exposiciones diarias y el rastro de como salieron."""

    exposiciones: pd.DataFrame
    seleccion_mensual: dict[pd.Timestamp, list[str]]
    stops_disparados: list[dict] = field(default_factory=list)
    dias_sin_candidatos: int = 0


def construir_exposiciones(
    cierres: pd.DataFrame,
    aperturas: pd.DataFrame,
    atr_relativo: pd.DataFrame,
    compuerta: pd.Series,
    universo_mensual: dict[pd.Timestamp, list[str]],
    dias: pd.DatetimeIndex,
    *,
    cuantas: int = CUANTAS_POSICIONES,
    tope: float = TOPE_POR_ACTIVO,
    objetivo: float = SIGMA_OBJETIVO,
    k_max: float = K_MAX,
    ventana_vol: int = VENTANA_VOLATILIDAD_DIAS,
    multiplicador_stop: float = cat.MULTIPLICADOR_ATR,
) -> Armado:
    """
    El armado completo, dia por dia.

    `universo_mensual` es la salida de `core.universo.construir`: para cada
    primer dia de mes, los 20 mas liquidos reconstruidos sin sesgo de
    supervivencia. `atr_relativo` es ATR(14) como fraccion del precio.
    """
    sigmas = sigmas_diarias(cierres, ventana_vol)
    marcas = puntajes(cierres, sigmas)
    retornos = np.log(cierres / cierres.shift(1))

    columnas = sorted({s for v in universo_mensual.values() for s in v})

    # Indexado posicional: el bucle corre 2.200 veces y despues 20 veces mas
    # para la comparacion por pares. Con mascaras booleanas sobre 650 columnas
    # tardaba minutos; con numpy tarda segundos. El calculo es el mismo.
    retornos_np = np.nan_to_num(retornos.to_numpy(), nan=0.0)
    columna_de = {c: j for j, c in enumerate(retornos.columns)}
    posicion = retornos.index.get_indexer(dias)

    seleccion_actual: list[str] = []
    excluidos: set[str] = set()          # los que salieron por stop este mes
    entradas: dict[str, float] = {}      # precio al que se entro
    stops: dict[str, float] = {}
    disparados: list[dict] = []
    sin_candidatos = 0

    filas: list[dict[str, float]] = []
    for i, fecha in enumerate(dias):
        # --- 1. Rebalanceo de seleccion, solo el primer dia del mes --------
        if fecha in universo_mensual:
            seleccion_actual = seleccionar(marcas.loc[fecha],
                                           universo_mensual[fecha], cuantas)
            excluidos = set()
            if not seleccion_actual:
                sin_candidatos += 1

        # --- 2. El stop se evaluo con el CIERRE DE AYER --------------------
        # Se mira ayer y se ejecuta hoy a la apertura, igual que todo lo demas.
        if i > 0:
            ayer = dias[i - 1]
            for s in list(stops):
                if s not in cierres.columns:
                    continue
                cierre_ayer = cierres.at[ayer, s]
                if np.isfinite(cierre_ayer) and cat.se_disparo(float(cierre_ayer),
                                                               stops[s]):
                    excluidos.add(s)
                    disparados.append({"simbolo": s, "fecha": fecha,
                                       "entrada": entradas.get(s),
                                       "stop": stops[s],
                                       "cierre": float(cierre_ayer)})
                    stops.pop(s, None)
                    entradas.pop(s, None)

        # Los pesos se calculan sobre la seleccion COMPLETA del mes, incluidos
        # los que ya salieron por stop, y recien despues se pone en cero al
        # que salio. Si se recalcularan solo entre los sobrevivientes, la
        # normalizacion les repartiria el peso liberado -- que es exactamente
        # lo que la especificacion prohibe: "el resto de la cartera no se
        # toca". Ese peso se va a efectivo.
        activos = list(seleccion_actual)
        g = int(compuerta.get(fecha, 0))

        if g == 0 or not activos or len(excluidos) >= len(activos):
            # Todo a efectivo. Se olvidan las entradas: si mañana se vuelve,
            # es una posicion nueva con un stop nuevo.
            entradas.clear()
            stops.clear()
            filas.append({})
            continue

        # --- 3. Pesos y escalar, con los sigmas de ayer --------------------
        sigma_hoy = sigmas.loc[fecha, activos].dropna()
        sigma_hoy = sigma_hoy[sigma_hoy > 0]
        if sigma_hoy.empty:
            filas.append({})
            continue
        w = pesos_inversa_volatilidad(sigma_hoy, tope)

        p = posicion[i]
        if p < MINIMO_DE_OBSERVACIONES:
            filas.append({})
            continue
        bloque = retornos_np[max(0, p - ventana_vol):p][
            :, [columna_de[s] for s in w.index]]
        if len(bloque) < MINIMO_DE_OBSERVACIONES:
            filas.append({})
            continue
        de_cartera = bloque @ w.to_numpy()
        sigma_cartera = float(de_cartera.std(ddof=1) * np.sqrt(DIAS_POR_ANIO))
        k = escalar_de_volatilidad(sigma_cartera, objetivo, k_max)
        if k <= 0:
            filas.append({})
            continue

        exposicion = {s: v for s, v in (w * k).items() if s not in excluidos}
        filas.append(exposicion)

        # --- 4. Memoria de entradas y stops --------------------------------
        for s in list(entradas):
            if s not in exposicion:
                entradas.pop(s, None)
                stops.pop(s, None)
        for s in exposicion:
            if s in entradas:
                continue
            precio = aperturas.at[fecha, s] if s in aperturas.columns else np.nan
            atr = (atr_relativo.at[fecha, s]
                   if s in atr_relativo.columns else np.nan)
            if not np.isfinite(precio) or precio <= 0 or not np.isfinite(atr):
                continue
            entradas[s] = float(precio)
            stops[s] = cat.precio_de_stop(float(precio), float(atr),
                                          multiplicador_stop)

    marco = pd.DataFrame(filas, index=dias).reindex(columns=columnas)
    return Armado(marco.fillna(0.0), universo_mensual, disparados,
                  sin_candidatos)


def rangos_de_liquidez(universo_mensual: dict[pd.Timestamp, list[str]],
                       dias: pd.DatetimeIndex) -> pd.DataFrame:
    """
    El puesto de cada simbolo en el universo, dia a dia, para el slippage.

    `core.universo.construir` devuelve las listas ya ordenadas por liquidez,
    asi que el puesto es la posicion en la lista, 1-based.
    """
    columnas = sorted({s for v in universo_mensual.values() for s in v})
    marco = pd.DataFrame(np.nan, index=dias, columns=columnas)
    for fecha, simbolos in sorted(universo_mensual.items()):
        for puesto, s in enumerate(simbolos, start=1):
            marco.loc[marco.index >= fecha, s] = puesto
    return marco
