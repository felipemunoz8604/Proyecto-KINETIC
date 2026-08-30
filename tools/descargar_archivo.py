r"""
Baja el historico diario desde el archivo oficial, CON los pares deslistados.

QUE LO DIFERENCIA DE `descargar_historico.py`
----------------------------------------------
Aquel baja del endpoint `/api/v3/klines`, que solo sirve los simbolos que
Binance decide servir hoy. Es de donde salio todo lo de la Fase 1, y por eso
el universo era "las que sobrevivieron": **485 pares USDT operando contra 250
deslistados -- la Fase 1 vio el 66% del mercado que existio.**

Este baja del archivo `data.binance.vision`, que conserva el historico de los
pares muertos. Verificado el 30-ago-2026 con
`tools/verificar_archivo_binance.py`.

CUANTO TARDA Y POR QUE VA EN PARALELO
--------------------------------------
Son ~723 pares USDT, con una mediana de 24 mensuales cada uno, y cada mensual
son dos peticiones (el zip y su `.CHECKSUM`). Unas **35.000 peticiones**. En
serie eso son dos horas; con doce hilos, unos quince minutos.

La concurrencia se mantiene modesta a proposito. El bucket es un servicio
publico y gratuito: apurarlo con cien hilos es maleducado y ademas devuelve
errores que despues hay que reintentar igual.

ES INCREMENTAL
--------------
Un simbolo que ya esta en disco se saltea. Volver a correrlo despues de una
interrupcion no rehace el trabajo hecho. Con `--rehacer` se ignora lo guardado.

Se corre asi:

    venv\Scripts\python.exe tools\descargar_archivo.py
    venv\Scripts\python.exe tools\descargar_archivo.py --limite 20
    venv\Scripts\python.exe tools\descargar_archivo.py --hilos 8
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import archivo_binance as arch  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
_candado = threading.Lock()


class Contador:
    """Progreso compartido entre hilos. Con candado porque `print` se entrevera."""

    def __init__(self, total: int) -> None:
        self.total = total
        self.hechos = 0
        self.velas = 0
        self.fallados: list[str] = []
        self.meses_rotos = 0
        self.comienzo = time.time()

    def anotar(self, simbolo: str, velas: int, rotos: int, error: str | None) -> None:
        with _candado:
            self.hechos += 1
            if error:
                self.fallados.append(f"{simbolo}: {error}")
            else:
                self.velas += velas
                self.meses_rotos += rotos
            if self.hechos % 25 == 0 or self.hechos == self.total:
                transcurrido = time.time() - self.comienzo
                ritmo = self.hechos / transcurrido if transcurrido else 0
                faltan = (self.total - self.hechos) / ritmo if ritmo else 0
                print(f"    {self.hechos:>4}/{self.total}  "
                      f"{self.velas:>9,} velas   "
                      f"{len(self.fallados)} fallados   "
                      f"faltan ~{faltan / 60:.0f} min", flush=True)


def bajar_uno(simbolo: str, tf: str, rehacer: bool, contador: Contador) -> None:
    destino = CARPETA / f"{simbolo}_{tf}.csv"
    if destino.exists() and not rehacer:
        contador.anotar(simbolo, 0, 0, None)
        return
    try:
        df = arch.bajar_simbolo(simbolo, tf)
        arch.guardar(df, simbolo, tf, CARPETA)
        contador.anotar(simbolo, len(df), len(df.attrs.get("meses_fallados", [])), None)
    except Exception as e:  # noqa: BLE001 - un simbolo caido no frena la descarga
        contador.anotar(simbolo, 0, 0, str(e)[:120])


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Descarga desde data.binance.vision")
    parser.add_argument("--tf", default="1d", help="temporalidad (la Fase 2 usa 1d)")
    parser.add_argument("--hilos", type=int, default=12)
    parser.add_argument("--limite", type=int, help="baja solo los primeros N (pruebas)")
    parser.add_argument("--rehacer", action="store_true")
    args = parser.parse_args()

    print("=" * 76)
    print(" KINETIC - descarga del archivo historico (con deslistados)")
    print("=" * 76)
    print(f"  Destino: {CARPETA}")
    print(f"  Temporalidad: {args.tf}   Hilos: {args.hilos}")
    print()

    print("  Enumerando simbolos del archivo...", flush=True)
    todos = arch.simbolos_disponibles()

    # El filtro es ESTATICO: depende solo del nombre. No consulta si el par
    # sigue vivo, que es exactamente como entro el sesgo en la Fase 1.
    universo = [s for s in todos if arch.es_apuesta_direccional(s)]
    print(f"    {len(todos):,} simbolos en el archivo")
    print(f"    {len(universo):,} pares USDT direccionales "
          f"(sin stablecoins ni tokens apalancados)")

    if args.limite:
        universo = universo[: args.limite]
        print(f"    limitado a {len(universo)} por --limite")

    ya_estaban = sum(1 for s in universo if (CARPETA / f"{s}_{args.tf}.csv").exists())
    if ya_estaban and not args.rehacer:
        print(f"    {ya_estaban:,} ya estan en disco y se saltean")

    print(f"\n  Bajando...\n", flush=True)
    contador = Contador(len(universo))
    with ThreadPoolExecutor(max_workers=args.hilos) as pool:
        tareas = [pool.submit(bajar_uno, s, args.tf, args.rehacer, contador)
                  for s in universo]
        for t in as_completed(tareas):
            t.result()

    minutos = (time.time() - contador.comienzo) / 60
    print()
    print("=" * 76)
    print(f" LISTO en {minutos:.1f} min")
    print("=" * 76)
    print(f"  Simbolos con datos: {len(universo) - len(contador.fallados):,}")
    print(f"  Velas nuevas:       {contador.velas:,}")
    if contador.meses_rotos:
        print(f"  Meses salteados:    {contador.meses_rotos} "
              f"(checksum o descarga fallida; el simbolo se conservo igual)")
    if contador.fallados:
        print(f"  Simbolos fallados:  {len(contador.fallados)}")
        for f in contador.fallados[:15]:
            print(f"    {f}")
        if len(contador.fallados) > 15:
            print(f"    ... y {len(contador.fallados) - 15} mas")
        print("  Volve a correr el comando: es incremental y reintenta solo esos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
