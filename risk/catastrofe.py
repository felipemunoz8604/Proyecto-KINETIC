r"""
Riesgo v2 -- el stop de catastrofe y el cortacircuito diario.

DOS COSAS DISTINTAS QUE SE CONFUNDEN FACIL
--------------------------------------------
- El **stop de catastrofe** es por activo. Cierra UNA posicion cuando ese
  activo se derrumba. El resto de la cartera sigue igual.
- El **cortacircuito diario** es de la cartera entera. Mira el patrimonio a
  precio de mercado y frena todo si el dia fue muy malo.

EL STOP NO ESTA PARA GESTIONAR RIESGO ORDINARIO
------------------------------------------------
    stop_i = precio_entrada_i x (1 - 4 x ATR%(14))

Cuatro ATR es deliberadamente ancho. Un stop apretado sale seguido por ruido y
convierte la estrategia en otra cosa. Este esta para que el colapso de un
activo -- LUNA, que hizo -100% -- no se lleve puesta la cartera.

Se evalua **sobre el cierre diario, no intradia**. Es mas honesto: el archivo
tiene velas diarias, y fingir que se ejecuto en el minimo del dia seria
inventar una ejecucion que nadie puede probar.

QUE PASA CON EL PESO QUE QUEDA LIBRE: NADA
-------------------------------------------
La especificacion es explicita -- "se cierra esa posicion y el activo queda
excluido hasta el siguiente rebalanceo mensual. El resto de la cartera no se
toca". O sea que ese peso **se va a efectivo** y ahi se queda.

No se reparte entre los que quedan, y la tentacion de repartirlo es fuerte
porque "mejora" el resultado. Repartirlo seria aumentar la exposicion justo
despues de que algo se derrumbo, que es exactamente cuando no hay que hacerlo.

EL 3% DIARIO ES PROVISIONAL, Y ESTA MARCADO COMO TAL
------------------------------------------------------
La especificacion avisa: "un cortacircuito que se activa cada semana no es un
cortacircuito, es un parametro escondido de la estrategia". El 3% viene de la
Fase 1, donde se medía sobre operaciones cerradas; sobre patrimonio a precio
de mercado de una cartera de cripto se va a disparar mucho mas seguido.

Por eso `disparos_del_cortacircuito` existe: para contar antes de fijar. Y por
eso el umbral es un argumento obligatorio -- para que nadie lo use sin
elegirlo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from strategy.indicators import atr_porcentual

MULTIPLICADOR_ATR = 4.0
PERIODO_ATR = 14

# PROVISIONAL. Heredado de la Fase 1, pendiente de medir sobre patrimonio a
# precio de mercado. No se usa como default en ninguna funcion a proposito.
PERDIDA_DIARIA_MAXIMA_PCT_PROVISIONAL = 3.0


# --- Stop de catastrofe ---------------------------------------------------

def atr_relativo(velas: pd.DataFrame, periodo: int = PERIODO_ATR) -> pd.Series:
    """
    ATR como fraccion del precio (0,05 = 5%), no como porcentaje.

    `strategy/indicators.atr_porcentual` devuelve 5,0 para ese mismo caso. La
    division por 100 vive aca, una sola vez, porque mezclar las dos unidades
    en la formula del stop lo pondria 100 veces mas lejos sin que se note.
    """
    return atr_porcentual(velas, periodo) / 100.0


def precio_de_stop(precio_entrada: float, atr_frac: float,
                   multiplicador: float = MULTIPLICADOR_ATR) -> float:
    """
    El precio al que se abandona la posicion. Nunca por debajo de cero.
    """
    if precio_entrada <= 0:
        raise ValueError(f"precio de entrada invalido: {precio_entrada}")
    if not np.isfinite(atr_frac) or atr_frac < 0:
        raise ValueError(f"ATR invalido: {atr_frac}")
    return max(precio_entrada * (1.0 - multiplicador * atr_frac), 0.0)


def se_disparo(cierre: float, stop: float) -> bool:
    """
    Sobre el CIERRE del dia. Si el precio toco el stop intradia y se recupero
    antes del cierre, aca no pasa nada -- y esta bien que sea asi: con velas
    diarias no hay forma de saber en que orden ocurrieron el minimo y el
    cierre.
    """
    return bool(cierre <= stop)


@dataclass
class Posicion:
    """Lo minimo que hace falta para vigilar un stop."""

    simbolo: str
    precio_entrada: float
    stop: float

    def revisar(self, cierre: float) -> bool:
        return se_disparo(cierre, self.stop)


def revisar_stops(posiciones: list[Posicion],
                  cierres: pd.Series) -> list[str]:
    """
    Los simbolos que hay que cerrar hoy. Un simbolo sin precio hoy no dispara:
    no hay dato, no hay decision.
    """
    return [p.simbolo for p in posiciones
            if p.simbolo in cierres.index
            and np.isfinite(cierres[p.simbolo])
            and p.revisar(float(cierres[p.simbolo]))]


# --- Cortacircuito diario -------------------------------------------------

def perdidas_diarias_pct(patrimonio: pd.Series) -> pd.Series:
    """
    Variacion diaria del patrimonio a precio de mercado, en porcentaje.
    Negativo es perdida.
    """
    if not patrimonio.index.is_monotonic_increasing:
        raise ValueError("el patrimonio tiene que venir ordenado por fecha")
    return patrimonio.pct_change().dropna() * 100.0


def disparos_del_cortacircuito(patrimonio: pd.Series,
                               umbral_pct: float) -> pd.Series:
    """
    Los dias en que la perdida supero el umbral. `umbral_pct` es positivo:
    3.0 significa "cayo mas de 3%".

    Es un argumento obligatorio a proposito. El numero de la Fase 1 se medía
    sobre operaciones cerradas y no se puede trasladar sin medir de nuevo.
    """
    if umbral_pct <= 0:
        raise ValueError("el umbral se pasa en positivo, por ejemplo 3.0")
    diarias = perdidas_diarias_pct(patrimonio)
    return diarias[diarias < -umbral_pct]


def frecuencia_de_disparo(patrimonio: pd.Series,
                          umbral_pct: float) -> dict[str, float]:
    """
    Cada cuanto se dispararia el cortacircuito con ese umbral.

    Es la cuenta que la especificacion pide hacer ANTES de dejar el 3% fijo:
    uno que salta cada semana no es un cortacircuito, es un parametro
    escondido de la estrategia.
    """
    disparos = disparos_del_cortacircuito(patrimonio, umbral_pct)
    dias = len(perdidas_diarias_pct(patrimonio))
    anios = dias / 365.0 if dias else float("nan")
    return {
        "umbral_pct": umbral_pct,
        "disparos": len(disparos),
        "dias": dias,
        "por_anio": len(disparos) / anios if anios else float("nan"),
        "peor_dia_pct": float(perdidas_diarias_pct(patrimonio).min())
                        if dias else float("nan"),
    }
