r"""
Cuanto cuesta cerrar a la fuerza en el borde de cada ventana del walk-forward.

EL PROBLEMA QUE MIDE
--------------------
El walk-forward parte la historia en ventanas de un anio y, al terminar cada
una, cierra a la fuerza cualquier posicion abierta. Esa fecha de corte -- el
17 de agosto -- no tiene ninguna relacion con el mercado: es un artefacto de
como partimos los datos.

En una estrategia donde una sola operacion aporta el 66% del resultado,
cortar una ganadora en una fecha arbitraria puede cambiar el numero final por
completo. Si es asi, el resultado del walk-forward no esta midiendo la
estrategia: esta midiendo nuestra forma de partir el calendario.

COMO LO MIDE
------------
Por cada operacion cerrada con motivo "fin del periodo":

  1. Se REPLICA la operacion desde su entrada, vela por vela, con la misma
     mecanica del motor. Al llegar al borde se compara el stop reconstruido
     contra el que el motor registro. Si no coinciden, la replica esta mal y
     el script lo dice en vez de mentir con un numero lindo.
  2. Se la deja CONTINUAR mas alla del borde, con el mismo trailing, hasta
     que toque el stop de verdad.
  3. La diferencia entre lo que la operacion dio y lo que habria dado es lo
     que el borde dejo sobre la mesa.

LO QUE ESTE NUMERO NO ES
------------------------
No es "el resultado verdadero del walk-forward". Si una operacion hubiera
seguido abierta, habria bloqueado entradas posteriores y cambiado el capital
de todo lo que vino despues. Esto mide el TAMANO DEL ARTEFACTO, que es lo que
hace falta para saber si preocuparse, no un resultado alternativo.

Se corre asi:

    venv\Scripts\python.exe tools\medir_cierres_de_ventana.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main_walkforward as mwf  # noqa: E402
from backtesting import walk_forward as wf  # noqa: E402
from core import data_feed  # noqa: E402
from risk import stop_manager  # noqa: E402
from strategy import indicators as ind  # noqa: E402


def replicar(df, op, mult_trailing, mult_inicial, slippage, comision, borde):
    """
    Rehace la operacion desde su entrada y la deja seguir pasado el borde.

    Devuelve (stop_en_el_borde, momento_salida, precio_salida, neto) o None si
    la replica no pudo validarse contra lo que el motor registro.
    """
    posiciones = df.index.get_indexer([op.entrada_momento])
    if posiciones[0] <= 0:
        return None
    i_entrada = posiciones[0]

    # El motor dimensiona con el ATR de la vela de SENAL, que es la anterior.
    atr_entrada = float(df["atr"].iloc[i_entrada - 1])
    if atr_entrada <= 0:
        return None

    try:
        estado = stop_manager.abrir(
            op.entrada_precio, atr_entrada, mult_inicial, mult_trailing
        )
    except ValueError:
        return None

    stop_en_el_borde = None
    for momento, fila in df.iloc[i_entrada:].iterrows():
        if stop_manager.toco_el_stop(estado, float(fila["low"])):
            precio = min(estado.stop_actual, float(fila["open"])) * (1 - slippage)
            return stop_en_el_borde, momento, precio, _neto(op, precio, comision)
        estado = stop_manager.actualizar(
            estado, float(fila["close"]), float(df["atr"].loc[momento])
        )
        if momento == borde:
            stop_en_el_borde = estado.stop_actual

    ultima = df.iloc[-1]
    precio = float(ultima["close"]) * (1 - slippage)
    return stop_en_el_borde, df.index[-1], precio, _neto(op, precio, comision)


def _neto(op, precio_salida, comision):
    """Neto de la operacion si hubiera salido a `precio_salida`."""
    # El costo de entrada es exacto: el registrado menos el de su salida real.
    costo_entrada = op.costos - op.salida_precio * op.cantidad * comision
    costos = costo_entrada + precio_salida * op.cantidad * comision
    return (precio_salida - op.entrada_precio) * op.cantidad - costos


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    cfg = mwf.base_config()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]
    comision = float(cfg["costos"]["comision_por_lado_pct"]) / 100.0
    slippage = float(cfg["costos"]["slippage_pct_por_lado"]) / 100.0
    mult_inicial = float(cfg["stops"]["atr_multiplicador_sl"])

    print("=" * 76)
    print(" KINETIC - cuanto cuestan los cierres forzados de ventana")
    print("=" * 76)

    for par in cfg["backtest"]["universo"]:
        for tf in ("15m", "1h"):
            print(f"\n{'=' * 76}\n {par} {tf}\n{'=' * 76}", flush=True)
            df = ind.agregar_indicadores(data_feed.cargar(par, tf, carpeta=carpeta), cfg)
            r = wf.correr(
                df, cfg, par, tf, mwf.CANDIDATOS, mwf.aplicar_trailing,
                anios_entrenamiento=3, anios_prueba=1, reglas_simbolo=mwf.REGLAS,
            )
            if not r.ventanas:
                print("  Sin ventanas.")
                continue

            total_real = total_cf = 0.0
            cortadas = replicas_malas = 0

            for v in r.ventanas:
                for op in v.operaciones_prueba:
                    if op.motivo_salida != "fin del periodo":
                        continue
                    cortadas += 1
                    salida = replicar(
                        df, op, v.elegido, mult_inicial, slippage, comision,
                        op.salida_momento,
                    )
                    if salida is None:
                        replicas_malas += 1
                        continue
                    stop_borde, momento_cf, precio_cf, neto_cf = salida

                    # Validacion: el stop reconstruido en el borde tiene que
                    # coincidir con el que el motor registro al cortar.
                    if stop_borde is None or abs(stop_borde - op.stop_final) > 1e-6:
                        replicas_malas += 1
                        print(f"  [!] ventana {v.numero}: la replica no valida "
                              f"(stop {stop_borde} vs {op.stop_final}) -- se ignora")
                        continue

                    total_real += op.resultado_neto
                    total_cf += neto_cf
                    dias = (momento_cf - op.salida_momento).days
                    print(f"  V{v.numero} entrada {op.entrada_momento:%Y-%m-%d} "
                          f"cortada {op.salida_momento:%Y-%m-%d}: "
                          f"{op.resultado_neto:+8.2f}  ->  seguia hasta "
                          f"{momento_cf:%Y-%m-%d} (+{dias}d) y daba "
                          f"{neto_cf:+8.2f}   ({neto_cf - op.resultado_neto:+.2f})")

            print(f"\n  Operaciones cortadas por el borde: {cortadas} de "
                  f"{r.metricas.operaciones}")
            if replicas_malas:
                print(f"  Replicas que no se pudieron validar: {replicas_malas}")
            if cortadas and cortadas > replicas_malas:
                print(f"  Sumadas dieron:          {total_real:+.2f} USDT")
                print(f"  De haber seguido:        {total_cf:+.2f} USDT")
                print(f"  El borde dejo sobre la mesa: "
                      f"{total_cf - total_real:+.2f} USDT")
                print(f"  (resultado del walk-forward: "
                      f"{r.metricas.resultado_neto:+.2f} USDT)")
            elif not cortadas:
                print("  Ninguna. El borde no cambio nada en este tramo.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
