"""
Filtro de regimen: decide si el mercado esta como para intentar rupturas.

UNA TENSION QUE HAY QUE ENTENDER ANTES DE TOCAR ESTE ARCHIVO
------------------------------------------------------------
La seccion 7 del MEGAPROMPT pide dos cosas que, tomadas al pie de la letra
sobre la misma vela, se pelean entre si:

  - Paso 1: que haya TENDENCIA (ADX alto). Si el mercado esta en rango, no
    evaluar rupturas.
  - Paso 2: que haya CONSOLIDACION (volatilidad baja en las ultimas 50
    velas) antes de la ruptura.

El problema: una consolidacion ES, por definicion, un tramo sin tendencia.
Mientras el precio esta quieto, el ADX baja. Exigir "ADX alto AHORA" y
"quieto en las ultimas 50 velas" al mismo tiempo describe una situacion que
casi no ocurre, y el backtest devolveria casi cero operaciones.

Por eso hay dos metodos, y cual gana lo decide el backtest, no este
comentario:

  - `adx`: mide fuerza de tendencia LOCAL. Es el que sufre la tension de
    arriba. Se ofrece igual porque el ADX empieza a subir justo en la vela
    de ruptura, asi que con un umbral bajo puede funcionar como
    confirmacion en vez de como filtro previo.
  - `pendiente_sma`: mide hacia donde apunta el mercado EN GRANDE (la SMA
    de 200 subiendo o bajando). No se pelea con la consolidacion local:
    perfectamente puede haber una pausa de 50 velas dentro de una tendencia
    mayor de meses. Sospecho que es el que corresponde, pero es una
    sospecha y se decide midiendo.

Este archivo NO decide si se opera. Solo responde "el mercado esta como
para mirar rupturas: si o no".
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from strategy import indicators as ind


@dataclass(frozen=True)
class Regimen:
    """Lo que el filtro concluyo sobre una vela, y por que."""

    apto: bool
    metodo: str
    valor: float | None
    umbral: float | None
    motivo: str


def _sin_datos(metodo: str) -> Regimen:
    return Regimen(
        apto=False,
        metodo=metodo,
        valor=None,
        umbral=None,
        motivo="indicador todavia sin calentar (faltan velas)",
    )


def evaluar_adx(fila: pd.Series, umbral: float) -> Regimen:
    """Apto si el ADX de esta vela llega al umbral."""
    valor = fila.get("adx")
    if valor is None or pd.isna(valor):
        return _sin_datos("adx")

    apto = bool(valor >= umbral)
    return Regimen(
        apto=apto,
        metodo="adx",
        valor=float(valor),
        umbral=float(umbral),
        motivo=(
            f"ADX {valor:.1f} >= {umbral} (hay fuerza de tendencia)"
            if apto
            else f"ADX {valor:.1f} < {umbral} (mercado sin fuerza)"
        ),
    )


def evaluar_pendiente(fila: pd.Series, umbral: float) -> Regimen:
    """Apto si la media larga apunta hacia arriba lo suficiente."""
    valor = fila.get("pendiente_sma")
    if valor is None or pd.isna(valor):
        return _sin_datos("pendiente_sma")

    apto = bool(valor >= umbral)
    return Regimen(
        apto=apto,
        metodo="pendiente_sma",
        valor=float(valor),
        umbral=float(umbral),
        motivo=(
            f"la media larga sube {valor:+.2f}% (umbral {umbral:+.2f}%)"
            if apto
            else f"la media larga va {valor:+.2f}%, no llega a {umbral:+.2f}%"
        ),
    )


def evaluar(fila: pd.Series, cfg_regimen: dict) -> Regimen:
    """Aplica el metodo que diga la configuracion."""
    metodo = cfg_regimen.get("metodo", "adx")

    if metodo == "adx":
        umbral = cfg_regimen.get("adx_minimo")
        if umbral is None:
            raise ValueError(
                "estrategia.regimen.adx_minimo esta sin definir en config.yaml. "
                "Es un pendiente de la Fase 1: lo decide el backtest."
            )
        return evaluar_adx(fila, umbral)

    if metodo == "pendiente_sma":
        umbral = cfg_regimen.get("pendiente_minima_pct")
        if umbral is None:
            raise ValueError(
                "estrategia.regimen.pendiente_minima_pct esta sin definir en "
                "config.yaml. Es un pendiente de la Fase 1."
            )
        return evaluar_pendiente(fila, umbral)

    raise ValueError(
        f"Metodo de regimen desconocido: {metodo!r}. Validos: adx, pendiente_sma"
    )


def agregar_pendiente(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Agrega la columna `pendiente_sma` al DataFrame de indicadores.

    Vive aca y no en indicators.py porque solo la necesita este filtro.
    """
    est = cfg["estrategia"]
    salida = df.copy()
    salida["pendiente_sma"] = ind.pendiente_sma(
        df["close"],
        periodo=est["portfolio_guard"]["sma_periodo"],
        ventana=est["regimen"].get("pendiente_ventana", 20),
    )
    return salida
