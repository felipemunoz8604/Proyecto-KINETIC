"""
Validacion walk-forward de la hipotesis del trailing - Fase 1.

LA HIPOTESIS
------------
Con 24-27% de acierto, el resultado depende de que las pocas ganadoras
corran mucho. Un trailing a 2xATR se mueve muy pegado al precio: un
retroceso de 2xATR es ruido normal dentro de una tendencia, asi que
probablemente este cortando ganadoras que todavia tenian recorrido.

Se prueba dando mas aire al trailing SIN tocar el stop inicial. Son dos
trabajos distintos: el inicial define cuanto se arriesga (y cuanto se
compra), el trailing define cuanto aire tiene una ganadora.

COMO SE JUZGA
-------------
No se elige el mejor sobre los nueve anios: eso seria ajustar a un pasado
que ya conocemos. Se reelige cada anio usando solo los tres anteriores, y se
juzga con el anio siguiente, que el elegido nunca vio.

Y se compara contra dos referencias:
  - FIJO 2x: no elegir nada, dejar el trailing como estaba.
  - El mejor VISTO EN RETROSPECTIVA sobre todo el periodo, que es lo que
    daria un barrido tramposo. La distancia entre ese numero y el de
    walk-forward es, literalmente, cuanto nos habriamos enganado.

Se corre asi:

    venv\\Scripts\\python.exe main_walkforward.py
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from backtesting import backtest_engine as motor  # noqa: E402
from backtesting import walk_forward as wf  # noqa: E402
from core import config_loader as cfgmod  # noqa: E402
from core import data_feed  # noqa: E402
from risk import position_sizing  # noqa: E402
from strategy import indicators as ind  # noqa: E402

REGLAS = position_sizing.ReglasSimbolo(0.00001, 0.00001, 5.0)
CANDIDATOS = [2.0, 3.0, 4.0, 5.0, 6.0]
ADX_MINIMO = 20.0
UMBRAL_CONSOLIDACION = 0.75


def aplicar_trailing(cfg: dict, valor: float) -> None:
    cfg["stops"]["trailing_atr_multiplicador"] = valor


def base_config() -> dict:
    cfg = copy.deepcopy(cfgmod.cargar())
    cfg["estrategia"]["regimen"]["adx_minimo"] = ADX_MINIMO
    cfg["estrategia"]["consolidacion"]["umbral_desviacion_pct"] = UMBRAL_CONSOLIDACION
    cfg["estrategia"]["portfolio_guard"]["distancia_maxima_bajo_sma_pct"] = None
    return cfg


def nota_de_brecha(elegidos, mejor_valor, brecha) -> list[str]:
    """
    Explica la distancia entre el walk-forward y el mejor en retrospectiva.

    La brecha solo es "el precio de no conocer el futuro" en la medida en que
    el walk-forward haya elegido algo DISTINTO del valor que gano mirando
    todo el periodo. Si eligio el mismo valor en TODAS las ventanas, la
    diferencia viene de otro lado -- cierres forzados en los bordes, por
    ejemplo -- y llamarla sobreajuste seria mentir.

    La cuenta va ventana por ventana. El 29-ago-2026 esta nota comparaba
    contra el valor DOMINANTE y dijo "mismo valor que eligio el walk-forward:
    5.0x" cuando 5.0x habia ganado 3 de 6 ventanas y las otras 3 eligieron 4x
    y 6x. Mando a buscar la causa a donde no estaba: se gasto una corrida
    entera persiguiendo cierres forzados que resultaron ser cero.
    """
    if brecha >= 0:
        lineas = [f"  -> un barrido sobre todo el periodo se veria "
                  f"{brecha:.2f} USDT MEJOR de lo que el walk-forward capturo"]
    else:
        lineas = [f"  -> un barrido sobre todo el periodo se veria "
                  f"{-brecha:.2f} USDT PEOR: no hubo premio por mirar el futuro"]

    iguales = elegidos.count(mejor_valor)
    if iguales == len(elegidos):
        lineas.append(
            f"     (el walk-forward eligio {mejor_valor}x en TODAS las ventanas: "
            f"la brecha NO es sobreajuste de parametro, buscar la causa en otro lado)"
        )
    else:
        otros = sorted(set(elegidos) - {mejor_valor})
        lineas.append(
            f"     (el walk-forward eligio {mejor_valor}x en solo {iguales} de "
            f"{len(elegidos)} ventanas; en el resto eligio {otros} -- esa "
            f"diferencia SI es el precio de no conocer el futuro)"
        )
    return lineas


def concentracion(operaciones) -> float:
    if not operaciones:
        return 0.0
    neto = sum(o.resultado_neto for o in operaciones)
    if neto == 0:
        return 0.0
    return max(o.resultado_neto for o in operaciones) / neto * 100.0


def main() -> int:
    # Sin esto Python retiene la salida en el bufer y no se ve ningun
    # avance hasta que termina todo, que son varios minutos.
    sys.stdout.reconfigure(line_buffering=True)

    cfg = base_config()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]

    print("=" * 76)
    print(" KINETIC - WALK-FORWARD: hipotesis del trailing")
    print("=" * 76)
    print(f"  Candidatos:  trailing en {CANDIDATOS} x ATR")
    print("  Stop inicial fijo en 2xATR (no se toca: define el riesgo)")
    print("  Entrenar 3 anios -> probar 1 anio -> avanzar 1 anio")
    print(f"  Filtros: ADX >= {ADX_MINIMO}, consolidacion <= {UMBRAL_CONSOLIDACION}%")
    print()

    for par in cfg["backtest"]["universo"]:
        for tf in ("15m", "1h"):
            print("=" * 76, flush=True)
            print(f" {par} {tf}")
            print("=" * 76)
            t0 = time.time()

            print("  calculando indicadores...", flush=True)
            df = ind.agregar_indicadores(data_feed.cargar(par, tf, carpeta=carpeta), cfg)
            print(f"  {len(df):,} velas. Corriendo ventanas...", flush=True)

            resultado = wf.correr(
                df, cfg, par, tf, CANDIDATOS, aplicar_trailing,
                anios_entrenamiento=3, anios_prueba=1, reglas_simbolo=REGLAS,
            )
            if not resultado.ventanas:
                print("  Sin ventanas suficientes.")
                continue

            print(resultado.informe())
            print()
            print("  Puntaje de cada candidato en el entrenamiento:")
            print(resultado.informe_de_candidatos())
            m = resultado.metricas
            pf = m.profit_factor
            pf_txt = "inf" if pf == float("inf") else f"{pf:.3f}"
            print()
            print("  --- FUERA DE MUESTRA (lo unico que cuenta) ---")
            print(f"  Operaciones:   {m.operaciones:,}   PF {pf_txt}   "
                  f"acierto {m.tasa_acierto_pct:.1f}%")
            print(f"  Capital:       {m.capital_inicial:,.2f} -> {m.capital_final:,.2f} "
                  f"USDT ({m.retorno_total_pct:+.2f}%)")
            print(f"  Elegidos:      {resultado.elegidos}")
            dispersion = resultado.dispersion_pct
            detalle = (f" (las elecciones abarcan el {dispersion:.0f}% del menu "
                       f"de candidatos)" if dispersion is not None else "")
            print(f"  Estabilidad:   {resultado.estabilidad}{detalle}")
            print(f"  Concentracion: la mejor operacion aporta "
                  f"{resultado.concentracion_pct:.0f}% del neto")

            # --- Referencia 1: no elegir nada, dejar el trailing en 2x ----
            primera = resultado.ventanas[0].prueba_desde
            tramo = df[df.index >= primera]
            # `tramo` es un pedazo del historico, no el historico: si se
            # dejara recortar, perderia 30 dias que el walk-forward SI
            # midio, y la comparacion no seria contra lo mismo.
            fijo = motor.correr(tramo, cfg, par, tf, REGLAS,
                                recortar_inicio=False)
            print(f"\n  Referencia FIJO 2x sobre el mismo tramo: "
                  f"{fijo.metricas.resultado_neto:+.2f} USDT "
                  f"({fijo.metricas.operaciones} ops)")

            # --- Referencia 2: el mejor en retrospectiva (tramposo) -------
            mejor_valor, mejor_neto = None, float("-inf")
            for valor in CANDIDATOS:
                c = copy.deepcopy(cfg)
                aplicar_trailing(c, valor)
                r = motor.correr(tramo, c, par, tf, REGLAS, recortar_inicio=False)
                if r.metricas.resultado_neto > mejor_neto:
                    mejor_valor, mejor_neto = valor, r.metricas.resultado_neto
            print(f"  Referencia MEJOR EN RETROSPECTIVA ({mejor_valor}x): "
                  f"{mejor_neto:+.2f} USDT")

            for linea in nota_de_brecha(
                resultado.elegidos, mejor_valor, mejor_neto - m.resultado_neto
            ):
                print(linea)
            print(f"\n  ({time.time() - t0:.0f} s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
