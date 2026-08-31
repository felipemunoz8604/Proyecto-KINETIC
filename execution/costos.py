r"""
Modelo de costos v2 -- lo que cuesta operar, separado por venue.

POR QUE SE REESCRIBE EL DE LA FASE 1
------------------------------------
El de la Fase 1 era un numero solo: 0,1% de comision y 0,05% de slippage,
iguales para todo. Servia porque solo habia un venue (Spot), un tipo de orden
(taker) y quince pares parecidos entre si.

Ninguna de esas tres cosas sigue siendo cierta:

- **Entran los perpetuos**, que cobran distinto Y cobran financiacion cada
  ocho horas. La financiacion no es un detalle: en una posicion sostenida un
  mes son 90 cobros, y puede superar largamente el ahorro en comisiones.
- **Entran las ordenes maker**, cuya ventaja NO esta en la comision (en Spot
  VIP 0 maker y taker cuestan lo mismo) sino en no cruzar el spread.
- **Entra un universo de 20**, y el puesto 20 por liquidez no se opera al
  mismo precio que BTC.

QUE NO MODELA ESTE ARCHIVO, Y HAY QUE SABERLO
---------------------------------------------
**El riesgo de no ejecucion de las ordenes maker.** Una orden maker puede no
completarse nunca. Suponer que siempre entra es regalarse el ahorro de
slippage sin pagar su costo, y ese sesgo es invisible en el resultado: se ve
igual que una estrategia buena. Quien use `TipoOrden.MAKER` tiene que modelar
el reintento por su cuenta (la especificacion propone cerrar a taker al dia
siguiente). Este modulo cobra lo que se le pide cobrar, no averigua si la
orden entro.

EL DESCUENTO POR BNB VIENE APAGADO A PROPOSITO
-----------------------------------------------
Binance descuenta 25% en Spot y 10% en futuros si se pagan las comisiones en
BNB. **Todavia no esta verificado contra la cuenta real de Felipe** -- la
especificacion lo deja como pendiente explicito de ingenieria. Hasta que se
verifique, el default es sin descuento, que es el supuesto caro. Un backtest
que se regala un 25% de descuento que despues no existe miente a favor.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Venue(Enum):
    """Donde se ejecuta. Cobran distinto y no se mezclan."""

    SPOT = "spot"
    PERPETUO_USDT_M = "perpetuo_usdt_m"


class TipoOrden(Enum):
    MAKER = "maker"
    TAKER = "taker"


@dataclass(frozen=True)
class EsquemaComisiones:
    """Las comisiones de un venue, en porcentaje POR LADO."""

    maker_pct: float
    taker_pct: float
    descuento_bnb_pct: float

    def comision_pct(self, tipo: TipoOrden, con_bnb: bool = False) -> float:
        base = self.maker_pct if tipo is TipoOrden.MAKER else self.taker_pct
        if con_bnb:
            base *= (1.0 - self.descuento_bnb_pct / 100.0)
        return base


# Nivel VIP 0, que es donde esta la cuenta. En Spot maker y taker cuestan lo
# mismo: la ventaja de maker esta en el spread, no en la comision.
COMISIONES: dict[Venue, EsquemaComisiones] = {
    Venue.SPOT: EsquemaComisiones(maker_pct=0.10, taker_pct=0.10,
                                  descuento_bnb_pct=25.0),
    Venue.PERPETUO_USDT_M: EsquemaComisiones(maker_pct=0.02, taker_pct=0.05,
                                             descuento_bnb_pct=10.0),
}


# --- Slippage ------------------------------------------------------------
#
# Por rango de liquidez dentro del universo, no un valor unico. Los tramos
# estan fijados de antemano y son pesimistas a proposito, en la misma linea
# que el 0,05% de la Fase 1 (que se eligio como cinco veces el spread tipico
# de BTCUSDT). Se pueden refinar midiendo spreads reales por rango, pero eso
# se mide ANTES de correr, no despues de ver el resultado.

TRAMOS_DE_SLIPPAGE: tuple[tuple[int, float], ...] = (
    (5, 0.03),    # puestos 1 a 5
    (12, 0.05),   # puestos 6 a 12
    (20, 0.10),   # puestos 13 a 20
)

# Una orden maker no cruza el spread: ese es todo su ahorro. Es POR LADO, o
# sea 0,02% en viaje de ida y vuelta, que es el numero de la especificacion.
# Plano, porque lo que se paga no es el rango sino el riesgo de que la orden
# no entre, y eso este modulo no lo cobra (ver el encabezado).
SLIPPAGE_MAKER_PCT = 0.01


def slippage_pct(rango: int, tipo: TipoOrden = TipoOrden.TAKER) -> float:
    """
    Slippage por lado, en porcentaje, segun el puesto en el universo.

    `rango` es 1-based: 1 es el mas liquido. Un rango mayor al universo cobra
    el peor tramo -- no es un error, pero tampoco se lo premia con el
    slippage del puesto 20.
    """
    if rango < 1:
        raise ValueError(f"el rango de liquidez es 1-based, llego {rango}")
    if tipo is TipoOrden.MAKER:
        return SLIPPAGE_MAKER_PCT
    for tope, valor in TRAMOS_DE_SLIPPAGE:
        if rango <= tope:
            return valor
    return TRAMOS_DE_SLIPPAGE[-1][1]


# --- El modelo -----------------------------------------------------------

@dataclass(frozen=True)
class ModeloDeCostos:
    """
    Un venue, un tipo de orden, y la decision del BNB. Inmutable a proposito:
    si una estrategia opera en dos venues, son dos modelos, no uno con un
    parametro que cambia a mitad de camino.
    """

    venue: Venue = Venue.SPOT
    tipo_orden: TipoOrden = TipoOrden.TAKER
    con_bnb: bool = False

    @property
    def comision_pct(self) -> float:
        return COMISIONES[self.venue].comision_pct(self.tipo_orden, self.con_bnb)

    def slippage_pct(self, rango: int) -> float:
        return slippage_pct(rango, self.tipo_orden)

    def peaje_por_lado_pct(self, rango: int) -> float:
        return self.comision_pct + self.slippage_pct(rango)

    def peaje_ida_y_vuelta_pct(self, rango: int) -> float:
        return 2.0 * self.peaje_por_lado_pct(rango)

    def costo_de_lado(self, nocional: float, rango: int) -> float:
        """
        Lo que cuesta mover `nocional` USDT una vez, en USDT. Siempre positivo:
        comprar y vender cuestan lo mismo.
        """
        if nocional < 0:
            raise ValueError("el nocional de un lado se pasa en valor absoluto")
        return nocional * self.peaje_por_lado_pct(rango) / 100.0

    def precio_efectivo(self, precio: float, rango: int, *,
                        comprando: bool) -> float:
        """
        El precio al que se ejecuta de verdad, con el slippage adentro. Compras
        mas caro y vendes mas barato -- nunca al reves.

        La comision NO esta aca: se cobra aparte sobre el nocional, porque
        meterla en el precio la haria desaparecer del recuento de costos.
        """
        desvio = self.slippage_pct(rango) / 100.0
        return precio * (1.0 + desvio) if comprando else precio * (1.0 - desvio)


# --- Financiacion --------------------------------------------------------

# Los cortes teoricos de un perpetuo de 8 horas. Se dejan como referencia,
# pero NO se usan para cobrar: ver `financiacion_acumulada`.
HORAS_DE_FINANCIACION = (0, 8, 16)


class FinanciacionFaltante(RuntimeError):
    """
    Falta la tasa de un momento en que habia posicion abierta.

    Es un error y no un cero por una razon: un cero silencioso convierte un
    backtest de perpetuos invalido en uno que se ve perfecto.
    """


def momentos_de_financiacion(desde: pd.Timestamp,
                             hasta: pd.Timestamp,
                             horas: int = 8) -> pd.DatetimeIndex:
    """
    Los cortes TEORICOS que atraviesa una posicion, cada `horas` horas.

    Convencion: `desde < momento <= hasta`. Se cobra si la posicion estaba
    abierta EN el corte. Cerrar exactamente a las 16:00 paga ese corte; es el
    lado pesimista de una ambiguedad real.

    Sirve para razonar y para las pruebas. **Para cobrar de verdad se usan los
    cobros reales del archivo**, porque el dato real no se parece a esto: hay
    simbolos con intervalos de 2, 4 y 8 horas, y sellos de tiempo corridos un
    milisegundo (`12:00:00.001`). Medido el 31-ago-2026 sobre 424.089 cobros.
    """
    desde = pd.Timestamp(desde)
    hasta = pd.Timestamp(hasta)
    if hasta < desde:
        raise ValueError("la posicion no puede cerrarse antes de abrirse")
    if horas <= 0 or 24 % horas:
        raise ValueError(f"intervalo de financiacion invalido: {horas} h")
    dia = desde.floor("D")
    cortes = pd.DatetimeIndex([
        dia + pd.Timedelta(days=d, hours=h)
        for d in range((hasta.floor("D") - dia).days + 2)
        for h in range(0, 24, horas)
    ])
    return cortes[(cortes > desde) & (cortes <= hasta)]


def flujo_de_financiacion(nocional_firmado: float, tasa: float) -> float:
    """
    Lo que entra (positivo) o sale (negativo) en UN corte de financiacion.

    `nocional_firmado`: positivo si estas largo, negativo si estas corto.
    Tasa positiva => los largos le pagan a los cortos. De ahi el signo menos.
    """
    return -nocional_firmado * tasa


def cobros_entre(tasas: pd.Series, desde: pd.Timestamp,
                 hasta: pd.Timestamp) -> pd.Series:
    """Los cobros REALES que atraviesa la posicion: `desde < momento <= hasta`."""
    if tasas.empty or not isinstance(tasas.index, pd.DatetimeIndex):
        return tasas.iloc[0:0]
    return tasas.loc[(tasas.index > pd.Timestamp(desde))
                     & (tasas.index <= pd.Timestamp(hasta))]


def financiacion_acumulada(nocional_firmado: float,
                           tasas: pd.Series,
                           desde: pd.Timestamp,
                           hasta: pd.Timestamp,
                           horas: float | None = None) -> float:
    """
    Suma la financiacion de una posicion de nocional constante.

    Cobra los cobros **reales** del archivo, no una grilla generada. La primera
    version generaba los cortes en 00, 08 y 16 en punto y exigia que
    coincidieran exactamente con el indice; contra el dato de verdad eso habria
    fallado en todo: hay simbolos de 2 y 4 horas, y sellos corridos un
    milisegundo.

    `horas` es el intervalo declarado del simbolo. Si se pasa, se verifica que
    no falte ningun cobro: un hueco mayor a una vez y media el intervalo
    **levanta** en vez de valer cero.
    """
    desde = pd.Timestamp(desde)
    hasta = pd.Timestamp(hasta)
    if hasta < desde:
        raise ValueError("la posicion no puede cerrarse antes de abrirse")

    cobros = cobros_entre(tasas, desde, hasta)
    if horas is not None and horas > 0:
        limite = pd.Timedelta(hours=horas * 1.5)
        bordes = pd.DatetimeIndex([desde]).append(cobros.index)
        bordes = bordes.append(pd.DatetimeIndex([hasta]))
        huecos = bordes.to_series().diff().dropna()
        grandes = huecos[huecos > limite]
        if len(grandes):
            raise FinanciacionFaltante(
                f"hay un hueco de {grandes.iloc[0]} entre {desde} y {hasta}, "
                f"con intervalo declarado de {horas} h. Falta dato de "
                "financiacion, y suponer cero haria pasar por bueno un "
                "backtest de perpetuos invalido."
            )
    if cobros.empty:
        return 0.0
    return float(sum(flujo_de_financiacion(nocional_firmado, t)
                     for t in cobros))
