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
    # Cuantas operaciones tuvo cada candidato en el tramo de ENTRENAMIENTO.
    # Sin esto no se sabe si la eleccion se hizo con evidencia o a los dados.
    operaciones_entrenamiento: dict[Any, int] = field(default_factory=dict)

    @property
    def respaldo(self) -> int:
        """Operaciones de entrenamiento detras del valor que se eligio."""
        return self.operaciones_entrenamiento.get(self.elegido, 0)

    @property
    def margen(self) -> float | None:
        """
        Cuanto le saco el elegido al segundo mejor, en el entrenamiento.

        Se mide contra el SEGUNDO, no contra el peor: contra el peor siempre
        parece holgado y esconde un empate arriba. Un margen de casi cero
        significa que el entrenamiento no distinguio entre los dos mejores;
        gano uno por redondeo, no por ser mejor.
        """
        if len(self.candidatos_evaluados) < 2:
            return None
        ordenados = sorted(self.candidatos_evaluados.values(), reverse=True)
        return ordenados[0] - ordenados[1]

    @property
    def la_eleccion_fue_arbitraria(self) -> bool:
        """
        True si el tramo de entrenamiento directamente no daba con que elegir.

        Dos condiciones objetivas, sin umbrales inventados:
          - el valor elegido no produjo ninguna operacion, o
          - los dos mejores empataron exactamente.
        En ambos casos `max()` devolvio el primero de la lista y eso no es una
        decision.

        OJO CON ESTA BANDERA: es deliberadamente estricta y por eso casi nunca
        se activa. El 29-ago-2026 dio CERO en los cuatro tramos, incluida una
        ventana de ETHUSDT 1h que eligio sobre NUEVE operaciones. Elegir sobre
        nueve operaciones es basura y la bandera no lo ve. El dato que sirve
        es la columna cruda de `respaldo`, no esta bandera.
        """
        if self.respaldo == 0:
            return True
        margen = self.margen
        return margen is not None and margen == 0.0


ESTABLE = "ESTABLE"
DUDOSA = "DUDOSA"
INESTABLE = "INESTABLE"


