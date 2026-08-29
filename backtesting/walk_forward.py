"""
Validacion walk-forward: la unica forma honesta de elegir un parametro.

EL PROBLEMA QUE RESUELVE
------------------------
Si probas 5 valores de un parametro sobre nueve anios de datos y te quedas
con el mejor, ese "mejor" ya vio todos los datos. No estas midiendo si el
parametro funciona: estas midiendo cuanto se puede ajustar un numero a un
pasado que ya conoces. Con suficientes intentos siempre encontras algo que
brilla, y siempre se apaga cuando lo sacas a la calle.

COMO FUNCIONA
-------------
Se parte la historia en ventanas encadenadas:

    [--- entrenar 3 anios ---][- probar 1 -]
              [--- entrenar 3 anios ---][- probar 1 -]
                        [--- entrenar 3 anios ---][- probar 1 -]

En cada ventana:
  1. Se prueban todos los candidatos SOLO sobre el tramo de entrenamiento.
  2. Se elige el mejor de ese tramo.
  3. Se aplica al tramo de prueba, que el candidato NUNCA vio.
  4. El resultado del tramo de prueba es el unico que cuenta.

Pegando todos los tramos de prueba se obtiene una curva de capital que
simula lo que habria pasado de verdad: reeligiendo el parametro cada anio
con la informacion disponible en ese momento, sin saber el futuro.

EL CAPITAL SE ARRASTRA
----------------------
Cada ventana de prueba arranca con el capital que dejo la anterior, no con
los 500 iniciales. Es lo que pasaria en la realidad, y hace que una perdida
temprana pese en todo lo que sigue.

QUE MIRAR EN EL RESULTADO
-------------------------
No solo el resultado final. Tambien:

  - CUANTO CAMBIA EL ELEGIDO entre ventanas. Si cada anio gana un valor
    distinto, no hay un optimo estable: hay ruido, y el proceso esta
    eligiendo al azar.
  - LA CONCENTRACION. Si el resultado fuera de muestra vuelve a depender de
    una sola operacion, no aprendimos nada.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from backtesting import backtest_engine as motor
from risk import position_sizing


@dataclass
class Ventana:
    """Una ventana de entrenamiento + prueba, con lo que se eligio y que paso."""

    numero: int
    entrena_desde: pd.Timestamp
    entrena_hasta: pd.Timestamp
    prueba_desde: pd.Timestamp
    prueba_hasta: pd.Timestamp
    elegido: Any
    resultado_entrenamiento: float
    metricas_prueba: motor.Metricas
    operaciones_prueba: list[motor.Operacion]
    candidatos_evaluados: dict[Any, float] = field(default_factory=dict)


@dataclass
class ResultadoWalkForward:
    ventanas: list[Ventana]
    operaciones: list[motor.Operacion]
    capital_inicial: float
    capital_final: float

    @property
    def elegidos(self) -> list[Any]:
        return [v.elegido for v in self.ventanas]

    @property
    def el_elegido_es_estable(self) -> bool:
        """True si el mismo valor gano en al menos la mitad de las ventanas."""
        if not self.ventanas:
            return False
        conteo: dict[Any, int] = {}
        for valor in self.elegidos:
            conteo[valor] = conteo.get(valor, 0) + 1
        return max(conteo.values()) >= len(self.ventanas) / 2

    @property
    def concentracion_pct(self) -> float:
        """Que porcentaje del resultado neto aporta la mejor operacion sola."""
        if not self.operaciones:
            return 0.0
        neto = sum(o.resultado_neto for o in self.operaciones)
        if neto == 0:
            return 0.0
        mejor = max(o.resultado_neto for o in self.operaciones)
        return mejor / neto * 100.0

    @property
    def metricas(self) -> motor.Metricas:
        """Las metricas agregadas de TODOS los tramos de prueba juntos."""
        ganancias = [o.resultado_neto for o in self.operaciones if o.resultado_neto > 0]
        perdidas = [o.resultado_neto for o in self.operaciones if o.resultado_neto <= 0]
        return motor.Metricas(
            operaciones=len(self.operaciones),
            ganadoras=len(ganancias),
            perdedoras=len(perdidas),
            capital_inicial=self.capital_inicial,
            capital_final=self.capital_final,
            ganancia_bruta=sum(ganancias),
            perdida_bruta=abs(sum(perdidas)),
            costos_totales=sum(o.costos for o in self.operaciones),
            mejor=max((o.resultado_neto for o in self.operaciones), default=0.0),
            peor=min((o.resultado_neto for o in self.operaciones), default=0.0),
            desde=self.ventanas[0].prueba_desde if self.ventanas else None,
            hasta=self.ventanas[-1].prueba_hasta if self.ventanas else None,
        )

    def informe(self) -> str:
        lineas = ["  Ventana  Entrenamiento          Prueba                 Elegido   Resultado"]
        for v in self.ventanas:
            lineas.append(
                f"  {v.numero:>7}  {v.entrena_desde.date()} a {v.entrena_hasta.date()}  "
                f"{v.prueba_desde.date()} a {v.prueba_hasta.date()}  "
                f"{str(v.elegido):>7}   {v.metricas_prueba.resultado_neto:>+9.2f} "
                f"({v.metricas_prueba.operaciones} ops)"
            )
        return "\n".join(lineas)


def _por_resultado_neto(metricas: motor.Metricas) -> float:
    return metricas.resultado_neto


def correr(
    df: pd.DataFrame,
    cfg_base: dict,
    par: str,
    temporalidad: str,
    candidatos: list[Any],
    aplicar: Callable[[dict, Any], None],
    anios_entrenamiento: int = 3,
    anios_prueba: int = 1,
    reglas_simbolo: position_sizing.ReglasSimbolo | None = None,
    criterio: Callable[[motor.Metricas], float] = _por_resultado_neto,
) -> ResultadoWalkForward:
    """
    Corre la validacion walk-forward.

    `aplicar(cfg, valor)` escribe el candidato en la config. Se pasa como
    funcion para que este modulo no sepa QUE parametro se esta validando:
    sirve igual para el multiplicador del trailing, para el ADX minimo o
    para lo que venga.
    """
    reglas_simbolo = reglas_simbolo or position_sizing.ReglasSimbolo()
    if df.empty:
        return ResultadoWalkForward([], [], 0.0, 0.0)

    # El descarte de los primeros dias tras el listado se hace UNA VEZ, sobre
    # el historico entero, antes de partirlo en ventanas. Si se dejara que lo
    # hiciera el motor en cada tramo, cada ventana perderia sus primeros 30
    # dias -- tanto las de entrenamiento (contaminando la eleccion del
    # parametro) como las de prueba (dejando sin medir casi el 9% del periodo
    # fuera de muestra, y un mes ciego despues de cada costura).
    df = motor._recortar_inicio(
        df, cfg_base.get("backtest_motor", {}).get("descartar_dias_iniciales", 0)
    )
    if df.empty:
        return ResultadoWalkForward([], [], 0.0, 0.0)

    inicio, fin = df.index[0], df.index[-1]
    capital_inicial = float(cfg_base["capital"]["monto"])
    capital = capital_inicial

    ventanas: list[Ventana] = []
    todas_las_operaciones: list[motor.Operacion] = []
    numero = 0
    corte_entrena = inicio

    while True:
        fin_entrena = corte_entrena + pd.DateOffset(years=anios_entrenamiento)
        fin_prueba = fin_entrena + pd.DateOffset(years=anios_prueba)
        if fin_entrena >= fin:
            break

        entrena = df[(df.index >= corte_entrena) & (df.index < fin_entrena)]
        prueba = df[(df.index >= fin_entrena) & (df.index < min(fin_prueba, fin))]
        if entrena.empty or prueba.empty:
            break

        numero += 1

        # --- Eleccion: SOLO con el tramo de entrenamiento -----------------
        puntajes: dict[Any, float] = {}
        for valor in candidatos:
            cfg = copy.deepcopy(cfg_base)
            cfg["capital"]["monto"] = capital
            aplicar(cfg, valor)
            r = motor.correr(entrena, cfg, par, temporalidad, reglas_simbolo,
                             recortar_inicio=False)
            puntajes[valor] = criterio(r.metricas)

        elegido = max(puntajes, key=lambda v: puntajes[v])

        # --- Juicio: con el tramo que el elegido nunca vio ----------------
        cfg = copy.deepcopy(cfg_base)
        cfg["capital"]["monto"] = capital
        aplicar(cfg, elegido)
        resultado = motor.correr(prueba, cfg, par, temporalidad, reglas_simbolo,
                                 recortar_inicio=False)

        capital += resultado.metricas.resultado_neto
        todas_las_operaciones.extend(resultado.operaciones)

        ventanas.append(
            Ventana(
                numero=numero,
                entrena_desde=entrena.index[0], entrena_hasta=entrena.index[-1],
                prueba_desde=prueba.index[0], prueba_hasta=prueba.index[-1],
                elegido=elegido,
                resultado_entrenamiento=puntajes[elegido],
                metricas_prueba=resultado.metricas,
                operaciones_prueba=resultado.operaciones,
                candidatos_evaluados=puntajes,
            )
        )
        corte_entrena = corte_entrena + pd.DateOffset(years=anios_prueba)

    return ResultadoWalkForward(ventanas, todas_las_operaciones, capital_inicial, capital)
