r"""
La vara corregida: c_up, c_down, la frontera derivada y la CDaR -- C-A' y C-B'.

DE DONDE SALE Y QUE REEMPLAZA
-------------------------------
De la respuesta del analista externo del 2-sep-2026, que acepto las tres
objeciones que le hicimos y reemplazo los umbrales inventados (70% y 40%) por
algo derivado.

**Este modulo NO reemplaza a `metrics/regimen.py`, lo sucede.** `regimen.py`
implementa el criterio viejo -- C-A y C-B condicionados a una ventana de
tendencia de 12 meses -- que se retiro porque esa ventana resulto ser un
parametro libre que movia C-B un factor de 15. Se conserva a proposito: si el
veredicto fuera distinto con una vara y con la otra, eso hay que poder verlo.

LOS TRES DEFECTOS QUE ARREGLA
-------------------------------
1. **C-A componia retornos de meses no contiguos.** Multiplicar (1+r) sobre
   meses salteados supone que fueron consecutivos, y no lo fueron. Aca todo va
   en **log-retornos, que son aditivos**: sumar meses salteados es legitimo.
2. **La ventana de regimen era un parametro libre.** Se elimina: un periodo es
   alcista si **B1 subio en ese mismo periodo**. Sin ventana, sin rezago.
3. **El denominador quedaba cerca de cero.** Con el etiquetado rezagado, B1
   acumulaba -12,5% en los meses "bajistas" -- 9 de 17 habian subido. Con el
   signo del propio periodo, el conjunto que bajo tiene un log-retorno
   agregado grande y negativo, y el cociente queda estable.

POR QUE PARTICIONAR POR EL SIGNO DEL PROPIO MES NO ES MIRAR AL FUTURO
-----------------------------------------------------------------------
Es la objecion obvia y hay que tenerla contestada, porque el proyecto entero
descansa en no mirar al futuro.

**c_up y c_down son criterios de EVALUACION, no reglas de trading.** La
estrategia nunca ve la etiqueta: los retornos ya estan generados y la
particion solo decide como se reportan. Habria anticipacion si la exposicion
se decidiera con la etiqueta, y no se decide.

Es distinto de lo que hicimos el 1-sep-2026 en `tools/sensibilidad_regimen.py`,
donde SACAMOS meses del conjunto segun su propio resultado para limpiar un
numerador. Eso si contaminaba, y por eso quedo marcado ahi como diagnostico y
no como criterio. **Particionar la muestra entera de forma exhaustiva es otra
cosa: no se descarta nada.**

LA FRONTERA ES UNA IDENTIDAD, NO UN UMBRAL
--------------------------------------------
Sean, en log-retornos sobre la ventana de evaluacion:

    U = suma de los log-retornos de B1 en los periodos en que subio  (> 0)
    D = suma de los log-retornos de B1 en los periodos en que bajo   (< 0)

Entonces B1 total = U + D, y la estrategia total = c_up*U + c_down*D, **por
definicion de c_up y c_down y porque los logaritmos suman**. Pedir que la
estrategia iguale a B1 es pedir

    c_up*U + c_down*D  >=  U + D

y despejando c_up, con R = |D|/U:

    c_up  >=  1 - (1 - c_down) * R

**No hay ningun numero elegido en esa linea.** R se mide una vez sobre B1 y la
frontera queda determinada. `test_la_frontera_es_exactamente_ganarle_a_b1`
comprueba que pasar la frontera y superar el retorno total de B1 son el mismo
evento, no dos parecidos.

Y de ahi sale la lectura incomoda: **una estrategia a exposicion constante b
sobre los log-retornos puntua c_up = c_down = b, y con R < 1 solo pasa si
b >= 1.** Media exposicion no puede pasar por construccion. Es lo que hace que
la vara sea vara.

POR QUE LA CAIDA SE MIDE CON CDaR Y NO CON LA CAIDA MAXIMA
-------------------------------------------------------------
La caida maxima tiene **una sola observacion**: es un unico numero sacado de
un unico tramo de la historia. E0 quedo en 0,525 contra un objetivo de 0,50, y
esa diferencia no se distingue de ruido con una observacion.

La CDaR al 95% es el promedio del peor 5% de la distribucion diaria de caida.
Tiene cientos de observaciones, admite intervalo de confianza y es coherente.
La caida maxima se sigue reportando; el criterio se evalua sobre la CDaR.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from metrics import metricas

# Las tres periodicidades. El criterio se fija en mensual, que es la
# convencion; las otras dos son control de robustez -- si el veredicto cambia
# con el periodo, eso hay que decirlo, no elegir el que convenga.
MENSUAL, SEMANAL, TRIMESTRAL = "ME", "W", "QE"
_A_PERIODO = {MENSUAL: "M", SEMANAL: "W", TRIMESTRAL: "Q"}

NIVEL_CDAR = 0.95
CAIDA_OBJETIVO = 0.50          # "la mitad de la caida", el objetivo de Felipe
BLOQUE_MESES = 3
EPISODIOS = 3                  # cuantos episodios de caida entran en C-B'
MESES_POR_ANIO = 12

# La frontera es una igualdad exacta, y `exigido` se calcula dividiendo y
# volviendo a multiplicar. Una estrategia que empate EXACTO con B1 puede caer
# del lado equivocado por 1e-16, o sea por aritmetica de punto flotante y no
# por su resultado. Esta tolerancia no es un umbral aflojado: es reconocer que
# a esa distancia la estrategia y el mercado son indistinguibles.
TOLERANCIA = 1e-9


def log_por_periodo(patrimonio: pd.Series, regla: str = MENSUAL) -> pd.Series:
    """
    Log-retornos por periodo, sin perder el tramo inicial.

    El arreglo del tramo inicial es el mismo que en `regimen._mensual` y en
    `robustez.retiro_top_k`, y esta por el mismo motivo: `resample().last()`
    seguido de un cambio porcentual descarta el primer valor, y con el se
    pierde entero el tramo del inicio de la serie al primer cierre de periodo.
    """
    if regla not in _A_PERIODO:
        raise ValueError(f"Periodicidad desconocida: {regla!r}. "
                         f"Las validas son {sorted(_A_PERIODO)}.")
    patrimonio = patrimonio.dropna()
    cierres = patrimonio.resample(regla).last().dropna()
    serie = pd.concat([patrimonio.iloc[:1], cierres])
    serie = serie[~serie.index.duplicated(keep="first")].sort_index()
    r = np.log(serie / serie.shift(1)).dropna()
    r.index = r.index.to_period(_A_PERIODO[regla])
    return r[~r.index.duplicated(keep="last")]


@dataclass(frozen=True)
class Frontera:
    """U, D y R medidos sobre B1. Fija la frontera y cuesta cero pruebas."""

    regla: str
    u: float                    # log-retorno agregado de B1 donde subio
    d: float                    # ... donde bajo. Negativo.
    periodos_arriba: int
    periodos_abajo: int

    @property
    def r(self) -> float:
        """R = |D| / U. Cuanto pesa la baja contra la subida en esta ventana."""
        return abs(self.d) / self.u if self.u else float("nan")

    def exige(self, c_down: float) -> float:
        """El c_up minimo para igualar a B1, dado ese c_down."""
        return 1.0 - (1.0 - c_down) * self.r


def frontera(patrimonio_b1: pd.Series, regla: str = MENSUAL) -> Frontera:
    """U, D y R de B1. Es el paso 1: se mide una vez y no depende de nadie."""
    b = log_por_periodo(patrimonio_b1, regla)
    arriba = b > 0
    return Frontera(
        regla=regla,
        u=float(b[arriba].sum()),
        d=float(b[~arriba].sum()),
        periodos_arriba=int(arriba.sum()),
        periodos_abajo=int((~arriba).sum()),
    )


@dataclass(frozen=True)
class Captura:
    """c_up y c_down de una curva, ya contrastados contra la frontera."""

    nombre: str
    regla: str
    c_up: float
    c_down: float
    exigido: float
    periodos_arriba: int
    periodos_abajo: int

    @property
    def pasa(self) -> bool:
        return bool(self.c_up >= self.exigido - TOLERANCIA)

    @property
    def margen(self) -> float:
        """Cuanto le falta (negativo) o le sobra (positivo) de captura."""
        return self.c_up - self.exigido


def capturas(patrimonio: pd.Series,
             patrimonio_b1: pd.Series,
             nombre: str = "",
             regla: str = MENSUAL) -> Captura:
    """
    C-A': captura al alza y a la baja, particionadas por el signo de B1.

    `c_up` alto es bueno. `c_down` bajo es bueno, y `c_down` **negativo**
    significa que la estrategia gana cuando el mercado pierde -- que es lo que
    hace E0, y por eso la palabra "proteccion" se le quedaba corta.
    """
    e = log_por_periodo(patrimonio, regla)
    b = log_por_periodo(patrimonio_b1, regla)
    comunes = e.index.intersection(b.index)
    e, b = e.loc[comunes], b.loc[comunes]
    arriba = b > 0

    u, d = float(b[arriba].sum()), float(b[~arriba].sum())
    c_up = float(e[arriba].sum()) / u if u else float("nan")
    c_down = float(e[~arriba].sum()) / d if d else float("nan")
    r = abs(d) / u if u else float("nan")

    return Captura(
        nombre=nombre,
        regla=regla,
        c_up=c_up,
        c_down=c_down,
        exigido=1.0 - (1.0 - c_down) * r,
        periodos_arriba=int(arriba.sum()),
        periodos_abajo=int((~arriba).sum()),
    )


def caida_diaria(patrimonio: pd.Series) -> pd.Series:
    """Caida contra el maximo previo, dia a dia. Cero o negativa."""
    patrimonio = patrimonio.dropna()
    return patrimonio / patrimonio.cummax() - 1.0


def cdar(patrimonio: pd.Series, nivel: float = NIVEL_CDAR) -> float:
    """
    CDaR: el promedio del peor (1-nivel) de la distribucion diaria de caida.

    Negativa, como la caida maxima. Y nunca mas extrema que ella en valor
    absoluto, porque promedia una cola en vez de quedarse con el minimo -- eso
    es justamente lo que le da observaciones.

    La cola se toma con al menos un dia: con series cortas, redondear a cero
    devolveria 0,0 y eso diria "no cayo nunca", que es falso.
    """
    if not 0.0 < nivel < 1.0:
        raise ValueError(f"El nivel va entre 0 y 1 y llego {nivel}.")
    caidas = caida_diaria(patrimonio).to_numpy()
    if not len(caidas):
        return float("nan")
    cuantos = max(1, int(round(len(caidas) * (1.0 - nivel))))
    return float(np.sort(caidas)[:cuantos].mean())


def fraccion_de_cdar(patrimonio: pd.Series,
                     patrimonio_b1: pd.Series,
                     nivel: float = NIVEL_CDAR) -> float:
    """
    C-B': la CDaR de la estrategia sobre la de B1, curva completa.

    **Sin condicionar al regimen.** La caida es un estadistico de trayectoria:
    recortarla sobre un conjunto de periodos no contiguos arma una curva que
    nunca existio, y fue lo que produjo el factor de 15 de la tabla del
    1-sep-2026.
    """
    propia, referencia = cdar(patrimonio, nivel), cdar(patrimonio_b1, nivel)
    if not referencia:
        return float("nan")
    return abs(propia) / abs(referencia)


def intervalo_de_exceso(patrimonio: pd.Series,
                        patrimonio_b1: pd.Series,
                        *,
                        bloque_meses: int = BLOQUE_MESES,
                        remuestreos: int = 10_000,
                        semilla: int = 20260903) -> tuple[float, float]:
    """
    C-C': IC 95% del exceso MENSUAL de log-retorno contra B1, por bloques.

    Cambia respecto del C-C anterior, que remuestreaba el cociente de captura y
    preguntaba si excluia 1,0. Con la frontera, la indiferencia ya no esta en
    1,0 sino en el punto de la frontera, asi que la forma limpia es medir
    directamente **el exceso** y pedir que su intervalo excluya cero.

    Por bloques y no por meses sueltos, por la misma razon que el bootstrap del
    CAGR: los retornos vienen en rachas y romperlas devuelve un intervalo
    demasiado angosto.
    """
    e = log_por_periodo(patrimonio, MENSUAL)
    b = log_por_periodo(patrimonio_b1, MENSUAL)
    comunes = e.index.intersection(b.index)
    exceso = (e.loc[comunes] - b.loc[comunes]).to_numpy()
    n = len(exceso)
    if n < bloque_meses * 2:
        return (float("nan"), float("nan"))

    rng = np.random.default_rng(semilla)
    bloques = max(1, n // bloque_meses)
    inicios = rng.integers(0, n - bloque_meses + 1, size=(remuestreos, bloques))
    indices = (inicios[:, :, None] + np.arange(bloque_meses)).reshape(
        remuestreos, -1)
    medias = exceso[indices].mean(axis=1)
    return (float(np.percentile(medias, 2.5)),
            float(np.percentile(medias, 97.5)))


def episodios_de_caida(patrimonio: pd.Series,
                       cuantos: int = EPISODIOS) -> list[float]:
    """
    Los `cuantos` peores episodios de caida pico-a-valle, sin superponerse.

    Es el reemplazo de la CDaR que propuso el analista el 4-sep-2026, y arregla
    el defecto que le encontramos: **la caida maxima tiene una sola observacion
    porque es un EPISODIO, no porque sea diaria.** Contar dias no multiplica
    nada -- un tramo en efectivo aporta 91 copias del mismo numero. Contar
    episodios si: son eventos distintos de verdad.

    Cada episodio se toma entero, del pico a la recuperacion, y despues se lo
    saca de la serie para buscar el siguiente. Asi no se cuenta dos veces el
    mismo derrumbe partido en dos.

    Devuelve valores negativos, del peor al menos malo.
    """
    if cuantos < 1:
        raise ValueError(f"Hacen falta al menos 1 episodio y llegaron {cuantos}.")
    segmentos = [patrimonio.dropna()]
    encontrados: list[float] = []
    for _ in range(cuantos):
        mejor = None
        for i, seg in enumerate(segmentos):
            if len(seg) < 2:
                continue
            peor, _, pico, fin = metricas.caida_maxima(seg)
            if peor < 0 and (mejor is None or peor < mejor[1]):
                mejor = (i, peor, pico, fin)
        if mejor is None:
            break
        i, peor, pico, fin = mejor
        seg = segmentos.pop(i)
        encontrados.append(float(peor))
        # Lo de antes del pico y lo de despues de la recuperacion siguen en
        # juego; el episodio en si sale, para no contarlo partido en dos.
        antes, despues = seg.loc[:pico], seg.loc[fin:]
        segmentos.extend(x for x in (antes, despues) if len(x) >= 2)
    return encontrados


def caida_por_episodios(patrimonio: pd.Series,
                        cuantos: int = EPISODIOS) -> float:
    """La media de la profundidad de los `cuantos` peores episodios."""
    episodios = episodios_de_caida(patrimonio, cuantos)
    if not episodios:
        return 0.0
    return float(np.mean(episodios))


def fraccion_por_episodios(patrimonio: pd.Series,
                           patrimonio_b1: pd.Series,
                           cuantos: int = EPISODIOS) -> float:
    """C-B' medida sobre episodios: la de la estrategia sobre la de B1."""
    propia = caida_por_episodios(patrimonio, cuantos)
    referencia = caida_por_episodios(patrimonio_b1, cuantos)
    if not referencia:
        return float("nan")
    return abs(propia) / abs(referencia)


def exceso_detectable(bajo: float, alto: float,
                      periodos_por_anio: int = MESES_POR_ANIO) -> float:
    """
    Cuanto exceso ANUAL sobre el benchmark haria falta para que C-C' lo vea.

    El semiancho del intervalo del exceso mensual de log-retorno es la barra
    que hay que superar para que el IC deje de contener cero. Anualizado y
    pasado a retorno simple, dice **cuanto tendria que rendir una estrategia
    por encima de B1 para que ESTA MUESTRA pudiera certificarlo.**

    Es un resultado sobre la muestra, no sobre las estrategias: aunque una
    septima funcionara, con 60 meses y un solo ciclo esta ventana no podria
    demostrarlo. Es el hallazgo que el analista propone como central, y por eso
    esta calculado aca y no a mano en una planilla.
    """
    if not (np.isfinite(bajo) and np.isfinite(alto)):
        return float("nan")
    semiancho = (alto - bajo) / 2.0
    return math.expm1(semiancho * periodos_por_anio)
