r"""
Baja los filtros de intercambio de Spot y dice sobre que parte del universo
son reales.

POR QUE HACE FALTA
------------------
El backtest tiene que redondear las cantidades al `stepSize` de cada simbolo y
descartar las ordenes que no llegan al `minNotional`. Esos numeros salen de
`exchangeInfo`, que es un endpoint **publico** -- no lleva llaves, no toca la
cuenta y no puede mover un peso.

LO QUE NO VA A ENCONTRAR, Y ESA ES LA MITAD DEL PUNTO
------------------------------------------------------
Los simbolos deslistados no estan en `exchangeInfo`. LUNA no esta. Para esos,
`execution/filtros.py` cae al filtro generico, que solo aplica el minimo de 5
USDT y **no redondea** -- o sea que subestima el efecto.

Por eso esta herramienta imprime la cobertura contra el universo reconstruido.
Ese numero hay que citarlo cuando se reporte un resultado: dice sobre que
fraccion de la cartera el filtro es una medicion y sobre cual es un supuesto.

Se corre asi:

    venv\Scripts\python.exe tools\bajar_filtros.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import universo as uni  # noqa: E402
from execution import filtros as filt  # noqa: E402
from metrics import ventana  # noqa: E402

URL = "https://api.binance.com/api/v3/exchangeInfo"
CARPETA = RAIZ / "data" / "archivo"
DESTINO = RAIZ / "data" / "filtros_spot.json"


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    print("=" * 76)
    print(" KINETIC - filtros de intercambio de Spot")
    print("=" * 76)
    print(f"  Endpoint publico, sin llaves: {URL}")
    print()

    with urllib.request.urlopen(URL, timeout=60) as respuesta:
        info = json.loads(respuesta.read())

    tabla = filt.desde_exchange_info(info)
    ruta = tabla.a_json(DESTINO)
    print(f"  {len(tabla)} simbolos guardados en {ruta.relative_to(RAIZ)}")

    # --- Cobertura contra el universo que de verdad se va a operar --------
    print("\n  Reconstruyendo el universo para medir la cobertura...")
    panel = uni.cargar_panel(CARPETA)
    fechas = [f for f in uni.fechas_de_rebalanceo(panel)
              if ventana.DISENO_DESDE <= f <= ventana.DISENO_HASTA]
    seleccion = uni.construir(panel, fechas)
    del_universo = sorted({s for v in seleccion.values() for s in v})

    reales, pedidos = tabla.cobertura(del_universo)
    sin_filtro = [s for s in del_universo if not tabla.de(s).es_real]

    print()
    print("=" * 76)
    print(" COBERTURA SOBRE EL UNIVERSO RECONSTRUIDO")
    print("=" * 76)
    print(f"  Simbolos que pasaron por el universo: {pedidos}")
    print(f"  Con filtro REAL de exchangeInfo:      {reales} "
          f"({reales / pedidos * 100:.0f}%)")
    print(f"  Con filtro GENERICO (supuesto):       {pedidos - reales}")
    print()
    print("  Los del generico no redondean al stepSize, o sea que el efecto")
    print("  del redondeo esta SUBESTIMADO en esa parte de la cartera.")
    if sin_filtro:
        print()
        print("  Sin filtro real (deslistados, casi todos):")
        for i in range(0, len(sin_filtro), 6):
            print("    " + "  ".join(f"{s:<12}" for s in sin_filtro[i:i + 6]))

    # --- El minimo de nocional que de verdad rige -------------------------
    minimos: dict[float, int] = {}
    for s in del_universo:
        m = tabla.de(s).nocional_minimo
        minimos[m] = minimos.get(m, 0) + 1
    print()
    print("  Minimos de nocional presentes en el universo:")
    for m, cuantos in sorted(minimos.items()):
        print(f"    {m:>8.2f} USDT   en {cuantos} simbolos")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
