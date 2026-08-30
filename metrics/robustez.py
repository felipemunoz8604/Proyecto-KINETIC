"""
Las cuatro pruebas que separan una ventaja de una observacion afortunada.

POR QUE HACE FALTA MAS QUE UN BUEN NUMERO
------------------------------------------
La Fase 1 dejo dos lecciones caras. Una: en tres corridas seguidas, la
pregunta *"cuanto aporta la mejor operacion"* fue mas informativa que el
profit factor, el retorno y la tasa de acierto juntos. Otra: un barrido en
retrospectiva inflaba el resultado entre 20% y 200%, medido.

Este modulo pone numero formal a lo mismo, con cuatro herramientas:

1. **Comparacion por pares** contra el benchmark, sobre muchas fechas de
   arranque. Contesta si el resultado depende del calendario.
2. **Bootstrap por bloques** sobre los retornos diarios. Contesta si el CAGR
   podria ser cero y tuvimos suerte.
3. **Curva de retiro top-k.** Contesta cuanto del resultado vive en un puñado
   de meses.
4. **Deflated Sharpe Ratio.** Contesta cuanto del Sharpe es un artefacto de
   haber probado varias configuraciones.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Callable

import numpy as np
import pandas as pd

from metrics import metricas

GAMMA_EULER = 0.5772156649015329
NORMAL = NormalDist()


# ---------------------------------------------------------------------------
# 1. Comparacion por pares contra el benchmark
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComparacionPareada:
    """El cociente estrategia/benchmark, medido sobre varias ventanas."""

    arranques: list[pd.Timestamp]
    calmar_estrategia: list[float]
    calmar_benchmark: list[float]
    cocientes: list[float]

    @property
    def mediana(self) -> float:
        return float(np.median(self.cocientes)) if self.cocientes else 0.0

    @property
    def peor(self) -> float:
        return min(self.cocientes) if self.cocientes else 0.0

    @property
    def mejor(self) -> float:
        return max(self.cocientes) if self.cocientes else 0.0

    def fraccion_por_encima(self, umbral: float) -> float:
        """Que proporcion de los arranques supera el umbral."""
        if not self.cocientes:
            return 0.0
        return sum(1 for c in self.cocientes if c >= umbral) / len(self.cocientes)

    def informe(self, umbral: float = 1.8) -> str:
        lineas = [
            f"  {'Arranque':<12} {'Calmar estr.':>13} {'Calmar B1':>11} {'Cociente':>10}",
        ]
        for a, e, b, c in zip(self.arranques, self.calmar_estrategia,
                              self.calmar_benchmark, self.cocientes):
            marca = " *" if c >= umbral else ""
            lineas.append(f"  {str(a.date()):<12} {e:>13.3f} {b:>11.3f} "
                          f"{c:>10.3f}{marca}")
        lineas.append(f"  {'-' * 50}")
        lineas.append(
            f"  Mediana {self.mediana:.3f}   peor {self.peor:.3f}   "
            f"mejor {self.mejor:.3f}   "
            f"({self.fraccion_por_encima(umbral) * 100:.0f}% supera {umbral})"
        )
        return "\n".join(lineas)


def fechas_de_arranque(
    datos: pd.DataFrame | pd.Series,
    cantidad: int = 20,
    paso_dias: int = 7,
) -> list[pd.Timestamp]:
    """
    Las fechas desde las que se va a repetir la medicion.

    Separadas una semana por defecto, como pide la especificacion 7.2. Se
    toman desde el inicio hacia adelante: correr la fecha de arranque acorta
    la ventana, y acortarla demasiado haria incomparables las ultimas.
    """
    if len(datos) == 0:
        return []
    inicio = datos.index[0]
    fechas = [inicio + pd.Timedelta(days=paso_dias * i) for i in range(cantidad)]
    return [f for f in fechas if f < datos.index[-1]]


def comparar_por_pares(
    datos: pd.DataFrame,
    construir_estrategia: Callable[[pd.DataFrame], pd.Series],
    construir_benchmark: Callable[[pd.DataFrame], pd.Series],
    *,
    arranques: list[pd.Timestamp] | None = None,
) -> ComparacionPareada:
    """
    Compara estrategia contra benchmark sobre LA MISMA ventana, muchas veces.

    Por que por pares y no contra un Calmar(B1) fijo: medido el 30-ago-2026,
    Calmar(B1) va de 0,439 a 0,973 segun el mes en que arranque la ventana. Un
    umbral atado a un solo arranque exige mas del doble segun una fecha que
    nadie eligio por una razon de fondo -- mide en parte la estrategia y en
    parte el calendario.

    Comparando los dos sobre la misma ventana, la fecha se cancela: lo que
    queda es cuanto mejor es la estrategia que comprar y esperar, que es la
    pregunta.
    """
    arranques = arranques if arranques is not None else fechas_de_arranque(datos)
    usados, ce, cb, cocientes = [], [], [], []

    for arranque in arranques:
        tramo = datos[datos.index >= arranque]
        if len(tramo) < 2:
            continue
        m_e = metricas.calcular(construir_estrategia(tramo), "estrategia")
        m_b = metricas.calcular(construir_benchmark(tramo), "benchmark")
        # Un benchmark con Calmar cero o negativo no sirve de divisor: el
        # cociente no significaria nada y arrastraria la mediana.
        if not math.isfinite(m_b.calmar) or m_b.calmar <= 0:
            continue
        usados.append(arranque)
        ce.append(m_e.calmar)
        cb.append(m_b.calmar)
        cocientes.append(m_e.calmar / m_b.calmar)

    return ComparacionPareada(usados, ce, cb, cocientes)


# ---------------------------------------------------------------------------
# 2. Bootstrap por bloques
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntervaloCAGR:
    estimacion: float
    bajo: float
    alto: float
    remuestreos: int
    bloque_dias: int

    @property
    def excluye_cero(self) -> bool:
        """El criterio 4: si el intervalo cruza cero, no hay ventaja."""
        return self.bajo > 0.0

    def informe(self) -> str:
        veredicto = "excluye cero" if self.excluye_cero else "CRUZA CERO"
        return (f"  CAGR {self.estimacion * 100:+.2f}%   "
                f"IC 95% [{self.bajo * 100:+.2f}%, {self.alto * 100:+.2f}%]   "
                f"{veredicto}")


def bootstrap_cagr(
    patrimonio: pd.Series,
    *,
    bloque_dias: int = 30,
    remuestreos: int = 10_000,
    semilla: int = 20260830,
) -> IntervaloCAGR:
    """
    Intervalo de confianza del CAGR remuestreando BLOQUES de retornos.

    Por bloques y no dia por dia: los retornos de un mercado no son
    independientes -- la volatilidad viene en rachas, y un dia malo tiende a
    seguir a otro dia malo. Remuestrear dias sueltos rompe esa estructura y
    devuelve un intervalo demasiado angosto, o sea demasiado optimista.

    La semilla queda fija para que el numero sea reproducible. Un intervalo de
    confianza que cambia en cada corrida es imposible de citar en un informe.
    """
    r = np.log1p(metricas.retornos_diarios(patrimonio).to_numpy())
    n = len(r)
    if n < bloque_dias * 2:
        estimacion = metricas.cagr(patrimonio)
        return IntervaloCAGR(estimacion, estimacion, estimacion,
                             0, bloque_dias)

    rng = np.random.default_rng(semilla)
    bloques = max(1, n // bloque_dias)
    # Cada remuestreo pega `bloques` tramos contiguos elegidos al azar.
    inicios = rng.integers(0, n - bloque_dias + 1, size=(remuestreos, bloques))
    desplazamiento = np.arange(bloque_dias)
    indices = (inicios[:, :, None] + desplazamiento).reshape(remuestreos, -1)
    sumas = r[indices].sum(axis=1)

    dias_sinteticos = bloques * bloque_dias
    cagrs = np.expm1(sumas * (metricas.DIAS_POR_ANIO / dias_sinteticos))
    bajo, alto = np.percentile(cagrs, [2.5, 97.5])
    return IntervaloCAGR(
        estimacion=metricas.cagr(patrimonio),
        bajo=float(bajo),
        alto=float(alto),
        remuestreos=remuestreos,
        bloque_dias=bloque_dias,
    )


# ---------------------------------------------------------------------------
# 3. Curva de retiro top-k
# ---------------------------------------------------------------------------

def retiro_top_k(
    patrimonio: pd.Series,
    ks: tuple[int, ...] = (1, 3, 5, 10),
) -> dict[int, float]:
    """
    El CAGR que queda al sacar los k MEJORES meses.

    Reemplaza a la bandera de concentracion de la Fase 1, que se rompia cerca
    de cero: la contribucion medida como % del NETO tiene denominador
    inestable, y por eso ETH 1h dio 920% -- una division por casi-cero, no una
    señal extrema.

    Ademas, aquel criterio estaba mal especificado para seguimiento de
    tendencia, que se define por asimetria positiva: la mayoria de las
    operaciones pierde poco y unas pocas pagan todo el año. La curva no
    pregunta "hay un mes grande" -- pregunta **cuanto sobrevive sin el**, que
    es lo que de verdad importa.
    """
    # OJO con esto, que costo una prueba roja: `resample("ME").last()` da los
    # cierres de fin de mes, y `pct_change()` descarta el primero. Con eso se
    # pierde entero el tramo del inicio de la serie al primer fin de mes, y el
    # producto de los meses deja de reproducir el retorno total. Medido sobre
    # 1.200 dias: el real daba 0,461 y la cadena mensual 0,576.
    #
    # Se arregla anteponiendo el punto de partida antes de encadenar. La
    # prueba `test_sin_sacar_nada_da_exactamente_el_cagr` fija el invariante.
    cierres = patrimonio.resample("ME").last()
    serie = pd.concat([patrimonio.iloc[:1], cierres])
    serie = serie[~serie.index.duplicated(keep="first")].sort_index()
    mensual = serie.pct_change().dropna()
    if mensual.empty:
        return {k: 0.0 for k in ks}

    anios = (patrimonio.index[-1] - patrimonio.index[0]).days / metricas.DIAS_POR_ANIO
    if anios <= 0:
        return {k: 0.0 for k in ks}

    ordenados = mensual.sort_values(ascending=False)
    salida: dict[int, float] = {}
    for k in ks:
        quedan = ordenados.iloc[k:] if k < len(ordenados) else ordenados.iloc[0:0]
        if quedan.empty:
            salida[k] = -1.0
            continue
        # Se recomponen los meses que quedan sobre el MISMO tiempo transcurrido:
        # sacar meses no hace que el periodo haya sido mas corto.
        crecimiento = float(np.prod(1.0 + quedan.to_numpy()))
        salida[k] = crecimiento ** (1.0 / anios) - 1.0 if crecimiento > 0 else -1.0
    return salida


def informe_retiro(patrimonio: pd.Series, referencia: float | None = None) -> str:
    curva = retiro_top_k(patrimonio)
    completo = metricas.cagr(patrimonio)
    lineas = [f"  {'Se sacan':>9}  {'CAGR queda':>11}  {'% del original':>14}"]
    lineas.append(f"  {'nada':>9}  {completo * 100:>10.2f}%  {'100%':>14}")
    for k, valor in curva.items():
        pct = valor / completo * 100 if completo != 0 else 0.0
        lineas.append(f"  {k:>4} meses  {valor * 100:>10.2f}%  {pct:>13.0f}%")
    if referencia is not None:
        tres = curva.get(3, 0.0)
        estado = "PASA" if tres >= 0.50 * referencia else "NO PASA"
        lineas.append(
            f"  Criterio 5: sin los 3 mejores meses, CAGR {tres * 100:.2f}% "
            f"vs {0.50 * referencia * 100:.2f}% exigido   {estado}"
        )
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# 4. Deflated Sharpe Ratio
# ---------------------------------------------------------------------------

def sharpe_esperado_por_azar(sharpes: list[float]) -> float:
    """
    El Sharpe mas alto que uno esperaria encontrar SIN ninguna ventaja real.

    Si se prueban N configuraciones sobre datos puro ruido, la mejor de las N
    igual va a tener Sharpe positivo -- por el mismo motivo por el que el mas
    alto de treinta personas mide mas que el promedio. Bailey y Lopez de Prado
    ponen numero a ese maximo esperado, y el DSR le descuenta eso al Sharpe
    observado antes de creerle.

    Es el equivalente formal de lo que la Fase 1 midio a mano: el barrido en
    retrospectiva inflaba entre 20% y 200%.
    """
    n = len(sharpes)
    if n < 2:
        return 0.0
    varianza = float(np.var(sharpes, ddof=1))
    if varianza <= 0:
        return 0.0
    return math.sqrt(varianza) * (
        (1 - GAMMA_EULER) * NORMAL.inv_cdf(1 - 1 / n)
        + GAMMA_EULER * NORMAL.inv_cdf(1 - 1 / (n * math.e))
    )


def deflated_sharpe(
    patrimonio: pd.Series,
    sharpes_probados: list[float],
) -> float:
    """
    Probabilidad de que el Sharpe observado sea real y no producto de probar.

    `sharpes_probados` son los Sharpe (sin anualizar) de TODAS las
    configuraciones evaluadas, incluida esta. El MEGAPROMPT v2.0 seccion 8b
    exige reportarlo siempre, no solo si se barre: probar E0, E1, E1-R1,
    E1-R2, E2 y E3 sobre la misma ventana ya es comparacion multiple aunque
    cada valor venga de literatura publicada.

    Devuelve una probabilidad. Por debajo de 0,95 no hay evidencia de ventaja
    una vez descontado el numero de intentos.
    """
    r = metricas.retornos_diarios(patrimonio)
    t = len(r)
    if t < 3:
        return 0.0

    sr = metricas.sharpe_por_observacion(patrimonio)
    sr0 = sharpe_esperado_por_azar(sharpes_probados)

    asimetria = float(r.skew())
    curtosis = float(r.kurtosis()) + 3.0  # pandas devuelve exceso; la formula no

    denominador = 1.0 - asimetria * sr + (curtosis - 1.0) / 4.0 * sr ** 2
    if denominador <= 0:
        return 0.0
    return NORMAL.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(denominador))
