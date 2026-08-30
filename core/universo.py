"""
Reconstruccion del universo mes a mes, sin sesgo de supervivencia.

QUE PROBLEMA RESUELVE
---------------------
La Fase 1 eligio su universo **una vez, con la lista de hoy**: los 15 pares
que en agosto de 2026 seguian operando y tenian historia desde 2019. Eso
parece inocente y no lo es. Preguntarle al presente quien existia en 2020 es
preguntarle a los sobrevivientes, y los sobrevivientes ganaron -- por eso
sobrevivieron.

Medido: 460 pares USDT operando hoy contra 190 deslistados. **La Fase 1 vio el
71% del universo descargado, y ninguno de los muertos.** La literatura estima
el costo de ese sesgo en 62% anualizado para carteras equiponderadas.

LA REGLA QUE GOBIERNA TODO ESTE ARCHIVO
----------------------------------------
**En la fecha t solo se puede mirar informacion anterior a t.** No "casi
solo": ni un dia. Si el universo del 1-mar-2021 se arma con el volumen de
marzo, la cartera esta comprando lo que va a ser liquido, no lo que era
liquido.

Esta escrito de una sola forma en un solo lugar -- `_hasta(panel, fecha)` --
porque es el tipo de regla que se rompe en el segundo sitio donde se
reimplementa. Hay pruebas que verifican la propiedad de frente: un simbolo que
muere en 2022 tiene que aparecer en el universo de 2020, y ninguna decision
puede cambiar si se le agregan datos posteriores.

LOS FILTROS, Y CUALES SON DE CADA TIPO
---------------------------------------
- **Estaticos** (dependen solo del nombre): contra USDT, sin stablecoins, sin
  tokens apalancados. Se aplican al descargar, en `archivo_binance`.
- **Por fecha** (dependen de que se sabia en t): antiguedad minima, que siga
  operando, y el ranking por liquidez. Se aplican aca.

Mezclarlos seria decidir hoy quien estaba en el universo en 2020.

EL SUSTITUTO DE LIQUIDEZ
------------------------
La literatura ordena por capitalizacion de mercado. El archivo de Binance no
la trae, asi que se ordena por **mediana del volumen cotizado diario de los
ultimos 30 dias**. Es una desviacion consciente y queda declarada: puede
cambiar la composicion del universo de formas que no se midieron.

Se usa la mediana y no la media a proposito. Un solo dia de volumen anormal
--un anuncio, un pump-- mueve la media lo suficiente como para meter una
moneda ilíquida en el top 20, y esa es exactamente la que despues no se puede
vender al precio que dice el backtest.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# De la especificacion de la Fase 2, seccion 4.1. Fijados de antemano.
TAMANO_UNIVERSO = 20
DIAS_MINIMOS_DE_HISTORIA = 180
DIAS_VENTANA_LIQUIDEZ = 30

# Cuantos dias sin operar hacen que un par se considere muerto en la fecha t.
# No esta en la especificacion y hace falta: sin esto, un par que dejo de
# operar en 2021 seguiria entrando al universo de 2023 con el volumen que
# tenia en su mejor momento. Que un par no tenga velas recientes es
# informacion disponible en t, asi que no es mirar al futuro.
DIAS_DE_GRACIA = 7


@dataclass
class Panel:
    """
    Los datos de todos los simbolos, alineados por fecha.

    Dos tablas anchas: filas = dias, columnas = simbolos. Un `NaN` significa
    que ese simbolo no tenia vela ese dia -- porque todavia no existia, porque
    ya lo deslistaron, o porque falta el dato. Los tres casos se distinguen
    mirando `primera_vela` y `ultima_vela`.
    """

    cierres: pd.DataFrame
    volumen_cotizado: pd.DataFrame

    @property
    def simbolos(self) -> list[str]:
        return list(self.cierres.columns)

    @property
    def primera_vela(self) -> pd.Series:
        return self.cierres.apply(lambda c: c.first_valid_index())

    @property
    def ultima_vela(self) -> pd.Series:
        """
        El ultimo dia con dato de cada simbolo.

        Es como se detecta un deslistado: si la ultima vela es muy anterior al
        final del panel, ese par murio. El backtest lo necesita para liquidar
        la posicion al ultimo cierre disponible con su penalizacion.
        """
        return self.cierres.apply(lambda c: c.last_valid_index())

    def __len__(self) -> int:
        return len(self.cierres)


def _hasta(datos: pd.DataFrame, fecha: pd.Timestamp) -> pd.DataFrame:
    """
    Lo unico que se sabia ANTES de `fecha`. Estrictamente antes.

    Toda decision del universo pasa por aca. Que sea una sola funcion no es
    prolijidad: es que una regla de no-anticipacion reimplementada en tres
    lugares se rompe en el segundo.
    """
    return datos[datos.index < fecha]


def cargar_panel(
    carpeta: Path,
    tf: str = "1d",
    *,
    usar_cache: bool = True,
) -> Panel:
    """
    Arma el panel leyendo todos los CSV de la carpeta.

    Son 650 archivos y tarda ~19 segundos, asi que se cachea. El cache se
    invalida solo comparando contra el archivo mas nuevo de la carpeta: si
    alguien baja un simbolo mas, se rehace sin que haya que acordarse.
    """
    archivos = sorted(carpeta.glob(f"*_{tf}.csv"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay ningun *_{tf}.csv en {carpeta}.\n"
            "Bajalos con:  venv\\Scripts\\python.exe tools\\descargar_archivo.py"
        )

    cache = carpeta / f"_panel_{tf}.pkl"
    if usar_cache and cache.exists():
        mas_nuevo = max(a.stat().st_mtime for a in archivos)
        if cache.stat().st_mtime >= mas_nuevo:
            try:
                with cache.open("rb") as f:
                    guardado = pickle.load(f)
                if guardado.get("simbolos") == len(archivos):
                    return Panel(guardado["cierres"], guardado["volumen"])
            except Exception as e:  # noqa: BLE001 - un cache roto se rehace
                log.warning("Cache del panel ilegible, se rehace: %s", e)

    cierres, volumenes = {}, {}
    for archivo in archivos:
        simbolo = archivo.name[: -(len(tf) + 5)]
        df = pd.read_csv(
            archivo, index_col="open_time", parse_dates=["open_time"],
            usecols=["open_time", "close", "quote_volume"],
        )
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        cierres[simbolo] = df["close"]
        volumenes[simbolo] = df["quote_volume"]

    panel = Panel(pd.DataFrame(cierres).sort_index(),
                  pd.DataFrame(volumenes).sort_index())

    if usar_cache:
        try:
            with cache.open("wb") as f:
                pickle.dump({"cierres": panel.cierres,
                             "volumen": panel.volumen_cotizado,
                             "simbolos": len(archivos)}, f)
        except Exception as e:  # noqa: BLE001 - sin cache se sigue igual
            log.warning("No se pudo escribir el cache del panel: %s", e)

    return panel


def liquidez_en(panel: Panel, fecha: pd.Timestamp) -> pd.Series:
    """
    Mediana del volumen cotizado de los ultimos 30 dias ANTES de `fecha`.

    Mediana y no media: un solo dia de volumen anormal --un anuncio, un
    pump-- mueve la media lo suficiente para meter una moneda iliquida en el
    top 20, y esa es justo la que despues no se puede vender al precio que
    dice el backtest.
    """
    previo = _hasta(panel.volumen_cotizado, fecha)
    if previo.empty:
        return pd.Series(dtype="float64")
    return previo.tail(DIAS_VENTANA_LIQUIDEZ).median()


def universo_en(
    panel: Panel,
    fecha: pd.Timestamp,
    *,
    tamano: int = TAMANO_UNIVERSO,
    dias_minimos: int = DIAS_MINIMOS_DE_HISTORIA,
    dias_de_gracia: int = DIAS_DE_GRACIA,
) -> list[str]:
    """
    Los simbolos que componen el universo en `fecha`, ordenados por liquidez.

    Tres condiciones, todas evaluadas con informacion anterior a `fecha`:

    1. **Antigüedad.** Al menos `dias_minimos` de historia. Descarta el ruido
       de los primeros meses tras el listado, cuando el libro esta vacio.
    2. **Sigue operando.** Tuvo al menos una vela en los ultimos
       `dias_de_gracia` dias. Sin esto, un par que murio en 2021 seguiria
       entrando al universo de 2023 con su volumen de la epoca buena.
    3. **Liquidez.** Los `tamano` primeros por mediana del volumen cotizado.

    **Un par que va a morir el mes que viene entra igual, y tiene que
    entrar.** Esa es la diferencia entre este universo y el de la Fase 1.
    """
    previo = _hasta(panel.cierres, fecha)
    if previo.empty:
        return []

    ultimo_dia = previo.index[-1]
    corte_antiguedad = fecha - pd.Timedelta(days=dias_minimos)
    corte_actividad = ultimo_dia - pd.Timedelta(days=dias_de_gracia)

    primeras = previo.apply(lambda c: c.first_valid_index())
    ultimas = previo.apply(lambda c: c.last_valid_index())

    apto = (
        primeras.notna()
        & (primeras <= corte_antiguedad)
        & (ultimas >= corte_actividad)
    )
    if not apto.any():
        return []

    liquidez = liquidez_en(panel, fecha)[apto[apto].index]
    liquidez = liquidez[liquidez > 0].sort_values(ascending=False)
    return list(liquidez.head(tamano).index)


def fechas_de_rebalanceo(
    panel: Panel,
    desde: pd.Timestamp | None = None,
    hasta: pd.Timestamp | None = None,
) -> list[pd.Timestamp]:
    """
    El primer dia de cada mes, a las 00:00 UTC. De la especificacion 6.2.

    Se generan a partir del calendario y no de los dias que existen en el
    panel: si un 1 de mes no tuviera vela, igual hay que rebalancear -- lo que
    cambia es con que precio, y eso lo resuelve el backtest, no el universo.
    """
    inicio = desde if desde is not None else panel.cierres.index[0]
    fin = hasta if hasta is not None else panel.cierres.index[-1]
    return list(pd.date_range(inicio.normalize(), fin, freq="MS", tz="UTC"))


def construir(
    panel: Panel,
    fechas: list[pd.Timestamp],
    **opciones,
) -> dict[pd.Timestamp, list[str]]:
    """El universo en cada fecha de rebalanceo. Es la salida que usa la estrategia."""
    return {f: universo_en(panel, f, **opciones) for f in fechas}


def matriz_disponibilidad(panel: Panel, freq: str = "MS") -> pd.DataFrame:
    """
    Que simbolos tenian datos en cada mes. Filas = mes, columnas = simbolo.

    Es descriptiva: sirve para ver el crecimiento del mercado y para
    contar deslistados, no para decidir nada.

    Se cuenta con `sum() > 0` y no con `any()` porque el resampler de esta
    version de pandas no expone `any()`.
    """
    return panel.cierres.notna().resample(freq).sum() > 0


def rotacion(seleccion: dict[pd.Timestamp, list[str]]) -> pd.Series:
    """
    Que fraccion del universo cambia entre rebalanceos consecutivos.

    Importa porque **esa rotacion se paga aunque la estrategia no cambie de
    opinion**: si un simbolo sale del top 20, hay que venderlo. Es costo
    forzado por la composicion del universo, no por la señal.
    """
    fechas = sorted(seleccion)
    valores = {}
    for antes, ahora in zip(fechas, fechas[1:]):
        previo, actual = set(seleccion[antes]), set(seleccion[ahora])
        if not previo:
            continue
        valores[ahora] = len(actual - previo) / len(previo)
    return pd.Series(valores)


# ---------------------------------------------------------------------------
# Renombramientos: no todo el que desaparece se murio
# ---------------------------------------------------------------------------
#
# Descubierto el 30-ago-2026 al mirar la lista de 22 "muertos" que atraveso la
# cartera: cinco de ellos no murieron, **se cambiaron de nombre**. El ticker
# viejo deja de operar y el nuevo arranca entre 0 y 8 dias despues, y quien
# tenia la moneda no perdio nada -- la conversion fue automatica.
#
# IMPORTA MAS DE LO QUE PARECE. La especificacion pide medir el impacto de los
# deslistados con penalizaciones de 0%, -20% y -50%. Aplicarle -50% a un
# cambio de nombre no es ser conservador: es estar equivocado, y ademas
# empujando el resultado hacia el lado que uno cree seguro, que es la peor
# forma de equivocarse.
#
# LA LISTA ES A MANO, Y ES A PROPOSITO. Detectar renombramientos por heuristica
# --"murio uno y nacio otro cerca"-- daria falsos positivos todo el tiempo,
# porque en cripto nacen monedas todas las semanas. Aca la decision queda
# visible y auditable. `detectar_renombramientos_candidatos()` propone; una
# persona confirma y agrega la linea con su evidencia.
RENOMBRAMIENTOS = {
    # viejo          nuevo           evidencia (dias entre la ultima y la primera vela)
    "MATICUSDT":    "POLUSDT",       # muere 2024-09-10, nace 2024-09-13  (+3)
    "RNDRUSDT":     "RENDERUSDT",    # muere 2024-07-22, nace 2024-07-26  (+4)
    "FTMUSDT":      "SUSDT",         # muere 2025-01-13, nace 2025-01-16  (+3)
    "BTTUSDT":      "BTTCUSDT",      # muere 2022-01-17, nace 2022-01-25  (+8)
    "BCHABCUSDT":   "BCHUSDT",       # muere 2019-11-28, nace 2019-11-28  (+0)
}


def detectar_renombramientos_candidatos(
    panel: Panel, dias_maximos: int = 10
) -> list[tuple[str, str, int]]:
    """
    Propone pares (muerto, nacido) que PODRIAN ser un cambio de nombre.

    **Propone, no decide.** Devuelve candidatos para que una persona los
    confirme y los agregue a `RENOMBRAMIENTOS` con su evidencia. Una
    heuristica que decidiera sola convertiria cada coincidencia temporal en un
    renombramiento inventado, y en cripto nacen monedas todas las semanas.
    """
    primeras, ultimas = panel.primera_vela, panel.ultima_vela
    fin = panel.cierres.index[-1]
    candidatos = []
    for muerto, final in ultimas.dropna().items():
        if final >= fin - pd.Timedelta(days=DIAS_DE_GRACIA):
            continue
        for nacido, inicio in primeras.dropna().items():
            if nacido == muerto:
                continue
            brecha = (inicio - final).days
            if 0 <= brecha <= dias_maximos:
                candidatos.append((muerto, nacido, brecha))
    return sorted(candidatos, key=lambda x: x[2])


def deslistados_en(
    panel: Panel,
    seleccion: dict[pd.Timestamp, list[str]],
    *,
    excluir_renombrados: bool = True,
) -> dict:
    """
    Que simbolos del universo murieron DE VERDAD despues de entrar.

    Es la cuenta que la Fase 1 no pudo hacer: cuantos muertos atraveso la
    cartera. Va en todo reporte de la Fase 2.

    Los renombramientos quedan afuera por defecto -- no son una perdida para
    quien tenia la moneda. Con `excluir_renombrados=False` se ven todos, que
    es lo que hay que mirar cuando se revisa si la lista de arriba esta al dia.
    """
    ultimas = panel.ultima_vela
    fin_panel = panel.cierres.index[-1]
    muertos = {}
    for fecha, simbolos in seleccion.items():
        for s in simbolos:
            if excluir_renombrados and s in RENOMBRAMIENTOS:
                continue
            final = ultimas.get(s)
            if final is not None and final < fin_panel - pd.Timedelta(days=DIAS_DE_GRACIA):
                muertos.setdefault(s, final)
    return muertos


def rotacion_anual(seleccion: dict[pd.Timestamp, list[str]]) -> pd.Series:
    """
    Que fraccion del universo cambia de un año al siguiente.

    Distinta de `rotacion()`, que suma cambios mes a mes. Las dos son utiles y
    NO son comparables entre si: la mensual sumada doce veces cuenta varias
    veces al simbolo que entra y sale; esta mira solo las dos puntas.

    Existe para poder compararse con la literatura -- Grobys y coautores
    documentan 37% anual sobre las 30 mayores capitalizaciones -- sin
    confundir una medida con la otra.
    """
    fechas = sorted(seleccion)
    valores = {}
    for antes in fechas:
        despues = antes + pd.DateOffset(years=1)
        if despues not in seleccion:
            continue
        previo, actual = set(seleccion[antes]), set(seleccion[despues])
        if previo:
            valores[despues] = len(actual - previo) / len(previo)
    return pd.Series(valores)
