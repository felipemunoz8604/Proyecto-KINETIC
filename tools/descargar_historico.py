"""
Descarga el historico de velas para el backtest - Fase 1.

Baja de Binance MAINNET, endpoint publico: NO usa ni necesita tus llaves.
Guarda un CSV por par y temporalidad en data/historico/ y audita cada serie
antes de darla por buena.

Se corre asi:

    venv\\Scripts\\python.exe tools\\descargar_historico.py

La primera vez tarda varios minutos (son casi nueve anios de velas de 15
minutos). Despues es casi instantaneo: solo pide lo que falta desde la
ultima vez.

Opciones:
    --rehacer         ignora lo guardado y baja todo de cero
    --par BTCUSDT     limita a un par
    --tf 1h           limita a una temporalidad
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import config_loader as cfgmod  # noqa: E402
from core import data_feed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga historico de Binance.")
    parser.add_argument("--rehacer", action="store_true", help="baja todo de cero")
    parser.add_argument("--par", help="limita a un solo par, ej. BTCUSDT")
    parser.add_argument("--tf", help="limita a una temporalidad, ej. 1h")
    parser.add_argument("--verboso", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verboso else logging.WARNING,
        format="%(message)s",
    )

    cfg = cfgmod.cargar()
    bt = cfg.get("backtest")
    if not bt:
        print("[X] Falta la seccion 'backtest' en config/config.yaml")
        return 1

    pares = [args.par] if args.par else list(bt["universo"])
    temporalidades = [args.tf] if args.tf else list(bt["temporalidades"])
    desde = bt["desde"]
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]

    print("=" * 68)
    print(" KINETIC - descarga de historico (Binance Mainnet, datos publicos)")
    print("=" * 68)
    print("  Pares:          " + ", ".join(pares))
    print("  Temporalidades: " + ", ".join(temporalidades))
    print("  Desde:          " + desde)
    print("  Carpeta:        " + str(carpeta))
    if args.rehacer:
        print("  Modo:           REHACER (se ignora lo ya guardado)")
    print("\n  No se usan tus llaves: el endpoint de velas es publico.\n")

    hubo_error = False
    total_velas = 0
    comienzo = time.time()

    for par in pares:
        for tf in temporalidades:
            etiqueta = par + " " + tf
            print("-" * 68)
            print("Bajando " + etiqueta + " ...", flush=True)
            t0 = time.time()
            try:
                df, reporte, nuevas = data_feed.actualizar(
                    par, tf, desde=desde, carpeta=carpeta, rehacer=args.rehacer
                )
            except Exception as e:  # noqa: BLE001 - queremos seguir con los demas
                print("[X] Fallo " + etiqueta + ": " + str(e))
                hubo_error = True
                continue

            segundos = time.time() - t0
            print(reporte.informe())
            print(f"  Velas nuevas: {nuevas:,}   ({segundos:.1f} s)")
            total_velas += len(df)

    print("=" * 68)
    if hubo_error:
        print(" TERMINO CON ERRORES - revisa los mensajes de arriba")
    else:
        print(f" LISTO - {total_velas:,} velas en disco "
              f"({time.time() - comienzo:.0f} s en total)")
    print("=" * 68)
    return 1 if hubo_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
