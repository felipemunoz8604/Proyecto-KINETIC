r"""
Cuanto de la proteccion de E0 la produce el rezago de la regla de regimen.

LA SOSPECHA
------------
Con la regla propuesta -- alcista si el retorno de BTC de los 12 meses previos
fue positivo -- los meses bajistas de la ventana comun son 2020-07 y despues
2022-03 hasta 2023-06. Quince meses corridos.

**Pero BTC subio 154,5% en 2023.** De enero a junio ya venia recuperando, y la
regla igual los marca bajistas porque mira doce meses para atras. Si E0 estuvo
afuera del mercado durante esos meses, su "proteccion" se calcula en parte
sobre meses que subieron, y esta inflada.

ESTO ES SENSIBILIDAD DE LA VARA, NO BARRIDO DE LA ESTRATEGIA
--------------------------------------------------------------
**E0 no cambia en ninguna de las corridas de este archivo.** Lo unico que
varia es la ventana con que se clasifican los meses, que es parte del criterio
y no de la estrategia.

Por eso cuesta **cero pruebas de Deflated Sharpe**: no se esta eligiendo entre
configuraciones de E0, se esta midiendo cuanto se mueve el instrumento de
medicion. Si al final hay que elegir una ventana, se elige por una razon
escrita y no por cual da mejor.

LAS TRES COSAS QUE MIDE
------------------------
1. **C-A y C-B con distintas ventanas de tendencia** (3 a 24 meses).
2. **Cuantos de los meses marcados bajistas de verdad bajaron.** Es la medida
   directa del error de etiquetado.
3. **Que exposicion tenia E0 en los meses mal etiquetados.** Es lo que decide
   si el error infla la proteccion o no: si E0 estaba adentro, no infla nada.

Se corre asi:

    venv\Scripts\python.exe tools\sensibilidad_regimen.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtesting import motor_cartera as mc  # noqa: E402
from core import archivo_binance as arch  # noqa: E402
from execution.costos import ModeloDeCostos, TipoOrden, Venue  # noqa: E402
from execution.filtros import TablaDeFiltros  # noqa: E402
from metrics import benchmarks, regimen, ventana  # noqa: E402
from strategy import e0  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
CARPETA_PERP = RAIZ / "data" / "perpetuo"
FILTROS = RAIZ / "data" / "filtros_spot.json"
CAPITAL = 500.0
REFERENCIA = "BTCUSDT"
VENTANAS = (3, 6, 9, 12, 18, 24)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 78)
    print(" KINETIC - cuanto de la proteccion de E0 la produce el rezago")
    print("=" * 78)
    print("  E0 NO cambia en ninguna corrida. Lo unico que varia es la ventana")
    print("  con que se clasifican los meses. Cuesta cero pruebas de DSR.")
    print()

    velas = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas = velas[velas.index <= ventana.DISENO_HASTA]

    # Ventana comun con E2, para que los numeros sean los del re-puntaje.
    primera_perp = min(
        arch.cargar(p.stem.replace("_1d", ""), "1d", CARPETA_PERP).index[0]
        for p in list(CARPETA_PERP.glob("BTCUSDT_1d.csv")))
    desde = max(ventana.DISENO_DESDE, primera_perp)

    datos = velas.assign(exposicion=e0.exposicion_objetivo(velas["close"]))
    datos = datos[datos.index >= desde]
    filtros = TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists() else None
    r = mc.simular(
        datos[["open"]].rename(columns={"open": e0.SIMBOLO}),
        datos[["close"]].rename(columns={"close": e0.SIMBOLO}),
        datos[["exposicion"]].rename(columns={"exposicion": e0.SIMBOLO}),
        CAPITAL, ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb=True),
        rangos={e0.SIMBOLO: 1}, filtros=filtros)
    p_b1 = benchmarks.comprar_y_mantener(datos, CAPITAL)
    print(f"  Ventana {datos.index[0].date()} a {datos.index[-1].date()}"
          f"   ({time.time() - t0:.0f} s)")

    # Retorno mensual REAL de BTC, para saber que meses bajaron de verdad.
    real = regimen._mensual(p_b1)
    exposicion = r.exposicion.sum(axis=1)
    exp_mensual = exposicion.resample("ME").mean()
    exp_mensual.index = exp_mensual.index.to_period("M")

    print()
    print("=" * 78)
    print(" C-A Y C-B SEGUN LA VENTANA DE TENDENCIA")
    print("=" * 78)
    print(f"  {'ventana':>9}{'bajistas':>10}{'C-A':>9}{'C-B':>9}"
          f"{'caida E0':>11}{'caida B1':>11}")
    filas = {}
    for meses in VENTANAS:
        alcistas = regimen.clasificar_meses(velas["close"], meses)
        p = regimen.puntuar(r.patrimonio, p_b1, alcistas, f"{meses}m")
        filas[meses] = (p, alcistas)
        print(f"  {meses:>7}m{p.meses_bajistas:>10}{p.captura:>9.3f}"
              f"{p.proteccion:>9.3f}{p.caida_bajista * 100:>10.1f}%"
              f"{p.caida_bajista_b1 * 100:>10.1f}%")

    print()
    print("=" * 78)
    print(" EL ERROR DE ETIQUETADO: MESES 'BAJISTAS' QUE SUBIERON")
    print("=" * 78)
    print(f"  {'ventana':>9}{'bajistas':>10}{'que subieron':>15}"
          f"{'% mal etiquetados':>20}")
    for meses, (p, alcistas) in filas.items():
        comunes = real.index.intersection(alcistas.index)
        marca = alcistas.loc[comunes]
        bajistas = real.loc[comunes][~marca]
        subieron = int((bajistas > 0).sum())
        print(f"  {meses:>7}m{len(bajistas):>10}{subieron:>15}"
              f"{subieron / max(len(bajistas), 1) * 100:>19.0f}%")

    print()
    print("  Un mes mal etiquetado NO infla la proteccion por si solo. La infla")
    print("  si ademas E0 estaba AFUERA del mercado ese mes: ahi la caida")
    print("  medida es cero por una razon que no es proteger de nada.")

    print()
    print("=" * 78)
    print(" LOS MESES MAL ETIQUETADOS CON VENTANA DE 12 (LA PROPUESTA)")
    print("=" * 78)
    p12, alc12 = filas[12]
    comunes = real.index.intersection(alc12.index).intersection(
        exp_mensual.index)
    marca = alc12.loc[comunes]
    tabla = pd.DataFrame({
        "retorno_btc": real.loc[comunes] * 100,
        "exposicion_e0": exp_mensual.loc[comunes],
    })[~marca]
    malos = tabla[tabla["retorno_btc"] > 0]
    print(f"  {'mes':<10}{'BTC':>9}{'exposicion E0':>16}")
    for mes, fila in tabla.iterrows():
        marca_error = "  <- subio" if fila["retorno_btc"] > 0 else ""
        print(f"  {str(mes):<10}{fila['retorno_btc']:>+8.1f}%"
              f"{fila['exposicion_e0']:>16.2f}{marca_error}")
    print()
    print(f"  De {len(tabla)} meses marcados bajistas, {len(malos)} subieron.")
    if len(malos):
        print(f"  Exposicion media de E0 en esos {len(malos)}: "
              f"{malos['exposicion_e0'].mean():.2f}")
        print(f"  Exposicion media en los que si bajaron: "
              f"{tabla[tabla['retorno_btc'] <= 0]['exposicion_e0'].mean():.2f}")

    print()
    print("=" * 78)
    print(" LA PROTECCION SIN LOS MESES MAL ETIQUETADOS")
    print("=" * 78)
    print("  Sacando de la cuenta los meses que la regla llamo bajistas y")
    print("  subieron, queda la proteccion sobre meses que de verdad cayeron.")
    solo_bajaron = alc12.copy()
    for mes in malos.index:
        solo_bajaron.loc[mes] = True      # se los saca del conjunto bajista
    p_limpia = regimen.puntuar(r.patrimonio, p_b1, solo_bajaron, "E0 limpia")
    print()
    print(f"  C-B con la regla tal cual:            {p12.proteccion:.3f}   "
          f"(caida E0 {p12.caida_bajista * 100:.1f}%)")
    print(f"  C-B solo sobre meses que bajaron:     "
          f"{p_limpia.proteccion:.3f}   "
          f"(caida E0 {p_limpia.caida_bajista * 100:.1f}%)")
    print()
    print("  OJO: la version 'limpia' usa el retorno del propio mes para")
    print("  decidir si contarlo, o sea que MIRA AL FUTURO. No sirve como")
    print("  criterio -- sirve solo para saber cuanto del numero venia del")
    print("  etiquetado y cuanto de la estrategia.")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
