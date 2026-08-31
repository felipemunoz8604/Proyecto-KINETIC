r"""
Mediciones 5.2 y 5.4 -- las dos que pueden reordenar el plan de la Fase 2.

POR QUE SE CORREN ANTES DE ESCRIBIR NINGUNA ESTRATEGIA
--------------------------------------------------------
Son baratas y pueden matar una estrategia sin haberla programado. Es lo que
pide la pregunta abierta #1 del informe de cierre: hacer la cuenta antes.

- **5.2 Dispersion transversal.** Elegir cinco de veinte solo sirve si las
  veinte hacen cosas distintas. La especificacion fija el corte: **si la
  correlacion media por pares supera ~0,80 y la dispersion es baja, E1 y E2
  pierden prioridad frente a E0.**
- **5.4 Frecuencia de la compuerta.** Cada cruce de BTC sobre su media de 200
  dias mueve la cartera entera. Si hay muchos latigazos hace falta un
  amortiguador, **y ese amortiguador es un parametro nuevo que se cuenta como
  tal.** Primero el numero, despues la decision.

Se corre asi:

    venv\Scripts\python.exe tools\mediciones_previas.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from core import universo as uni  # noqa: E402
from execution import costos  # noqa: E402
from metrics import transversal as tr  # noqa: E402
from metrics import ventana  # noqa: E402
from risk import compuerta as cp  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
REFERENCIA = "BTCUSDT"


def _peaje_medio_por_lado() -> float:
    """
    El peaje de mover un lado de la cartera entera, promediando los tramos de
    slippage de los 20 puestos. No es el de BTC ni el del puesto 20: es el que
    de verdad paga una cartera que los tiene a todos.
    """
    modelo = costos.ModeloDeCostos()
    return sum(modelo.peaje_por_lado_pct(r)
               for r in range(1, uni.TAMANO_UNIVERSO + 1)) / uni.TAMANO_UNIVERSO


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - mediciones previas 5.2 y 5.4")
    print("=" * 76)
    print(f"  Ventana de diseño: {ventana.DISENO_DESDE.date()} a "
          f"{ventana.DISENO_HASTA.date()}")
    print()

    print("  Cargando panel...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    seleccion = uni.construir(panel, fechas)
    print(f"    {len(panel):,} dias x {len(panel.simbolos)} simbolos, "
          f"{len(fechas)} rebalanceos ({time.time() - t0:.0f} s)")

    peaje_lado = _peaje_medio_por_lado()
    peaje_vuelta = 2 * peaje_lado

    # =====================================================================
    #  5.2 - DISPERSION TRANSVERSAL
    # =====================================================================
    r = tr.retornos_hacia_adelante(panel, seleccion, dias=tr.HORIZONTE_DIAS)
    disp = tr.dispersion(r.retornos)
    brecha = tr.brecha_perfecta(r.retornos, k=5)
    ventaja = tr.ventaja_del_mejor_grupo(r.retornos, k=5)
    corr = tr.correlacion_media_por_pares(panel, seleccion)

    print()
    print("=" * 76)
    print(" MEDICION 5.2 - DISPERSION TRANSVERSAL DEL UNIVERSO")
    print("=" * 76)
    print(f"  Horizonte: {tr.HORIZONTE_DIAS} dias.  "
          f"{r.observaciones} observaciones en {len(disp)} fechas.")
    print(f"  De esas, {r.truncados} quedaron cortadas por deslistado "
          f"({r.truncados / max(r.observaciones, 1) * 100:.1f}%) y se midieron")
    print("  contra su ultimo cierre, sin penalizacion. Es optimista.")
    print()
    print("  Desviacion estandar transversal de los retornos a 28 dias:")
    print(f"    mediana {disp.median() * 100:>6.1f}%   "
          f"media {disp.mean() * 100:>6.1f}%   "
          f"p10 {disp.quantile(0.10) * 100:>6.1f}%   "
          f"p90 {disp.quantile(0.90) * 100:>6.1f}%")
    print()
    print("  Correlacion media por pares (90 dias hacia atras):")
    print(f"    mediana {corr.median():>6.3f}   media {corr.mean():>6.3f}   "
          f"p10 {corr.quantile(0.10):>6.3f}   p90 {corr.quantile(0.90):>6.3f}")
    print()
    print(f"  Fechas con correlacion sobre 0,80: "
          f"{(corr > 0.80).sum()} de {len(corr)} "
          f"({(corr > 0.80).mean() * 100:.0f}%)")

    print()
    print("  LOS TECHOS. Es lo que sacaria alguien que adivinara siempre:")
    print(f"    Solo largo, mejores 5 contra la canasta:  "
          f"mediana {ventaja.median() * 100:>6.2f}% cada 28 dias")
    print(f"    Largo/corto, mejores 5 menos peores 5:    "
          f"mediana {brecha.median() * 100:>6.2f}% cada 28 dias")
    print()
    print(f"  Contra un peaje de ida y vuelta de {peaje_vuelta:.2f}% "
          f"(promedio de los 20 puestos):")
    print(f"    El techo solo-largo paga el peaje "
          f"{ventaja.median() * 100 / peaje_vuelta:>5.1f} veces.")
    print("    Nadie llega al techo. Si esa relacion es chica, no hay nada")
    print("    abajo que valga la pena buscar.")

    print()
    print("  Por año (mediana de cada uno):")
    for anio in sorted(set(disp.index.year)):
        d = disp[disp.index.year == anio].median()
        c = corr[corr.index.year == anio].median()
        v = ventaja[ventaja.index.year == anio].median()
        print(f"    {anio}   dispersion {d * 100:>5.1f}%   "
              f"correlacion {c:>5.2f}   techo largo {v * 100:>5.2f}%")

    # =====================================================================
    #  5.4 - FRECUENCIA DE LA COMPUERTA
    # =====================================================================
    btc = panel.cierres[REFERENCIA].dropna()
    btc = btc[(btc.index >= ventana.DISENO_DESDE)
              & (btc.index <= ventana.DISENO_HASTA)]
    g = cp.compuerta_de_regimen(btc)
    cambios = cp.cambios(g)
    t = cp.tramos(g)
    encendidos = t[t["estado"] == 1]
    apagados = t[t["estado"] == 0]
    anios = len(g) / 365.0

    print()
    print("=" * 76)
    print(" MEDICION 5.4 - FRECUENCIA DE CAMBIO DE LA COMPUERTA")
    print("=" * 76)
    print(f"  {REFERENCIA} contra su media de {cp.PERIODO_SMA} dias, "
          f"{len(g)} dias ({anios:.1f} años)")
    print()
    print(f"  Cambios de estado:        {len(cambios)}  "
          f"({len(cambios) / anios:.1f} por año)")
    print(f"  Fraccion del tiempo dentro: {g.mean() * 100:.0f}%")
    print()
    print(f"  Tramos DENTRO:  {len(encendidos):>3}   "
          f"mediana {encendidos['dias'].median():>5.0f} dias   "
          f"max {encendidos['dias'].max():>4.0f}")
    print(f"  Tramos FUERA:   {len(apagados):>3}   "
          f"mediana {apagados['dias'].median():>5.0f} dias   "
          f"max {apagados['dias'].max():>4.0f}")

    print()
    print("  Latigazos (tramos que duraron menos de N dias):")
    for n in (5, 10, 20, 30):
        cortos = cp.latigazos(g, dias_minimos=n)
        print(f"    menos de {n:>2} dias: {len(cortos):>3} tramos   "
              f"({len(cortos) / anios:.1f} por año)")

    costo_total = len(cambios) * peaje_lado
    print()
    print(f"  Cada cambio mueve la cartera ENTERA por un lado: "
          f"{peaje_lado:.3f}%")
    print(f"  Los {len(cambios)} cambios cuestan {costo_total:.2f}% del "
          f"capital en {anios:.1f} años,")
    print(f"  o sea {costo_total / anios:.2f}% por año, solo por la compuerta.")
    print()
    print("  Ese costo es el precio del seguro contra las caidas grandes.")
    print("  El amortiguador NO esta implementado: primero este numero,")
    print("  despues la decision, porque seria un parametro nuevo.")

    print()
    print("  Cambios por año:")
    por_anio = cambios.groupby(cambios.index.year).size()
    for anio in sorted(set(g.index.year)):
        print(f"    {anio}   {'#' * int(por_anio.get(anio, 0))}"
              f"  {por_anio.get(anio, 0)}")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
