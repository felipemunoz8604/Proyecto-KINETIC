"""
Donde va el stop, y como se mueve.

STOP INICIAL
------------
    stop = precio_entrada - 2 x ATR(14)

Se usa ATR y no un porcentaje fijo porque un 3% en un mercado dormido es un
mundo y en uno enloquecido es ruido. El ATR se adapta solo: cuando el
mercado se agita, el stop se aleja para no saltar por una sacudida normal.

TRAILING TIPO CHANDELIER
------------------------
    stop_nuevo = maximo(stop_actual, mayor_cierre_desde_la_entrada - 2 x ATR)

Dos propiedades que definen todo:

1. NUNCA BAJA. El `maximo(...)` lo garantiza. Un trailing que retrocede no
   es un trailing: es una forma elegante de ampliar la perdida cada vez que
   el precio va en contra.
2. Se cuelga del mayor CIERRE, no del mayor maximo. Una mecha larga de un
   minuto raro subiria el stop a un nivel que el precio nunca sostuvo, y la
   proxima vela normal lo tocaria. Usar cierres exige que el precio se haya
   QUEDADO ahi.

El break-even (mover el stop a la entrada cuando la operacion va ganando)
NO esta implementado y es a proposito. TITAN tuvo un bug de break-even que
nunca se activaba y que ninguna prueba automatizada atrapo -- solo lo
encontro la observacion en vivo. Si mas adelante se quiere, se agrega como
una regla explicita y con su propia prueba, no como un caso escondido
dentro del trailing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EstadoStop:
    """
    El stop de una posicion abierta, y de donde salio.

    Hay DOS multiplicadores y hacen trabajos distintos:

      - `multiplicador_atr` (el inicial) define cuanto se arriesga, y por lo
        tanto cuanto se compra. Tocarlo cambia el tamano de la posicion.
      - `multiplicador_trailing` define cuanto aire se le da a una ganadora
        para que corra. Tocarlo NO cambia el riesgo de la operacion.

    No hay ninguna razon para que sean el mismo numero, y config.yaml ya los
    declaraba por separado.
    """

    precio_entrada: float
    stop_actual: float
    stop_inicial: float
    mayor_cierre: float
    multiplicador_atr: float
    multiplicador_trailing: float
    veces_movido: int = 0

    @property
    def en_ganancia_asegurada(self) -> bool:
        """True si el stop ya esta por encima de la entrada: pase lo que pase, se gana."""
        return self.stop_actual > self.precio_entrada

    @property
    def distancia_pct(self) -> float:
        return (self.precio_entrada - self.stop_actual) / self.precio_entrada * 100.0


def stop_inicial(precio_entrada: float, atr: float, multiplicador: float = 2.0) -> float:
    """Calcula el stop de apertura. Siempre por debajo de la entrada."""
    if atr <= 0:
        raise ValueError(
            f"El ATR tiene que ser > 0 para poner un stop, y llego {atr}. "
            "Suele significar que el indicador todavia no calento."
        )
    if precio_entrada <= 0:
        raise ValueError(f"Precio de entrada invalido: {precio_entrada}")

    stop = precio_entrada - multiplicador * atr
    if stop <= 0:
        raise ValueError(
            f"El stop calculado ({stop:.4f}) da cero o negativo: el ATR ({atr:.4f}) "
            f"es enorme frente al precio ({precio_entrada:.4f}). Esa operacion no "
            "se puede dimensionar y hay que descartarla."
        )
    return stop


def abrir(
    precio_entrada: float,
    atr: float,
    multiplicador: float = 2.0,
    multiplicador_trailing: float | None = None,
) -> EstadoStop:
    """
    Crea el estado del stop al abrir una posicion.

    Si no se pasa `multiplicador_trailing`, el trailing usa el mismo numero
    que el stop inicial (el comportamiento de siempre).
    """
    inicial = stop_inicial(precio_entrada, atr, multiplicador)
    return EstadoStop(
        precio_entrada=precio_entrada,
        stop_actual=inicial,
        stop_inicial=inicial,
        mayor_cierre=precio_entrada,
        multiplicador_atr=multiplicador,
        multiplicador_trailing=(
            multiplicador if multiplicador_trailing is None else multiplicador_trailing
        ),
    )


def actualizar(estado: EstadoStop, cierre: float, atr: float) -> EstadoStop:
    """
    Recalcula el trailing con una vela nueva ya cerrada.

    Devuelve un estado NUEVO; no modifica el que recibe. Asi el backtest no
    puede corromper el historial sin querer.
    """
    if atr <= 0:
        # Sin ATR valido no se toca nada: dejar el stop donde esta es seguro,
        # moverlo con un numero basura no.
        return estado

    mayor_cierre = max(estado.mayor_cierre, cierre)
    candidato = mayor_cierre - estado.multiplicador_trailing * atr

    # El maximo() es la linea que hace que el stop nunca retroceda.
    nuevo_stop = max(estado.stop_actual, candidato)
    movido = estado.veces_movido + (1 if nuevo_stop > estado.stop_actual else 0)

    return EstadoStop(
        precio_entrada=estado.precio_entrada,
        stop_actual=nuevo_stop,
        stop_inicial=estado.stop_inicial,
        mayor_cierre=mayor_cierre,
        multiplicador_atr=estado.multiplicador_atr,
        multiplicador_trailing=estado.multiplicador_trailing,
        veces_movido=movido,
    )


def toco_el_stop(estado: EstadoStop, minimo_de_la_vela: float) -> bool:
    """
    True si la vela llego a tocar el stop.

    Se mira el MINIMO de la vela, no el cierre: si el precio bajo hasta el
    stop en algun momento, la orden se ejecuto, aunque despues rebotara y
    cerrara arriba. Suponer lo contrario hace que el backtest se salve de
    perdidas que en la realidad ocurrieron.
    """
    return minimo_de_la_vela <= estado.stop_actual
