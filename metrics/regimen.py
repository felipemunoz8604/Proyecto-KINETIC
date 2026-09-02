r"""
Captura y proteccion, condicionadas al regimen -- los criterios C-A y C-B.

DE DONDE SALEN
---------------
De la respuesta a la segunda consulta externa (1-sep-2026). El analista mostro
que el cociente de Calmar contra el benchmark se descompone **exactamente**
asi:

    Calmar(X) / Calmar(B1)  =  (CAGR_X / CAGR_B1)  /  (MaxDD_X / MaxDD_B1)
                            =   captura de retorno / fraccion de caida

Es algebra, no aproximacion: Calmar es CAGR sobre caida, y el cociente de dos
Calmar es el cociente de los CAGR sobre el cociente de las caidas.

**El problema del criterio 1 es que funde las dos cosas en un numero.** E0
falla el criterio 1, y de ese fallo no se puede leer que la caida ya esta
resuelta y que lo que falta es la captura. Separandolas se lee de inmediato.

POR QUE CONDICIONADO AL REGIMEN
---------------------------------
El criterio 1 se corrigio en su momento comparando por pares sobre 20 fechas
de arranque, porque Calmar(B1) varia un factor 2,2 segun el mes en que se
empiece. Eso cancelo el **calendario**.

No cancelo el **regimen**: los 20 arranques caen todos dentro de la misma
ventana, asi que comparten el mismo 2021 y el mismo 2022. Veinte muestras del
mismo ciclo son una muestra del ciclo.

Midiendo captura solo en meses alcistas y proteccion solo en bajistas, lo que
queda es una propiedad de la estrategia y no de que ventana le toco.

LA REGLA DE REGIMEN NO TIENE PARAMETROS LIBRES NUEVOS
-------------------------------------------------------
Un mes es **alcista** si el retorno de BTC de los 12 meses previos fue
positivo, **bajista** si no. La ventana de 12 meses sale de la literatura
estandar de tendencia, y los datos van rezagados: la clasificacion del mes M
usa hasta el cierre de M-1.

LOS UMBRALES 70% Y 40% ESTAN SIN JUSTIFICAR
---------------------------------------------
El analista los propuso pero **no derivo de donde salen**. Este modulo calcula
los valores; **no decide el veredicto**. Fijar los umbrales es una decision de
Felipe y hay que escribirla con su razon antes de usarlos como vara, o se
estaria cambiando un umbral arbitrario por dos.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MESES_DE_TENDENCIA = 12


def _mensual(patrimonio: pd.Series) -> pd.Series:
    """
    Retornos mensuales, sin perder el tramo inicial.

    Es el mismo arreglo que en `robustez.retiro_top_k`, y esta por el mismo
    motivo: `resample("ME").last().pct_change()` descarta el primer valor y con
    el se pierde entero el tramo del inicio de la serie al primer fin de mes.
    """
    cierres = patrimonio.resample("ME").last()
    serie = pd.concat([patrimonio.iloc[:1], cierres])
    serie = serie[~serie.index.duplicated(keep="first")].sort_index()
    mensual = serie.pct_change().dropna()
    mensual.index = mensual.index.to_period("M")
    return mensual[~mensual.index.duplicated(keep="last")]


def clasificar_meses(cierres_btc: pd.Series,
                     meses: int = MESES_DE_TENDENCIA) -> pd.Series:
    """
    True = mes alcista. Indexado por periodo mensual.

    El mes M se clasifica con el retorno de los `meses` meses ANTERIORES a M.
    El `shift(1)` es lo que impide que la clasificacion de un mes use su propio
    resultado, que seria mirar al futuro de la forma mas directa posible.
    """
    fin_de_mes = cierres_btc.resample("ME").last().dropna()
    tendencia = fin_de_mes / fin_de_mes.shift(meses) - 1.0
    alcista = (tendencia > 0).shift(1)
    alcista.index = alcista.index.to_period("M")
    return alcista.dropna().astype(bool)


def _encadenar(retornos: pd.Series) -> float:
    """Retorno acumulado de una serie de retornos mensuales."""
    if retornos.empty:
        return float("nan")
    return float(np.prod(1.0 + retornos.to_numpy()) - 1.0)


def _caida_maxima(retornos: pd.Series) -> float:
    """Caida maxima de la curva que arman esos retornos encadenados. Negativa."""
    if retornos.empty:
        return float("nan")
    curva = np.cumprod(1.0 + retornos.to_numpy())
    return float((curva / np.maximum.accumulate(curva) - 1.0).min())


@dataclass(frozen=True)
class Puntaje:
    """Lo que miden C-A y C-B, con los ingredientes a la vista."""

    nombre: str
    meses_alcistas: int
    meses_bajistas: int
    retorno_alcista: float          # de la estrategia, acumulado
    retorno_alcista_b1: float
    captura: float                  # C-A
    caida_bajista: float            # negativa
    caida_bajista_b1: float
    proteccion: float               # C-B
    caida_bajista_peor_tramo: float
    caida_bajista_peor_tramo_b1: float

    @property
    def proteccion_por_tramo(self) -> float:
        """C-B calculada sobre el peor tramo bajista contiguo, como control."""
        if self.caida_bajista_peor_tramo_b1 == 0:
            return float("nan")
        return (self.caida_bajista_peor_tramo
                / self.caida_bajista_peor_tramo_b1)


def puntuar(patrimonio: pd.Series,
            patrimonio_b1: pd.Series,
            alcistas: pd.Series,
            nombre: str = "") -> Puntaje:
    """
    C-A y C-B de una curva contra el benchmark, sobre los mismos meses.

    **La caida en meses bajistas encadena meses no contiguos.** Eso arma una
    curva que nunca existio, y hay que saberlo. Se hace igual para los dos
    lados, asi que el COCIENTE sigue siendo comparable, que es lo que el
    criterio mira. Como control se reporta tambien la caida del peor tramo
    bajista contiguo, que si es una curva real: si las dos versiones dieran
    veredictos distintos, el criterio depende de esa eleccion y no del dato.
    """
    e = _mensual(patrimonio)
    b = _mensual(patrimonio_b1)
    comunes = e.index.intersection(b.index).intersection(alcistas.index)
    e, b, marca = e.loc[comunes], b.loc[comunes], alcistas.loc[comunes]

    ret_alc, ret_alc_b1 = _encadenar(e[marca]), _encadenar(b[marca])
    caida, caida_b1 = _caida_maxima(e[~marca]), _caida_maxima(b[~marca])

    # Control: el peor tramo bajista CONTIGUO, que si es una curva real.
    grupo = (marca != marca.shift()).cumsum()
    peor = peor_b1 = 0.0
    for _, bloque in marca.groupby(grupo):
        if bloque.iloc[0] or len(bloque) < 2:
            continue
        peor = min(peor, _caida_maxima(e.loc[bloque.index]))
        peor_b1 = min(peor_b1, _caida_maxima(b.loc[bloque.index]))

    return Puntaje(
        nombre=nombre,
        meses_alcistas=int(marca.sum()),
        meses_bajistas=int((~marca).sum()),
        retorno_alcista=ret_alc,
        retorno_alcista_b1=ret_alc_b1,
        captura=ret_alc / ret_alc_b1 if ret_alc_b1 else float("nan"),
        caida_bajista=caida,
        caida_bajista_b1=caida_b1,
        proteccion=abs(caida) / abs(caida_b1) if caida_b1 else float("nan"),
        caida_bajista_peor_tramo=peor,
        caida_bajista_peor_tramo_b1=peor_b1,
    )


def intervalo_de_captura(patrimonio: pd.Series,
                         patrimonio_b1: pd.Series,
                         alcistas: pd.Series,
                         *,
                         bloque_meses: int = 3,
                         remuestreos: int = 10_000,
                         semilla: int = 20260901) -> tuple[float, float]:
    """
    IC 95% del cociente de captura, remuestreando BLOQUES de meses alcistas.

    Es el criterio C-C. Por bloques y no por meses sueltos, por la misma razon
    que el bootstrap del CAGR: los retornos vienen en rachas, y romperlas
    devuelve un intervalo demasiado angosto.

    **"Excluye la indiferencia" se interpreta como que el intervalo no
    contiene 1,0**, o sea que la captura se distingue de igualar al benchmark.
    El analista no lo dejo explicito y esta es la lectura que se uso.
    """
    e = _mensual(patrimonio)
    b = _mensual(patrimonio_b1)
    comunes = e.index.intersection(b.index).intersection(alcistas.index)
    marca = alcistas.loc[comunes]
    ea, ba = e.loc[comunes][marca].to_numpy(), b.loc[comunes][marca].to_numpy()
    n = len(ea)
    if n < bloque_meses * 2:
        return (float("nan"), float("nan"))

    rng = np.random.default_rng(semilla)
    bloques = max(1, n // bloque_meses)
    inicios = rng.integers(0, n - bloque_meses + 1, size=(remuestreos, bloques))
    indices = (inicios[:, :, None] + np.arange(bloque_meses)).reshape(
        remuestreos, -1)
    cocientes = np.array([
        (np.prod(1.0 + ea[fila]) - 1.0) / (np.prod(1.0 + ba[fila]) - 1.0)
        if (np.prod(1.0 + ba[fila]) - 1.0) != 0 else np.nan
        for fila in indices
    ])
    cocientes = cocientes[np.isfinite(cocientes)]
    if not len(cocientes):
        return (float("nan"), float("nan"))
    return (float(np.percentile(cocientes, 2.5)),
            float(np.percentile(cocientes, 97.5)))
