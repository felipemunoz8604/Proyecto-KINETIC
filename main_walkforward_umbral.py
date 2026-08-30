"""
Walk-forward de la hipotesis de la temporalidad - Fase 1 (reabierta).

LA HIPOTESIS
------------
El peaje es FIJO (0,30% ida y vuelta) y la ventaja por operacion crece con la
temporalidad. Medido el 29-ago-2026, el movimiento capturado promedio pasa de
+0,024% en BTC 15m a +0,316% en BTC 1h, y de +0,042% a +0,656% en ETH. Si esa
tendencia sigue, 4h deberia pagar el peaje con holgura.

4h nunca se pudo evaluar antes porque el filtro de consolidacion estaba en %
del precio -- una unidad que no escala con la temporalidad -- y tapaba el
97,6% de las velas en BTC 4h y el 99,3% en ETH 4h. Los "0 a 3 operaciones"
que estaban anotados como falta de señales eran el filtro, no el mercado.

Con `modo: relativo` eso queda arreglado. La dispersion dividida por el ATR%
no tiene unidades, y se nota: las cuatro distribuciones son casi la misma.

    par/tf      p10    p25   mediana   p75    p90
    BTC 1h     0.88   1.12    1.50    2.04   2.65
    BTC 4h     1.00   1.21    1.57    2.07   2.62
    ETH 1h     0.91   1.14    1.52    2.05   2.64
    ETH 4h     1.01   1.22    1.57    2.07   2.61

QUE SE ELIGE Y QUE NO
---------------------
Se barre UN SOLO parametro: el umbral relativo de consolidacion. El trailing
queda fijo en 2x ATR y el stop inicial tambien, como en toda la Fase 1.
Decision de Felipe del 30-ago-2026: barrer dos parametros a la vez multiplica
las combinaciones y con eso la chance de encontrar algo lindo por azar.

El menu de candidatos sale de la distribucion real de `desv_rel`, no de la
intuicion -- 1,0 es aproximadamente el percentil 10 de las velas y 1,8 ronda
el 65. **Cual de los cinco se usa lo decide el walk-forward ventana por
ventana, mirando solo el pasado**, que es la unica forma de que el numero
elegido no venga de haber visto el resultado.

1h va incluido A PROPOSITO, como control. Si 4h rinde mejor que 1h con la
misma regla y la misma unidad, la hipotesis tiene sustento. Si las dos dan
parecido, entonces lo que cambio fue el filtro y no la temporalidad, y la
hipotesis no se probo.

LAS DOS REFERENCIAS
-------------------
  - SIN FILTRO: un umbral tan alto que la consolidacion no rechaza nunca.
    Contesta si esa condicion aporta algo o solamente estorba.
  - MEJOR EN RETROSPECTIVA: el candidato que habria ganado mirando todo el
    periodo. La distancia contra el walk-forward es, literalmente, cuanto nos
    habriamos enganado a nosotros mismos con un barrido tramposo.

Se corre asi:

    venv\\Scripts\\python.exe main_walkforward_umbral.py
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

import main_walkforward as mwf  # noqa: E402
from backtesting import backtest_engine as motor  # noqa: E402
from backtesting import walk_forward as wf  # noqa: E402
from core import config_loader as cfgmod  # noqa: E402
from core import data_feed  # noqa: E402
from strategy import indicators as ind  # noqa: E402

# En unidades de ATR. Del p10 al ~p65 de las velas, segun la distribucion
# real medida arriba. Cinco, los mismos que tenia el barrido del trailing:
# mas candidatos es mas chances de que uno gane por casualidad.
CANDIDATOS = [1.0, 1.2, 1.4, 1.6, 1.8]

# Tan alto que la condicion nunca rechaza. No es un candidato: es la
# referencia contra la que se mide si el filtro sirve de algo.
SIN_FILTRO = 1e9

TEMPORALIDADES = ("1h", "4h")


def aplicar_umbral(cfg: dict, valor: float) -> None:
    cfg["estrategia"]["consolidacion"]["umbral_relativo"] = valor


def base_config() -> dict:
    """
    Igual que la de la Fase 1, salvo el modo de consolidacion.

    El ADX minimo se toma de `main_walkforward` a proposito, para que las dos
    corridas sean comparables: si aca se pusiera otro numero, cualquier
    diferencia de resultado podria venir de ahi y no de la temporalidad.
    """
    cfg = copy.deepcopy(cfgmod.cargar())
    cfg["estrategia"]["regimen"]["adx_minimo"] = mwf.ADX_MINIMO
    cfg["estrategia"]["consolidacion"]["modo"] = "relativo"
    cfg["estrategia"]["portfolio_guard"]["distancia_maxima_bajo_sma_pct"] = None
    return cfg


def por_anio(resultado) -> float:
    """
    Operaciones fuera de muestra por anio. El primer filtro que hay que pasar.

    Cada ventana de prueba dura un anio, asi que la cuenta es la division
    directa. Va primero en el informe a proposito: con menos de ~15 por anio
    el resto de las cifras son ruido, y ya nos paso con ETH 1h.
    """
    if not resultado.ventanas:
        return 0.0
    return len(resultado.operaciones) / len(resultado.ventanas)


def main() -> int:
    # Sin esto Python retiene la salida en el bufer y no se ve ningun avance
    # hasta que termina todo, que son varios minutos.
    sys.stdout.reconfigure(line_buffering=True)

    cfg = base_config()
    carpeta = RAIZ / cfg["datos"]["carpeta_historico"]

    print("=" * 76)
    print(" KINETIC - WALK-FORWARD: hipotesis de la temporalidad")
    print("=" * 76)
    print(f"  Candidatos:  umbral de consolidacion en {CANDIDATOS} x ATR")
    print("  Trailing y stop inicial fijos en 2xATR (no se tocan)")
    print("  Entrenar 3 anios -> probar 1 anio -> avanzar 1 anio")
    print(f"  Filtro de regimen: ADX >= {mwf.ADX_MINIMO}")
    print("  1h va como CONTROL. Lo que se prueba es 4h.")
    print()

    for par in cfg["backtest"]["universo"]:
        for tf in TEMPORALIDADES:
            archivo = carpeta / f"{par}_{tf}.csv"
            if not archivo.exists():
                print(f"  (sin datos de {par} {tf}, se saltea)")
                continue

            print("=" * 76, flush=True)
            print(f" {par} {tf}")
            print("=" * 76)
            t0 = time.time()

            print("  calculando indicadores...", flush=True)
            df = ind.agregar_indicadores(data_feed.cargar(par, tf, carpeta=carpeta), cfg)
            print(f"  {len(df):,} velas. Corriendo ventanas...", flush=True)

            resultado = wf.correr(
                df, cfg, par, tf, CANDIDATOS, aplicar_umbral,
                anios_entrenamiento=3, anios_prueba=1, reglas_simbolo=mwf.REGLAS,
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

            # El orden importa y es el acordado: primero cuantas operaciones
            # hay, porque sin muestra el resto de los numeros no significan
            # nada -- es la leccion de ETH 1h.
            anual = por_anio(resultado)
            aviso = "   <- muy pocas, cualquier cifra de abajo es ruido" if anual < 15 else ""
            print(f"  Operaciones:   {m.operaciones:,}  ({anual:.0f} por anio){aviso}")
            print(f"  Concentracion: la mejor operacion aporta "
                  f"{resultado.concentracion_pct:.0f}% del neto")
            dispersion = resultado.dispersion_pct
            detalle = (f" (las elecciones abarcan el {dispersion:.0f}% del menu)"
                       if dispersion is not None else "")
            print(f"  Estabilidad:   {resultado.estabilidad}{detalle}")
            print(f"  Elegidos:      {resultado.elegidos}")
            respaldo = resultado.respaldo_minimo
            if respaldo is not None:
                print(f"  Respaldo:      la ventana peor sostenida tuvo "
                      f"{respaldo} operaciones de entrenamiento")
            print(f"  PF {pf_txt}   acierto {m.tasa_acierto_pct:.1f}%")
            print(f"  Capital:       {m.capital_inicial:,.2f} -> {m.capital_final:,.2f} "
                  f"USDT ({m.retorno_total_pct:+.2f}%)")

            primera = resultado.ventanas[0].prueba_desde
            tramo = df[df.index >= primera]

            # --- Referencia 1: apagar el filtro de consolidacion ----------
            # `tramo` es un pedazo del historico, no el historico: si se
            # dejara recortar, perderia 30 dias que el walk-forward SI midio,
            # y la comparacion no seria contra lo mismo.
            c = copy.deepcopy(cfg)
            aplicar_umbral(c, SIN_FILTRO)
            apagado = motor.correr(tramo, c, par, tf, mwf.REGLAS, recortar_inicio=False)
            print(f"\n  Referencia SIN FILTRO de consolidacion: "
                  f"{apagado.metricas.resultado_neto:+.2f} USDT "
                  f"({apagado.metricas.operaciones} ops)")

            # --- Referencia 2: el mejor en retrospectiva (tramposo) -------
            mejor_valor, mejor_neto = None, float("-inf")
            for valor in CANDIDATOS:
                c = copy.deepcopy(cfg)
                aplicar_umbral(c, valor)
                r = motor.correr(tramo, c, par, tf, mwf.REGLAS, recortar_inicio=False)
                if r.metricas.resultado_neto > mejor_neto:
                    mejor_valor, mejor_neto = valor, r.metricas.resultado_neto
            print(f"  Referencia MEJOR EN RETROSPECTIVA ({mejor_valor} ATR): "
                  f"{mejor_neto:+.2f} USDT")

            for linea in mwf.nota_de_brecha(
                resultado.elegidos, mejor_valor, mejor_neto - m.resultado_neto
            ):
                print(linea)
            print(f"\n  ({time.time() - t0:.0f} s)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
