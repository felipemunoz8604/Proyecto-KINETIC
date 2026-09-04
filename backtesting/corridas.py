r"""
Las curvas de patrimonio de las corridas de la Fase 2, en un solo lugar.

POR QUE EXISTE ESTE ARCHIVO
-----------------------------
Cada herramienta que quiere comparar candidatas tenia que rearmar las seis
curvas: cargar el archivo, reconstruir el universo, armar exposiciones, correr
el motor con costos, filtros y financiacion. Son ochenta lineas identicas
copiadas en `tools/comparar_candidatos.py`, `tools/repuntuar.py` y ahora en la
herramienta de la frontera.

**Tres copias de la misma construccion se separan.** Y cuando se separan, dos
herramientas reportan numeros distintos de la misma estrategia y no hay forma
de saber cual miente. Se centraliza antes de que pase.

QUE NO HACE
------------
No mide nada y no decide nada. Devuelve curvas de patrimonio diarias, que es
lo unico que `metrics/` sabe leer. La vara vive en `metrics/`, la estrategia en
`strategy/` y el riesgo en `risk/`; este archivo solo los conecta.

LA VENTANA LA MANDA E2
------------------------
Antes de 2020 no hay perpetuos, asi que la ventana comun arranca donde arranca
el primer perpetuo. Todas las curvas se calculan sobre **la misma ventana** o
la comparacion no significa nada.

LAS REFERENCIAS B3 Y B4 NO SON ESTRATEGIAS
--------------------------------------------
Se construyen aca por comodidad, pero **no consumen presupuesto de Deflated
Sharpe**: B3 resuelve una ecuacion (que exposicion constante da este CAGR) y
B4 es E0 con la compuerta apagada. Ninguna de las dos elige nada.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from backtesting import motor_cartera as mc
from core import archivo_binance as arch
from core import financiacion as fin
from core import universo as uni
from execution.costos import ModeloDeCostos, TipoOrden, Venue
from execution.filtros import TablaDeFiltros
from metrics import benchmarks, ventana
from risk import catastrofe as cat
from risk import compuerta as cp
from strategy import e0, e1, e2

CAPITAL = 500.0
REFERENCIA = "BTCUSDT"


def modelo_de_costos() -> ModeloDeCostos:
    """Spot, taker, con descuento de BNB. Es el de todas las corridas."""
    return ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb=True)


@dataclass
class Corrida:
    """Todo lo que necesita una herramienta para comparar, ya alineado."""

    dias: pd.DatetimeIndex
    b1: pd.Series
    curvas: dict[str, pd.Series] = field(default_factory=dict)
    exposicion_e0: pd.Series | None = None
    velas_btc: pd.DataFrame | None = None
    filtros: TablaDeFiltros | None = None


def _cargar(carpeta: Path, simbolos: list[str]):
    ap, ci, at = {}, {}, {}
    for s in simbolos:
        try:
            v = arch.cargar(s, "1d", carpeta)
        except FileNotFoundError:
            continue
        v = v[v.index <= ventana.DISENO_HASTA]
        if v.empty:
            continue
        ap[s], ci[s], at[s] = v["open"], v["close"], cat.atr_relativo(v)
    return pd.DataFrame(ap), pd.DataFrame(ci), pd.DataFrame(at)


def construir(carpeta: Path,
              carpeta_perp: Path,
              carpeta_fin: Path,
              archivo_filtros: Path,
              *,
              capital: float = CAPITAL,
              con_transversales: bool = True,
              avisar=None) -> Corrida:
    """
    Arma B1, E0 y -- si se piden -- E1, R1, R2 y E2 sobre la ventana comun.

    `con_transversales=False` deja solo B1 y E0, que es lo que necesita una
    herramienta que mira nada mas la atribucion de E0 y no quiere esperar los
    varios minutos que tardan las de cartera.
    """
    def aviso(texto: str) -> None:
        if avisar is not None:
            avisar(texto)

    aviso("Cargando archivo y universo...")
    panel = uni.cargar_panel(carpeta)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})
    ap, ci, atr = _cargar(carpeta, candidatos)
    ap_p, ci_p, atr_p = _cargar(carpeta_perp, candidatos)
    filtros = (TablaDeFiltros.desde_json(archivo_filtros)
               if archivo_filtros.exists() else None)
    g = cp.compuerta_de_regimen(panel.cierres[REFERENCIA].dropna())

    velas_btc = arch.cargar(REFERENCIA, "1d", carpeta)
    velas_btc = velas_btc[velas_btc.index <= ventana.DISENO_HASTA]

    # La ventana comun la manda E2: antes de 2020 no hay perpetuos.
    desde = max(ventana.DISENO_DESDE,
                ci_p.apply(lambda c: c.first_valid_index()).min())
    dias = ci.index[(ci.index >= desde) & (ci.index <= ventana.DISENO_HASTA)]

    datos_btc = velas_btc.assign(
        exposicion=e0.exposicion_objetivo(velas_btc["close"]))
    datos_btc = datos_btc[datos_btc.index >= desde]
    b1 = benchmarks.comprar_y_mantener(datos_btc, capital)
    r_e0 = mc.simular(
        datos_btc[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos_btc[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos_btc[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        capital, modelo_de_costos(), rangos={e0.SIMBOLO: 1}, filtros=filtros)

    corrida = Corrida(dias=dias, b1=b1, curvas={"E0": r_e0.patrimonio},
                      exposicion_e0=r_e0.exposicion.sum(axis=1),
                      velas_btc=velas_btc, filtros=filtros)
    if not con_transversales:
        return corrida

    rangos = e1.rangos_de_liquidez(universo, dias)
    for nombre, kwargs in (("E1", {}), ("R1", {"dias_momentum": 90}),
                           ("R2", {"cuantas": 8})):
        aviso(f"Armando {nombre}...")
        a = e1.construir_exposiciones(ci, ap, atr, g, universo, dias, **kwargs)
        cols = list(a.exposiciones.columns)
        corrida.curvas[nombre] = mc.simular(
            ap.reindex(index=dias, columns=cols),
            ci.reindex(index=dias, columns=cols), a.exposiciones,
            capital, modelo_de_costos(), rangos=rangos,
            filtros=filtros).patrimonio

    aviso("Armando E2...")
    a2 = e2.construir_exposiciones(ci, ap, ci_p, ap_p, atr, atr_p, universo,
                                   dias)
    cols2 = list(a2.exposiciones.columns)

    def matriz(spot, perp):
        d = {}
        for c in cols2:
            base = e2.simbolo_base(c)
            origen = perp if e2.es_perpetuo(c) else spot
            if base in origen.columns:
                d[c] = origen[base]
        return pd.DataFrame(d).reindex(index=dias, columns=cols2)

    tasas = {c: fin.cargar(e2.simbolo_base(c), carpeta_fin)["tasa"]
             for c in cols2 if e2.es_perpetuo(c)
             and (carpeta_fin / f"{e2.simbolo_base(c)}.csv").exists()}
    corrida.curvas["E2"] = mc.simular(
        matriz(ap, ap_p), matriz(ci, ci_p), a2.exposiciones, capital,
        modelo_de_costos(),
        rangos=pd.DataFrame({c: rangos[e2.simbolo_base(c)] for c in cols2
                             if e2.simbolo_base(c) in rangos.columns},
                            index=dias),
        filtros=filtros, permitir_cortos=True,
        financiacion_de_cortos=tasas).patrimonio
    return corrida


def curva_a_exposicion_constante(corrida: Corrida, k: float,
                                 capital: float = CAPITAL) -> pd.Series:
    """B3 con una exposicion dada. La calibracion vive en `benchmarks`."""
    datos = corrida.velas_btc[corrida.velas_btc.index >= corrida.dias[0]]
    return mc.simular(
        datos[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos[["close"]].rename(columns={"close": e0.SIMBOLO}),
        benchmarks.exposicion_constante(datos.index, k, e0.SIMBOLO),
        capital, modelo_de_costos(), rangos={e0.SIMBOLO: 1},
        filtros=corrida.filtros).patrimonio


def curva_sin_compuerta(corrida: Corrida,
                        capital: float = CAPITAL) -> pd.Series:
    """B4: E0 con la compuerta apagada. Solo objetivo de volatilidad."""
    datos = corrida.velas_btc.assign(
        exposicion=e0.exposicion_objetivo(corrida.velas_btc["close"],
                                          con_compuerta=False))
    datos = datos[datos.index >= corrida.dias[0]]
    return mc.simular(
        datos[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        capital, modelo_de_costos(), rangos={e0.SIMBOLO: 1},
        filtros=corrida.filtros).patrimonio
