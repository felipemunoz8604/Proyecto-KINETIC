r"""
Calcula los benchmarks de la Fase 2. Hoy: B1.

POR QUE ESTO VA ANTES DE ESCRIBIR UNA SOLA ESTRATEGIA
------------------------------------------------------
El criterio 1 de aceptacion pide `Calmar(estrategia) >= 1,8 x Calmar(B1)`.
**Nadie calculo nunca cuanto vale Calmar(B1)**, y ese numero solo decide si la
vara es exigente-pero-alcanzable o directamente imposible.

Cuesta minutos y los datos ya estan en disco. Reescribir `risk/` y la capa de
datos cuesta dias. Hacerlo al reves seria construir sobre un supuesto sin
verificar, que es lo que el MEGAPROMPT v2.0 seccion 10 dice explicitamente que
no se hace.

Se corre asi:

    venv\Scripts\python.exe tools\calcular_benchmarks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from core import config_loader as cfgmod  # noqa: E402
from core import data_feed  # noqa: E402
from metrics import benchmarks, metricas, ventana  # noqa: E402

# Los umbrales de la especificacion seccion 3.3, para poder mostrar de una
# vez que le exige cada uno a una estrategia.
CRITERIO_1_CALMAR = 1.8
CRITERIO_2_CAIDA = 0.60


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    cfg = cfgmod.cargar()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]
    capital = float(cfg["capital"]["monto"])

    print("=" * 76)
    print(" KINETIC - benchmarks de la Fase 2")
    print("=" * 76)
    print(f"  Ventana de diseño: {ventana.DISENO_DESDE.date()} a "
          f"{ventana.DISENO_HASTA.date()}")
    print(f"  Capital: {capital:,.2f} USDT")
    print(f"  B1 paga {benchmarks.COSTO_ENTRADA_PCT}% una sola vez, al entrar.")
    print()

    completo = data_feed.cargar("BTCUSDT", "1d", carpeta=carpeta)
    print(f"  Historico en disco: {len(completo):,} velas diarias, "
          f"{completo.index[0].date()} a {completo.index[-1].date()}")

    # El candado del holdout se aplica solo: si por error se pasara la serie
    # entera, `comprar_y_mantener` cortaria en vez de medir sobre 2025-2026.
    diseno = ventana.recortar_a_diseno(completo)
    print(f"  Recortado a diseño: {len(diseno):,} velas, "
          f"{diseno.index[0].date()} a {diseno.index[-1].date()}")
    print()

    curva = benchmarks.b1(diseno, capital)
    m = metricas.calcular(curva, nombre="B1 — comprar BTCUSDT y no hacer nada")
    print(m.informe())
    if m.caida_desde is not None:
        print(f"    La caida:         de {m.caida_desde.date()} "
              f"a {m.caida_hasta.date()}")

    print()
    print("=" * 76)
    print(" LO QUE ESTO LE EXIGE A UNA ESTRATEGIA")
    print("=" * 76)
    print(f"  Criterio 1 — Calmar >= {CRITERIO_1_CALMAR} x {m.calmar:.3f}"
          f"  =  {CRITERIO_1_CALMAR * m.calmar:.3f}")
    print(f"  Criterio 2 — caida maxima <= {CRITERIO_2_CAIDA} x "
          f"{abs(m.caida_maxima) * 100:.1f}%  =  "
          f"{CRITERIO_2_CAIDA * abs(m.caida_maxima) * 100:.1f}%")
    print()
    print("  Traducido: para pasar, una estrategia tiene que quedarse con al")
    print(f"  menos el {CRITERIO_1_CALMAR * CRITERIO_2_CAIDA * 100:.0f}% del "
          f"CAGR de comprar y esperar, si cae exactamente el maximo permitido.")

    print()
    print("=" * 76)
    print(" QUE COMBINACIONES PASAN LOS DOS CRITERIOS A LA VEZ")
    print("=" * 76)
    print("  Los criterios 1 y 2 no son independientes. Si una estrategia cae")
    print("  menos, el criterio 1 le pide menos retorno -- porque el Calmar")
    print("  tiene la caida en el denominador. La cuenta:")
    print()
    print(f"  {'Su caida':>10}  {'= x B1':>7}   {'CAGR que necesita':>18}  {'= % de B1':>10}")
    for fraccion in (0.60, 0.50, 0.40, 0.30, 0.20):
        caida = fraccion * abs(m.caida_maxima)
        exigido = CRITERIO_1_CALMAR * m.calmar * caida
        print(f"  {caida * 100:>9.1f}%  {fraccion:>7.2f}   {exigido * 100:>17.1f}%  "
              f"{exigido / m.cagr * 100:>9.0f}%")
    print()
    print("  Leelo asi: en el TOPE de caida permitido hay que superar a comprar")
    print("  y esperar. Recien cortando la caida bastante mas abajo del tope, la")
    print("  vara se vuelve razonable. **La restriccion que manda es la caida,")
    print("  no el retorno.**")

    print()
    print("=" * 76)
    print(" CUANTO DEPENDE LA VARA DE LA FECHA DE ARRANQUE")
    print("=" * 76)
    print("  El 1-ene-2019 es una fecha arbitraria. Si Calmar(B1) cambia mucho")
    print("  segun donde se empiece, entonces el criterio 1 no mide la")
    print("  estrategia: mide de que dia arranco la ventana.")
    print()
    print(f"  {'Arranque':<12} {'CAGR B1':>9} {'Caida B1':>10} {'Calmar B1':>11} "
          f"{'Exige Calmar':>13}")
    calmares = []
    for inicio in pd.date_range("2019-01-01", "2021-01-01", freq="MS", tz="UTC"):
        tramo = diseno[diseno.index >= inicio]
        if len(tramo) < 400:
            continue
        c = benchmarks.b1(tramo, capital)
        mm = metricas.calcular(c, nombre=str(inicio.date()))
        calmares.append(mm.calmar)
        print(f"  {str(inicio.date()):<12} {mm.cagr * 100:>8.1f}% "
              f"{mm.caida_maxima * 100:>9.1f}% {mm.calmar:>11.3f} "
              f"{CRITERIO_1_CALMAR * mm.calmar:>13.3f}")
    if calmares:
        peor, mejor = min(calmares), max(calmares)
        print()
        print(f"  Calmar(B1) va de {peor:.3f} a {mejor:.3f} segun el mes de arranque.")
        print(f"  O sea que el criterio 1 exige entre {CRITERIO_1_CALMAR * peor:.2f} y "
              f"{CRITERIO_1_CALMAR * mejor:.2f}, dependiendo")
        print("  de una fecha que nadie eligio por una razon de fondo.")

    print()
    print("  (B2 y B0 todavia no existen: B2 necesita el universo reconstruido")
    print("   desde el archivo, y B0 necesita la estrategia E0 escrita.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
