r"""
Medicion 5.1 -- distribucion de las tasas de financiacion, y la falsacion de E3.

LO QUE DECIDE
--------------
Es la ultima de las cinco mediciones previas y la unica que puede **cerrar una
estrategia sin escribirla**. De la especificacion 6.4:

    Falsacion previa a codificar: si la mediana de la financiacion anualizada
    neta de comisiones no supera con margen el costo de montar la estructura,
    E3 no se codifica. Se anota el numero y se cierra.

Ademas contesta si la pata larga de E2 conviene en Spot o en perpetuo.

LAS TRES CUENTAS QUE HAY QUE HACER BIEN
-----------------------------------------
1. **Anualizar con el intervalo de cada simbolo**, no con la constante de 8
   horas. Binance paso varios a 4 horas y el archivo trae la columna.
2. **El costo de la estructura son CUATRO comisiones**: dos patas, entrada y
   salida. No dos.
3. **El capital se ocupa en las dos patas.** Con 500 USDT y sin
   apalancamiento, el nocional de cada pata es ~250, asi que un carry del X%
   sobre nocional rinde **la mitad** sobre el capital. La especificacion pide
   explicitamente calcular esto antes de codificar.

Y una cuarta, que la especificacion pide mirar aparte: **la compresion del
rendimiento**. Es un trade conocido y ocupado; el promedio historico puede
esconder que hace años que no paga. Por eso va el desglose por año.

Se corre asi:

    venv\Scripts\python.exe tools\medicion_51.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from core import financiacion as fin  # noqa: E402
from core import universo as uni  # noqa: E402
from execution.costos import ModeloDeCostos, TipoOrden, Venue  # noqa: E402
from metrics import ventana  # noqa: E402
from risk import compuerta as cp  # noqa: E402

CARPETA_VELAS = RAIZ / "data" / "archivo"
CARPETA_FIN = RAIZ / "data" / "financiacion"
CAPITAL = 500.0
RANGO = 1          # la estructura solo tiene sentido en los mas liquidos


def _costo_de_la_estructura(con_bnb: bool) -> float:
    """
    Montar y desmontar: cuatro comisiones mas cuatro slippages.

    Larga en Spot (entrada y salida) + corta en perpetuo (entrada y salida).
    """
    spot = ModeloDeCostos(Venue.SPOT, TipoOrden.TAKER, con_bnb)
    perp = ModeloDeCostos(Venue.PERPETUO_USDT_M, TipoOrden.TAKER, con_bnb)
    return (spot.peaje_ida_y_vuelta_pct(RANGO)
            + perp.peaje_ida_y_vuelta_pct(RANGO))


def _episodios_por_anio(series: dict[str, pd.DataFrame],
                        umbral: float) -> float:
    """
    Cuantas veces por año habria que montar la estructura con ese umbral.

    Se cuenta sobre BTCUSDT solo: mezclar simbolos contaria como "entrada"
    cada salto de uno a otro, que no es una operacion.
    """
    if "BTCUSDT" not in series:
        return 0.0
    anual = fin.anualizar(series["BTCUSDT"])
    dentro = (anual >= umbral).astype(int)
    entradas = int((dentro.diff().fillna(dentro.iloc[0]) == 1).sum())
    anios = (anual.index[-1] - anual.index[0]).days / 365.0
    return entradas / anios if anios > 0 else 0.0


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - medicion 5.1: tasas de financiacion de los perpetuos")
    print("=" * 76)
    print(f"  Ventana de diseño: {ventana.DISENO_DESDE.date()} a "
          f"{ventana.DISENO_HASTA.date()}")
    print()

    archivos = sorted(CARPETA_FIN.glob("*.csv"))
    if not archivos:
        print("  No hay datos. Corre antes tools/descargar_financiacion.py")
        return 1

    series: dict[str, pd.DataFrame] = {}
    for ruta in archivos:
        df = fin.cargar(ruta.stem, CARPETA_FIN)
        df = df[(df.index >= ventana.DISENO_DESDE)
                & (df.index <= ventana.DISENO_HASTA)]
        if len(df) >= 100:
            series[ruta.stem] = df
    print(f"  {len(series)} simbolos con al menos 100 cobros en la ventana")

    inicios = pd.Series({s: d.index[0] for s, d in series.items()})
    print(f"  El perpetuo mas viejo arranca {inicios.min().date()}; "
          f"la mediana arranca {inicios.median().date()}")
    print("  OJO: la muestra de perpetuos es MAS CORTA que la de Spot. Todo")
    print("  resultado de E2 y E3 se lee sobre esta ventana, no sobre 2019-2024.")

    # --- Intervalos --------------------------------------------------------
    intervalos: dict[float, int] = {}
    for d in series.values():
        for h in d["horas"].unique():
            intervalos[float(h)] = intervalos.get(float(h), 0) + 1
    print()
    print("  Intervalos de cobro presentes:")
    for h, cuantos in sorted(intervalos.items()):
        print(f"    cada {h:>4.0f} h   en {cuantos} simbolos")
    print("  Por eso se anualiza con el intervalo de cada fila y no con 3x365.")

    # --- Distribucion ------------------------------------------------------
    resumenes = {s: fin.resumen(d) for s, d in series.items()}
    tabla = pd.DataFrame(resumenes).T
    todas = pd.concat([fin.anualizar(d) for d in series.values()])

    print()
    print("=" * 76)
    print(" DISTRIBUCION DE LA FINANCIACION ANUALIZADA")
    print("=" * 76)
    print(f"  Sobre {len(todas):,} cobros de {len(series)} simbolos:")
    print(f"    mediana {todas.median() * 100:>7.2f}%    "
          f"media {todas.mean() * 100:>7.2f}%")
    print(f"    p10 {todas.quantile(0.10) * 100:>7.2f}%    "
          f"p90 {todas.quantile(0.90) * 100:>7.2f}%")
    print(f"    fraccion de cobros con tasa positiva: "
          f"{(todas > 0).mean() * 100:.1f}%")
    print()
    print(f"  Mediana POR SIMBOLO (la que importa para E3): "
          f"{tabla['mediana'].median() * 100:.2f}%")
    print(f"    el mejor simbolo {tabla['mediana'].max() * 100:.2f}%, "
          f"el peor {tabla['mediana'].min() * 100:.2f}%")
    print(f"    simbolos con mediana positiva: "
          f"{(tabla['mediana'] > 0).sum()} de {len(tabla)}")

    # --- Alcista contra bajista -------------------------------------------
    panel = uni.cargar_panel(CARPETA_VELAS)
    g = cp.compuerta_de_regimen(panel.cierres["BTCUSDT"].dropna())
    g_diario = g.reindex(pd.date_range(g.index[0], g.index[-1], freq="D",
                                       tz="UTC")).ffill()

    def regimen_de(indice: pd.DatetimeIndex) -> pd.Series:
        return g_diario.reindex(indice.floor("D")).to_numpy()

    alcista, bajista = [], []
    for d in series.values():
        anual = fin.anualizar(d)
        marca = regimen_de(d.index)
        alcista.append(anual[marca == 1])
        bajista.append(anual[marca == 0])
    alcista = pd.concat(alcista)
    bajista = pd.concat(bajista)

    print()
    print("=" * 76)
    print(" TRAMOS ALCISTAS CONTRA BAJISTAS")
    print("=" * 76)
    print("  Marcados con la misma compuerta de E0: BTC sobre su media de 200.")
    print(f"    ALCISTA  mediana {alcista.median() * 100:>7.2f}%   "
          f"positiva {(alcista > 0).mean() * 100:.0f}% del tiempo   "
          f"({len(alcista):,} cobros)")
    print(f"    BAJISTA  mediana {bajista.median() * 100:>7.2f}%   "
          f"positiva {(bajista > 0).mean() * 100:.0f}% del tiempo   "
          f"({len(bajista):,} cobros)")
    print()
    print("  Si el carry solo paga en los tramos alcistas, entonces NO es")
    print("  no direccional: es una apuesta al mercado con otro nombre.")

    # --- Compresion --------------------------------------------------------
    print()
    print("=" * 76)
    print(" ¿SE ESTA COMPRIMIENDO? (la especificacion pide mirarlo aparte)")
    print("=" * 76)
    print("    año     mediana anual   % positiva   cobros")
    for anio, bloque in todas.groupby(todas.index.year):
        print(f"    {anio}      {bloque.median() * 100:>7.2f}%        "
              f"{(bloque > 0).mean() * 100:>5.0f}%    {len(bloque):>7,}")

    # --- La mediana es un mal resumen, y hay que decir por que -------------
    exacta_base = float((todas.round(6) == round(0.0001 * 3 * 365, 6)).mean())
    print()
    print("=" * 76)
    print(" POR QUE LA MEDIANA DA 10,95% EN TODOS LADOS")
    print("=" * 76)
    print(f"  Porque {exacta_base * 100:.0f}% de los cobros vale exactamente la tasa")
    print("  base de Binance (0,01% por cobro). No es un error de calculo: es")
    print("  el piso del mercado asomando por la mediana.")
    print()
    print("  Consecuencia: la mediana SUBESTIMA lo que puede ganar E3, que por")
    print("  diseño entra solo cuando la financiacion esta alta. La cola es")
    print("  donde esta el dinero:")
    for q in (0.50, 0.75, 0.90, 0.95, 0.99):
        print(f"    p{q * 100:>4.0f}   {todas.quantile(q) * 100:>8.2f}% anual")

    print()
    print("  CURVA POR UMBRAL DE ENTRADA. El umbral es un PARAMETRO de E3 y se")
    print("  cuenta como tal: aca se reporta la curva entera, no se elige uno.")
    print()
    print("  OJO con leer la columna equivocada: 'mientras esta dentro' NO es")
    print("  el retorno anual. Si entras el 8% del tiempo a una tasa del 112%,")
    print("  ganas el 8% de eso, no el 112%. La columna que decide es la ultima.")
    print()
    print("    umbral   % del tiempo   mientras dentro   sobre capital"
          "   montajes/año   AL AÑO neto")
    costo_estructura = _costo_de_la_estructura(True) / 100.0
    for umbral in (0.0, 0.11, 0.20, 0.30, 0.50, 1.00):
        dentro = todas >= umbral
        arriba = todas[dentro]
        if arriba.empty:
            continue
        fraccion = float(dentro.mean())
        sobre_capital = arriba.mean() / 2.0
        ponderado = sobre_capital * fraccion
        # Cada tramo contiguo por encima del umbral es un montaje y un
        # desmontaje. Se cuentan sobre la serie de un solo simbolo grande para
        # no mezclar los saltos entre simbolos.
        montajes = _episodios_por_anio(series, umbral)
        neto = ponderado - costo_estructura * montajes
        print(f"    {umbral * 100:>5.0f}%   {fraccion * 100:>9.1f}%"
              f"   {arriba.mean() * 100:>13.2f}%   {sobre_capital * 100:>10.2f}%"
              f"   {montajes:>11.0f}   {neto * 100:>11.2f}%")
    print()
    print("  Apretar el umbral SUBE la tasa y BAJA el tiempo adentro, y las dos")
    print("  cosas casi se cancelan -- mientras el costo de montar y desmontar")
    print("  crece con cada entrada. El filtro no rescata a E3.")
    print()
    print("  ADVERTENCIA sobre esa ultima columna: cuenta un montaje cada vez")
    print("  que la tasa cruza el umbral, incluso por un solo cobro de 8 horas.")
    print("  Una implementacion real pondria histeresis o un minimo de dias, y")
    print("  montaria muchas menos veces. O sea que es una COTA PESIMISTA de la")
    print("  version ingenua, no el veredicto de E3. El veredicto es el de")
    print("  abajo, sobre la estructura sostenida sin filtro.")

    # --- LA FALSACION DE E3 ------------------------------------------------
    print()
    print("=" * 76)
    print(" FALSACION DE E3 (especificacion 6.4)")
    print("=" * 76)
    for etiqueta, con_bnb in (("con descuento BNB", True),
                              ("sin descuento", False)):
        costo = _costo_de_la_estructura(con_bnb)
        print(f"\n  Costo de montar y desmontar la estructura, {etiqueta}:")
        print(f"    cuatro comisiones + cuatro slippages = {costo:.3f}% "
              f"del nocional")

        bruto = float(tabla["mediana"].median())
        # El capital se ocupa en las DOS patas: con 500 USDT sin
        # apalancamiento, cada pata mueve ~250 de nocional.
        sobre_capital = bruto / 2.0
        print(f"    Carry mediano sobre NOCIONAL:  {bruto * 100:>7.2f}% anual")
        print(f"    Carry mediano sobre CAPITAL:   {sobre_capital * 100:>7.2f}% "
              f"anual  <- las dos patas ocupan capital")

        if bruto > 0:
            dias_para_cubrir = (costo / 100.0) / (bruto / 365.0)
            print(f"    Dias de posicion para cubrir un ciclo de costo: "
                  f"{dias_para_cubrir:.1f}")
        for meses in (1, 3, 12):
            ciclos = 12.0 / meses
            neto = sobre_capital - (costo / 100.0) * ciclos
            print(f"    Neto sobre capital rotando cada {meses:>2} mes(es): "
                  f"{neto * 100:>7.2f}% anual")

    costo = _costo_de_la_estructura(True)
    bruto = float(tabla["mediana"].median())
    neto_anual = bruto / 2.0 - (costo / 100.0)      # una sola vuelta al año
    print()
    print(f"  En el escenario MAS FAVORABLE que se puede armar -- montar una")
    print(f"  vez al año y no tocar -- E3 rinde {neto_anual * 100:.2f}% anual")
    print(f"  sobre {CAPITAL:.0f} USDT, o sea {neto_anual * CAPITAL:.2f} USDT.")

    print()
    print("  Referencias para dimensionar:")
    print(f"    E0 rindio 37,23% anual   B1 rindio 70,55% anual")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
