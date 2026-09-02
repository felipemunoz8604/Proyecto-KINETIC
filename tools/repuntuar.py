r"""
Paso 1 de la segunda consulta: re-puntuar las corridas contra C-A y C-B.

POR QUE CUESTA CERO PRUEBAS DE DSR
------------------------------------
**Re-puntuar no selecciona nada.** Son las mismas seis configuraciones ya
corridas, medidas con otra regla. No se prueba ninguna variante nueva, asi que
el numero de intentos no cambia y el Deflated Sharpe queda igual.

Es la diferencia entre cambiar la vara y probar otra estrategia.

LO QUE PUEDE RESOLVER
----------------------
El criterio 1 funde captura y proteccion en un numero. E0 lo falla, y de ahi
no se puede leer que **la caida ya esta resuelta** y que lo que falta es la
captura. C-A y C-B lo separan.

Si E0 pasa C-B con holgura y falla C-A, la conversacion deja de ser "no
encontramos nada" y pasa a ser "hay un seguro contra mercados bajistas cuya
prima esta medida en X puntos de captura". Es un producto distinto.

LOS UMBRALES SON PROVISIONALES Y ESTAN MARCADOS COMO TALES
------------------------------------------------------------
El analista propuso 70% de captura y 40% de caida, pero **no derivo de donde
salen esos numeros**. Adoptarlos sin justificacion seria cambiar un umbral
arbitrario por dos.

Este informe reporta los VALORES medidos, que valen cualquiera sea el umbral,
y muestra donde caerian contra 70/40 **marcado como provisional**. El veredicto
formal necesita que Felipe fije los umbrales con su razon, por escrito y antes
de usarlos.

Se corre asi:

    venv\Scripts\python.exe tools\repuntuar.py
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
from metrics import benchmarks, metricas, regimen, ventana  # noqa: E402
from risk import catastrofe as cat  # noqa: E402
from risk import compuerta as cp  # noqa: E402
from strategy import e0, e1, e2  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
CARPETA_PERP = RAIZ / "data" / "perpetuo"
CARPETA_FIN = RAIZ / "data" / "financiacion"
FILTROS = RAIZ / "data" / "filtros_spot.json"
CAPITAL = 500.0
REFERENCIA = "BTCUSDT"

# PROVISIONALES. Propuestos por el analista, sin derivacion. No son la vara
# hasta que Felipe los fije con su razon.
CAPTURA_PROPUESTA = 0.70
PROTECCION_PROPUESTA = 0.40


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
    print(" KINETIC - re-puntaje contra C-A (captura) y C-B (proteccion)")
    print("=" * 78)
    print("  Paso 1 de la respuesta a la segunda consulta. Cuesta CERO")
    print("  pruebas de DSR: son las mismas corridas con otra regla.")
    print()

    print("  Cargando...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas_reb = [f for f in uni.fechas_de_rebalanceo(panel)
                  if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    universo = uni.construir(panel, fechas_reb)
    candidatos = sorted({s for v in universo.values() for s in v})
    ap, ci, atr = _cargar(CARPETA, candidatos)
    ap_p, ci_p, atr_p = _cargar(CARPETA_PERP, candidatos)
    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None
    g = cp.compuerta_de_regimen(panel.cierres[REFERENCIA].dropna())

    velas_btc = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas_btc = velas_btc[velas_btc.index <= ventana.DISENO_HASTA]

    # La ventana comun la manda E2: antes de 2020 no hay perpetuos.
    desde = max(ventana.DISENO_DESDE,
                ci_p.apply(lambda c: c.first_valid_index()).min())
    dias = ci.index[(ci.index >= desde) & (ci.index <= ventana.DISENO_HASTA)]
    rangos = e1.rangos_de_liquidez(universo, dias)
    print(f"  Ventana comun {dias[0].date()} a {dias[-1].date()}   "
          f"({time.time() - t0:.0f} s)")

    # --- Regimen -----------------------------------------------------------
    alcistas = regimen.clasificar_meses(velas_btc["close"])
    en_ventana = alcistas[(alcistas.index >= dias[0].to_period("M"))
                          & (alcistas.index <= dias[-1].to_period("M"))]
    print(f"  Meses alcistas {int(en_ventana.sum())}, "
          f"bajistas {int((~en_ventana).sum())} de {len(en_ventana)}")
    print("  Regla: alcista si el retorno de BTC de los 12 meses PREVIOS fue")
    print("  positivo. Rezagado, asi que ningun mes se clasifica con su propio")
    print("  resultado.")
    print("\n  Los meses bajistas:")
    bajistas = [str(m) for m in en_ventana[~en_ventana].index]
    for i in range(0, len(bajistas), 8):
        print("    " + "  ".join(bajistas[i:i + 8]))

    # --- Las curvas --------------------------------------------------------
    datos_btc = velas_btc.assign(
        exposicion=e0.exposicion_objetivo(velas_btc["close"]))
    datos_btc = datos_btc[datos_btc.index >= desde]
    p_b1 = benchmarks.comprar_y_mantener(datos_btc, CAPITAL)
    r_e0 = mc.simular(
        datos_btc[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos_btc[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos_btc[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        CAPITAL, _modelo(), rangos={e0.SIMBOLO: 1}, filtros=filtros)

    curvas = {"E0": r_e0.patrimonio}
    for nombre, kwargs in (("E1", {}), ("R1", {"dias_momentum": 90}),
                           ("R2", {"cuantas": 8})):
        print(f"  Armando {nombre}...", flush=True)
        a = e1.construir_exposiciones(ci, ap, atr, g, universo, dias, **kwargs)
        cols = list(a.exposiciones.columns)
        curvas[nombre] = mc.simular(
            ap.reindex(index=dias, columns=cols),
            ci.reindex(index=dias, columns=cols), a.exposiciones,
            CAPITAL, _modelo(), rangos=rangos, filtros=filtros).patrimonio

    print("  Armando E2...", flush=True)
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

    tasas = {c: fin.cargar(e2.simbolo_base(c), CARPETA_FIN)["tasa"]
             for c in cols2 if e2.es_perpetuo(c)
             and (CARPETA_FIN / f"{e2.simbolo_base(c)}.csv").exists()}
    curvas["E2"] = mc.simular(
        matriz(ap, ap_p), matriz(ci, ci_p), a2.exposiciones, CAPITAL,
        _modelo(),
        rangos=pd.DataFrame({c: rangos[e2.simbolo_base(c)] for c in cols2
                             if e2.simbolo_base(c) in rangos.columns},
                            index=dias),
        filtros=filtros, permitir_cortos=True,
        financiacion_de_cortos=tasas).patrimonio

    # Un nulo de media exposicion, que es contra lo que hay que leer todo.
    media = float(r_e0.exposicion.sum(axis=1).mean())
    curvas[f"Nulo {media:.0%}"] = (
        benchmarks.comprar_y_mantener(datos_btc, CAPITAL * media)
        + CAPITAL * (1.0 - media))

    # --- El cuadro ---------------------------------------------------------
    print()
    print("=" * 78)
    print(" C-A (CAPTURA EN MESES ALCISTAS) Y C-B (PROTECCION EN BAJISTAS)")
    print("=" * 78)
    print(f"  {'':<12}{'C-A':>9}{'C-B':>9}{'C-B tramo':>12}"
          f"{'ret. alcista':>14}{'caida bajista':>15}")
    puntajes = {}
    for nombre, curva in curvas.items():
        p = regimen.puntuar(curva, p_b1, alcistas, nombre)
        puntajes[nombre] = p
        print(f"  {nombre:<12}{p.captura:>9.3f}{p.proteccion:>9.3f}"
              f"{p.proteccion_por_tramo:>12.3f}"
              f"{p.retorno_alcista * 100:>13.1f}%"
              f"{p.caida_bajista * 100:>14.1f}%")
    pb1 = regimen.puntuar(p_b1, p_b1, alcistas, "B1")
    print(f"  {'B1':<12}{pb1.captura:>9.3f}{pb1.proteccion:>9.3f}"
          f"{pb1.proteccion_por_tramo:>12.3f}"
          f"{pb1.retorno_alcista * 100:>13.1f}%"
          f"{pb1.caida_bajista * 100:>14.1f}%")

    print()
    print("  'C-B tramo' usa el peor tramo bajista CONTIGUO, que es una curva")
    print("  real. La columna C-B encadena meses bajistas no contiguos. Si las")
    print("  dos dieran veredictos distintos, el criterio dependeria de esa")
    print("  eleccion y no del dato.")

    # --- Contra los umbrales propuestos ------------------------------------
    print()
    print("=" * 78)
    print(" CONTRA LOS UMBRALES PROPUESTOS -- PROVISIONAL")
    print("=" * 78)
    print(f"  El analista propuso C-A >= {CAPTURA_PROPUESTA:.0%} y "
          f"C-B <= {PROTECCION_PROPUESTA:.0%}, SIN derivar de donde salen.")
    print("  Esto es informativo, no un veredicto. Fijar los umbrales con su")
    print("  razon es decision de Felipe, y va escrito antes de usarlos.")
    print()
    for nombre, p in puntajes.items():
        ca = "si" if p.captura >= CAPTURA_PROPUESTA else "NO"
        cb = "si" if p.proteccion <= PROTECCION_PROPUESTA else "NO"
        print(f"  {nombre:<12} C-A {ca}   C-B {cb}")

    # --- El intervalo de C-C ------------------------------------------------
    print()
    print("=" * 78)
    print(" C-C: IC 95% DEL COCIENTE DE CAPTURA (bloques de 3 meses)")
    print("=" * 78)
    for nombre, curva in curvas.items():
        bajo, alto = regimen.intervalo_de_captura(curva, p_b1, alcistas)
        excluye = "excluye 1,0" if (alto < 1.0 or bajo > 1.0) else "contiene 1,0"
        print(f"  {nombre:<12} [{bajo:>6.3f}, {alto:>6.3f}]   {excluye}")

    # --- La lectura --------------------------------------------------------
    e = puntajes["E0"]
    print()
    print("=" * 78)
    print(" LO QUE C-A Y C-B SEPARAN Y EL CRITERIO 1 FUNDIA")
    print("=" * 78)
    print(f"  E0 protege: su caida en meses bajistas es el "
          f"{e.proteccion * 100:.0f}% de la de B1.")
    print(f"  E0 no captura: se queda con el {e.captura * 100:.0f}% de la "
          "subida.")
    print()
    print("  El criterio 1 daba un solo numero y de ahi no se leia cual de las")
    print("  dos mitades estaba resuelta. Ahora se lee.")
    faltan = (CAPTURA_PROPUESTA - e.captura) * 100
    print(f"\n  La prima del seguro, medida: {faltan:.0f} puntos de captura")
    print(f"  por debajo del {CAPTURA_PROPUESTA:.0%} propuesto.")

    print("\n  Y el metricas clasico de cada uno, para tener las dos lecturas:")
    for nombre, curva in curvas.items():
        m = metricas.calcular(curva, nombre)
        print(f"    {nombre:<12} CAGR {m.cagr * 100:>+7.2f}%   "
              f"caida {m.caida_maxima * 100:>6.1f}%   Calmar {m.calmar:>6.3f}")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
