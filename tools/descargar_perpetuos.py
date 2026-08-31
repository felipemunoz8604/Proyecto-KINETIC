r"""
Baja velas diarias de los perpetuos USDT-M del universo.

POR QUE NO ALCANZA CON LOS PRECIOS DE SPOT
--------------------------------------------
E2 vende en corto en el **perpetuo**, no en Spot. Usar el precio de Spot para
la pata corta seria suponer que los dos instrumentos valen exactamente lo
mismo todo el tiempo, y no es cierto: esa diferencia es el **riesgo de base**
que la especificacion 6.4 nombra explicitamente como algo a modelar.

Ademas la muestra es distinta. El perpetuo de un simbolo nace despues que su
par de Spot, a veces años despues, y eso acorta la ventana de cualquier
resultado de E2.

EL DESAJUSTE DE NOMBRES ENTRE SPOT Y FUTUROS
----------------------------------------------
Cuatro monedas del universo cotizan en futuros con otro ticker, porque el
contrato es sobre mil unidades: SHIB es 1000SHIBUSDT, PEPE es 1000PEPEUSDT.
La tabla esta escrita **a mano**, igual que `RENOMBRAMIENTOS` en el universo,
y por la misma razon: una heuristica de nombres parecidos daria falsos
positivos y aca un falso positivo significa operar el instrumento equivocado.

Los precios de un contrato "1000X" son mil veces los de X. Para los retornos
da igual --- y E2 solo usa retornos --- pero queda dicho para que nadie
compare los dos niveles y crea que hay un error.

Se corre asi:

    venv\Scripts\python.exe tools\descargar_perpetuos.py
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import archivo_binance as arch  # noqa: E402
from core import universo as uni  # noqa: E402
from metrics import ventana  # noqa: E402

CARPETA_SPOT = RAIZ / "data" / "archivo"
DESTINO = RAIZ / "data" / "perpetuo"
HILOS = 8

# El contrato de futuros es sobre 1.000 unidades. Escrita a mano a proposito.
EN_FUTUROS = {
    "SHIBUSDT": "1000SHIBUSDT",
    "PEPEUSDT": "1000PEPEUSDT",
    "BONKUSDT": "1000BONKUSDT",
    "FLOKIUSDT": "1000FLOKIUSDT",
    "LUNCUSDT": "1000LUNCUSDT",
}


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - velas diarias de perpetuos USDT-M")
    print("=" * 76)
    print()

    print("  Reconstruyendo el universo...", flush=True)
    panel = uni.cargar_panel(CARPETA_SPOT)
    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    seleccion = uni.construir(panel, fechas)
    del_universo = sorted({s for v in seleccion.values() for s in v})
    print(f"    {len(del_universo)} simbolos en el universo")

    print("  Listando perpetuos disponibles...", flush=True)
    hay = set(arch.simbolos_disponibles(arch.PERPETUO))
    print(f"    {len(hay)} perpetuos en el archivo")

    # Cada simbolo de Spot con su nombre en futuros, si existe.
    objetivo: dict[str, str] = {}
    sin_perpetuo: list[str] = []
    for s in del_universo:
        candidato = EN_FUTUROS.get(s, s)
        if candidato in hay:
            objetivo[s] = candidato
        else:
            sin_perpetuo.append(s)

    renombrados = {s: p for s, p in objetivo.items() if s != p}
    print(f"    {len(objetivo)} tienen perpetuo "
          f"({len(renombrados)} con otro ticker), {len(sin_perpetuo)} no")
    for s, p in sorted(renombrados.items()):
        print(f"      {s:<14} -> {p}")
    if sin_perpetuo:
        print("    Sin perpetuo (no se pueden vender en corto):")
        for i in range(0, len(sin_perpetuo), 6):
            print("      " + "  ".join(f"{s:<12}" for s in sin_perpetuo[i:i + 6]))

    DESTINO.mkdir(parents=True, exist_ok=True)
    faltan = {s: p for s, p in objetivo.items()
              if not (DESTINO / f"{s}_1d.csv").exists()}
    print(f"\n  Ya estaban: {len(objetivo) - len(faltan)}. Faltan: {len(faltan)}")

    errores: list[tuple[str, str]] = []
    velas = 0

    def bajar(par: tuple[str, str]) -> tuple[str, int, str]:
        spot, perp = par
        try:
            df = arch.bajar_simbolo(perp, "1d", mercado=arch.PERPETUO)
            if df.empty:
                return spot, 0, "sin datos"
            # Se guarda con el nombre de SPOT para que el resto del proyecto
            # use una sola clave por moneda y no dos.
            arch.guardar(df, spot, "1d", DESTINO)
            return spot, len(df), ""
        except Exception as e:  # noqa: BLE001 - se reporta y se sigue
            return spot, 0, str(e)[:90]

    if faltan:
        print()
        with ThreadPoolExecutor(max_workers=HILOS) as pool:
            for i, (s, n, error) in enumerate(
                    pool.map(bajar, sorted(faltan.items())), 1):
                if error:
                    errores.append((s, error))
                    print(f"    [{i}/{len(faltan)}] {s:<14} ERROR: {error}")
                else:
                    velas += n
                    print(f"    [{i}/{len(faltan)}] {s:<14} {n:>6,} velas")

    print()
    print("=" * 76)
    print(f"  {velas:,} velas nuevas en {DESTINO.relative_to(RAIZ)}")
    print(f"  Archivos totales: {len(list(DESTINO.glob('*_1d.csv')))}")
    if errores:
        print(f"  {len(errores)} errores:")
        for s, e in errores[:10]:
            print(f"    {s}: {e}")
    print(f"  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
