r"""
E1 -- la candidata principal, contra los seis criterios de la seccion 3.3.

LA VARA
--------
E1 tiene que pasar los seis. El que manda es el **criterio 3**: superar a E0
por al menos 15% en Calmar. Si no lo hace, la seleccion transversal no esta
aportando nada sobre la compuerta de regimen -- y como E0 ya empato con
comprar y esperar, seria la segunda mala noticia seguida.

Se reporta ademas contra **B2**, la canasta de los 10 mas liquidos
equiponderada con rebalanceo mensual, que es el rival "sin señal pero con
diversificacion".

POR QUE SE CORRE CON COSTOS TAKER Y NO MAKER
----------------------------------------------
La especificacion pide ordenes maker "con modelado de no ejecucion", **pero no
da la tasa de ejecucion**. Inventarla violaria la regla 1 del proyecto (cero
suposiciones), y suponer que la maker siempre entra es el sesgo que la propia
especificacion advierte: se ve igual que una estrategia buena.

Asi que el resultado principal va con **taker**, que ademas tiene una ventaja
que importa mas: E0 corrio con taker, y el criterio 3 los compara entre si. Si
E1 pagara menos comisiones que E0, la comparacion mediria el modelo de costos
en vez de la estrategia.

La corrida maker se reporta al lado como **cota optimista**: el mejor caso
posible si todas las ordenes entraran siempre. Nadie deberia creerle.

Se corre asi:

    venv\Scripts\python.exe tools\correr_e1.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtesting import motor_cartera as mc  # noqa: E402
from core import archivo_binance as arch  # noqa: E402
from core import universo as uni  # noqa: E402
from execution.costos import ModeloDeCostos, TipoOrden, Venue  # noqa: E402
from execution.filtros import TablaDeFiltros  # noqa: E402
from metrics import benchmarks, metricas, robustez, ventana  # noqa: E402
from risk import catastrofe as cat  # noqa: E402
from risk import compuerta as cp  # noqa: E402
from strategy import e0, e1  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
FILTROS = RAIZ / "data" / "filtros_spot.json"
CAPITAL = 500.0
REFERENCIA = "BTCUSDT"
CUANTOS_B2 = 10


def _modelo(tipo: TipoOrden) -> ModeloDeCostos:
    return ModeloDeCostos(venue=Venue.SPOT, tipo_orden=tipo, con_bnb=True)


def _cargar_ohlc(simbolos: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aperturas y ATR relativo de los simbolos que pueden entrar a la cartera."""
    aperturas, atrs = {}, {}
    for s in simbolos:
        try:
            velas = arch.cargar(s, "1d", CARPETA)
        except FileNotFoundError:
            continue
        velas = velas[velas.index <= ventana.DISENO_HASTA]
        if velas.empty:
            continue
        aperturas[s] = velas["open"]
        atrs[s] = cat.atr_relativo(velas)
    return pd.DataFrame(aperturas), pd.DataFrame(atrs)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - E1: momentum transversal con volatilidad objetivo")
    print("=" * 76)
    print(f"  Capital {CAPITAL:.0f} USDT   ventana "
          f"{ventana.DISENO_DESDE.date()} a {ventana.DISENO_HASTA.date()}")
    print(f"  Momentum {e1.DIAS_MOMENTUM}d con salto {e1.SALTO_DIAS}d   "
          f"{e1.CUANTAS_POSICIONES} posiciones   costos TAKER")
    print()

    print("  Cargando panel y universo...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})
    print(f"    {len(fechas_reb)} rebalanceos, {len(candidatos)} simbolos "
          f"candidatos ({time.time() - t0:.0f} s)")

    print("  Cargando OHLC de los candidatos...", flush=True)
    aperturas, atr = _cargar_ohlc(candidatos)
    cierres = panel.cierres[[c for c in candidatos if c in panel.cierres.columns]]
    print(f"    {aperturas.shape[1]} simbolos con OHLC "
          f"({time.time() - t0:.0f} s)")

    g = cp.compuerta_de_regimen(panel.cierres[REFERENCIA].dropna())
    dias = cierres.index[(cierres.index >= ventana.DISENO_DESDE)
                         & (cierres.index <= ventana.DISENO_HASTA)]
    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None
    rangos = e1.rangos_de_liquidez(universo, dias)

    print("  Armando exposiciones...", flush=True)
    armado = e1.construir_exposiciones(cierres, aperturas, atr, g, universo,
                                       dias)
    print(f"    listo ({time.time() - t0:.0f} s)")

    def correr(exposiciones: pd.DataFrame, tipo: TipoOrden
               ) -> mc.ResultadoCartera:
        cols = list(exposiciones.columns)
        return mc.simular(aperturas.reindex(columns=cols, index=exposiciones.index),
                          cierres.reindex(columns=cols, index=exposiciones.index),
                          exposiciones, CAPITAL, _modelo(tipo),
                          rangos=rangos, filtros=filtros)

    r = correr(armado.exposiciones, TipoOrden.TAKER)
    m_e1 = metricas.calcular(r.patrimonio, "E1",
                             exposicion=r.exposicion.sum(axis=1),
                             rotacion_anual=r.rotacion_anual,
                             costo_anual_pct=r.costo_anual_pct)

    # --- Los rivales -------------------------------------------------------
    velas_btc = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas_btc = velas_btc[velas_btc.index <= ventana.DISENO_HASTA]
    exp_e0 = e0.exposicion_objetivo(velas_btc["close"])
    datos_e0 = velas_btc.assign(exposicion=exp_e0)
    datos_e0 = datos_e0[datos_e0.index >= ventana.DISENO_DESDE]
    r_e0 = mc.simular(
        datos_e0[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos_e0[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos_e0[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        CAPITAL, _modelo(TipoOrden.TAKER),
        rangos={e0.SIMBOLO: 1}, filtros=filtros)
    m_e0 = metricas.calcular(r_e0.patrimonio, "B0 = E0")
    m_b1 = metricas.calcular(
        benchmarks.comprar_y_mantener(datos_e0, CAPITAL), "B1 comprar y mantener")

    # B2: los 10 mas liquidos, equiponderados, rebalanceo mensual.
    exp_b2 = pd.DataFrame(0.0, index=dias, columns=armado.exposiciones.columns)
    for fecha, simbolos in sorted(universo.items()):
        elegidos = [s for s in simbolos[:CUANTOS_B2]
                    if s in exp_b2.columns]
        if not elegidos:
            continue
        exp_b2.loc[exp_b2.index >= fecha, :] = 0.0
        exp_b2.loc[exp_b2.index >= fecha, elegidos] = 1.0 / len(elegidos)
    r_b2 = correr(exp_b2, TipoOrden.TAKER)
    m_b2 = metricas.calcular(r_b2.patrimonio, "B2 canasta top-10",
                             rotacion_anual=r_b2.rotacion_anual,
                             costo_anual_pct=r_b2.costo_anual_pct)

    print()
    print("=" * 76)
    print(" RESULTADO")
    print("=" * 76)
    for m in (m_e1, m_e0, m_b1, m_b2):
        print(m.informe())
        print()

    print(f"  Stops de catastrofe disparados: {len(armado.stops_disparados)}")
    print(f"  Meses sin ningun candidato positivo: {armado.dias_sin_candidatos}")
    print(f"  Deslistados atravesados: {len(r.deslistados)}")
    print(f"  Ordenes rechazadas por el minimo de 5 USDT: "
          f"{r.ordenes_rechazadas:,}")

    # --- Los seis criterios -----------------------------------------------
    print()
    print("=" * 76)
    print(" LOS SEIS CRITERIOS (docs/FASE_2_criterios.md)")
    print("=" * 76)
    resultados = {}

    print("  Criterio 1 -- Calmar contra B1, comparado por pares...",
          flush=True)
    comparacion = robustez.comparar_por_pares(
        pd.DataFrame(index=dias).assign(marca=1.0),
        lambda tramo: correr(
            armado.exposiciones.loc[armado.exposiciones.index >= tramo.index[0]],
            TipoOrden.TAKER).patrimonio,
        lambda tramo: benchmarks.comprar_y_mantener(
            datos_e0[datos_e0.index >= tramo.index[0]], CAPITAL),
    )
    resultados[1] = comparacion.mediana >= 1.8
    print(f"    mediana {comparacion.mediana:.3f}   peor {comparacion.peor:.3f}"
          f"   mejor {comparacion.mejor:.3f}   exigido 1,8   "
          f"{'PASA' if resultados[1] else 'NO PASA'}")

    tope = 0.60 * abs(m_b1.caida_maxima)
    resultados[2] = abs(m_e1.caida_maxima) <= tope
    print(f"  Criterio 2 -- caida {abs(m_e1.caida_maxima) * 100:.1f}% vs "
          f"{tope * 100:.1f}% permitido   "
          f"{'PASA' if resultados[2] else 'NO PASA'}")

    # El criterio 3 se evalua contra max(Calmar(B0), Calmar(B1)): si la linea
    # base barata sale peor que comprar y esperar, entonces comprar y esperar
    # pasa a ser la linea base. Es la regla 3.3 de los criterios.
    piso = max(m_e0.calmar, m_b1.calmar)
    cual = "E0" if m_e0.calmar >= m_b1.calmar else "B1"
    resultados[3] = m_e1.calmar >= 1.15 * piso
    print(f"  Criterio 3 -- Calmar {m_e1.calmar:.3f} vs "
          f"{1.15 * piso:.3f} exigido (1,15 x {cual} = {piso:.3f})   "
          f"{'PASA' if resultados[3] else 'NO PASA'}")

    ic = robustez.bootstrap_cagr(r.patrimonio)
    resultados[4] = ic.excluye_cero
    print(f"  Criterio 4 -- IC 95% del CAGR [{ic.bajo * 100:+.2f}%, "
          f"{ic.alto * 100:+.2f}%]   "
          f"{'PASA' if resultados[4] else 'NO PASA'}")

    curva = robustez.retiro_top_k(r.patrimonio)
    resultados[5] = curva[3] >= 0.50 * m_b1.cagr
    print(f"  Criterio 5 -- sin los 3 mejores meses {curva[3] * 100:+.2f}% vs "
          f"{0.50 * m_b1.cagr * 100:+.2f}% exigido   "
          f"{'PASA' if resultados[5] else 'NO PASA'}")

    bruto = m_e1.cagr + r.costo_anual_pct / 100.0
    resultados[6] = (r.costo_anual_pct / 100.0) <= 0.25 * bruto if bruto > 0 else False
    print(f"  Criterio 6 -- costo {r.costo_anual_pct:.2f}% anual vs "
          f"{25 * bruto:.2f}% permitido   "
          f"{'PASA' if resultados[6] else 'NO PASA'}")

    pasa = all(resultados.values())
    print()
    print(f"  {sum(resultados.values())} de 6 criterios")
    print(f"  >>> {'E1 PASA' if pasa else 'E1 NO PASA'} <<<")
    if not pasa:
        print(f"  Falla: {', '.join(str(k) for k, v in resultados.items() if not v)}")

    print()
    print(f"  Informacion, no filtro: CAGR(E1)/CAGR(B1) = "
          f"{m_e1.cagr / m_b1.cagr:.3f}")
    print(f"  Contra la canasta B2: Calmar {m_e1.calmar:.3f} vs "
          f"{m_b2.calmar:.3f}")

    # --- Robustez ----------------------------------------------------------
    print()
    print("=" * 76)
    print(" ROBUSTEZ")
    print("=" * 76)
    print(robustez.informe_retiro(r.patrimonio, referencia=m_b1.cagr))
    print()
    sharpes = [metricas.sharpe_por_observacion(x)
               for x in (r_e0.patrimonio, r.patrimonio)]
    print(f"  Deflated Sharpe Ratio: "
          f"{robustez.deflated_sharpe(r.patrimonio, sharpes):.3f}  "
          f"(2 configuraciones probadas: E0 y E1)")

    # --- Sensibilidades ----------------------------------------------------
    print()
    print("=" * 76)
    print(" SENSIBILIDADES")
    print("=" * 76)
    maker = correr(armado.exposiciones, TipoOrden.MAKER)
    m_maker = metricas.calcular(maker.patrimonio, "E1 maker")
    print("  Ordenes maker suponiendo que TODAS entran (cota optimista, no")
    print("  creible: la especificacion no da tasa de ejecucion):")
    print(f"    CAGR {m_maker.cagr * 100:+.2f}%   Calmar {m_maker.calmar:.3f}   "
          f"costo {maker.costo_anual_pct:.2f}% anual")
    print(f"    Principal (taker): CAGR {m_e1.cagr * 100:+.2f}%   "
          f"Calmar {m_e1.calmar:.3f}   costo {r.costo_anual_pct:.2f}% anual")

    print()
    print("  Por año:")
    print("    año     E1        E0        B1        B2")
    for anio in sorted(set(r.patrimonio.index.year)):
        def var(serie):
            t = serie[serie.index.year == anio]
            return (t.iloc[-1] / t.iloc[0] - 1) * 100 if len(t) > 1 else np.nan
        print(f"    {anio}  {var(r.patrimonio):>+7.1f}%  "
              f"{var(r_e0.patrimonio):>+7.1f}%  "
              f"{var(benchmarks.comprar_y_mantener(datos_e0, CAPITAL)):>+7.1f}%  "
              f"{var(r_b2.patrimonio):>+7.1f}%")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
