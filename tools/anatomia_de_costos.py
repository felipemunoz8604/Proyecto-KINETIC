r"""
Anatomia del peaje: que forma tiene la distribucion de movimientos capturados.

QUE PREGUNTA CONTESTA
---------------------
Sabemos el diagnostico grueso -- la ventaja bruta existe y el costo se la
come -- pero no sabemos la FORMA de esa distribucion, y eso cambia por
completo que hipotesis tiene sentido probar despues:

  - Si son muchas operaciones que capturan APENAS MENOS que el costo, el
    problema es marginal y un filtro que corte las peores podria alcanzar.
  - Si son pocas grandes contra un mar de chiquitas, el problema es
    estructural: hay que dejar de tomar las chiquitas, y eso es un cambio de
    criterio de entrada, no un ajuste.
  - Si el movimiento capturado no se correlaciona con nada observable ANTES
    de entrar, entonces no hay filtro posible y la unica salida es operar
    menos veces por otra razon.

EL COSTO, EN LA UNIDAD QUE IMPORTA
-----------------------------------
El peaje no es un monto fijo: es un PORCENTAJE del precio, cobrado dos veces.
Con 0,1% de comision y 0,05% de slippage por lado, ida y vuelta son 0,30%.

Entonces la pregunta correcta no es "cuanto gano por operacion" sino
**cuanto se mueve el precio, en porcentaje, comparado con ese 0,30%**. Una
operacion que capture 0,25% pierde plata aunque haya "acertado" la direccion.

QUE MIRA, Y QUE NO
------------------
Todo lo que se reporta aca es DESCRIPTIVO sobre operaciones ya ocurridas. No
propone ni prueba ninguna hipotesis: sirve para decidir cual vale la pena
probar. La regla del proyecto sigue siendo una hipotesis por vez, con razon
mecanica, validada con walk-forward.

Se corre asi:

    venv\Scripts\python.exe tools\anatomia_de_costos.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main_walkforward as mwf  # noqa: E402
from backtesting import backtest_engine as motor  # noqa: E402
from core import data_feed  # noqa: E402
from strategy import indicators as ind  # noqa: E402


def percentil(valores: list[float], p: float) -> float:
    """Percentil simple, sin traer dependencias nuevas."""
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * p / 100.0
    bajo, alto = int(k), min(int(k) + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def analizar(operaciones, costo_ida_y_vuelta_pct: float) -> None:
    if not operaciones:
        print("  Sin operaciones.")
        return

    # El movimiento capturado, en % del precio de entrada. Es BRUTO: la
    # pregunta es si el movimiento alcanza para pagar el peaje, asi que el
    # peaje no puede estar ya descontado.
    movimientos = [
        (o.salida_precio - o.entrada_precio) / o.entrada_precio * 100.0
        for o in operaciones
    ]
    ganadoras = [m for m in movimientos if m > 0]
    perdedoras = [m for m in movimientos if m <= 0]

    print(f"  Operaciones: {len(operaciones):,}   "
        f"({len(ganadoras)} en verde / {len(perdedoras)} en rojo)")
    print(f"  Peaje ida y vuelta: {costo_ida_y_vuelta_pct:.2f}% del precio")
    print()

    print("  MOVIMIENTO CAPTURADO (bruto, % del precio de entrada)")
    for etiqueta, p in (("p10", 10), ("p25", 25), ("mediana", 50),
                        ("p75", 75), ("p90", 90), ("p99", 99)):
        print(f"    {etiqueta:>8}  {percentil(movimientos, p):>8.3f}%")
    print(f"    {'promedio':>8}  {sum(movimientos)/len(movimientos):>8.3f}%")
    print(f"    {'mejor':>8}  {max(movimientos):>8.3f}%")
    print()

    # --- La cuenta que importa --------------------------------------------
    # De las que acertaron la direccion, cuantas capturaron lo suficiente
    # como para pagar el peaje.
    paga = [m for m in ganadoras if m > costo_ida_y_vuelta_pct]
    no_paga = [m for m in ganadoras if m <= costo_ida_y_vuelta_pct]
    print("  DE LAS QUE ACERTARON LA DIRECCION:")
    if ganadoras:
        print(f"    pagan el peaje:    {len(paga):>5}  "
              f"({len(paga)/len(ganadoras)*100:>5.1f}% de las verdes)")
        print(f"    NO lo pagan:       {len(no_paga):>5}  "
              f"({len(no_paga)/len(ganadoras)*100:>5.1f}% de las verdes)"
              "   <- acertaron y perdieron plata")
    print()

    # --- De donde sale el resultado bruto ---------------------------------
    bruto_total = sum(o.resultado_bruto for o in operaciones)
    costo_total = sum(o.costos for o in operaciones)
    positivos = sorted((o.resultado_bruto for o in operaciones), reverse=True)
    top10 = sum(positivos[:max(1, len(positivos) // 10)])

    print("  DE DONDE SALE EL RESULTADO (en USDT)")
    print(f"    Bruto total:            {bruto_total:>+10.2f}")
    print(f"    Costos pagados:         {costo_total:>10.2f}")
    print(f"    Neto:                   {bruto_total - costo_total:>+10.2f}")
    if bruto_total > 0:
        print(f"    El 10% mejor aporta:    {top10:>+10.2f}"
              f"   ({top10/bruto_total*100:.0f}% del bruto)")
    print(f"    Costo por operacion:    {costo_total/len(operaciones):>10.3f}")
    print()

    # --- Cuanto tendria que durar para que el peaje se diluya -------------
    velas = [o.velas_abierta for o in operaciones]
    print("  DURACION (velas abiertas)")
    print(f"    mediana {percentil([float(v) for v in velas], 50):.0f}   "
          f"p90 {percentil([float(v) for v in velas], 90):.0f}   "
          f"maxima {max(velas)}")


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    cfg = mwf.base_config()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]
    costo = 2 * (float(cfg["costos"]["comision_por_lado_pct"])
                 + float(cfg["costos"]["slippage_pct_por_lado"]))

    print("=" * 76)
    print(" KINETIC - anatomia del peaje")
    print("=" * 76)
    print("  Descriptivo. No prueba ninguna hipotesis: sirve para decidir")
    print("  cual vale la pena probar.")

    for par in cfg["backtest"]["universo"]:
        for tf in ("15m", "1h"):
            print(f"\n{'=' * 76}\n {par} {tf}\n{'=' * 76}", flush=True)
            df = ind.agregar_indicadores(data_feed.cargar(par, tf, carpeta=carpeta), cfg)
            r = motor.correr(df, cfg, par, tf, mwf.REGLAS)
            analizar(r.operaciones, costo)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
