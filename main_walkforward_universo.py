r"""
La hipotesis de la temporalidad, sobre 15 pares en 4h - Fase 1 (reabierta).

QUE ES ESTO Y QUE NO ES
-----------------------
NO es una hipotesis nueva. Es exactamente la misma pregunta del
`main_walkforward_umbral.py` --si 4h paga el peaje fijo de 0,30%-- con el
mismo metodo, el mismo barrido de un solo parametro, los mismos candidatos y
el mismo trailing fijo. Lo unico que cambia es cuanto mercado se mira.

Se hace porque en BTC y ETH el efecto aparecio pero con 10 y 9 operaciones
por anio, y sobre esa muestra no se puede confiar en ninguna cifra.

EL UNIVERSO NO SE ELIGE ACA
---------------------------
Sale de `tools/elegir_universo.py`, con una regla que no consulta ningun
backtest. Esta pegado abajo como constante para que la corrida sea
reproducible, pero el que manda es el criterio, no la lista.

**Sesgo de supervivencia:** son los pares que llegaron vivos hasta hoy. Los
que se listaron en 2018 y se murieron no estan, y no hay forma de traerlos
desde el endpoint publico. Cualquier resultado de aca esta inflado por una
cantidad que no se puede medir. Va impreso al final a proposito.

LO QUE ESTA CUENTA NO ES
------------------------
**No es una simulacion de cartera.** Cada par corre con sus propios 500 USDT
y su propia contabilidad, y despues se suman los netos. Eso mide el efecto,
que es lo que se quiere medir, pero NO modela nada de lo que hace falta para
operar de verdad: capital compartido, tope de posiciones simultaneas, ni el
hecho de que quince criptos contra el dolar suben y bajan casi todas juntas
--que es una sola apuesta tomada quince veces, el mismo agujero que TITAN
tiene anotado como bug F.

Si la hipotesis se sostuviera, la cartera es el trabajo siguiente, no un
detalle.

LOS CRITERIOS ESTABAN ESCRITOS ANTES
------------------------------------
Los cuatro de abajo se fijaron en `docs/BITACORA_KINETIC.md` y se
commitearon ANTES de bajar los datos. El script los evalua solo e imprime
SOSTENIDA o NO SOSTENIDA sin que nadie tenga que interpretar nada.

Se corre asi:

    venv\Scripts\python.exe main_walkforward_universo.py
"""

from __future__ import annotations

import copy
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import main_walkforward as mwf  # noqa: E402
import main_walkforward_umbral as umb  # noqa: E402
from backtesting import backtest_engine as motor  # noqa: E402
from backtesting import walk_forward as wf  # noqa: E402
from core import data_feed  # noqa: E402
from strategy import indicators as ind  # noqa: E402

# De tools/elegir_universo.py, corte 2019-01-01. Ordenados por antiguedad.
UNIVERSO = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "NEOUSDT", "LTCUSDT", "QTUMUSDT",
    "ADAUSDT", "IOTAUSDT", "XLMUSDT", "XRPUSDT", "ETCUSDT", "ICXUSDT",
    "ONTUSDT", "TRXUSDT", "VETUSDT",
]

TEMPORALIDAD = "4h"

# --- Los cuatro criterios, tal como quedaron commiteados ------------------
MINIMO_PARES_EN_POSITIVO = 8      # de 15
MAXIMO_APORTE_DE_UN_PAR_PCT = 50.0
MAXIMO_APORTE_DE_UNA_OP_PCT = 20.0


@dataclass
class Fila:
    par: str
    operaciones: int
    ventanas: int
    neto: float
    neto_sin_filtro: float
    mejor_operacion: float
    estabilidad: str
    elegidos: list


def correr_par(par: str, cfg: dict, carpeta: Path) -> Fila | None:
    df = ind.agregar_indicadores(
        data_feed.cargar(par, TEMPORALIDAD, carpeta=carpeta), cfg
    )
    resultado = wf.correr(
        df, cfg, par, TEMPORALIDAD, umb.CANDIDATOS, umb.aplicar_umbral,
        anios_entrenamiento=3, anios_prueba=1, reglas_simbolo=mwf.REGLAS,
    )
    if not resultado.ventanas:
        return None

    m = resultado.metricas
    neto = m.capital_final - m.capital_inicial

    # Misma referencia que en la corrida de dos pares: apagar la condicion de
    # consolidacion. `recortar_inicio=False` porque `tramo` es un pedazo del
    # historico y el descarte de los 30 dias ya lo hizo el walk-forward.
    tramo = df[df.index >= resultado.ventanas[0].prueba_desde]
    c = copy.deepcopy(cfg)
    umb.aplicar_umbral(c, umb.SIN_FILTRO)
    apagado = motor.correr(tramo, c, par, TEMPORALIDAD, mwf.REGLAS,
                           recortar_inicio=False)

    mejor = max((o.resultado_neto for o in resultado.operaciones), default=0.0)
    return Fila(
        par=par,
        operaciones=m.operaciones,
        ventanas=len(resultado.ventanas),
        neto=neto,
        neto_sin_filtro=apagado.metricas.resultado_neto,
        mejor_operacion=mejor,
        estabilidad=resultado.estabilidad,
        elegidos=resultado.elegidos,
    )


