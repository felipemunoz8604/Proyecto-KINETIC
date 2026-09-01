r"""
R1 y R2 -- las dos hipotesis de rescate de E1, corridas por decision de Felipe.

QUE SON, Y POR QUE NO SON UN BARRIDO
--------------------------------------
Estan **preautorizadas en la especificacion**, nombradas y cerradas antes de
ver ningun resultado:

- **R1:** ventana de momentum de **90 dias** en lugar de 28. Esta dentro del
  rango que la literatura considera.
- **R2:** **8 posiciones** en lugar de 5, para diluir el riesgo idiosincratico.

Todo lo demas es identico a E1. La especificacion tambien dice, con todas las
letras: *"Una tercera no se hace."* Con estas dos se agota el cupo.

DECISION DE FELIPE, 31-ago-2026
---------------------------------
La recomendacion registrada era **no correrlas**: a E1 le faltaba un factor de
cuatro en Calmar, y su criterio 4 decia que no hay señal, no que este mal
sintonizada. Felipe decidio correrlas igual, y la decision es suya. Queda
anotado que se corrieron sabiendo eso, no en lugar de saberlo.

EL PRECIO SE PAGA EN EL DEFLATED SHARPE
-----------------------------------------
Probar mas configuraciones sobre la misma ventana sube la probabilidad de
encontrar algo bueno por azar, aunque cada valor venga de literatura. El
compromiso previo lo dice: *"se reporta con el numero de configuraciones
probadas hasta ese momento, que crece a lo largo de la fase."*

Antes de esto habia **tres** (E0, E1, E2). Con R1 y R2 son **cinco**, y el DSR
se calcula sobre las cinco. Es la contabilidad honesta de haber probado mas.

Se corre asi:

    venv\Scripts\python.exe tools\correr_rescates.py
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

VARIANTES = {
    "E1":  {},                          # la base, para tener la referencia
    "R1":  {"dias_momentum": 90},
    "R2":  {"cuantas": 8},
}


def _modelo() -> ModeloDeCostos:
    return ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb=True)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 78)
    print(" KINETIC - R1 y R2, las dos hipotesis de rescate de E1")
    print("=" * 78)
    print("  R1: ventana de momentum 90 dias (en vez de 28)")
    print("  R2: 8 posiciones (en vez de 5)")
    print("  Todo lo demas identico a E1. Preautorizadas en la especificacion.")
    print()

    print("  Cargando...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})

    ap, ci, atr = {}, {}, {}
    for s in candidatos:
        try:
            v = arch.cargar(s, "1d", CARPETA)
        except FileNotFoundError:
            continue
        v = v[v.index <= ventana.DISENO_HASTA]
        if v.empty:
            continue
        ap[s], ci[s], atr[s] = v["open"], v["close"], cat.atr_relativo(v)
    ap, ci, atr = pd.DataFrame(ap), pd.DataFrame(ci), pd.DataFrame(atr)

    g = cp.compuerta_de_regimen(panel.cierres[REFERENCIA].dropna())
    dias = ci.index[(ci.index >= ventana.DISENO_DESDE)
                    & (ci.index <= ventana.DISENO_HASTA)]
    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None
    rangos = e1.rangos_de_liquidez(universo, dias)
    print(f"  Ventana {dias[0].date()} a {dias[-1].date()} "
          f"({len(dias):,} dias)   {time.time() - t0:.0f} s")

    # --- Los rivales ------------------------------------------------------
    velas_btc = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas_btc = velas_btc[velas_btc.index <= ventana.DISENO_HASTA]
    datos_btc = velas_btc.assign(
        exposicion=e0.exposicion_objetivo(velas_btc["close"]))
    datos_btc = datos_btc[datos_btc.index >= ventana.DISENO_DESDE]
    r_e0 = mc.simular(
        datos_btc[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos_btc[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos_btc[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        CAPITAL, _modelo(), rangos={e0.SIMBOLO: 1}, filtros=filtros)
    m_e0 = metricas.calcular(r_e0.patrimonio, "E0")
    p_b1 = benchmarks.comprar_y_mantener(datos_btc, CAPITAL)
    m_b1 = metricas.calcular(p_b1, "B1")

    # --- Las variantes ----------------------------------------------------
    corridas = {}
    for nombre, kwargs in VARIANTES.items():
        print(f"  Armando {nombre}...", flush=True)
        armado = e1.construir_exposiciones(ci, ap, atr, g, universo, dias,
                                           **kwargs)
        cols = list(armado.exposiciones.columns)
        r = mc.simular(ap.reindex(index=dias, columns=cols),
                       ci.reindex(index=dias, columns=cols),
                       armado.exposiciones, CAPITAL, _modelo(),
                       rangos=rangos, filtros=filtros)
        corridas[nombre] = (armado, r, metricas.calcular(r.patrimonio, nombre))

    print()
    print("=" * 78)
    print(" EL CUADRO")
    print("=" * 78)
    print(f"  {'':<6}{'CAGR':>9}{'Caida':>9}{'Calmar':>9}{'USDT':>10}"
          f"{'Costo/año':>11}{'Posiciones':>12}")
    for nombre, (armado, r, m) in corridas.items():
        posiciones = int((armado.exposiciones > 0).sum(axis=1).max())
        print(f"  {nombre:<6}{m.cagr * 100:>+8.2f}%{m.caida_maxima * 100:>8.1f}%"
              f"{m.calmar:>9.3f}{m.patrimonio_final - CAPITAL:>+10.0f}"
              f"{r.costo_anual_pct:>10.2f}%{posiciones:>12}")
    print(f"  {'E0':<6}{m_e0.cagr * 100:>+8.2f}%{m_e0.caida_maxima * 100:>8.1f}%"
          f"{m_e0.calmar:>9.3f}{m_e0.patrimonio_final - CAPITAL:>+10.0f}"
          f"{r_e0.costo_anual_pct:>10.2f}%{1:>12}")
    print(f"  {'B1':<6}{m_b1.cagr * 100:>+8.2f}%{m_b1.caida_maxima * 100:>8.1f}%"
          f"{m_b1.calmar:>9.3f}{m_b1.patrimonio_final - CAPITAL:>+10.0f}"
          f"{'--':>11}{1:>12}")

    # --- Los seis criterios, para cada rescate -----------------------------
    print()
    print("=" * 78)
    print(" LOS SEIS CRITERIOS")
    print("=" * 78)
    piso = max(m_e0.calmar, m_b1.calmar)
    exigido_1 = 1.8
    print(f"  El criterio 1 pide mediana del cociente >= {exigido_1}, "
          f"el 3 pide Calmar >= {1.15 * piso:.3f}")
    print()

    veredictos = {}
    for nombre, (armado, r, m) in corridas.items():
        comparacion = robustez.comparar_por_pares(
            pd.DataFrame(index=dias).assign(marca=1.0),
            lambda tramo, _a=armado: mc.simular(
                ap.reindex(index=_a.exposiciones.index[
                    _a.exposiciones.index >= tramo.index[0]],
                    columns=list(_a.exposiciones.columns)),
                ci.reindex(index=_a.exposiciones.index[
                    _a.exposiciones.index >= tramo.index[0]],
                    columns=list(_a.exposiciones.columns)),
                _a.exposiciones.loc[_a.exposiciones.index >= tramo.index[0]],
                CAPITAL, _modelo(), rangos=rangos, filtros=filtros).patrimonio,
            lambda tramo: benchmarks.comprar_y_mantener(
                datos_btc[datos_btc.index >= tramo.index[0]], CAPITAL),
        )
        ic = robustez.bootstrap_cagr(r.patrimonio)
        curva = robustez.retiro_top_k(r.patrimonio)
        bruto = m.cagr + r.costo_anual_pct / 100.0
        c = {
            1: comparacion.mediana >= exigido_1,
            2: abs(m.caida_maxima) <= 0.60 * abs(m_b1.caida_maxima),
            3: m.calmar >= 1.15 * piso,
            4: ic.excluye_cero,
            5: curva[3] >= 0.50 * m_b1.cagr,
            6: (r.costo_anual_pct / 100.0) <= 0.25 * bruto if bruto > 0 else False,
        }
        veredictos[nombre] = c
        marcas = "  ".join(f"{k}:{'si ' if v else 'NO '}" for k, v in c.items())
        print(f"  {nombre:<4} {marcas}   {sum(c.values())}/6  "
              f"{'PASA' if all(c.values()) else 'NO PASA'}")
        print(f"       criterio 1: mediana {comparacion.mediana:.3f}   "
              f"criterio 4: IC [{ic.bajo * 100:+.1f}%, {ic.alto * 100:+.1f}%]   "
              f"criterio 5: {curva[3] * 100:+.2f}%")

    # --- El precio de haber probado mas ------------------------------------
    print()
    print("=" * 78)
    print(" EL DEFLATED SHARPE, AHORA SOBRE CINCO CONFIGURACIONES")
    print("=" * 78)
    print("  Antes de R1 y R2 habia tres probadas (E0, E1, E2). Ahora cinco.")
    print("  Probar mas sube la probabilidad de encontrar algo bueno por azar,")
    print("  y el DSR es lo que descuenta eso. Es el precio de esta corrida.")
    print()
    sharpes_tres = [metricas.sharpe_por_observacion(r_e0.patrimonio),
                    metricas.sharpe_por_observacion(corridas["E1"][1].patrimonio)]
    sharpes_cinco = sharpes_tres + [
        metricas.sharpe_por_observacion(corridas["R1"][1].patrimonio),
        metricas.sharpe_por_observacion(corridas["R2"][1].patrimonio)]
    for nombre, (_, r, _) in corridas.items():
        con_tres = robustez.deflated_sharpe(r.patrimonio, sharpes_tres)
        con_cinco = robustez.deflated_sharpe(r.patrimonio, sharpes_cinco)
        print(f"  {nombre:<4}  con 3 configuraciones {con_tres:.3f}   "
              f"con 5 {con_cinco:.3f}")
    print("  Hace falta 0,95 para hablar de evidencia.")

    print()
    print("  Por año:")
    print("    año     E1        R1        R2        E0        B1")
    for anio in sorted(set(dias.year)):
        def var(serie):
            t = serie[serie.index.year == anio]
            return (t.iloc[-1] / t.iloc[0] - 1) * 100 if len(t) > 1 else np.nan
        fila = "  ".join(f"{var(corridas[n][1].patrimonio):>+7.1f}%"
                         for n in ("E1", "R1", "R2"))
        print(f"    {anio}  {fila}  {var(r_e0.patrimonio):>+7.1f}%  "
              f"{var(p_b1):>+7.1f}%")

    print()
    print("=" * 78)
    print(" EL CUPO DE RESCATES QUEDA AGOTADO")
    print("=" * 78)
    print("  La especificacion permite dos hipotesis de rescate por estrategia")
    print("  y dice, textual: 'Una tercera no se hace.' Estas eran las dos.")
    print("  Cualquier variante nueva sobre E1 ya seria un barrido.")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
