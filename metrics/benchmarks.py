"""
Los benchmarks contra los que se mide todo, desde la Fase 2.

LA AUSENCIA MAS GRAVE DE LA FASE 1
-----------------------------------
La Fase 1 midio contra dos referencias internas: no elegir parametro, y el
mejor parametro en retrospectiva. **Nunca midio contra comprar el activo y no
hacer nada.** En un mercado direccional al alza y con estrategia mayormente
larga, el competidor real no es cero -- es el activo. Aquel "+2,6% en seis
años" no fue una ventaja que no alcanzo: frente a comprar y esperar fue
destruccion de valor de dos ordenes de magnitud, y el informe no lo decia
porque nadie habia hecho la cuenta.

LOS TRES
--------
- **B1** — comprar y mantener BTCUSDT Spot. Un solo costo de entrada. Es el
  primario, y es contra el que se evaluan los criterios 1 y 2.
- **B2** — canasta de los 10 mas liquidos, equiponderada, rebalanceo mensual,
  universo sin sesgo de supervivencia, costos completos.
- **B0** — la estrategia E0 (BTC + SMA200 + volatilidad objetivo). La linea
  base barata: si nada la supera, se implementa E0 y se cierra la
  investigacion.

**Hoy solo esta B1.** B2 necesita el universo reconstruido desde el archivo,
que es la etapa 0 y todavia no existe; B0 necesita E0 escrita. Los dos entran
aca cuando esten, con la misma firma: reciben datos y devuelven una curva de
patrimonio diaria, que es lo unico que `metricas.calcular` sabe leer.

POR QUE B1 NO PAGA COSTO DE SALIDA
-----------------------------------
Porque no sale. Comprar y mantener es exactamente eso: se paga una vez al
entrar y despues nada. Cobrarle una salida seria inventarle un costo que el
inversor pasivo no tiene, y con eso hacerle mas facil el examen a la
estrategia. El benchmark tiene que ser el rival mas duro posible, no el mas
comodo de vencer.
"""

from __future__ import annotations

import pandas as pd

from metrics import ventana

# Costo de entrada de B1, de la especificacion seccion 3.1: comision con
# descuento por BNB mas slippage. Una sola vez.
COSTO_ENTRADA_PCT = 0.075 + 0.05


def comprar_y_mantener(
    velas: pd.DataFrame,
    capital_inicial: float,
    *,
    costo_entrada_pct: float = COSTO_ENTRADA_PCT,
    columna: str = "close",
    nombre: str = "B1 comprar y mantener",
    permitir_holdout: bool = False,
) -> pd.Series:
    """
    Curva de patrimonio de comprar el primer dia y no tocar nada mas.

    Se compra al CIERRE del primer dia de la ventana, no a la apertura: es la
    misma convencion conservadora que usa el motor de backtest, y evita
    regalarle al benchmark un dia de ventaja que la estrategia no tiene.
    """
    ventana.verificar(velas, permitir_holdout=permitir_holdout, contexto=nombre)

    precios = velas[columna].dropna()
    if len(precios) < 2:
        raise ValueError(
            f"{nombre}: hacen falta al menos dos velas y hay {len(precios)}."
        )

    invertido = capital_inicial * (1.0 - costo_entrada_pct / 100.0)
    curva = invertido * (precios / float(precios.iloc[0]))
    curva.name = nombre
    return curva


def b1(
    velas_btc: pd.DataFrame,
    capital_inicial: float,
    *,
    permitir_holdout: bool = False,
) -> pd.Series:
    """B1: el benchmark primario. Comprar BTCUSDT y no hacer nada."""
    return comprar_y_mantener(
        velas_btc,
        capital_inicial,
        nombre="B1 comprar y mantener BTCUSDT",
        permitir_holdout=permitir_holdout,
    )
