r"""
Medicion 5.2 -- cuanto se separan entre si las monedas del universo.

LA PREGUNTA
-----------
Elegir cinco de veinte solo puede aportar algo si las veinte hacen cosas
distintas. Si suben y bajan todas juntas, elegir bien y elegir mal dan casi lo
mismo, y lo unico que queda del intento es la factura de comisiones.

El informe de cierre de la Fase 1 ya lo habia anticipado mirando quince pares:
contra el dolar suben y bajan casi todas a la vez. Esto le pone numero.

**Si la correlacion media por pares supera ~0,80 y la dispersion es baja, E1 y
E2 tienen poco margen, y hay que decirlo ANTES de invertir semanas.**

ACA SE MIRA HACIA ADELANTE A PROPOSITO -- NO COPIAR ESTO A UNA ESTRATEGIA
--------------------------------------------------------------------------
`retornos_hacia_adelante` toma el universo en `t` y mide lo que paso DESPUES
de `t`. En una estrategia eso seria anticipacion y estaria mal. Aca es
exactamente lo que se quiere saber: si el corte transversal se abre despues
de elegir. Es una descripcion del mercado, no una regla de decision, y ningun
resultado de este modulo puede entrar a un backtest.

Lo mismo vale para `brecha_perfecta`: mide lo que ganaria alguien que
adivinara siempre cuales son los mejores cinco. Es un **techo**, no un
resultado. Si el techo no le gana a los costos, no hay nada abajo que buscar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

HORIZONTE_DIAS = 28
VENTANA_CORRELACION_DIAS = 90


def _precio_al_cierre_de(serie: pd.Series, fecha: pd.Timestamp) -> float:
    """El ultimo cierre disponible en `fecha` o antes. NaN si no hay ninguno."""
    previos = serie.loc[serie.index <= fecha].dropna()
    return float(previos.iloc[-1]) if len(previos) else float("nan")


@dataclass
class RetornosTransversales:
    """
    Retornos futuros de cada universo, y cuantos quedaron cortados por muerte.

    `truncados` importa: si un simbolo se deslista antes de cumplirse el
    horizonte, su retorno se mide contra el ultimo cierre que hubo. Eso NO
    incluye la penalizacion por deslistado -- es el precio de la ultima vela,
    que suele ser optimista respecto de lo que se recupera de verdad.
    """

    retornos: pd.DataFrame
    truncados: int
    observaciones: int


def retornos_hacia_adelante(panel, seleccion: dict, dias: int = HORIZONTE_DIAS
                            ) -> RetornosTransversales:
    """
    Para cada fecha de rebalanceo, el retorno de sus 20 durante los `dias`
    siguientes. Filas = fechas, columnas = simbolos, casi todo NaN.
    """
    horizonte = pd.Timedelta(days=dias)
    ultima = panel.ultima_vela
    filas: dict[pd.Timestamp, dict[str, float]] = {}
    truncados = 0
    observaciones = 0

    for fecha, simbolos in sorted(seleccion.items()):
        fila: dict[str, float] = {}
        for s in simbolos:
            serie = panel.cierres[s]
            p0 = _precio_al_cierre_de(serie, fecha)
            p1 = _precio_al_cierre_de(serie, fecha + horizonte)
            if not np.isfinite(p0) or not np.isfinite(p1) or p0 <= 0:
                continue
            fila[s] = p1 / p0 - 1.0
            observaciones += 1
            if pd.notna(ultima[s]) and ultima[s] < fecha + horizonte:
                truncados += 1
        if fila:
            filas[fecha] = fila

    marco = pd.DataFrame.from_dict(filas, orient="index").sort_index()
    return RetornosTransversales(marco, truncados, observaciones)


def dispersion(retornos: pd.DataFrame) -> pd.Series:
    """Desviacion estandar transversal por fecha. Cuanto se abre el abanico."""
    return retornos.std(axis=1, ddof=1).dropna()


def brecha_perfecta(retornos: pd.DataFrame, k: int = 5) -> pd.Series:
    """
    Promedio de los `k` mejores menos promedio de los `k` peores, por fecha.

    Es el **techo** de la seleccion transversal: lo que sacaria alguien con
    vision perfecta yendo largo de los mejores y corto de los peores. Nadie
    llega ni cerca, pero si ese techo no le gana comodo a los costos, no hace
    falta buscar mas abajo.
    """
    def _de(fila: pd.Series) -> float:
        vivos = fila.dropna()
        if len(vivos) < 2 * k:
            return float("nan")
        ordenados = vivos.sort_values()
        return float(ordenados.iloc[-k:].mean() - ordenados.iloc[:k].mean())

    return retornos.apply(_de, axis=1).dropna()


def ventaja_del_mejor_grupo(retornos: pd.DataFrame, k: int = 5) -> pd.Series:
    """
    Promedio de los `k` mejores menos el promedio de TODOS, por fecha.

    Es el techo de una estrategia solo-largo que elige `k` de 20: lo que
    sacaria por encima de comprar la canasta entera equiponderada, si acertara
    siempre. Es el numero que le corresponde a E1, porque E1 no va corto.
    """
    def _de(fila: pd.Series) -> float:
        vivos = fila.dropna()
        if len(vivos) <= k:
            return float("nan")
        mejores = vivos.sort_values().iloc[-k:]
        return float(mejores.mean() - vivos.mean())

    return retornos.apply(_de, axis=1).dropna()


def correlacion_media_por_pares(panel, seleccion: dict,
                                dias: int = VENTANA_CORRELACION_DIAS
                                ) -> pd.Series:
    """
    Correlacion media entre los pares del universo, por fecha de rebalanceo.

    Se calcula sobre los retornos diarios de los `dias` ANTERIORES a la fecha
    -- aca si se mira solo el pasado, porque la correlacion es justamente lo
    que una estrategia podria estimar en el momento de decidir.
    """
    ventana = pd.Timedelta(days=dias)
    salida: dict[pd.Timestamp, float] = {}

    for fecha, simbolos in sorted(seleccion.items()):
        recorte = panel.cierres.loc[
            (panel.cierres.index > fecha - ventana)
            & (panel.cierres.index < fecha),
            [s for s in simbolos if s in panel.cierres.columns],
        ]
        retornos = np.log(recorte / recorte.shift(1)).dropna(how="all")
        # Un simbolo con muy pocos datos ensucia la matriz entera.
        retornos = retornos.loc[:, retornos.count() >= dias // 2]
        if retornos.shape[1] < 2:
            continue
        matriz = retornos.corr()
        arriba = np.triu(np.ones(matriz.shape, dtype=bool), k=1)
        valores = matriz.to_numpy()[arriba]
        valores = valores[np.isfinite(valores)]
        if len(valores):
            salida[fecha] = float(valores.mean())

    return pd.Series(salida).sort_index()
