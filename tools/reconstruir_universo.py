r"""
Reconstruye el universo mes a mes y contesta las mediciones 5.3 y 5.5.

QUE CONTESTA, Y POR QUE ANTES DE CODIFICAR NINGUNA ESTRATEGIA
--------------------------------------------------------------
La especificacion pide cinco mediciones previas porque **pueden matar una
estrategia antes de escribirla**. Dos salen directo de aca:

- **5.3 Rotacion del universo.** Que fraccion del top 20 se renueva cada mes.
  Esa rotacion **se paga aunque la estrategia no cambie de opinion**: si un
  simbolo sale del top 20 hay que venderlo. Es costo forzado por la
  composicion, no por la señal, y se suma al que genere el momentum.
- **5.5 Frecuencia de deslistado.** Cuantos muertos atraviesa la cartera. Es
  la magnitud real del sesgo que la Fase 1 no pudo medir.

Ademas imprime la evolucion del universo, que es la prueba visible de que la
reconstruccion funciona: si en 2019 aparecen los mismos nombres que hoy, algo
esta mal.

Se corre asi:

    venv\Scripts\python.exe tools\reconstruir_universo.py
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

CARPETA = RAIZ / "data" / "archivo"


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    print("=" * 76)
    print(" KINETIC - reconstruccion del universo mes a mes")
    print("=" * 76)
    print(f"  Ventana de diseño: {ventana.DISENO_DESDE.date()} a "
          f"{ventana.DISENO_HASTA.date()}")
    print(f"  Top {uni.TAMANO_UNIVERSO} por mediana de volumen cotizado de "
          f"{uni.DIAS_VENTANA_LIQUIDEZ} dias")
    print(f"  Antigüedad minima: {uni.DIAS_MINIMOS_DE_HISTORIA} dias")
    print()

    t0 = time.time()
    print("  Cargando panel...", flush=True)
    panel = uni.cargar_panel(CARPETA)
    print(f"    {len(panel):,} dias x {len(panel.simbolos)} simbolos "
          f"({time.time() - t0:.0f} s)")

    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    print(f"    {len(fechas)} fechas de rebalanceo en la ventana de diseño")

    print("\n  Reconstruyendo...", flush=True)
    seleccion = uni.construir(panel, fechas)

    # --- La prueba visible de que funciona --------------------------------
    print()
    print("=" * 76)
    print(" EL UNIVERSO A LO LARGO DEL TIEMPO")
    print("=" * 76)
    print("  Si en 2019 aparecieran los mismos nombres que hoy, la")
    print("  reconstruccion no estaria funcionando.")
    print()
    for fecha in fechas[::12]:
        nombres = [s[:-4] for s in seleccion[fecha][:10]]
        print(f"  {fecha.date()}  {', '.join(nombres)}")

    # --- 5.3 Rotacion -----------------------------------------------------
    rot = uni.rotacion(seleccion)
    print()
    print("=" * 76)
    print(" MEDICION 5.3 - ROTACION DEL UNIVERSO")
    print("=" * 76)
    print(f"  Mensual:  mediana {rot.median() * 100:.1f}%   "
          f"media {rot.mean() * 100:.1f}%   maxima {rot.max() * 100:.1f}%")
    anual = uni.rotacion_anual(seleccion)
    print(f"  Anual (punta a punta):  mediana {anual.median() * 100:.0f}%   "
          f"media {anual.mean() * 100:.0f}%")
    print()
    print("  OJO: las dos NO son comparables entre si. La mensual sumada doce")
    print("  veces cuenta varias veces al simbolo que entra y sale; la anual")
    print("  mira solo las dos puntas. La literatura (Grobys) reporta 37%")
    print("  anual sobre las 30 mayores por capitalizacion, asi que la que hay")
    print("  que comparar contra ese numero es la anual.")
    print()
    print("  Esto se paga SIEMPRE, aunque la estrategia no cambie de opinion:")
    print("  si un simbolo sale del top 20, hay que venderlo.")
    coste = rot.sum() / len(rot) * 12 * 0.25
    print(f"  Con el peaje de 0,25% ida y vuelta: ~{coste:.2f}% anual antes")
    print("  de que la señal haga absolutamente nada.")

    por_anio = rot.groupby(rot.index.year).mean() * 100
    print()
    print("  Por año:")
    for anio, valor in por_anio.items():
        print(f"    {anio}   {valor:>5.1f}% mensual")

    # --- 5.5 Deslistados --------------------------------------------------
    muertos = uni.deslistados_en(panel, seleccion)
    todos_desaparecidos = uni.deslistados_en(panel, seleccion,
                                             excluir_renombrados=False)
    renombrados = sorted(set(todos_desaparecidos) - set(muertos))
    todos_los_elegidos = {s for v in seleccion.values() for s in v}
    print()
    print("=" * 76)
    print(" MEDICION 5.5 - DESLISTADOS QUE ATRAVIESA LA CARTERA")
    print("=" * 76)
    print(f"  Simbolos distintos que pasaron por el universo: {len(todos_los_elegidos)}")
    print(f"  Desaparecieron del archivo:                     "
          f"{len(todos_desaparecidos)}")
    print(f"    de los cuales solo se RENOMBRARON:            "
          f"{len(renombrados)}  <- no son una perdida")
    print(f"    y MURIERON de verdad:                         {len(muertos)}")
    if todos_los_elegidos:
        print(f"  Proporcion:                                     "
              f"{len(muertos) / len(todos_los_elegidos) * 100:.0f}%")
    print()
    if renombrados:
        print()
        print("  RENOMBRADOS (el ticker cambio, el tenedor no perdio nada).")
        print("  Castigarlos con -20% o -50% no seria conservador, seria un error:")
        for s_ in renombrados:
            print(f"    {s_:<14} -> {uni.RENOMBRAMIENTOS[s_]}")
    print()
    print("  MUERTOS DE VERDAD. Es la cuenta que la Fase 1 no pudo hacer, y")
    print("  cada uno habria sido invisible con el universo de la lista de hoy:")
    for s, final in sorted(muertos.items(), key=lambda x: x[1])[:15]:
        print(f"    {s:<14} ultima vela {final.date()}")
    if len(muertos) > 15:
        print(f"    ... y {len(muertos) - 15} mas")

    # --- Tamaño efectivo --------------------------------------------------
    tamanos = pd.Series({f: len(v) for f, v in seleccion.items()})
    incompletos = tamanos[tamanos < uni.TAMANO_UNIVERSO]
    print()
    print("=" * 76)
    print(" TAMAÑO EFECTIVO DEL UNIVERSO")
    print("=" * 76)
    print(f"  Fechas con los {uni.TAMANO_UNIVERSO} completos: "
          f"{len(tamanos) - len(incompletos)} de {len(tamanos)}")
    if len(incompletos):
        print(f"  Fechas con menos:  {len(incompletos)}  "
              f"(de {incompletos.min()} a {incompletos.max()} simbolos)")
        print(f"  La primera: {incompletos.index[0].date()} con "
              f"{incompletos.iloc[0]} simbolos")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
