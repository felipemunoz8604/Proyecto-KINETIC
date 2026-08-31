r"""
Baja el historico de financiacion de los perpetuos del universo.

QUE HABILITA ESTA DESCARGA
---------------------------
La medicion 5.1, que es la unica de las cinco que falta y la que decide dos
cosas: si **E3** (carry de financiacion) se codifica o se cierra con un
numero, y si la pata larga de **E2** conviene en Spot o en perpetuo.

E3 tiene falsacion **previa a codificar**: si la mediana de la financiacion
anualizada neta de comisiones no supera con margen el costo de montar la
estructura, no se escribe una linea de estrategia.

AUTORIZACION
-------------
MEGAPROMPT v2.0, regla 8: no se baja un solo dato de perpetuos hasta que la
prueba de cerrojos cubra futuros. Esta verde desde el commit 22eebf8, que la
verifico **en rojo** y no solo en verde.

Nada de esto toca la cuenta: el archivo publico no lleva llaves.

Se corre asi:

    venv\Scripts\python.exe tools\descargar_financiacion.py
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import financiacion as fin  # noqa: E402
from core import universo as uni  # noqa: E402
from metrics import ventana  # noqa: E402

CARPETA_VELAS = RAIZ / "data" / "archivo"
DESTINO = RAIZ / "data" / "financiacion"
HILOS = 8


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - historico de financiacion de perpetuos USDT-M")
    print("=" * 76)
    print()

    print("  Reconstruyendo el universo para saber que bajar...", flush=True)
    panel = uni.cargar_panel(CARPETA_VELAS)
    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    seleccion = uni.construir(panel, fechas)
    del_universo = sorted({s for v in seleccion.values() for s in v})
    print(f"    {len(del_universo)} simbolos pasaron por el universo")

    print("  Listando perpetuos con financiacion...", flush=True)
    con_perpetuo = set(fin.simbolos_disponibles())
    print(f"    {len(con_perpetuo)} perpetuos en el archivo")

    objetivo = [s for s in del_universo if s in con_perpetuo]
    sin_perpetuo = [s for s in del_universo if s not in con_perpetuo]
    print(f"    {len(objetivo)} del universo tienen perpetuo, "
          f"{len(sin_perpetuo)} no")
    if sin_perpetuo:
        print("    Sin perpetuo (E2 y E3 no pueden tocarlos):")
        for i in range(0, len(sin_perpetuo), 6):
            print("      " + "  ".join(f"{s:<12}" for s in sin_perpetuo[i:i + 6]))

    DESTINO.mkdir(parents=True, exist_ok=True)
    hechos = {p.stem for p in DESTINO.glob("*.csv")}
    faltan = [s for s in objetivo if s not in hechos]
    print(f"\n  Ya estaban: {len(hechos & set(objetivo))}. "
          f"Faltan: {len(faltan)}")

    errores: list[tuple[str, str]] = []
    cobros = 0

    def bajar(simbolo: str) -> tuple[str, int, str]:
        try:
            df = fin.bajar_simbolo(simbolo)
            if df.empty:
                return simbolo, 0, "sin datos"
            fin.guardar(df, simbolo, DESTINO)
            return simbolo, len(df), ""
        except Exception as e:  # noqa: BLE001 - se reporta y se sigue
            return simbolo, 0, str(e)[:90]

    if faltan:
        print()
        with ThreadPoolExecutor(max_workers=HILOS) as pool:
            for i, (s, n, error) in enumerate(pool.map(bajar, faltan), 1):
                if error:
                    errores.append((s, error))
                    print(f"    [{i}/{len(faltan)}] {s:<14} ERROR: {error}")
                else:
                    cobros += n
                    print(f"    [{i}/{len(faltan)}] {s:<14} {n:>6,} cobros")

    print()
    print("=" * 76)
    print(f"  {cobros:,} cobros nuevos guardados en "
          f"{DESTINO.relative_to(RAIZ)}")
    print(f"  Archivos totales: {len(list(DESTINO.glob('*.csv')))}")
    if errores:
        print(f"  {len(errores)} errores:")
        for s, e in errores[:10]:
            print(f"    {s}: {e}")
    print(f"  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