@dataclass
class ResultadoWalkForward:
    ventanas: list[Ventana]
    operaciones: list[motor.Operacion]
    capital_inicial: float
    capital_final: float
    # El menu que se le ofrecio a cada ventana. Sin esto no se puede saber si
    # elegir "4 o 5" fue afinar o fue tirar los dados: depende de que tan
    # grande era el menu.
    candidatos: list[Any] = field(default_factory=list)

    @property
    def elegidos(self) -> list[Any]:
        return [v.elegido for v in self.ventanas]

    @property
    def dispersion_pct(self) -> float | None:
        """
        Cuanto del menu de candidatos abarcan las elecciones, en porcentaje.

        Con candidatos [2,3,4,5,6], elegir siempre 6 da 0%; elegir entre 4 y 6
        da 50%; elegir entre 2 y 6 da 100%, o sea que en algun anio el
        entrenamiento apunto a un extremo y en otro al opuesto.

        Devuelve None si los candidatos no son numeros ordenados (para un
        parametro categorico la distancia entre dos valores no significa
        nada).
        """
        elegidos = self.elegidos
        if not elegidos or not self.candidatos:
            return None
        try:
            recorrido = float(max(self.candidatos)) - float(min(self.candidatos))
            if recorrido <= 0:
                return 0.0
            usado = float(max(elegidos)) - float(min(elegidos))
        except (TypeError, ValueError):
            return None
        return usado / recorrido * 100.0

    @property
    def estabilidad(self) -> str:
        """
        ESTABLE / DUDOSA / INESTABLE, segun cuanto se movio la eleccion.

        POR QUE SE MIDE LA DISPERSION Y NO "CUANTAS VECES GANO EL MISMO VALOR"
        ----------------------------------------------------------------------
        El criterio anterior era "el mismo valor gano en al menos la mitad de
        las ventanas". Tiene dos defectos:

        1. Con pocas ventanas, una mayoria minima alcanza. El 29-ago-2026, en
           ETHUSDT 1h, los elegidos fueron [5, 5, 2, 6, 6, 6] -- van de punta
           a punta del menu -- y la bandera dijo "estable" porque 6.0 gano
           exactamente 3 de 6. En la corrida anterior el MISMO tramo daba
           "inestable"; lo unico que habia cambiado era tener una ventana
           menos.
        2. Trata los candidatos como etiquetas sueltas cuando son numeros
           ORDENADOS. Elegir 4 y despues 5 es casi ponerse de acuerdo. Elegir
           2 y despues 6 es no haber encontrado nada. Contar apariciones no
           distingue esos dos casos.

        El umbral: si las elecciones abarcan mas de la mitad del menu, el
        entrenamiento no esta localizando una region, esta recorriendo la
        carta. Esa frase vale independientemente de nuestros datos, que es
        justamente lo que se le pide a un criterio.

        ADVERTENCIA HONESTA: este criterio se escribio el 29-ago-2026 DESPUES
        de ver los cuatro resultados. Se eligio por el razonamiento de arriba
        y no por el veredicto que produce, pero el riesgo de haberse
        acomodado a los datos existe y hay que tenerlo presente. Por eso
        `dispersion_pct` se reporta siempre en crudo: si el umbral esta mal
        puesto, el numero de al lado lo delata.
        """
        if not self.ventanas:
            return INESTABLE

        dispersion = self.dispersion_pct
        if dispersion is None:
            # Candidatos no numericos: no se puede medir distancia. Se cae al
            # criterio viejo, que al menos agarra el caso extremo.
            conteo: dict[Any, int] = {}
            for valor in self.elegidos:
                conteo[valor] = conteo.get(valor, 0) + 1
            return ESTABLE if max(conteo.values()) > len(self.ventanas) / 2 else INESTABLE

        if dispersion <= 25.0:
            return ESTABLE
        if dispersion <= 50.0:
            return DUDOSA
        return INESTABLE

    @property
    def el_elegido_es_estable(self) -> bool:
        """Solo ESTABLE cuenta como estable. DUDOSA no es un si tibio."""
        return self.estabilidad == ESTABLE

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

    @property
    def ventanas_arbitrarias(self) -> list["Ventana"]:
        """Las ventanas donde el entrenamiento no daba con que elegir."""
        return [v for v in self.ventanas if v.la_eleccion_fue_arbitraria]

    @property
    def respaldo_minimo(self) -> int | None:
        """Operaciones de entrenamiento de la ventana peor respaldada."""
        if not self.ventanas:
            return None
        return min(v.respaldo for v in self.ventanas)

    def informe_de_candidatos(self) -> str:
        """
        Que puntaje sacó CADA candidato en CADA tramo de entrenamiento.

        POR QUE UNA MATRIZ Y NO UNA COMPARACION ENTRE DOS GRUPOS
        --------------------------------------------------------
        La pregunta que motivo esto era "cuanta distancia hay entre el grupo
        4-6 y el grupo 2-3". Partir el menu en esos dos grupos habria sido
        elegir la particion mirando los resultados que ya conocemos, que es
        exactamente el error que este proyecto trata de no cometer. La matriz
        no impone ninguna agrupacion: si los de arriba se agrupan, se ve; y si
        se agrupan de otra forma, tambien.

        El `*` marca el que gano. La ultima columna es la distancia entre el
        mejor y el peor candidato de esa ventana: si es chica, el parametro
        casi no cambia nada y elegirlo importa poco -- que es una respuesta
        distinta de "la eleccion fue un volado".
        """
        if not self.ventanas:
            return "  Sin ventanas."

        candidatos = self.candidatos or sorted(
            {c for v in self.ventanas for c in v.candidatos_evaluados}
        )
        ancho = 11
        cabecera = "  Ventana" + "".join(f"{str(c) + 'x':>{ancho}}" for c in candidatos)
        lineas = [cabecera + f"{'mejor-peor':>13}"]

        for v in self.ventanas:
            celdas = ""
            for c in candidatos:
                puntaje = v.candidatos_evaluados.get(c)
                if puntaje is None:
                    celdas += f"{'-':>{ancho}}"
                    continue
                marca = "*" if c == v.elegido else " "
                celdas += f"{puntaje:>{ancho - 1}.1f}{marca}"
            valores = list(v.candidatos_evaluados.values())
            recorrido = max(valores) - min(valores) if valores else 0.0
            lineas.append(f"  {v.numero:>7}" + celdas + f"{recorrido:>13.1f}")

        lineas.append("  (* = el elegido. Puntajes del tramo de ENTRENAMIENTO, en USDT.)")
        return chr(10).join(lineas)

    def informe(self) -> str:
        lineas = [
            "  Ventana  Entrenamiento          Prueba                 "
            "Elegido   Resultado          Respaldo"
        ]
        for v in self.ventanas:
            margen = "" if v.margen is None else f", +{v.margen:.2f} al 2do"
            aviso = "  <-- ARBITRARIA" if v.la_eleccion_fue_arbitraria else ""
            lineas.append(
                f"  {v.numero:>7}  {v.entrena_desde.date()} a {v.entrena_hasta.date()}  "
                f"{v.prueba_desde.date()} a {v.prueba_hasta.date()}  "
                f"{str(v.elegido):>7}   {v.metricas_prueba.resultado_neto:>+9.2f} "
                f"({v.metricas_prueba.operaciones} ops)"
                f"   {v.respaldo} ops{margen}{aviso}"
            )
        return chr(10).join(lineas)


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
        ops_entrena: dict[Any, int] = {}
        for valor in candidatos:
            cfg = copy.deepcopy(cfg_base)
            cfg["capital"]["monto"] = capital
            aplicar(cfg, valor)
            r = motor.correr(entrena, cfg, par, temporalidad, reglas_simbolo,
                             recortar_inicio=False)
            puntajes[valor] = criterio(r.metricas)
            ops_entrena[valor] = r.metricas.operaciones

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
                operaciones_entrenamiento=ops_entrena,
            )
        )
        corte_entrena = corte_entrena + pd.DateOffset(years=anios_prueba)

    return ResultadoWalkForward(
        ventanas, todas_las_operaciones, capital_inicial, capital, list(candidatos)
    )
