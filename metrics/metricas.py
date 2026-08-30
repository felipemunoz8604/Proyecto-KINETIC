"""
Las metricas obligatorias de todo reporte de la Fase 2.

TODO OPERA SOBRE UNA CURVA DE PATRIMONIO DIARIA
------------------------------------------------
Una serie indexada por fecha con el valor de la cuenta al cierre de cada dia.
Nada de aca sabe si eso salio de una estrategia, de un benchmark o de comprar
y esperar, y esa ignorancia es deliberada: la decision D2 cambia la
contabilidad de "operaciones abiertas y cerradas" a "pesos de cartera", y una
metrica atada al concepto de operacion habria que reescribirla de nuevo.

LA METRICA PRIMARIA ES CALMAR, NO EL RETORNO
---------------------------------------------
La vara de la Fase 2 es "igualar al mercado con la mitad de la caida". No se
formaliza como dos condiciones simultaneas (retorno >= 100% del benchmark Y
caida <= 50%) porque los sistemas de seguimiento de tendencia **entregan parte
del retorno bruto** a cambio de recortar la caida: estan fuera del mercado en
parte de la subida. Exigir las dos cosas a la vez rechazaria un sistema que
funciona, que es exactamente el error del criterio 3 de la Fase 1.

Se formaliza como Calmar = CAGR / |caida maxima|. El ratio de retorno contra
el benchmark se reporta como informacion, no como filtro.

POR QUE 365 Y NO 252
--------------------
Cripto opera todos los dias del año, sabados y feriados incluidos. Anualizar
con 252 dias habiles seria importar un supuesto de la bolsa que aca es falso,
y inflaria la volatilidad reportada en un 20%.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

DIAS_POR_ANIO = 365.0


@dataclass(frozen=True)
class Metricas:
    """Lo que hay que reportar de cualquier curva de patrimonio."""

    nombre: str
    dias: int
    patrimonio_inicial: float
    patrimonio_final: float
    cagr: float
    volatilidad: float
    caida_maxima: float          # negativa, ej. -0.77 = cayo 77%
    caida_duracion_dias: int
    caida_desde: pd.Timestamp | None
    caida_hasta: pd.Timestamp | None
    calmar: float
    sortino: float
    tiempo_en_mercado_pct: float | None = None
    rotacion_anual: float | None = None
    costo_anual_pct: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def retorno_total_pct(self) -> float:
        return (self.patrimonio_final / self.patrimonio_inicial - 1.0) * 100.0

    def informe(self) -> str:
        lineas = [
            f"  {self.nombre}",
            f"    Periodo:          {self.dias:,} dias",
            f"    Patrimonio:       {self.patrimonio_inicial:,.2f} -> "
            f"{self.patrimonio_final:,.2f}  ({self.retorno_total_pct:+.1f}%)",
            f"    CAGR:             {self.cagr * 100:+.2f}%",
            f"    Volatilidad:      {self.volatilidad * 100:.1f}% anualizada",
            f"    Caida maxima:     {self.caida_maxima * 100:.1f}%"
            f"   ({self.caida_duracion_dias:,} dias sin recuperarse)",
            f"    CALMAR:           {self.calmar:.3f}",
            f"    Sortino:          {self.sortino:.3f}",
        ]
        if self.tiempo_en_mercado_pct is not None:
            lineas.append(f"    Tiempo en mercado: {self.tiempo_en_mercado_pct:.0f}%")
        if self.rotacion_anual is not None:
            lineas.append(f"    Rotacion anual:   {self.rotacion_anual:.2f}x")
        if self.costo_anual_pct is not None:
            lineas.append(f"    Costo pagado:     {self.costo_anual_pct:.2f}% anual")
        return "\n".join(lineas)


def retornos_diarios(patrimonio: pd.Series) -> pd.Series:
    """Retornos simples dia a dia. Se descarta el primero, que no existe."""
    return patrimonio.pct_change().dropna()


def cagr(patrimonio: pd.Series) -> float:
    """
    Tasa de crecimiento anual compuesta, sobre dias de calendario.

    Se usa el tiempo transcurrido real y no la cantidad de filas: si la serie
    tuviera un hueco, contar filas mentiria sobre cuanto tardo en crecer.
    """
    if len(patrimonio) < 2:
        return 0.0
    inicial, final = float(patrimonio.iloc[0]), float(patrimonio.iloc[-1])
    if inicial <= 0:
        return 0.0
    dias = (patrimonio.index[-1] - patrimonio.index[0]).total_seconds() / 86400.0
    if dias <= 0:
        return 0.0
    if final <= 0:
        return -1.0  # se fundio: no hay raiz real que reportar
    return (final / inicial) ** (DIAS_POR_ANIO / dias) - 1.0


def volatilidad_anual(patrimonio: pd.Series) -> float:
    r = retornos_diarios(patrimonio)
    if len(r) < 2:
        return 0.0
    return float(r.std(ddof=1)) * math.sqrt(DIAS_POR_ANIO)


def caida_maxima(patrimonio: pd.Series):
    """
    La peor caida desde un maximo, y cuanto duro.

    Devuelve `(caida, dias, desde, hasta)`. La duracion se mide desde el
    maximo previo hasta que el patrimonio lo recupera; si nunca lo recupera,
    hasta el final de la serie -- que es la respuesta honesta, no un cero.
    """
    if len(patrimonio) < 2:
        return 0.0, 0, None, None

    maximos = patrimonio.cummax()
    caidas = patrimonio / maximos - 1.0
    fondo = caidas.idxmin()
    peor = float(caidas.loc[fondo])
    if peor == 0.0:
        return 0.0, 0, None, None

    # El pico que precede al fondo: el ultimo momento en que la curva iba
    # tocando su maximo historico.
    previo = patrimonio.loc[:fondo]
    pico = previo[previo >= maximos.loc[fondo]].index[0]

    # La recuperacion: el primer dia posterior al fondo que vuelve al pico.
    posterior = patrimonio.loc[fondo:]
    recuperado = posterior[posterior >= float(patrimonio.loc[pico])]
    fin = recuperado.index[0] if len(recuperado) else patrimonio.index[-1]

    dias = int((fin - pico).total_seconds() // 86400)
    return peor, dias, pico, fin


def sortino(patrimonio: pd.Series, objetivo_diario: float = 0.0) -> float:
    """
    Como el Sharpe, pero castigando solo la volatilidad hacia abajo.

    La de arriba no es riesgo: a nadie le molesta que su cuenta suba rapido.
    Si no hay ningun dia por debajo del objetivo devuelve infinito, que es
    literalmente lo que pasa -- no hay denominador.
    """
    r = retornos_diarios(patrimonio)
    if len(r) < 2:
        return 0.0
    exceso = r - objetivo_diario
    malos = exceso[exceso < 0]
    if len(malos) == 0:
        return float("inf")
    desvio_malo = math.sqrt(float((malos ** 2).mean()))
    if desvio_malo == 0:
        return float("inf")
    return float(exceso.mean()) / desvio_malo * math.sqrt(DIAS_POR_ANIO)


def sharpe_por_observacion(patrimonio: pd.Series) -> float:
    """
    Sharpe SIN anualizar, en unidades de retorno diario.

    Lo pide el Deflated Sharpe Ratio, que trabaja sobre la distribucion de
    retornos por observacion. Anualizarlo antes rompe la formula.
    """
    r = retornos_diarios(patrimonio)
    if len(r) < 2:
        return 0.0
    desvio = float(r.std(ddof=1))
    if desvio == 0:
        return 0.0
    return float(r.mean()) / desvio


def calcular(
    patrimonio: pd.Series,
    nombre: str = "",
    *,
    exposicion: pd.Series | None = None,
    rotacion_anual: float | None = None,
    costo_anual_pct: float | None = None,
    extra: dict | None = None,
) -> Metricas:
    """
    Todas las metricas de una curva, de una sola pasada.

    `exposicion` es opcional: una serie con la fraccion invertida cada dia.
    Si se pasa, se reporta el tiempo en mercado -- que en una estrategia con
    compuerta de regimen es la mitad de la explicacion del resultado.
    """
    patrimonio = patrimonio.dropna()
    if len(patrimonio) < 2:
        raise ValueError(
            f"La curva de patrimonio '{nombre}' tiene {len(patrimonio)} punto(s). "
            "Hacen falta al menos dos para medir cualquier cosa."
        )

    crecimiento = cagr(patrimonio)
    peor, dias_caida, desde, hasta = caida_maxima(patrimonio)

    # Calmar con caida cero es infinito de verdad: gano sin caer nunca. Es
    # rarisimo y casi siempre significa que la serie es demasiado corta, pero
    # devolver 0 seria mentir en la direccion contraria.
    if peor == 0.0:
        ratio = float("inf") if crecimiento > 0 else 0.0
    else:
        ratio = crecimiento / abs(peor)

    en_mercado = None
    if exposicion is not None and len(exposicion):
        alineada = exposicion.reindex(patrimonio.index).fillna(0.0)
        en_mercado = float((alineada.abs() > 1e-9).mean()) * 100.0

    return Metricas(
        nombre=nombre,
        dias=int((patrimonio.index[-1] - patrimonio.index[0]).days),
        patrimonio_inicial=float(patrimonio.iloc[0]),
        patrimonio_final=float(patrimonio.iloc[-1]),
        cagr=crecimiento,
        volatilidad=volatilidad_anual(patrimonio),
        caida_maxima=peor,
        caida_duracion_dias=dias_caida,
        caida_desde=desde,
        caida_hasta=hasta,
        calmar=ratio,
        sortino=sortino(patrimonio),
        tiempo_en_mercado_pct=en_mercado,
        rotacion_anual=rotacion_anual,
        costo_anual_pct=costo_anual_pct,
        extra=extra or {},
    )
