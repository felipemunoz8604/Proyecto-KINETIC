r"""
E2 -- momentum transversal largo-corto, con la pata corta en perpetuos.

QUE CAMBIA RESPECTO DE E1
--------------------------
Es E1 con una pata corta agregada, y con dos cosas que desaparecen:

| | E1 | E2 |
|---|---|---|
| Pata larga | 5 mejores `s_i`, Spot | igual |
| Pata corta | -- | **5 peores `s_i`, perpetuo USDT-M** |
| Compuerta de regimen | diaria | **no se aplica** |
| Financiacion | -- | **cada pocas horas sobre la pata corta** |

La compuerta se saca porque la cartera es aproximadamente neutral al mercado
por construccion: apagarla cuando BTC baja no tendria sentido si justamente lo
que se busca es no depender de BTC.

POR QUE E2 SE CODIFICA AUNQUE E1 HAYA FALLADO
-----------------------------------------------
La especificacion dice: *"solo se codifica si E1 pasa, **o si la medicion 5.2
muestra dispersion transversal alta**"*. E1 fallo, pero 5.2 dio correlacion
media 0,59 -- muy por debajo del corte de 0,80 -- y dispersion mediana del
17,3% a 28 dias. La segunda condicion se cumple, asi que E2 entra.

Conviene entrar con expectativas medidas: E2 usa el **mismo puntaje de
momentum** que en E1 destruyo valor. Lo que aporta de nuevo es la pata corta,
y eso es lo unico que esta a prueba aca.

LA NEUTRALIDAD Y EL APALANCAMIENTO ESCONDIDO
----------------------------------------------
"Nocional bruto igual en ambas patas" con "exposicion bruta total <= 1,0"
significa **0,5 por pata como maximo**. La bruta se mide en valores absolutos:
+0,6 y -0,6 no son exposicion cero, son 1,2 de bruta. El motor levanta si
alguien lo intenta.

LOS PESOS DE LA PATA CORTA NO SE RENORMALIZAN CONTRA LA LARGA
---------------------------------------------------------------
Cada pata reparte por inversa de volatilidad **dentro de si misma**, y despues
se escala a la mitad de `k`. Si una pata se queda con menos de cinco nombres
--- porque un simbolo no tiene perpetuo, o porque salto un stop --- esa pata
queda mas chica y la cartera deja de ser exactamente neutral. **Se deja asi a
proposito**: forzar la neutralidad rellenando con otro nombre seria elegir por
un motivo que no es el puntaje.

QUE NO MODELA, Y HAY QUE SABERLO
----------------------------------
- **Riesgo de liquidacion.** Con bruta <= 1,0 y media pata por lado, el
  colateral cubre de sobra y una liquidacion es practicamente imposible. Por
  eso no se modela margen explicito. Si algun dia `k_max` sube, esto deja de
  ser cierto y hay que rehacerlo.
- **Riesgo de base.** Se usa el precio del perpetuo para la pata corta y el de
  Spot para la larga, que es lo correcto. La base entre los dos queda adentro
  del resultado, no borrada.
- **Cuatro monedas del universo no tienen perpetuo** (BCHABC, ERD, TFUEL,
  WIN): no pueden shortearse y quedan fuera de la pata corta.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from risk import catastrofe as cat
from risk.pesos import (
    DIAS_POR_ANIO,
    K_MAX,
    MINIMO_DE_OBSERVACIONES,
    SIGMA_OBJETIVO,
    TOPE_POR_ACTIVO,
    VENTANA_VOLATILIDAD_DIAS,
    escalar_de_volatilidad,
    pesos_inversa_volatilidad,
)
from strategy.e1 import (
    CUANTAS_POSICIONES,
    puntajes,
    seleccionar,
    sigmas_diarias,
)

# Cada pata se lleva como mucho la mitad de la exposicion bruta.
FRACCION_POR_PATA = 0.5

# La pata corta se nombra con sufijo porque es OTRO INSTRUMENTO.
#
# BTCUSDT en Spot y el perpetuo de BTCUSDT no son la misma cosa: tienen precios
# distintos (esa diferencia es la base) y uno cobra financiacion y el otro no.
# Si las dos patas compartieran columna, cada cambio de venue le meteria al
# motor un salto de precio que no ocurrio nunca, y ese salto aparece como
# ganancia o perdida de la nada.
SUFIJO_PERPETUO = ".P"


def es_perpetuo(columna: str) -> bool:
    return columna.endswith(SUFIJO_PERPETUO)


def simbolo_base(columna: str) -> str:
    """`BTCUSDT.P` -> `BTCUSDT`. La moneda detras del instrumento."""
    return (columna[:-len(SUFIJO_PERPETUO)] if es_perpetuo(columna)
            else columna)


def seleccionar_cortos(fila_de_puntajes: pd.Series,
                       candidatos: list[str],
                       cuantos: int = CUANTAS_POSICIONES) -> list[str]:
    """
    Los `cuantos` de MENOR puntaje entre los candidatos.

    La especificacion dice "los 5 de menor `s_i`", sin exigir que sean
    negativos --- al reves que la pata larga, que si exige `s_i > 0`. Se
    respeta la asimetria tal como esta escrita, porque estaba preregistrada.
    Queda anotado que es una asimetria y no un descuido.
    """
    disponibles = [c for c in candidatos if c in fila_de_puntajes.index]
    validos = fila_de_puntajes[disponibles].dropna()
    return list(validos.sort_values().index[:cuantos])


@dataclass
class ArmadoLargoCorto:
    exposiciones: pd.DataFrame
    stops_disparados: list[dict] = field(default_factory=list)
    dias_sin_largos: int = 0
    dias_sin_cortos: int = 0


def construir_exposiciones(
    cierres_spot: pd.DataFrame,
    aperturas_spot: pd.DataFrame,
    cierres_perp: pd.DataFrame,
    aperturas_perp: pd.DataFrame,
    atr_spot: pd.DataFrame,
    atr_perp: pd.DataFrame,
    universo_mensual: dict[pd.Timestamp, list[str]],
    dias: pd.DatetimeIndex,
    *,
    cuantas: int = CUANTAS_POSICIONES,
    tope: float = TOPE_POR_ACTIVO,
    objetivo: float = SIGMA_OBJETIVO,
    k_max: float = K_MAX,
    ventana_vol: int = VENTANA_VOLATILIDAD_DIAS,
    multiplicador_stop: float = cat.MULTIPLICADOR_ATR,
) -> ArmadoLargoCorto:
    """
    Exposiciones diarias con signo: positivas la pata larga, negativas la corta.

    El puntaje se calcula **siempre sobre precios de Spot**, para las dos
    patas. Es a proposito: el ranking tiene que ser el mismo objeto en los dos
    lados, y mezclarlo (largos por Spot, cortos por perpetuo) meteria la base
    adentro de la señal sin que nadie lo pidiera.
    """
    sigmas = sigmas_diarias(cierres_spot, ventana_vol)
    marcas = puntajes(cierres_spot, sigmas)
    retornos = np.log(cierres_spot / cierres_spot.shift(1))

    shorteables = set(cierres_perp.columns)
    monedas = sorted({s for v in universo_mensual.values() for s in v})
    columnas = monedas + [s + SUFIJO_PERPETUO for s in sorted(shorteables)]

    retornos_np = np.nan_to_num(retornos.to_numpy(), nan=0.0)
    columna_de = {c: j for j, c in enumerate(retornos.columns)}
    posicion = retornos.index.get_indexer(dias)

    largos: list[str] = []
    cortos: list[str] = []
    excluidos: set[str] = set()
    entradas: dict[str, float] = {}
    stops: dict[str, float] = {}
    disparados: list[dict] = []
    sin_largos = sin_cortos = 0

    filas: list[dict[str, float]] = []
    for i, fecha in enumerate(dias):
        # --- 1. Seleccion mensual ------------------------------------------
        if fecha in universo_mensual:
            candidatos = universo_mensual[fecha]
            largos = seleccionar(marcas.loc[fecha], candidatos, cuantas)
            # Solo se puede vender en corto lo que tiene perpetuo.
            cortos = seleccionar_cortos(
                marcas.loc[fecha],
                [c for c in candidatos if c in shorteables], cuantas)
            # Un simbolo no puede estar en las dos patas a la vez.
            cortos = [c for c in cortos if c not in largos]
            excluidos = set()

        # --- 2. Stops, mirados con el cierre de ayer -----------------------
        if i > 0:
            ayer = dias[i - 1]
            for s in list(stops):
                es_corto = es_perpetuo(s)
                base = simbolo_base(s)
                marco = cierres_perp if es_corto else cierres_spot
                if base not in marco.columns:
                    continue
                cierre_ayer = marco.at[ayer, base] if ayer in marco.index else np.nan
                if not np.isfinite(cierre_ayer):
                    continue
                salto = (cat.se_disparo_corto(float(cierre_ayer), stops[s])
                         if es_corto
                         else cat.se_disparo(float(cierre_ayer), stops[s]))
                if salto:
                    excluidos.add(s)
                    disparados.append({"simbolo": s, "fecha": fecha,
                                       "pata": "corta" if es_corto else "larga",
                                       "entrada": entradas.get(s),
                                       "stop": stops[s],
                                       "cierre": float(cierre_ayer)})
                    stops.pop(s, None)
                    entradas.pop(s, None)

        if not largos:
            sin_largos += 1
        if not cortos:
            sin_cortos += 1
        if not largos and not cortos:
            entradas.clear()
            stops.clear()
            filas.append({})
            continue

        # --- 3. Pesos dentro de cada pata ----------------------------------
        p = posicion[i]
        if p < MINIMO_DE_OBSERVACIONES:
            filas.append({})
            continue

        def pesos_de(nombres: list[str]) -> pd.Series:
            if not nombres:
                return pd.Series(dtype="float64")
            sigma = sigmas.loc[fecha, [n for n in nombres
                                       if n in sigmas.columns]].dropna()
            sigma = sigma[sigma > 0]
            return pesos_inversa_volatilidad(sigma, tope)

        w_largo = pesos_de(largos)
        w_corto = pesos_de(cortos)
        if w_largo.empty and w_corto.empty:
            filas.append({})
            continue

        # Los pesos con signo. La pata corta va con el sufijo del perpetuo.
        w_corto = w_corto.rename(lambda s: s + SUFIJO_PERPETUO)
        firmados = pd.concat([w_largo * FRACCION_POR_PATA,
                              -w_corto * FRACCION_POR_PATA])

        # Para la volatilidad de cartera se usan los retornos de Spot en las
        # dos patas: el perpetuo sigue al Spot de cerquisima y no hay serie de
        # perpetuo para todos. La base es de segundo orden para esto.
        columnas_ventana = [s for s in firmados.index
                            if simbolo_base(s) in columna_de]
        if not columnas_ventana:
            filas.append({})
            continue
        bloque = retornos_np[max(0, p - ventana_vol):p][
            :, [columna_de[simbolo_base(s)] for s in columnas_ventana]]
        if len(bloque) < MINIMO_DE_OBSERVACIONES:
            filas.append({})
            continue
        de_cartera = bloque @ firmados[columnas_ventana].to_numpy()
        sigma_cartera = float(de_cartera.std(ddof=1) * np.sqrt(DIAS_POR_ANIO))
        k = escalar_de_volatilidad(sigma_cartera, objetivo, k_max)
        if k <= 0:
            filas.append({})
            continue

        exposicion = {s: v * k for s, v in firmados.items()
                      if s not in excluidos and abs(v) > 0}
        filas.append(exposicion)

        # --- 4. Memoria de entradas y stops --------------------------------
        for s in list(entradas):
            if s not in exposicion:
                entradas.pop(s, None)
                stops.pop(s, None)
        for s in exposicion:
            if s in entradas:
                continue
            es_corto = es_perpetuo(s)
            base = simbolo_base(s)
            ap = aperturas_perp if es_corto else aperturas_spot
            at = atr_perp if es_corto else atr_spot
            if base not in ap.columns or base not in at.columns:
                continue
            precio = ap.at[fecha, base] if fecha in ap.index else np.nan
            atr = at.at[fecha, base] if fecha in at.index else np.nan
            if not np.isfinite(precio) or precio <= 0 or not np.isfinite(atr):
                continue
            entradas[s] = float(precio)
            stops[s] = (cat.precio_de_stop_corto(float(precio), float(atr),
                                                 multiplicador_stop)
                        if es_corto
                        else cat.precio_de_stop(float(precio), float(atr),
                                                multiplicador_stop))

    marco = pd.DataFrame(filas, index=dias).reindex(columns=columnas)
    return ArmadoLargoCorto(marco.fillna(0.0), disparados,
                            sin_largos, sin_cortos)
