r"""
Riesgo v2 -- cuanto va en cada activo, y cuanto va en total.

LA FORMULA ENTERA, EN UNA LINEA
--------------------------------
    exposicion_i(t) = G(t) x k(t) x w_i(t)

Tres piezas independientes, y esa independencia es el punto:

- **w_i(t)** reparte entre los elegidos. Inversa de la volatilidad, con tope
  del 40%. Suma 1.
- **k(t)** decide cuanto del capital se usa. Baja cuando la cartera esta
  agitada. **Nunca sube de 1,0.**
- **G(t)** apaga todo cuando BTC esta debajo de su media de 200 dias. Vive en
  `risk/compuerta.py`.

Ninguna mira que activo es. Eso lo decide `strategy/`; aca solo se decide con
cuanto. Es la regla 3 del proyecto.

k_max = 1,0 ES UN CERROJO, NO UN DEFAULT
-----------------------------------------
La regla 7 del MEGAPROMPT v2.0 dice que los perpetuos entran para habilitar la
pata corta y bajar comisiones, **no para apalancar**. Pedir un `k_max` mayor
que 1 levanta una excepcion. No es un valor por defecto que se puede pisar
pasando otro: esta cerrado por codigo, igual que los otros tres cerrojos del
proyecto. Cambiarlo es una decision de riesgo de Felipe, no un parametro.

POR QUE LA VOLATILIDAD DE LA CARTERA NO ES EL PROMEDIO DE LAS VOLATILIDADES
-----------------------------------------------------------------------------
Es menor, salvo que todo este perfectamente correlacionado. Esa diferencia es
la diversificacion, y es justamente lo que la medicion 5.2 encontro que existe
en este universo (correlacion media 0,59). Calcular `sigma_cartera` como un
promedio ponderado seria sobreestimarla y hacer que `k` baje de mas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.universo import hasta

DIAS_POR_ANIO = 365.0
VENTANA_VOLATILIDAD_DIAS = 30

# De la especificacion, seccion 4.4. Los tres marcados [FIJO].
TOPE_POR_ACTIVO = 0.40
SIGMA_OBJETIVO = 0.35
K_MAX = 1.0

# Con menos de esto la volatilidad de 30 dias es ruido. Un simbolo del
# universo siempre tiene 180 dias de historia, asi que esto solo se activa en
# datos rotos -- y es preferible que se note.
MINIMO_DE_OBSERVACIONES = 20


class SinApalancamiento(ValueError):
    """Alguien pidio un k_max mayor que 1. Ver la regla 7 del MEGAPROMPT."""


def _retornos_log(cierres: pd.DataFrame) -> pd.DataFrame:
    return np.log(cierres / cierres.shift(1))


def volatilidad_anualizada(panel_cierres: pd.DataFrame,
                           fecha: pd.Timestamp,
                           simbolos: list[str],
                           dias: int = VENTANA_VOLATILIDAD_DIAS) -> pd.Series:
    """
    Sigma de cada simbolo: desviacion de los retornos log diarios de los
    ultimos `dias`, anualizada por raiz de 365.

    365 y no 252: cripto opera todos los dias, incluidos los domingos.

    Solo mira lo anterior a `fecha`, y lo hace pasando por `universo.hasta`,
    que es la unica funcion del proyecto que corta el futuro.
    """
    columnas = [s for s in simbolos if s in panel_cierres.columns]
    previo = hasta(panel_cierres[columnas], fecha).iloc[-(dias + 1):]
    retornos = _retornos_log(previo)
    suficientes = retornos.count() >= MINIMO_DE_OBSERVACIONES
    sigmas = retornos.std(ddof=1) * np.sqrt(DIAS_POR_ANIO)
    return sigmas.where(suficientes).dropna()


def _aplicar_tope(pesos: pd.Series, tope: float) -> pd.Series:
    """
    Baja al tope a los que se pasan y reparte el excedente entre los demas,
    en proporcion. Se repite hasta que nadie se pasa.

    Recortar y renormalizar de una sola pasada NO alcanza: al renormalizar,
    alguno de los otros puede pasarse del tope y queda violado en silencio.
    """
    n = len(pesos)
    if n == 0:
        return pesos
    if n * tope < 1.0 - 1e-12:
        # Con tan pocos activos el tope es imposible de cumplir sumando 1.
        # Repartir parejo es lo mas cerca que se puede estar de respetarlo.
        return pd.Series(1.0 / n, index=pesos.index)

    w = pesos.astype(float).copy()
    capados = pd.Series(False, index=w.index)
    for _ in range(n + 1):
        excede = (w > tope + 1e-12) & ~capados
        if not excede.any():
            break
        exceso = float((w[excede] - tope).sum())
        w[excede] = tope
        capados |= excede
        libres = ~capados
        disponible = float(w[libres].sum())
        if not libres.any() or disponible <= 0:
            break
        w[libres] += exceso * w[libres] / disponible
    return w


def pesos_inversa_volatilidad(sigmas: pd.Series,
                              tope: float = TOPE_POR_ACTIVO) -> pd.Series:
    """
    w_i = (1/sigma_i) / suma(1/sigma_j), con tope por activo. Suma 1.

    El que menos se mueve se lleva mas. No es una prediccion de retorno: es
    que sin esto una sola moneda del puesto 18 domina el riesgo de la cartera
    entera aunque pese lo mismo que BTC en dinero.
    """
    validas = sigmas[sigmas > 0].dropna()
    if validas.empty:
        return pd.Series(dtype="float64")
    crudos = (1.0 / validas) / (1.0 / validas).sum()
    return _aplicar_tope(crudos, tope)


def volatilidad_de_cartera(panel_cierres: pd.DataFrame,
                           fecha: pd.Timestamp,
                           pesos: pd.Series,
                           dias: int = VENTANA_VOLATILIDAD_DIAS) -> float:
    """
    Sigma de la cartera con los pesos de hoy aplicados a los retornos de los
    ultimos `dias`. Anualizada.

    "Ex-ante" significa que los pesos son los que se acaban de decidir; los
    retornos son todos pasados. No hay nada del futuro adentro.
    """
    columnas = [s for s in pesos.index if s in panel_cierres.columns]
    if not columnas:
        return float("nan")
    previo = hasta(panel_cierres[columnas], fecha).iloc[-(dias + 1):]
    retornos = _retornos_log(previo).dropna(how="all")
    if len(retornos) < MINIMO_DE_OBSERVACIONES:
        return float("nan")
    de_cartera = (retornos.fillna(0.0) * pesos[columnas]).sum(axis=1)
    return float(de_cartera.std(ddof=1) * np.sqrt(DIAS_POR_ANIO))


def escalar_de_volatilidad(sigma_cartera: float,
                           objetivo: float = SIGMA_OBJETIVO,
                           k_max: float = K_MAX) -> float:
    """
    k(t) = min(objetivo / sigma_cartera, k_max).

    Si `sigma_cartera` no se pudo calcular, k vale 0: sin poder medir el
    riesgo no se toma. Es el mismo criterio que la compuerta antes del dia 200.
    """
    if k_max > K_MAX:
        raise SinApalancamiento(
            f"k_max={k_max} pasa de {K_MAX}. Los perpetuos entraron para la "
            "pata corta y para bajar comisiones, no para apalancar "
            "(MEGAPROMPT v2.0, regla 7). Cambiarlo es una decision de riesgo "
            "de Felipe y necesita una corrida nueva."
        )
    if not np.isfinite(sigma_cartera) or sigma_cartera <= 0:
        return 0.0
    return float(min(objetivo / sigma_cartera, k_max))


def exposiciones(panel_cierres: pd.DataFrame,
                 fecha: pd.Timestamp,
                 simbolos: list[str],
                 compuerta: int,
                 *,
                 tope: float = TOPE_POR_ACTIVO,
                 objetivo: float = SIGMA_OBJETIVO,
                 k_max: float = K_MAX,
                 dias: int = VENTANA_VOLATILIDAD_DIAS) -> pd.Series:
    """
    La formula completa: G(t) x k(t) x w_i(t), por activo.

    Lo que devuelve es la fraccion del patrimonio que va a cada uno. La suma
    es la exposicion bruta, que nunca pasa de 1: sin apalancamiento.
    """
    if compuerta == 0:
        return pd.Series(0.0, index=simbolos)
    sigmas = volatilidad_anualizada(panel_cierres, fecha, simbolos, dias)
    w = pesos_inversa_volatilidad(sigmas, tope)
    if w.empty:
        return pd.Series(0.0, index=simbolos)
    sigma_p = volatilidad_de_cartera(panel_cierres, fecha, w, dias)
    k = escalar_de_volatilidad(sigma_p, objetivo, k_max)
    return (w * k * compuerta).reindex(simbolos).fillna(0.0)
