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

LAS DOS QUE SE AGREGARON EL 3-SEP-2026: B3 Y B4
-------------------------------------------------
Las pidio el analista externo en su §7.1 del 2-sep-2026, y son la respuesta a
una pregunta que el proyecto no sabia contestar: **de todo lo que hace E0,
cuanto aporta el DIMENSIONAMIENTO y cuanto la TEMPORIZACION.**

- **B3 -- BTC a exposicion constante rebalanceada**, calibrada al MISMO CAGR
  que la estrategia. Si una estrategia no le gana a B3, todo lo que hace es
  tomar menos posicion, cosa que se consigue sin ninguna señal.
- **B4 -- E0 sin la compuerta**, solo objetivo de volatilidad y siempre
  dentro. La diferencia entre E0 y B4 es lo que aporta la compuerta, aislado.

**Son referencias, no estrategias: no seleccionan nada y no consumen
presupuesto de Deflated Sharpe.** B4 vive como una bandera de
`strategy/e0.py`, no como un archivo aparte, para que sea identico a E0 en
todo lo demas por construccion.

POR QUE B1 NO PAGA COSTO DE SALIDA
-----------------------------------
Porque no sale. Comprar y mantener es exactamente eso: se paga una vez al
entrar y despues nada. Cobrarle una salida seria inventarle un costo que el
inversor pasivo no tiene, y con eso hacerle mas facil el examen a la
estrategia. El benchmark tiene que ser el rival mas duro posible, no el mas
comodo de vencer.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from metrics import metricas, ventana

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


def exposicion_constante(indice: pd.DatetimeIndex,
                         k: float,
                         simbolo: str = "BTCUSDT") -> pd.DataFrame:
    """
    B3: la misma fraccion invertida todos los dias, sin ninguna señal.

    Rebalanceada a diario igual que E0, asi que paga costos de rebalanceo y
    sufre el mismo arrastre de volatilidad. Eso es deliberado: si B3 no pagara
    lo mismo, la comparacion le regalaria a la estrategia una ventaja que no
    viene de la señal.
    """
    return pd.DataFrame({simbolo: float(k)}, index=indice)


def calibrar_exposicion_constante(
    curva_de: Callable[[float], pd.Series],
    cagr_objetivo: float,
    *,
    k_min: float = 0.0,
    k_max: float = 1.0,
    tolerancia: float = 1e-4,
    iteraciones: int = 40,
) -> tuple[float, pd.Series]:
    """
    Busca la exposicion constante que da el mismo CAGR que la estrategia.

    Por biseccion sobre `k`, corriendo la curva completa en cada paso. **No es
    un barrido de parametros**: no se elige `k` porque de un resultado lindo,
    se lo resuelve para igualar un CAGR que ya estaba fijado por la estrategia.
    Es una ecuacion con una incognita, y la respuesta es la que es.

    Se apoya en que el CAGR crece con `k` en el rango util. Con costos y
    arrastre de volatilidad eso deja de valer para `k` grandes, asi que el tope
    por defecto es `K_MAX = 1,0` -- que ademas es el cerrojo del proyecto.
    """
    if not callable(curva_de):
        raise TypeError("curva_de tiene que ser una funcion de k a curva.")
    bajo, alto = float(k_min), float(k_max)
    mejor_k, mejor_curva = alto, curva_de(alto)
    for _ in range(iteraciones):
        medio = (bajo + alto) / 2.0
        curva = curva_de(medio)
        diferencia = metricas.cagr(curva) - cagr_objetivo
        mejor_k, mejor_curva = medio, curva
        if abs(diferencia) <= tolerancia:
            break
        if diferencia < 0:
            bajo = medio
        else:
            alto = medio
    return mejor_k, mejor_curva
