r"""
Los cuatro candidatos de la Fase 2, uno al lado del otro, sobre la MISMA ventana.

POR QUE HACE FALTA ESTE CUADRO
-------------------------------
Cada candidata se corrio con la ventana que le tocaba: E0 y E1 desde 2019, E2
recien desde 2020 porque los perpetuos nacen despues. Comparar sus CAGR asi es
comparar periodos distintos, y 2019 fue un año en que BTC hizo +89%.

Aca todo se recalcula desde la fecha mas tardia de las cuatro. Los numeros no
coinciden con los de cada informe individual, y esta bien que no coincidan: son
la misma estrategia medida sobre otro tramo.

QUE ES Y QUE NO ES
-------------------
Es una **reagrupacion de resultados ya obtenidos**. No hay ninguna
configuracion nueva, ningun parametro distinto, ninguna variante que no se
haya corrido ya con sus criterios escritos de antemano.

**No busca la combinacion que funcione.** Despues de ver fallar cuatro
candidatas, armar una quinta mirando lo que fallo seria el barrido que este
proyecto existe para evitar --- y peor que un barrido comun, porque ya
conocemos los datos.

Se corre asi:

    venv\Scripts\python.exe tools\comparar_candidatos.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from backtesting import motor_cartera as mc  # noqa: E402
from core import archivo_binance as arch  # noqa: E402
from core import financiacion as fin  # noqa: E402
from core import universo as uni  # noqa: E402
from execution.costos import ModeloDeCostos, TipoOrden, Venue  # noqa: E402
from execution.filtros import TablaDeFiltros  # noqa: E402
from metrics import benchmarks, metricas, robustez, ventana  # noqa: E402
from risk import catastrofe as cat  # noqa: E402
from risk import compuerta as cp  # noqa: E402
from strategy import e0, e1, e2  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
CARPETA_PERP = RAIZ / "data" / "perpetuo"
CARPETA_FIN = RAIZ / "data" / "financiacion"
FILTROS = RAIZ / "data" / "filtros_spot.json"
CAPITAL = 500.0
REFERENCIA = "BTCUSDT"

# De docs/FASE_2_criterios.md, seccion 3.
UMBRALES = {1: 1.8, 2: 0.60, 3: 1.15, 5: 0.50, 6: 0.25}


def _modelo() -> ModeloDeCostos:
    return ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb=True)


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


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 78)
    print(" KINETIC - los cuatro candidatos de la Fase 2, sobre la misma ventana")
    print("=" * 78)
    print()

    print("  Cargando...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})
    ap_spot, ci_spot, atr_spot = _cargar(CARPETA, candidatos)
    ap_perp, ci_perp, atr_perp = _cargar(CARPETA_PERP, candidatos)

    desde = max(ventana.DISENO_DESDE,
                ci_perp.apply(lambda c: c.first_valid_index()).min())
    dias = ci_spot.index[(ci_spot.index >= desde)
                         & (ci_spot.index <= ventana.DISENO_HASTA)]
    anios = len(dias) / 365.0
    print(f"  Ventana comun: {dias[0].date()} a {dias[-1].date()} "
          f"({anios:.1f} años)")
    print("  La manda E2: antes de 2020 no habia perpetuos.")

    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None
    rangos_moneda = e1.rangos_de_liquidez(universo, dias)
    g = cp.compuerta_de_regimen(panel.cierres[REFERENCIA].dropna())

    # --- B1 y E0 ----------------------------------------------------------
    velas_btc = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas_btc = velas_btc[velas_btc.index <= ventana.DISENO_HASTA]
    datos_btc = velas_btc.assign(
        exposicion=e0.exposicion_objetivo(velas_btc["close"]))
    datos_btc = datos_btc[datos_btc.index >= desde]

    r_e0 = mc.simular(
        datos_btc[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos_btc[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos_btc[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        CAPITAL, _modelo(), rangos={e0.SIMBOLO: 1}, filtros=filtros)
    p_b1 = benchmarks.comprar_y_mantener(datos_btc, CAPITAL)

    # --- E1 ----------------------------------------------------------------
    a_e1 = e1.construir_exposiciones(ci_spot, ap_spot, atr_spot, g, universo,
                                     dias)
    cols_e1 = list(a_e1.exposiciones.columns)
    r_e1 = mc.simular(ap_spot.reindex(index=dias, columns=cols_e1),
                      ci_spot.reindex(index=dias, columns=cols_e1),
                      a_e1.exposiciones, CAPITAL, _modelo(),
                      rangos=rangos_moneda, filtros=filtros)

    # --- E2 ----------------------------------------------------------------
    a_e2 = e2.construir_exposiciones(ci_spot, ap_spot, ci_perp, ap_perp,
                                     atr_spot, atr_perp, universo, dias)
    cols_e2 = list(a_e2.exposiciones.columns)

    def matriz(spot, perp):
        datos = {}
        for c in cols_e2:
            base = e2.simbolo_base(c)
            origen = perp if e2.es_perpetuo(c) else spot
            if base in origen.columns:
                datos[c] = origen[base]
        return pd.DataFrame(datos).reindex(index=dias, columns=cols_e2)

    tasas = {}
    for c in cols_e2:
        if not e2.es_perpetuo(c):
            continue
        base = e2.simbolo_base(c)
        if (CARPETA_FIN / f"{base}.csv").exists():
            tasas[c] = fin.cargar(base, CARPETA_FIN)["tasa"]

    r_e2 = mc.simular(
        matriz(ap_spot, ap_perp), matriz(ci_spot, ci_perp), a_e2.exposiciones,
        CAPITAL, _modelo(),
        rangos=pd.DataFrame({c: rangos_moneda[e2.simbolo_base(c)]
                             for c in cols_e2
                             if e2.simbolo_base(c) in rangos_moneda.columns},
                            index=dias),
        filtros=filtros, permitir_cortos=True, financiacion_de_cortos=tasas)

    # --- Los nulos, que son lo que hace interpretable todo lo demas --------
    media_e0 = float(r_e0.exposicion.sum(axis=1).mean())
    p_nulo = (benchmarks.comprar_y_mantener(datos_btc, CAPITAL * media_e0)
              + CAPITAL * (1.0 - media_e0))

    filas = [
        ("B1  comprar y mantener BTC", metricas.calcular(p_b1, "B1"), None),
        (f"Nulo  {media_e0:.0%} de BTC, una vez",
         metricas.calcular(p_nulo, "nulo"), None),
        ("E0  BTC + compuerta + vol objetivo",
         metricas.calcular(r_e0.patrimonio, "E0"), r_e0),
        ("E1  momentum transversal largo",
         metricas.calcular(r_e1.patrimonio, "E1"), r_e1),
        ("E2  momentum largo/corto",
         metricas.calcular(r_e2.patrimonio, "E2"), r_e2),
    ]

    print()
    print("=" * 78)
    print(" EL CUADRO")
    print("=" * 78)
    print(f"  {'':<36}{'CAGR':>9}{'Caida':>9}{'Calmar':>9}"
          f"{'USDT':>11}{'Costo/año':>11}")
    for nombre, m, r in filas:
        costo = f"{r.costo_anual_pct:.2f}%" if r else "--"
        print(f"  {nombre:<36}{m.cagr * 100:>+8.2f}%{m.caida_maxima * 100:>8.1f}%"
              f"{m.calmar:>9.3f}{m.patrimonio_final - CAPITAL:>+11.0f}"
              f"{costo:>11}")
    print()
    print(f"  E3  carry de financiacion            "
          f"{5.12:>+8.2f}%{'--':>9}{'--':>9}{5.12 / 100 * CAPITAL * anios:>+11.0f}"
          f"{'0.36%':>11}")
    print("      (de la medicion 5.1, no simulada: la falsacion previa la")
    print("       resolvio antes de codificarla)")

    # --- La matriz de criterios -------------------------------------------
    print()
    print("=" * 78)
    print(" MATRIZ DE CRITERIOS")
    print("=" * 78)
    m_b1 = filas[0][1]
    m_e0 = filas[2][1]
    print(f"  {'':<8}{'1 Calmar':>10}{'2 Caida':>10}{'3 vs base':>11}"
          f"{'4 IC':>8}{'5 cola':>9}{'6 costo':>9}   veredicto")
    for nombre, m, r in filas[2:]:
        if r is None:
            continue
        ic = robustez.bootstrap_cagr(r.patrimonio)
        curva = robustez.retiro_top_k(r.patrimonio)
        bruto = m.cagr + r.costo_anual_pct / 100.0
        piso = max(m_e0.calmar, m_b1.calmar)
        c = {
            1: m.calmar >= UMBRALES[1] * m_b1.calmar,
            2: abs(m.caida_maxima) <= UMBRALES[2] * abs(m_b1.caida_maxima),
            3: m.calmar >= UMBRALES[3] * piso,
            4: ic.excluye_cero,
            5: curva[3] >= UMBRALES[5] * m_b1.cagr,
            6: (r.costo_anual_pct / 100.0) <= UMBRALES[6] * bruto if bruto > 0
               else False,
        }
        marcas = "".join(f"{'  si' if c[k] else '  NO':>10}"
                         if k in (1, 2) else
                         f"{'  si' if c[k] else '  NO':>11}" if k == 3 else
                         f"{'  si' if c[k] else '  NO':>8}" if k == 4 else
                         f"{'  si' if c[k] else '  NO':>9}"
                         for k in (1, 2, 3, 4, 5, 6))
        print(f"  {m.nombre:<8}{marcas}   "
              f"{sum(c.values())}/6  {'PASA' if all(c.values()) else 'NO PASA'}")
    print()
    print("  El criterio 1 exige Calmar >= 1,8 x el de B1, o sea "
          f"{UMBRALES[1] * m_b1.calmar:.3f}.")
    print("  El mejor de los cuatro llego a "
          f"{max(f[1].calmar for f in filas[2:]):.3f}.")

    # --- El patron ---------------------------------------------------------
    print()
    print("=" * 78)
    print(" QUE DICE EL PATRON")
    print("=" * 78)
    calmares = {m.nombre: m.calmar for _, m, _ in filas}
    print("  Cada capa que se le agrego a 'comprar BTC' le RESTO Calmar:")
    print(f"    comprar y mantener BTC            {calmares['B1']:.3f}")
    print(f"    + compuerta y volatilidad (E0)    {calmares['E0']:.3f}")
    print(f"    + seleccion por momentum (E1)     {calmares['E1']:.3f}")
    print(f"    + pata corta (E2)                 {calmares['E2']:.3f}")
    print()
    print("  El nulo dice de donde viene lo poco que E0 aporta:")
    print(f"    tener {media_e0:.0%} de BTC sin mirar nada      "
          f"{calmares['nulo']:.3f}")
    print(f"    E0, o sea mirarlo todos los dias        {calmares['E0']:.3f}")
    print("  La compuerta SI compra Calmar sobre no hacer nada. Lo que no")
    print("  alcanza es a superar a tener BTC y punto.")

    print()
    print("  Concentracion (CAGR que queda sacando los 3 mejores meses):")
    for nombre, m, r in filas[2:]:
        if r is None:
            continue
        curva = robustez.retiro_top_k(r.patrimonio)
        print(f"    {m.nombre:<4} {m.cagr * 100:>+7.2f}%  ->  "
              f"{curva[3] * 100:>+7.2f}%")

    print()
    print("  Costo pagado por año, y rotacion:")
    for nombre, m, r in filas[2:]:
        if r is None:
            continue
        print(f"    {m.nombre:<4} {r.costo_anual_pct:>5.2f}%   "
              f"{r.rotacion_anual:>5.1f} vueltas")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
