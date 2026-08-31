r"""
E0 -- la corrida de la linea base, contra B1 y contra sus propios criterios.

LO QUE SE DECIDE ACA
---------------------
E0 no compite por ser la estrategia elegida: **es la vara**. Su falsacion, de
la especificacion 6.1:

    Si E0 no alcanza Calmar >= 1,3 x Calmar(B1), la compuerta de regimen no
    funciona en este mercado, y E1 y E2 -- que dependen de la misma compuerta
    -- quedan muy debilitadas antes de probarse.

Eso seria un hallazgo mayor, y hay que anotarlo aunque duela.

DOS DECISIONES DE FELIPE, 30-ago-2026, TOMADAS ANTES DE VER UN RESULTADO
--------------------------------------------------------------------------
1. **Rebalanceo diario.** La especificacion no fijaba cada cuanto se vuelve a
   la exposicion objetivo. Se eligio la lectura literal y la mas cara.
2. **Comision con descuento por BNB (0,075%)** como resultado principal,
   porque es lo que la especificacion fijo y es lo mismo que paga B1 -- asi la
   comparacion es pareja. La sensibilidad sin descuento se reporta al lado.

EL CALMAR SE COMPARA POR PARES, NO CONTRA UN NUMERO FIJO
----------------------------------------------------------
Calmar(B1) va de 0,439 a 0,973 segun el mes en que arranque la ventana. Un
umbral atado a un solo arranque mide en parte la estrategia y en parte el
calendario. Se usa el metodo ya acordado para el criterio 1 -- mediana del
cociente sobre 20 arranques -- con el umbral 1,3 que la especificacion le puso
a E0. Cambia el metodo de medicion, no la vara.

LA VENTANA ANTES DE 2019 SE USA SOLO PARA CALENTAR LOS INDICADORES
--------------------------------------------------------------------
La SMA de 200 dias necesita 200 dias. Si se los sacara de adentro de la
ventana de diseño, E0 empezaria a operar en julio de 2019 mientras B1 compra
el 1 de enero, y la comparacion seria injusta contra E0. Se usan los datos de
2017-2018 para el calentamiento y **se simula solo desde 2019-01-01**.

Se corre asi:

    venv\Scripts\python.exe tools\correr_e0.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from backtesting import motor_cartera as mc  # noqa: E402
from core import archivo_binance as arch  # noqa: E402
from execution.costos import ModeloDeCostos, TipoOrden, Venue  # noqa: E402
from execution.filtros import TablaDeFiltros  # noqa: E402
from metrics import benchmarks, metricas, robustez, ventana  # noqa: E402
from strategy import e0  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
FILTROS = RAIZ / "data" / "filtros_spot.json"
CAPITAL = 500.0                      # config.yaml, confirmado por Felipe
RANGO_BTC = 1                        # el mas liquido: slippage 0,03% por lado
UMBRAL_FALSACION = 1.3               # especificacion 6.1


def _modelo(con_bnb: bool) -> ModeloDeCostos:
    return ModeloDeCostos(venue=Venue.SPOT, tipo_orden=TipoOrden.TAKER,
                          con_bnb=con_bnb)


def _correr(datos: pd.DataFrame, modelo: ModeloDeCostos,
            filtros: TablaDeFiltros | None) -> mc.ResultadoCartera:
    aperturas = datos[["open"]].rename(columns={"open": e0.SIMBOLO})
    cierres = datos[["close"]].rename(columns={"close": e0.SIMBOLO})
    exposiciones = datos[["exposicion"]].rename(
        columns={"exposicion": e0.SIMBOLO})
    return mc.simular(aperturas, cierres, exposiciones, CAPITAL, modelo,
                      rangos={e0.SIMBOLO: RANGO_BTC}, filtros=filtros)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    t0 = time.time()
    print("=" * 76)
    print(" KINETIC - E0: BTC con compuerta de tendencia y volatilidad objetivo")
    print("=" * 76)
    print(f"  Capital {CAPITAL:.0f} USDT   ventana de diseño "
          f"{ventana.DISENO_DESDE.date()} a {ventana.DISENO_HASTA.date()}")
    print("  Rebalanceo diario. Comision 0,075% (con BNB) + slippage 0,03%.")
    print()

    velas = arch.cargar(e0.SIMBOLO, "1d", CARPETA)
    velas = velas[velas.index <= ventana.DISENO_HASTA]
    ventana.verificar(velas, contexto="velas de E0")
    print(f"  {len(velas):,} velas diarias desde {velas.index[0].date()}")

    # Calentamiento con 2017-2018; la simulacion arranca en 2019.
    exposicion = e0.exposicion_objetivo(velas["close"])
    datos = velas.assign(exposicion=exposicion)
    datos = datos[datos.index >= ventana.DISENO_DESDE]
    print(f"  {len(datos):,} dias simulados desde {datos.index[0].date()}")

    filtros = (TablaDeFiltros.desde_json(FILTROS) if FILTROS.exists()
               else None)
    if filtros is None:
        print("  AVISO: sin data/filtros_spot.json, no se aplica stepSize.")

    # --- La corrida principal --------------------------------------------
    r = _correr(datos, _modelo(True), filtros)
    m_e0 = metricas.calcular(r.patrimonio, "E0", exposicion=r.exposicion.sum(axis=1),
                             rotacion_anual=r.rotacion_anual,
                             costo_anual_pct=r.costo_anual_pct)
    patrimonio_b1 = benchmarks.comprar_y_mantener(datos, CAPITAL)
    m_b1 = metricas.calcular(patrimonio_b1, "B1 comprar y mantener")

    print()
    print("=" * 76)
    print(" RESULTADO")
    print("=" * 76)
    print(m_e0.informe())
    print()
    print(m_b1.informe())

    print()
    print(f"  Ordenes rechazadas por el minimo de 5 USDT: {r.ordenes_rechazadas:,}")
    print(f"  Dias con operacion: {(r.negociado > 0).sum():,} de {len(r.negociado):,}")
    print(f"  Costo total pagado: {r.costo_total:.2f} USDT")

    # --- La falsacion, comparada por pares --------------------------------
    print()
    print("=" * 76)
    print(" LA FALSACION DE E0 (especificacion 6.1)")
    print("=" * 76)
    comparacion = robustez.comparar_por_pares(
        datos,
        lambda tramo: _correr(tramo, _modelo(True), filtros).patrimonio,
        lambda tramo: benchmarks.comprar_y_mantener(tramo, CAPITAL),
    )
    print(comparacion.informe(umbral=UMBRAL_FALSACION)
          if hasattr(comparacion, "informe") else "")
    mediana = comparacion.mediana
    print(f"  Arranques usados: {len(comparacion.cocientes)}")
    print(f"  Calmar(E0)/Calmar(B1), mediana: {mediana:.3f}   "
          f"minimo {min(comparacion.cocientes):.3f}   "
          f"maximo {max(comparacion.cocientes):.3f}")
    print(f"  Umbral: {UMBRAL_FALSACION}")
    veredicto = "PASA" if mediana >= UMBRAL_FALSACION else "NO PASA"
    print(f"  >>> {veredicto} <<<")

    # --- Los criterios que le corresponden a E0 ---------------------------
    print()
    print("=" * 76)
    print(" CRITERIOS DE LA SECCION 3.3")
    print("=" * 76)
    print("  El criterio 3 (superar a la linea base) NO aplica: E0 ES la")
    print("  linea base. Los demas se evaluan igual, como informacion.")
    print()

    tope_caida = 0.60 * abs(m_b1.caida_maxima)
    c2 = abs(m_e0.caida_maxima) <= tope_caida
    print(f"  2. Caida maxima {abs(m_e0.caida_maxima) * 100:.1f}% "
          f"vs {tope_caida * 100:.1f}% permitido   "
          f"{'PASA' if c2 else 'NO PASA'}")

    ic = robustez.bootstrap_cagr(r.patrimonio)
    c4 = ic.excluye_cero
    print(f"  4. IC 95% del CAGR: [{ic.bajo * 100:+.2f}%, "
          f"{ic.alto * 100:+.2f}%]   "
          f"{'PASA' if c4 else 'NO PASA'} (tiene que excluir cero)")

    curva = robustez.retiro_top_k(r.patrimonio)
    c5 = curva[3] >= 0.50 * m_b1.cagr
    print(f"  5. Sin los 3 mejores meses: CAGR {curva[3] * 100:+.2f}% "
          f"vs {0.50 * m_b1.cagr * 100:+.2f}% exigido   "
          f"{'PASA' if c5 else 'NO PASA'}")

    cagr_bruto = m_e0.cagr + r.costo_anual_pct / 100.0
    c6 = (r.costo_anual_pct / 100.0) <= 0.25 * cagr_bruto if cagr_bruto > 0 else False
    print(f"  6. Costo {r.costo_anual_pct:.2f}% anual vs "
          f"{25 * cagr_bruto:.2f}% permitido (25% del CAGR bruto "
          f"{cagr_bruto * 100:.2f}%)   {'PASA' if c6 else 'NO PASA'}")

    print()
    print(f"  Informacion, no filtro: CAGR(E0)/CAGR(B1) = "
          f"{m_e0.cagr / m_b1.cagr:.3f}" if m_b1.cagr else "")

    # --- El control nulo --------------------------------------------------
    #
    # NO es una estrategia candidata ni una hipotesis nueva: es el control que
    # hace falta para interpretar el resultado. E0 saca la mitad del retorno
    # de B1 con la mitad de la caida, y eso es exactamente lo que daria tener
    # una fraccion fija de BTC y el resto en efectivo, sin ninguna señal.
    #
    # Si el nulo empata con E0, entonces la compuerta y el escalar de
    # volatilidad no estan aportando timing: solo estan achicando la posicion.
    print()
    print("=" * 76)
    print(" CONTROL NULO: LA MISMA EXPOSICION MEDIA, SIN NINGUNA SEÑAL")
    print("=" * 76)
    media = float(r.exposicion.sum(axis=1).mean())
    datos_nulo = datos.assign(exposicion=media)
    nulo = _correr(datos_nulo, _modelo(True), filtros)
    m_nulo = metricas.calcular(nulo.patrimonio, f"Nulo: {media:.0%} de BTC fijo")
    print(f"  E0 estuvo en promedio al {media:.0%} del capital. El nulo tiene")
    print(f"  esa misma exposicion TODOS los dias, sin compuerta y sin")
    print("  volatilidad objetivo. Es lo mas tonto que se puede hacer.")
    print()
    print(m_nulo.informe())
    print()
    print(f"  Calmar E0 {m_e0.calmar:.3f}   vs   nulo dinamico "
          f"{m_nulo.calmar:.3f}   cociente {m_e0.calmar / m_nulo.calmar:.3f}")
    print()
    print("  OJO: este nulo rebalancea a peso fijo todos los dias, y eso en")
    print("  una caida sostenida obliga a COMPRAR mientras baja. Por eso su")
    print("  caida maxima no es menor que la de E0. Es un nulo flojo.")

    # El nulo duro: comprar una vez la misma fraccion y no tocar nunca mas.
    # No rebalancea, asi que no compra en la caida. Es lo mas parecido a "no
    # hacer nada" que existe, y es el rival que de verdad hay que ganarle.
    print()
    print("  EL NULO DURO: comprar esa fraccion UNA vez y no tocar nunca mas.")
    estatico = datos.assign(exposicion=0.0)
    estatico.iloc[0, estatico.columns.get_loc("exposicion")] = media
    # Se compra el primer dia y despues la exposicion objetivo se ignora,
    # porque el motor solo vende si se le pide: se le pide `media` siempre,
    # pero sobre el patrimonio del dia, asi que hay que armarlo distinto.
    patrimonio_estatico = benchmarks.comprar_y_mantener(
        datos, CAPITAL * media) + CAPITAL * (1.0 - media)
    m_estatico = metricas.calcular(
        patrimonio_estatico, f"Nulo duro: {media:.0%} de BTC comprado una vez")
    print()
    print(m_estatico.informe())
    print()
    print(f"  Calmar E0 {m_e0.calmar:.3f}   vs   nulo duro "
          f"{m_estatico.calmar:.3f}   "
          f"cociente {m_e0.calmar / m_estatico.calmar:.3f}")
    if m_e0.calmar < m_estatico.calmar:
        print("  >>> E0 PIERDE contra no hacer nada con la misma exposicion")
        print("      inicial. La compuerta no esta comprando Calmar. <<<")

    # --- Robustez ---------------------------------------------------------
    print()
    print("=" * 76)
    print(" ROBUSTEZ")
    print("=" * 76)
    print(robustez.informe_retiro(r.patrimonio, referencia=m_b1.cagr))
    print()
    dsr = robustez.deflated_sharpe(
        r.patrimonio,
        [metricas.sharpe_por_observacion(r.patrimonio)])
    print(f"  Deflated Sharpe Ratio: {dsr:.3f}  "
          f"(1 configuracion probada hasta ahora)")
    print("  Por debajo de 0,95 no hay evidencia de ventaja descontando")
    print("  el numero de intentos. Va a bajar cuando se prueben E1 y E2.")

    # --- Sensibilidades ---------------------------------------------------
    print()
    print("=" * 76)
    print(" SENSIBILIDADES")
    print("=" * 76)
    sin_bnb = _correr(datos, _modelo(False), filtros)
    m_sin = metricas.calcular(sin_bnb.patrimonio, "E0 sin descuento BNB")
    print(f"  Comision 0,10% (sin verificar el descuento por BNB):")
    print(f"    CAGR {m_sin.cagr * 100:+.2f}%   Calmar {m_sin.calmar:.3f}   "
          f"costo {sin_bnb.costo_anual_pct:.2f}% anual")
    print(f"    Contra el principal: CAGR {m_e0.cagr * 100:+.2f}%   "
          f"Calmar {m_e0.calmar:.3f}   costo {r.costo_anual_pct:.2f}% anual")

    sin_filtros = _correr(datos, _modelo(True), None)
    m_sf = metricas.calcular(sin_filtros.patrimonio, "E0 sin minimo de 5 USDT")
    print()
    print("  Sin el minimo de 5 USDT (o sea, rebalanceando de verdad todos")
    print("  los dias, sin la banda que impone Binance):")
    print(f"    CAGR {m_sf.cagr * 100:+.2f}%   Calmar {m_sf.calmar:.3f}   "
          f"costo {sin_filtros.costo_anual_pct:.2f}% anual   "
          f"rotacion {sin_filtros.rotacion_anual:.1f}x")

    print()
    print("  Por año:")
    print("    año    E0        B1     exposicion media")
    for anio in sorted(set(r.patrimonio.index.year)):
        pe = r.patrimonio[r.patrimonio.index.year == anio]
        pb = patrimonio_b1[patrimonio_b1.index.year == anio]
        ex = r.exposicion.sum(axis=1)
        ex = ex[ex.index.year == anio]
        print(f"    {anio}  {(pe.iloc[-1] / pe.iloc[0] - 1) * 100:>+7.1f}%  "
              f"{(pb.iloc[-1] / pb.iloc[0] - 1) * 100:>+7.1f}%       "
              f"{ex.mean():.2f}")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
