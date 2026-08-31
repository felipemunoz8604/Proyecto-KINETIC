r"""
Que hace la capa de riesgo v2 sobre los datos reales, antes de correr E0.

POR QUE ESTO NO ES UN BACKTEST
-------------------------------
No compra nada ni mide resultado. Solo calcula, en cada rebalanceo, cuanta
exposicion habria tenido la cartera y como repartida. Es el equivalente de
prender el motor en el taller antes de sacar el auto a la ruta.

LA PREGUNTA QUE CONTESTA
-------------------------
`k(t) = min(0,35 / sigma_cartera, 1,0)`. En cripto la volatilidad anualizada
de una cartera anda muy por encima del 35%, asi que la sospecha es que **k
esta pegado abajo casi siempre** y la estrategia corre permanentemente con una
fraccion chica del capital.

Si es asi, no esta mal -- es lo que el objetivo de volatilidad pide -- pero
cambia por completo que retorno es razonable esperar, y es mejor saberlo ahora
que descubrirlo interpretando el CAGR de E0.

Se corre asi:

    venv\Scripts\python.exe tools\perfil_de_riesgo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from core import universo as uni  # noqa: E402
from metrics import ventana  # noqa: E402
from risk import compuerta as cp  # noqa: E402
from risk import pesos as pz  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
REFERENCIA = "BTCUSDT"


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - perfil de la capa de riesgo v2")
    print("=" * 76)
    print(f"  sigma objetivo {pz.SIGMA_OBJETIVO:.0%}   "
          f"k_max {pz.K_MAX}   tope por activo {pz.TOPE_POR_ACTIVO:.0%}")
    print()

    print("  Cargando panel...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    seleccion = uni.construir(panel, fechas)

    btc = panel.cierres[REFERENCIA].dropna()
    g = cp.compuerta_de_regimen(btc)

    filas = []
    for fecha in fechas:
        simbolos = seleccion[fecha]
        sigmas = pz.volatilidad_anualizada(panel.cierres, fecha, simbolos)
        w = pz.pesos_inversa_volatilidad(sigmas)
        if w.empty:
            continue
        sigma_p = pz.volatilidad_de_cartera(panel.cierres, fecha, w)
        k = pz.escalar_de_volatilidad(sigma_p)
        compuerta = int(g.get(fecha, 0))
        filas.append({
            "fecha": fecha,
            "activos": len(w),
            "sigma_mediana": float(sigmas.median()),
            "sigma_cartera": sigma_p,
            "k": k,
            "compuerta": compuerta,
            "bruta": k * compuerta,
            "peso_max": float(w.max()),
            "en_el_tope": int((w >= pz.TOPE_POR_ACTIVO - 1e-9).sum()),
        })

    d = pd.DataFrame(filas).set_index("fecha")
    print(f"    {len(d)} rebalanceos ({time.time() - t0:.0f} s)")

    print()
    print("=" * 76)
    print(" VOLATILIDAD: LOS ACTIVOS CONTRA LA CARTERA")
    print("=" * 76)
    print(f"  sigma mediana de un activo:  {d['sigma_mediana'].median():.0%}")
    print(f"  sigma de la cartera:         {d['sigma_cartera'].median():.0%}")
    print(f"  Lo que ahorra diversificar:  "
          f"{1 - d['sigma_cartera'].median() / d['sigma_mediana'].median():.0%}")
    print()
    print("  La cartera es menos volatil que sus partes porque las 20 no se")
    print("  mueven todas juntas. Eso ya lo habia medido 5.2 (correlacion")
    print("  media 0,59) y aca se ve en el numero que de verdad importa.")

    print()
    print("=" * 76)
    print(" EL ESCALAR k(t): CUANTO DEL CAPITAL SE USA")
    print("=" * 76)
    print(f"  mediana {d['k'].median():.2f}   media {d['k'].mean():.2f}   "
          f"minimo {d['k'].min():.2f}   maximo {d['k'].max():.2f}")
    print(f"  Rebalanceos con k pegado en 1,0: "
          f"{(d['k'] >= pz.K_MAX - 1e-9).sum()} de {len(d)}")
    print()
    print("  Exposicion bruta final (k x compuerta):")
    print(f"    mediana {d['bruta'].median():.2f}   media {d['bruta'].mean():.2f}")
    print(f"    En cero (compuerta cerrada): {(d['bruta'] == 0).sum()} de {len(d)}")
    print()
    print("  Ese es el capital que de verdad trabaja. Si la mediana es 0,3,")
    print("  esperar el retorno de una cartera al 100% es esperar de mas.")

    print()
    print("=" * 76)
    print(" EL TOPE DEL 40%")
    print("=" * 76)
    print(f"  Peso maximo de un activo: mediana {d['peso_max'].median():.3f}, "
          f"maximo {d['peso_max'].max():.3f}")
    print(f"  Rebalanceos con al menos un activo en el tope: "
          f"{(d['en_el_tope'] > 0).sum()} de {len(d)}")
    print("  Si nunca se toca el tope, no esta haciendo nada y hay que decirlo.")

    print()
    print("  Por año:")
    print("    año   sigma cart.   k    bruta   activos")
    for anio, bloque in d.groupby(d.index.year):
        print(f"    {anio}     {bloque['sigma_cartera'].median():>6.0%}     "
              f"{bloque['k'].median():.2f}   {bloque['bruta'].median():.2f}"
              f"     {bloque['activos'].median():.0f}")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
