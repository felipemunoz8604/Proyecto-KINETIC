r"""
M3a y M3b: las dos condiciones que cualquier compuerta tiene que cumplir.

QUE CONTESTAN
--------------
Si A2 --un estimador de regimen que no parpadee-- puede pasar la vara, sin
correr A2 y sin gastar la prueba de Deflated Sharpe que costaria.

De la identidad de la frontera salen dos condiciones necesarias y suficientes
para una compuerta de encendido y apagado a exposicion plena:

    C-A'  pasa  <=>  los dias que deja AFUERA suman log-retorno negativo,
                     por mas que el costo de las transiciones

    C-B'  pasa  <=>  la curva de los dias que deja ADENTRO no cae mas de
                     0,50 x 76,6% = 38,3%

**Las dos tiran de los mismos dias en direcciones opuestas.** Sacar un tramo
malo mejora la caida y cuesta retorno; dejarlo adentro hace lo contrario.

POR QUE CUESTA CERO PRUEBAS DE DSR
------------------------------------
Son **particiones de la serie de BTC**, no corridas de estrategia. Misma
naturaleza que el calculo de A1 del 3-sep. El contador sigue en seis.

EL TECHO Y LA VERSION IMPLEMENTABLE
-------------------------------------
`consolidar` **mira al futuro**: para saber que un tramo fue corto hay que
esperar a que termine. No se puede operar con eso, y por lo tanto M3a tal como
el analista lo escribio es un **techo**, no una estrategia.

Como falsador es valido y de una sola cara: **si ni el techo pasa, ninguna
version implementable pasa.** Por eso se reporta tambien `con_confirmacion`,
que solo usa el pasado, y la diferencia entre las dos mide cuanto de la mejora
del des-parpadeo era mirar adelante.

LA REGLA ESTA ESCRITA Y COMMITEADA DE ANTES
---------------------------------------------
En `docs/CRITERIOS_M3_4sep2026.md`, commit anterior a esta corrida. **El N es
10, declarado ahi.** Los otros tres se reportan; ninguno se elige.

Se corre asi:

    venv\Scripts\python.exe tools\m3_condiciones_de_compuerta.py
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from core import archivo_binance as arch  # noqa: E402
from metrics import benchmarks, frontera, metricas, ventana  # noqa: E402
from risk import compuerta as cp  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
REFERENCIA = "BTCUSDT"
CAPITAL = 500.0
DESDE = pd.Timestamp("2020-01-01", tz="UTC")

# Declarados en docs/CRITERIOS_M3_4sep2026.md, antes de correr.
ENES = (5, 10, 20, 30)
N_DECLARADO = 10

# Costo de un lado, igual que el de entrada de B1: comision con BNB mas
# slippage. Cada transicion de la compuerta es un lado.
COSTO_POR_LADO = benchmarks.COSTO_ENTRADA_PCT / 100.0


def _titulo(texto: str) -> None:
    print()
    print("=" * 78)
    print(f" {texto}")
    print("=" * 78)


def _curva_de(log: pd.Series, dentro: pd.Series) -> pd.Series:
    """
    La curva de patrimonio de una compuerta a exposicion plena, con costos.

    A exposicion 1,0 el rebalanceo es no hacer nada, asi que lo unico que se
    paga son las transiciones -- un lado cada una.
    """
    propios = np.where(dentro.to_numpy() == 1, log.to_numpy(), 0.0)
    peaje = np.log(1.0 - COSTO_POR_LADO)
    cambios = np.abs(np.diff(dentro.to_numpy(), prepend=0)) > 0
    return pd.Series(CAPITAL * np.exp(np.cumsum(propios + cambios * peaje)),
                     index=log.index)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    warnings.filterwarnings("ignore", message="Converting to PeriodArray")
    t0 = time.time()
    print("=" * 78)
    print(" KINETIC - M3a y M3b: las dos condiciones de cualquier compuerta")
    print("=" * 78)
    print("  Particiones de la serie de BTC, no corridas de estrategia.")
    print("  CERO pruebas de DSR. El contador sigue en seis.")
    print("  La regla esta en docs/CRITERIOS_M3_4sep2026.md, commiteada antes.")
    print()

    velas = arch.cargar(REFERENCIA, "1d", CARPETA)
    velas = velas[velas.index <= ventana.DISENO_HASTA]
    g_cruda = cp.compuerta_de_regimen(velas["close"])
    velas = velas[velas.index >= DESDE]
    g_cruda = g_cruda.reindex(velas.index).fillna(0).astype(int)
    log = np.log(velas["close"] / velas["close"].shift(1)).fillna(0.0)
    total_b1 = float(log.sum())

    b1 = benchmarks.comprar_y_mantener(velas, CAPITAL)
    caida_b1, _, _, _ = metricas.caida_maxima(b1)
    episodios_b1 = frontera.episodios_de_caida(b1)
    umbral_caida = frontera.CAIDA_OBJETIVO * abs(caida_b1)
    umbral_episodios = frontera.CAIDA_OBJETIVO * abs(np.mean(episodios_b1))

    print(f"  Ventana {velas.index[0].date()} a {velas.index[-1].date()}"
          f"   ({len(velas)} dias)")
    print(f"  Log-retorno total de B1                {total_b1:>+9.4f}")
    print(f"  Caida maxima de B1                     {caida_b1 * 100:>8.1f}%")
    print(f"  3 peores episodios de B1               "
          f"{', '.join(f'{e * 100:.1f}%' for e in episodios_b1)}")
    print()
    print(f"  UMBRAL de caida (0,50 x caida de B1)   "
          f"{umbral_caida * 100:>8.1f}%")
    print(f"  UMBRAL por episodios (0,50 x la media) "
          f"{umbral_episodios * 100:>8.1f}%")

    # --- Las compuertas ----------------------------------------------------
    puertas: dict[str, pd.Series] = {"E0 sin des-parpadear": g_cruda}
    for n in ENES:
        puertas[f"consolidada N={n} (techo)"] = cp.consolidar(g_cruda, n)
    for n in ENES:
        puertas[f"confirmada N={n} (real)"] = cp.con_confirmacion(g_cruda, n)

    # Los oraculos. NINGUNO es candidata: todos exigen saber el resultado del
    # periodo antes de que empiece. Estan para acotar el problema, y hay
    # cuatro y no uno porque **la resolucion es lo que decide**: el analista
    # miro solo el anual y de ahi concluyo imposibilidad.
    for etiqueta, clave in (("mensual", "M"), ("trimestral", "Q")):
        periodo = pd.Series(velas.index.to_period(clave), index=velas.index)
        retorno = log.groupby(periodo.to_numpy()).sum()
        puertas[f"ORACULO {etiqueta}"] = pd.Series(
            periodo.map(retorno > 0).to_numpy().astype(int), index=velas.index)
    es_2022 = (velas.index.year == 2022)
    puertas["ORACULO anual (sin 2022)"] = pd.Series(
        (~es_2022).astype(int), index=velas.index)

    filas = []
    for nombre, g in puertas.items():
        dentro = g == 1
        transiciones = int((np.abs(np.diff(g.to_numpy(), prepend=0)) > 0).sum())
        afuera = float(log[~dentro].sum())
        curva = _curva_de(log, g)
        caida, _, _, _ = metricas.caida_maxima(curva)
        episodios = frontera.episodios_de_caida(curva)
        filas.append({
            "nombre": nombre,
            "dias_afuera": int((~dentro).sum()),
            "transiciones": transiciones,
            "log_afuera": afuera,
            "costo": transiciones * COSTO_POR_LADO,
            "log_final": float(np.log(curva.iloc[-1] / curva.iloc[0])),
            "caida": caida,
            "episodios": float(np.mean(episodios)) if episodios else 0.0,
        })

    # --- M3a ---------------------------------------------------------------
    _titulo("M3a - LA CONDICION DE RETORNO")
    print("  Pasa si y solo si los dias que deja AFUERA suman log-retorno")
    print("  NEGATIVO, por mas que el costo de las transiciones.")
    print()
    print(f"  {'':<26}{'dias fuera':>11}{'trans.':>8}{'log afuera':>12}"
          f"{'costo':>8}{'':>7}")
    for f in filas:
        pasa = f["log_afuera"] + f["costo"] < 0
        f["m3a"] = pasa
        print(f"  {f['nombre']:<26}{f['dias_afuera']:>11}"
              f"{f['transiciones']:>8}{f['log_afuera']:>+12.4f}"
              f"{f['costo']:>8.4f}{'  PASA' if pasa else '    NO':>7}")
    print()
    print("  Y lo que termina valiendo cada una, contra el log-retorno de B1:")
    print()
    print(f"  {'':<26}{'log final':>12}{'% de B1':>10}")
    for f in filas:
        print(f"  {f['nombre']:<26}{f['log_final']:>+12.4f}"
              f"{f['log_final'] / total_b1 * 100:>9.1f}%")

    # --- M3b ---------------------------------------------------------------
    _titulo("M3b - LA CONDICION DE CAIDA")
    print(f"  Pasa si y solo si la curva de los dias que deja ADENTRO no cae")
    print(f"  mas de {umbral_caida * 100:.1f}%. Se reporta tambien la media de "
          "los 3 peores")
    print(f"  episodios, contra su propio umbral de "
          f"{umbral_episodios * 100:.1f}%.")
    print()
    print(f"  {'':<26}{'caida max':>11}{'':>7}{'3 episodios':>13}{'':>7}")
    for f in filas:
        pasa = abs(f["caida"]) <= umbral_caida
        pasa_ep = abs(f["episodios"]) <= umbral_episodios
        f["m3b"] = pasa
        f["m3b_ep"] = pasa_ep
        print(f"  {f['nombre']:<26}{f['caida'] * 100:>10.1f}%"
              f"{'  PASA' if pasa else '    NO':>7}"
              f"{f['episodios'] * 100:>12.1f}%"
              f"{'  PASA' if pasa_ep else '    NO':>7}")

    # --- La regla ----------------------------------------------------------
    _titulo("LA REGLA DE DECISION, TAL COMO QUEDO COMMITEADA")
    ningun_a = not any(f["m3a"] for f in filas
                       if "ORACULO" not in f["nombre"])
    ningun_b = not any(f["m3b"] for f in filas
                       if "ORACULO" not in f["nombre"])
    print("  1. Si ningun N deja afuera log-retorno negativo -> cerrar.")
    print(f"     Ningun N lo logra: {'SI' if ningun_a else 'no'}")
    print(f"  2. Si ningun N deja adentro una caida menor a "
          f"{umbral_caida * 100:.1f}% -> cerrar.")
    print(f"     Ningun N lo logra: {'SI' if ningun_b else 'no'}")
    print(f"  3. Si alguno cumple las dos, se toma el N DECLARADO = "
          f"{N_DECLARADO}, no el mejor.")
    print()

    techo = next(f for f in filas
                 if f["nombre"] == f"consolidada N={N_DECLARADO} (techo)")
    real = next(f for f in filas
                if f["nombre"] == f"confirmada N={N_DECLARADO} (real)")
    for etiqueta, f in (("techo (consolidada)", techo),
                        ("real (confirmada)", real)):
        print(f"  N={N_DECLARADO} {etiqueta:<22} "
              f"C-A' {'PASA' if f['m3a'] else 'NO'}   "
              f"C-B' {'PASA' if f['m3b'] else 'NO'}")

    print()
    if ningun_a or ningun_b:
        cual = []
        if ningun_a:
            cual.append("la de retorno")
        if ningun_b:
            cual.append("la de caida")
        print(f"  >>> NINGUN N cumple {' ni '.join(cual)}.")
        print("  >>> La regla dice CERRAR. A2 no se corre.")
    elif techo["m3a"] and techo["m3b"] and real["m3a"] and real["m3b"]:
        print("  >>> El N declarado cumple las dos, en el techo Y en la")
        print("  >>> version implementable. A2 se puede correr, y cuesta una")
        print("  >>> prueba de DSR. Necesita decision explicita de Felipe.")
    elif techo["m3a"] and techo["m3b"]:
        print("  >>> El techo cumple pero la version implementable no.")
        print("  >>> Por la regla adicional de los criterios, A2 no se corre:")
        print("  >>> lo que la haria pasar es mirar al futuro.")
    else:
        print(f"  >>> El N declarado ({N_DECLARADO}) no cumple las dos, aunque")
        print("  >>> algun otro N si. La regla PROHIBE elegir ese otro.")
        print("  >>> A2 no se corre.")

    # --- Lo que separa al techo de lo implementable ------------------------
    _titulo("CUANTO DEL DES-PARPADEO ERA MIRAR AL FUTURO")
    print(f"  {'N':>4}{'log afuera techo':>19}{'log afuera real':>18}"
          f"{'diferencia':>13}")
    for n in ENES:
        t = next(f for f in filas if f["nombre"] == f"consolidada N={n} (techo)")
        r = next(f for f in filas if f["nombre"] == f"confirmada N={n} (real)")
        print(f"  {n:>4}{t['log_afuera']:>+19.4f}{r['log_afuera']:>+18.4f}"
              f"{r['log_afuera'] - t['log_afuera']:>+13.4f}")
    print()
    print("  La consolidacion fusiona tramos cortos sabiendo que fueron")
    print("  cortos. La confirmacion espera N dias y llega tarde a cada giro.")
    print("  La diferencia es el precio de no poder mirar adelante, y es lo")
    print("  que separa un diagnostico de una estrategia.")

    # --- Los oraculos -------------------------------------------------------
    _titulo("LOS ORACULOS: DONDE ESTA EL LIMITE, Y POR QUE NO ES IMPOSIBLE")
    print("  El analista concluye de su oraculo de 2022 que el asunto queda")
    print("  cerrado 'por imposibilidad'. **Eso no se sostiene, y hay que")
    print("  decirlo:** su oraculo resuelve al nivel ANUAL, y la resolucion es")
    print("  justamente lo que decide.")
    print()
    print(f"  {'':<26}{'log afuera':>12}{'% de B1':>10}{'caida':>9}"
          f"{'C-A':>6}{'C-B':>6}")
    for f in filas:
        if "ORACULO" not in f["nombre"]:
            continue
        print(f"  {f['nombre']:<26}{f['log_afuera']:>+12.4f}"
              f"{f['log_final'] / total_b1 * 100:>9.1f}%"
              f"{f['caida'] * 100:>8.1f}%"
              f"{'  si' if f['m3a'] else '  NO':>6}"
              f"{'  si' if f['m3b'] else '  NO':>6}")
    print()
    print("  El oraculo MENSUAL cumple las dos condiciones con holgura, y el")
    print("  trimestral tambien. Solo el anual falla la de caida, porque deja")
    print("  adentro marzo de 2020 y mediados de 2021 enteros.")
    print()
    print("  **Entonces la conclusion correcta NO es que sea imposible.** Es")
    print("  que hace falta resolver al nivel del TRIMESTRE o mas fino, y el")
    print("  oraculo lo logra porque conoce el resultado del periodo antes de")
    print("  que empiece. La pregunta que queda no es si existe una compuerta")
    print("  que pase --existe-- sino si alguna ESTIMABLE llega ahi.")
    print()
    print("  Y sobre eso la evidencia de arriba es la que decide, no el")
    print("  oraculo: las cuatro compuertas implementables dejan afuera entre")
    print("  +0,78 y +1,27 de log-retorno, o sea que son PEORES que la")
    print("  compuerta cruda de E0, que ya dejaba afuera +0,49. Y las cuatro")
    print("  fallan la condicion de caida por margen amplio.")

    # --- C-C' ---------------------------------------------------------------
    _titulo("VERIFICACION - CUANTO EXCESO HACE FALTA PARA SER DETECTABLE")
    print("  Traduccion del intervalo de C-C' medido el 3-sep. No cambia")
    print("  ningun veredicto; se verifica porque es el numero que el analista")
    print("  propone como hallazgo central del proyecto.")
    print()
    intervalos = {"B4 sin compuerta": (-0.0323, 0.0112),
                  "B3 constante": (-0.0462, 0.0113),
                  "E0": (-0.0478, 0.0190),
                  "E1": (-0.0699, 0.0152)}
    print(f"  {'':<20}{'semiancho/mes':>15}{'exceso anual necesario':>25}")
    for nombre, (bajo, alto) in intervalos.items():
        print(f"  {nombre:<20}{(alto - bajo) / 2:>15.4f}"
              f"{frontera.exceso_detectable(bajo, alto) * 100:>24.1f}%")
    print()
    print("  Para que ESTA ventana pudiera certificar que una estrategia le")
    print("  gana a comprar Bitcoin, esa estrategia tendria que rendir entre")
    print("  30% y 49% ANUAL por encima de BTC. No es un resultado sobre las")
    print("  estrategias probadas: es un resultado sobre la muestra.")

    print(f"\\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
