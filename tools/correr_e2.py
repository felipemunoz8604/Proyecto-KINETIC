r"""
E2 -- largo/corto con perpetuos, contra los seis criterios y contra E1.

LA VARA, QUE ACA ES DOBLE
--------------------------
De la especificacion 6.3: *"Falsacion: falla los criterios de 3.3, **o no
supera a E1 en Calmar**. Si no supera a E1, la pata corta no justifica el
riesgo operativo adicional (liquidacion, financiacion, venue extra) y se
descarta."*

O sea que E2 tiene que pasar los seis criterios Y ademas superar a E1. Y hay
que decir algo incomodo de entrada: **E1 saco Calmar 0,268**, asi que superar
a E1 es una vara baja. Pasar los seis criterios no lo es.

LA ADVERTENCIA QUE LA ESPECIFICACION PIDE VIGILAR
---------------------------------------------------
*"El Calmar puede quedar bien y el retorno absoluto puede quedar demasiado
bajo para tener sentido con 500 USDT de capital. Ese caso hay que
identificarlo y reportarlo explicitamente, no esconderlo detras de un buen
ratio."*

Una cartera neutral cancela riesgo Y retorno. Por eso este informe reporta
siempre el retorno **en dolares**, no solo en ratios.

LA VENTANA ES MAS CORTA, Y ESO CAMBIA LA LECTURA
--------------------------------------------------
Los perpetuos nacen despues que sus pares de Spot: el mas viejo en 2020-01 y
la mediana en 2020-10. Todo numero de E2 se lee sobre la ventana efectiva que
imprime este informe, no sobre 2019-2024. Comparar su CAGR con el de E0 o E1
sin mirar eso seria comparar periodos distintos.

Se corre asi:

    venv\Scripts\python.exe tools\correr_e2.py
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


def _modelo() -> ModeloDeCostos:
    return ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb=True)


def _cargar(carpeta: Path, simbolos: list[str]):
    aperturas, cierres, atrs = {}, {}, {}
    for s in simbolos:
        try:
            velas = arch.cargar(s, "1d", carpeta)
        except FileNotFoundError:
            continue
        velas = velas[velas.index <= ventana.DISENO_HASTA]
        if velas.empty:
            continue
        aperturas[s] = velas["open"]
        cierres[s] = velas["close"]
        atrs[s] = cat.atr_relativo(velas)
    return pd.DataFrame(aperturas), pd.DataFrame(cierres), pd.DataFrame(atrs)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - E2: momentum largo/corto con perpetuos")
    print("=" * 76)
    print(f"  Capital {CAPITAL:.0f} USDT   sin compuerta   costos TAKER")
    print(f"  {e1.CUANTAS_POSICIONES} posiciones por pata, "
          f"{e2.FRACCION_POR_PATA:.0%} de bruta cada una")
    print()

    print("  Cargando panel y universo...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})

    print("  Cargando OHLC de Spot y de perpetuos...", flush=True)
    ap_spot, ci_spot, atr_spot = _cargar(CARPETA, candidatos)
    ap_perp, ci_perp, atr_perp = _cargar(CARPETA_PERP, candidatos)
    print(f"    {ci_spot.shape[1]} en Spot, {ci_perp.shape[1]} con perpetuo")
    if ci_perp.empty:
        print("  No hay perpetuos. Corre antes tools/descargar_perpetuos.py")
        return 1

    # --- La ventana efectiva ---------------------------------------------
    primera_perp = ci_perp.apply(lambda c: c.first_valid_index()).min()
    desde = max(ventana.DISENO_DESDE, primera_perp)
    dias = ci_spot.index[(ci_spot.index >= desde)
                         & (ci_spot.index <= ventana.DISENO_HASTA)]
    print(f"  VENTANA EFECTIVA: {dias[0].date()} a {dias[-1].date()} "
          f"({len(dias):,} dias)")
    print(f"    contra la de diseño, que empieza "
          f"{ventana.DISENO_DESDE.date()}: se pierden "
          f"{(desde - ventana.DISENO_DESDE).days} dias por el nacimiento de "
          "los perpetuos")

    print("\n  Armando exposiciones...", flush=True)
    armado = e2.construir_exposiciones(ci_spot, ap_spot, ci_perp, ap_perp,
                                       atr_spot, atr_perp, universo, dias)
    cols = list(armado.exposiciones.columns)
    print(f"    listo ({time.time() - t0:.0f} s)")

    # --- Precios por instrumento -----------------------------------------
    # Cada columna se sirve del venue que le corresponde. `AAAUSDT` toma
    # precios de Spot y `AAAUSDT.P` del perpetuo: son instrumentos distintos.
    def matriz(spot: pd.DataFrame, perp: pd.DataFrame) -> pd.DataFrame:
        datos = {}
        for c in cols:
            base = e2.simbolo_base(c)
            origen = perp if e2.es_perpetuo(c) else spot
            if base in origen.columns:
                datos[c] = origen[base]
        return pd.DataFrame(datos).reindex(index=dias, columns=cols)

    aperturas = matriz(ap_spot, ap_perp)
    cierres = matriz(ci_spot, ci_perp)

    rangos_moneda = e1.rangos_de_liquidez(universo, dias)
    rangos = pd.DataFrame(
        {c: rangos_moneda[e2.simbolo_base(c)]
         for c in cols if e2.simbolo_base(c) in rangos_moneda.columns},
        index=dias)

    # --- Financiacion de la pata corta ------------------------------------
    tasas: dict[str, pd.Series] = {}
    for c in cols:
        if not e2.es_perpetuo(c):
            continue
        base = e2.simbolo_base(c)
        ruta = CARPETA_FIN / f"{base}.csv"
        if not ruta.exists():
            continue
        d = fin.cargar(base, CARPETA_FIN)
        tasas[c] = d["tasa"]
    print(f"  Financiacion cargada para {len(tasas)} perpetuos")

    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None

    def correr(exposiciones: pd.DataFrame,
               con_financiacion: bool = True) -> mc.ResultadoCartera:
        return mc.simular(
            aperturas.reindex(index=exposiciones.index),
            cierres.reindex(index=exposiciones.index),
            exposiciones, CAPITAL, _modelo(), rangos=rangos, filtros=filtros,
            permitir_cortos=True,
            financiacion_de_cortos=tasas if con_financiacion else None)

    r = correr(armado.exposiciones)
    m_e2 = metricas.calcular(r.patrimonio, "E2",
                             exposicion=r.exposicion.abs().sum(axis=1),
                             rotacion_anual=r.rotacion_anual,
                             costo_anual_pct=r.costo_anual_pct)

    # --- Los rivales, sobre LA MISMA ventana ------------------------------
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
    m_e0 = metricas.calcular(r_e0.patrimonio, "B0 = E0")
    m_b1 = metricas.calcular(
        benchmarks.comprar_y_mantener(datos_btc, CAPITAL), "B1")

    armado_e1 = e1.construir_exposiciones(ci_spot, ap_spot, atr_spot,
                                          cp.compuerta_de_regimen(
                                              panel.cierres[REFERENCIA].dropna()),
                                          universo, dias)
    cols_e1 = list(armado_e1.exposiciones.columns)
    r_e1 = mc.simular(
        ap_spot.reindex(index=dias, columns=cols_e1),
        ci_spot.reindex(index=dias, columns=cols_e1),
        armado_e1.exposiciones, CAPITAL, _modelo(),
        rangos=rangos_moneda, filtros=filtros)
    m_e1 = metricas.calcular(r_e1.patrimonio, "E1")

    print()
    print("=" * 76)
    print(" RESULTADO (todos sobre la ventana efectiva de E2)")
    print("=" * 76)
    for m in (m_e2, m_e1, m_e0, m_b1):
        print(m.informe())
        print()

    print(f"  Financiacion cobrada por la pata corta: "
          f"{r.financiacion_total:+.2f} USDT "
          f"({r.financiacion_total / CAPITAL * 100:+.1f}% del capital inicial)")
    print(f"  Stops disparados: {len(armado.stops_disparados)} "
          f"({sum(1 for d in armado.stops_disparados if d['pata'] == 'corta')} "
          "en la pata corta)")
    print(f"  Dias sin pata corta: {armado.dias_sin_cortos}")
    print(f"  Deslistados atravesados: {len(r.deslistados)}")

    # --- Los criterios -----------------------------------------------------
    print()
    print("=" * 76)
    print(" LOS SEIS CRITERIOS, MAS LA FALSACION PROPIA DE E2")
    print("=" * 76)
    resultados = {}

    print("  Criterio 1 -- Calmar contra B1, por pares...", flush=True)
    comparacion = robustez.comparar_por_pares(
        pd.DataFrame(index=dias).assign(marca=1.0),
        lambda tramo: correr(armado.exposiciones.loc[
            armado.exposiciones.index >= tramo.index[0]]).patrimonio,
        lambda tramo: benchmarks.comprar_y_mantener(
            datos_btc[datos_btc.index >= tramo.index[0]], CAPITAL),
    )
    resultados[1] = comparacion.mediana >= 1.8
    print(f"    mediana {comparacion.mediana:.3f}   exigido 1,8   "
          f"{'PASA' if resultados[1] else 'NO PASA'}")

    tope = 0.60 * abs(m_b1.caida_maxima)
    resultados[2] = abs(m_e2.caida_maxima) <= tope
    print(f"  Criterio 2 -- caida {abs(m_e2.caida_maxima) * 100:.1f}% vs "
          f"{tope * 100:.1f}%   {'PASA' if resultados[2] else 'NO PASA'}")

    piso = max(m_e0.calmar, m_b1.calmar)
    cual = "E0" if m_e0.calmar >= m_b1.calmar else "B1"
    resultados[3] = m_e2.calmar >= 1.15 * piso
    print(f"  Criterio 3 -- Calmar {m_e2.calmar:.3f} vs {1.15 * piso:.3f} "
          f"(1,15 x {cual})   {'PASA' if resultados[3] else 'NO PASA'}")

    ic = robustez.bootstrap_cagr(r.patrimonio)
    resultados[4] = ic.excluye_cero
    print(f"  Criterio 4 -- IC 95% [{ic.bajo * 100:+.2f}%, "
          f"{ic.alto * 100:+.2f}%]   "
          f"{'PASA' if resultados[4] else 'NO PASA'}")

    curva = robustez.retiro_top_k(r.patrimonio)
    resultados[5] = curva[3] >= 0.50 * m_b1.cagr
    print(f"  Criterio 5 -- sin 3 meses {curva[3] * 100:+.2f}% vs "
          f"{0.50 * m_b1.cagr * 100:+.2f}%   "
          f"{'PASA' if resultados[5] else 'NO PASA'}")

    bruto = m_e2.cagr + r.costo_anual_pct / 100.0
    resultados[6] = (r.costo_anual_pct / 100.0) <= 0.25 * bruto if bruto > 0 else False
    print(f"  Criterio 6 -- costo {r.costo_anual_pct:.2f}% vs "
          f"{25 * bruto:.2f}%   {'PASA' if resultados[6] else 'NO PASA'}")

    supera_e1 = m_e2.calmar > m_e1.calmar
    print()
    print(f"  Falsacion propia: Calmar E2 {m_e2.calmar:.3f} vs "
          f"E1 {m_e1.calmar:.3f}   "
          f"{'supera a E1' if supera_e1 else 'NO supera a E1'}")
    if not supera_e1:
        print("    => la pata corta no justifica el riesgo operativo extra")

    pasa = all(resultados.values()) and supera_e1
    print()
    print(f"  {sum(resultados.values())} de 6 criterios"
          f"{' + supera a E1' if supera_e1 else ''}")
    print(f"  >>> {'E2 PASA' if pasa else 'E2 NO PASA'} <<<")
    if not all(resultados.values()):
        print(f"  Falla: {', '.join(str(k) for k, v in resultados.items() if not v)}")

    # --- Lo que la especificacion pide vigilar ---------------------------
    print()
    print("=" * 76)
    print(" EL RETORNO ABSOLUTO, QUE UN BUEN RATIO PUEDE ESCONDER")
    print("=" * 76)
    anios = len(dias) / 365.0
    print(f"  E2 sobre {CAPITAL:.0f} USDT en {anios:.1f} años: "
          f"{m_e2.patrimonio_final - CAPITAL:+.2f} USDT")
    print(f"    o sea {(m_e2.patrimonio_final - CAPITAL) / anios:+.2f} USDT "
          "por año")
    print(f"  E0 en la misma ventana: "
          f"{m_e0.patrimonio_final - CAPITAL:+.2f} USDT")
    print(f"  B1 en la misma ventana: "
          f"{m_b1.patrimonio_final - CAPITAL:+.2f} USDT")

    # --- Robustez y sensibilidades ---------------------------------------
    print()
    print("=" * 76)
    print(" ROBUSTEZ Y SENSIBILIDADES")
    print("=" * 76)
    print(robustez.informe_retiro(r.patrimonio, referencia=m_b1.cagr))
    sharpes = [metricas.sharpe_por_observacion(x)
               for x in (r_e0.patrimonio, r_e1.patrimonio, r.patrimonio)]
    print(f"\n  Deflated Sharpe: "
          f"{robustez.deflated_sharpe(r.patrimonio, sharpes):.3f}  "
          "(3 configuraciones: E0, E1, E2)")

    sin_fin = correr(armado.exposiciones, con_financiacion=False)
    m_sin = metricas.calcular(sin_fin.patrimonio, "E2 sin financiacion")
    print()
    print("  Sin cobrar financiacion (para ver cuanto aporta):")
    print(f"    CAGR {m_sin.cagr * 100:+.2f}%   Calmar {m_sin.calmar:.3f}")
    print(f"    Con financiacion: CAGR {m_e2.cagr * 100:+.2f}%   "
          f"Calmar {m_e2.calmar:.3f}")

    print()
    print("  Por año:")
    print("    año     E2        E1        E0        B1")
    for anio in sorted(set(r.patrimonio.index.year)):
        def var(serie):
            t = serie[serie.index.year == anio]
            return (t.iloc[-1] / t.iloc[0] - 1) * 100 if len(t) > 1 else np.nan
        print(f"    {anio}  {var(r.patrimonio):>+7.1f}%  "
              f"{var(r_e1.patrimonio):>+7.1f}%  {var(r_e0.patrimonio):>+7.1f}%  "
              f"{var(benchmarks.comprar_y_mantener(datos_btc, CAPITAL)):>+7.1f}%")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