def veredicto(filas: list[Fila]) -> bool:
    """Evalua los cuatro criterios y los imprime. Devuelve si se sostuvo."""
    neto_total = sum(f.neto for f in filas)
    en_positivo = [f for f in filas if f.neto > 0]
    mejor_par = max(filas, key=lambda f: f.neto)
    mejor_op = max(f.mejor_operacion for f in filas)

    print()
    print("=" * 76)
    print(" LOS CUATRO CRITERIOS (fijados antes de bajar los datos)")
    print("=" * 76)

    c1 = len(en_positivo) >= MINIMO_PARES_EN_POSITIVO
    print(f"  1. Amplitud: {len(en_positivo)} de {len(filas)} pares en positivo "
          f"(hacen falta {MINIMO_PARES_EN_POSITIVO})            "
          f"{'PASA' if c1 else 'NO PASA'}")

    # Contra un neto agregado negativo el porcentaje no significa nada: un par
    # que gana plata daria un aporte negativo y "pasaria" el criterio por un
    # accidente de signo. Se declara indefinido, que es lo que es.
    if neto_total > 0:
        aporte_par = mejor_par.neto / neto_total * 100.0
        c2 = aporte_par < MAXIMO_APORTE_DE_UN_PAR_PCT
        print(f"  2. Ningun par domina: {mejor_par.par} aporta {aporte_par:.0f}% "
              f"del neto (tope {MAXIMO_APORTE_DE_UN_PAR_PCT:.0f}%)      "
              f"{'PASA' if c2 else 'NO PASA'}")
        aporte_op = mejor_op / neto_total * 100.0
        c3 = aporte_op < MAXIMO_APORTE_DE_UNA_OP_PCT
        print(f"  3. Ninguna operacion domina: la mejor aporta {aporte_op:.0f}% "
              f"(tope {MAXIMO_APORTE_DE_UNA_OP_PCT:.0f}%)       "
              f"{'PASA' if c3 else 'NO PASA'}")
    else:
        c2 = c3 = False
        print("  2. Ningun par domina:        INDEFINIDO con neto agregado "
              "negativo   NO PASA")
        print("  3. Ninguna operacion domina: INDEFINIDO con neto agregado "
              "negativo   NO PASA")

    c4 = neto_total > 0
    print(f"  4. Neto agregado positivo: {neto_total:+.2f} USDT sobre "
          f"{len(filas) * 500:,} de capital   {'PASA' if c4 else 'NO PASA'}")

    sostenida = c1 and c2 and c3 and c4
    print()
    print("=" * 76)
    print(f" HIPOTESIS {'SOSTENIDA' if sostenida else 'NO SOSTENIDA'}")
    print("=" * 76)
    if not sostenida:
        print("  Segun lo commiteado antes de correr, la Fase 1 se cierra.")
        print("  No se ajusta el criterio ni se saca el par que molesta.")
    return sostenida


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    cfg = umb.base_config()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]

    print("=" * 76)
    print(" KINETIC - la hipotesis de la temporalidad sobre 15 pares en 4h")
    print("=" * 76)
    print(f"  Mismo metodo que con dos pares: umbral relativo en "
          f"{umb.CANDIDATOS} x ATR,")
    print("  elegido por ventana mirando solo el pasado. Trailing fijo en 2xATR.")
    print("  Universo por regla ciega al resultado (tools/elegir_universo.py).")
    print("  500 USDT por par, contabilidad independiente. NO es una cartera.")
    print()

    filas: list[Fila] = []
    t0 = time.time()
    for par in UNIVERSO:
        if not (carpeta / f"{par}_{TEMPORALIDAD}.csv").exists():
            print(f"  [X] faltan datos de {par} {TEMPORALIDAD} -- se saltea")
            continue
        print(f"  {par:<10} ...", end="", flush=True)
        fila = correr_par(par, cfg, carpeta)
        if fila is None:
            print(" sin ventanas suficientes")
            continue
        filas.append(fila)
        print(f" {fila.operaciones:>4} ops   {fila.neto:>+9.2f} USDT   "
              f"{fila.estabilidad}")

    if not filas:
        print("\n  No se pudo correr ningun par.")
        return 1

    print()
    print("=" * 76)
    print(" DETALLE POR PAR (todo fuera de muestra)")
    print("=" * 76)
    print(f"  {'Par':<10} {'Ops':>5} {'Ops/anio':>9} {'Neto':>10} "
          f"{'Sin filtro':>11} {'Mejor op':>9}  Estabilidad")
    for f in sorted(filas, key=lambda x: x.neto, reverse=True):
        print(f"  {f.par:<10} {f.operaciones:>5} "
              f"{f.operaciones / f.ventanas:>9.0f} {f.neto:>+10.2f} "
              f"{f.neto_sin_filtro:>+11.2f} {f.mejor_operacion:>+9.2f}  "
              f"{f.estabilidad}")

    total_ops = sum(f.operaciones for f in filas)
    total_anios = sum(f.ventanas for f in filas)
    neto_total = sum(f.neto for f in filas)
    sin_filtro_total = sum(f.neto_sin_filtro for f in filas)
    print("  " + "-" * 72)
    print(f"  {'AGREGADO':<10} {total_ops:>5} "
          f"{total_ops / total_anios:>9.0f} {neto_total:>+10.2f} "
          f"{sin_filtro_total:>+11.2f}")

    veredicto(filas)

    print()
    print("  RECORDATORIOS QUE VIAJAN PEGADOS AL NUMERO:")
    print("  - Sesgo de supervivencia: son los pares que llegaron vivos hasta")
    print("    hoy. Los que se murieron no estan y no se pueden traer. El")
    print("    resultado esta inflado por una cantidad que no se puede medir.")
    print("  - No es una cartera: 15 cuentas de 500 corriendo en paralelo. Las")
    print("    criptos contra el dolar se mueven casi todas juntas, asi que")
    print("    esto es una apuesta tomada quince veces, no quince apuestas.")
    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
