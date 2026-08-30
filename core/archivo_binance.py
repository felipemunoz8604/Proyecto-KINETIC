"""
Descarga desde el archivo historico oficial de Binance, con los deslistados.

POR QUE EXISTE, SI YA HAY UN `data_feed`
-----------------------------------------
`data_feed` baja del endpoint `/api/v3/klines`, y ese endpoint **solo sirve
los simbolos que Binance decide servir hoy**. Todo lo que se midio en la
Fase 1 salio de ahi, y por eso el universo era "las que sobrevivieron": 485
pares USDT operando contra 250 deslistados, o sea que la Fase 1 vio el 66% del
mercado que existio.

La literatura le pone numero a lo que eso cuesta. Ammann, Burdorf, Liebi y
Stockl midieron el sesgo sobre 3.904 criptomonedas entre 2014 y 2021: **0,93%
anualizado para carteras ponderadas por capitalizacion, 62,19% para
equiponderadas**. El agregado de 15 pares equiponderados de la Fase 1 era
exactamente el peor caso.

DONDE ESTABA EL AGUJERO DE VERDAD
----------------------------------
La especificacion dice que el archivo tiene simbolos que `exchangeInfo` no
tiene. **Casi falso:** comparado contra todo `exchangeInfo` aparecen 25
simbolos extra, 1 solo contra USDT.

Lo que pasa es que **Binance no borra un par deslistado de `exchangeInfo` --
lo deja con estado `BREAK`**, a veces por años. Hay 2.327 asi. El sesgo de la
Fase 1 no entro por usar el endpoint equivocado: entro por filtrar
`status == "TRADING"`.

Importa para no arreglarlo mal: **si alguien cambia la fuente de datos y sigue
filtrando por TRADING, el sesgo vuelve entero.** Por eso `simbolos_disponibles`
no filtra por estado, y hay una prueba que lo exige.

QUE BAJA
--------
Velas **diarias** (`1d`). La Fase 2 no necesita 15m, 1h ni 4h -- todas las
estrategias candidatas rebalancean mensualmente y evaluan sobre cierre diario.
El volumen de datos baja drasticamente y eso hace viable bajar cientos de
pares en vez de quince.

Cada mensual viene con su `.CHECKSUM` y se verifica. No es ceremonia: un zip
truncado se descomprime igual y mete datos falsos sin avisar.
"""

from __future__ import annotations

import hashlib
import io
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BASE = "https://data.binance.vision"
ESPACIO = "{http://s3.amazonaws.com/doc/2006-03-01/}"

# Las columnas que trae el CSV del archivo, en orden. No tiene encabezado.
COLUMNAS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]

# Las unicas que se conservan. `quote_volume` entra porque es el sustituto de
# liquidez con el que se ordena el universo: el archivo no trae
# capitalizacion de mercado, y esa desviacion respecto de la literatura queda
# declarada en la bitacora.
UTILES = ["open", "high", "low", "close", "volume", "quote_volume"]


class ArchivoNoDisponible(RuntimeError):
    """El archivo pedido no existe en el bucket, o no se pudo leer."""


class ChecksumInvalido(RuntimeError):
    """El zip bajo pero su SHA256 no coincide con el .CHECKSUM publicado."""


@dataclass(frozen=True)
class Mercado:
    """
    Que rama del archivo se lee.

    Existe para que no haya rutas armadas a mano repartidas por el codigo:
    Spot y perpetuos viven en prefijos distintos y es facil equivocarse.
    """

    nombre: str
    prefijo: str

    def ruta_simbolo(self, simbolo: str, tf: str) -> str:
        return f"{self.prefijo}{simbolo}/{tf}/"


SPOT = Mercado("spot", "data/spot/monthly/klines/")
PERPETUO = Mercado("perpetuo USDT-M", "data/futures/um/monthly/klines/")


def _leer(url: str, timeout: int = 60) -> bytes:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 - se re-lanza con contexto util
        raise ArchivoNoDisponible(f"No se pudo leer {url}: {e}") from e


def _listar(prefijo: str, solo_carpetas: bool) -> list[str]:
    """Lista el bucket con paginacion. Devuelve nombres relativos al prefijo."""
    salida: list[str] = []
    marcador = ""
    while True:
        url = f"{BUCKET}?prefix={urllib.parse.quote(prefijo, safe='/')}"
        if solo_carpetas:
            url += "&delimiter=/"
        if marcador:
            url += f"&marker={urllib.parse.quote(marcador, safe='')}"
        raiz = ET.fromstring(_leer(url))

        if solo_carpetas:
            lote = [
                p.find(f"{ESPACIO}Prefix").text[len(prefijo):].strip("/")
                for p in raiz.findall(f"{ESPACIO}CommonPrefixes")
            ]
            ultimo_crudo = prefijo + lote[-1] + "/" if lote else ""
        else:
            claves = [c.find(f"{ESPACIO}Key").text
                      for c in raiz.findall(f"{ESPACIO}Contents")]
            lote = [k[len(prefijo):] for k in claves]
            ultimo_crudo = claves[-1] if claves else ""

        if not lote:
            break
        salida.extend(lote)
        truncado = raiz.find(f"{ESPACIO}IsTruncated")
        if truncado is None or truncado.text != "true":
            break
        marcador = ultimo_crudo
    return salida


def simbolos_disponibles(mercado: Mercado = SPOT) -> list[str]:
    """
    Todos los simbolos del archivo, **incluidos los deslistados**.

    NO filtra por estado a proposito, y hay una prueba que lo exige. Filtrar
    por `status == "TRADING"` es exactamente como entro el sesgo de
    supervivencia en la Fase 1. El filtrado que corresponda (stablecoins,
    tokens apalancados, liquidez) va despues y en otro lado, sobre esta lista
    completa.
    """
    return sorted(_listar(mercado.prefijo, solo_carpetas=True))


def meses_disponibles(simbolo: str, tf: str = "1d",
                      mercado: Mercado = SPOT) -> list[str]:
    """Los nombres de los zip mensuales de un simbolo, del mas viejo al mas nuevo."""
    nombres = _listar(mercado.ruta_simbolo(simbolo, tf), solo_carpetas=False)
    return sorted(n for n in nombres if n.endswith(".zip"))


def bajar_mes(simbolo: str, archivo: str, tf: str = "1d",
              mercado: Mercado = SPOT, verificar: bool = True) -> pd.DataFrame:
    """
    Un mensual, verificado y ya convertido a DataFrame.

    El checksum se comprueba por defecto. Se puede apagar para pruebas, nunca
    en una descarga de verdad: un zip truncado se descomprime igual y mete
    datos falsos sin avisar, y despues aparece como un "hallazgo" raro.
    """
    url = f"{BASE}/{mercado.ruta_simbolo(simbolo, tf)}{archivo}"
    crudo = _leer(url)

    if verificar:
        esperado = _leer(url + ".CHECKSUM").decode().split()[0]
        obtenido = hashlib.sha256(crudo).hexdigest()
        if obtenido != esperado:
            raise ChecksumInvalido(
                f"{simbolo} {archivo}: el SHA256 no coincide.\n"
                f"  esperado: {esperado}\n  obtenido: {obtenido}\n"
                "El zip llego corrupto o incompleto. No se usa."
            )

    with zipfile.ZipFile(io.BytesIO(crudo)) as z:
        with z.open(z.namelist()[0]) as f:
            df = pd.read_csv(f, header=None, names=COLUMNAS)

    # Algunos meses traen encabezado y otros no, segun cuando los genero
    # Binance. Si la primera fila no es numerica, era el encabezado.
    if not str(df["open_time"].iloc[0]).replace("-", "").isdigit():
        df = df.iloc[1:].reset_index(drop=True)

    return _a_indice_temporal(df)


def _a_indice_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deja el DataFrame con indice UTC en milisegundos y solo las columnas utiles.

    El `open_time` del archivo viene en milisegundos en los meses viejos y en
    MICROsegundos en los nuevos -- Binance lo cambio a mitad de camino. Si no
    se detecta, las fechas nuevas caen en el año 56.000 y la serie queda
    inutilizable de una forma que no salta a la vista.
    """
    tiempos = pd.to_numeric(df["open_time"])
    # Un timestamp en milisegundos de una fecha real tiene 13 digitos; en
    # microsegundos, 16. El corte esta muy lejos de cualquier fecha plausible.
    unidad = "us" if tiempos.max() > 1e15 else "ms"

    salida = df[UTILES].apply(pd.to_numeric, errors="coerce")
    # OJO: nada de `.values` aca. Sobre un indice con zona horaria, `.values`
    # devuelve datetime64 SIN zona y el UTC se pierde en silencio -- el codigo
    # no falla, simplemente el indice queda ingenuo y despues no se puede
    # comparar contra las fechas de la ventana de diseño, que si tienen zona.
    # Lo atrapo `test_el_indice_queda_ordenado_y_en_utc`.
    salida.index = pd.DatetimeIndex(
        pd.to_datetime(tiempos.to_numpy(), unit=unidad, utc=True)
    ).as_unit("ms")
    salida.index.name = "open_time"
    return salida.sort_index()


def bajar_simbolo(
    simbolo: str,
    tf: str = "1d",
    mercado: Mercado = SPOT,
    *,
    meses: list[str] | None = None,
) -> pd.DataFrame:
    """
    El historico completo de un simbolo, pegando todos sus mensuales.

    Un mes que falla no tumba la descarga entera: se registra y se sigue. Un
    par deslistado hace años puede tener un mes roto en el archivo, y perder
    el simbolo completo por eso seria volver a introducir sesgo -- justo lo
    que este modulo existe para evitar.
    """
    meses = meses if meses is not None else meses_disponibles(simbolo, tf, mercado)
    if not meses:
        raise ArchivoNoDisponible(
            f"{simbolo} {tf} no tiene ningun mensual en el archivo ({mercado.nombre})."
        )

    trozos, fallados = [], []
    for archivo in meses:
        try:
            trozos.append(bajar_mes(simbolo, archivo, tf, mercado))
        except (ArchivoNoDisponible, ChecksumInvalido) as e:
            fallados.append(archivo)
            log.warning("%s: se saltea %s (%s)", simbolo, archivo, e)

    if not trozos:
        raise ArchivoNoDisponible(f"{simbolo} {tf}: ningun mensual se pudo bajar.")

    df = pd.concat(trozos).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df.attrs["meses_fallados"] = fallados
    df.attrs["simbolo"] = simbolo
    return df


def guardar(df: pd.DataFrame, simbolo: str, tf: str, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{simbolo}_{tf}.csv"
    df.to_csv(ruta)
    return ruta


def cargar(simbolo: str, tf: str, carpeta: Path) -> pd.DataFrame:
    ruta = carpeta / f"{simbolo}_{tf}.csv"
    if not ruta.exists():
        raise FileNotFoundError(
            f"No hay archivo guardado para {simbolo} {tf} en {carpeta}.\n"
            "Bajalo con:  venv\\Scripts\\python.exe tools\\descargar_archivo.py"
        )
    df = pd.read_csv(ruta, index_col="open_time", parse_dates=["open_time"])
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.as_unit("ms")
    return df.sort_index()


# ---------------------------------------------------------------------------
# Filtros estaticos del universo
# ---------------------------------------------------------------------------
#
# OJO CON LA DIFERENCIA, que es la que hundio a la Fase 1: estos filtros son
# ESTATICOS -- dependen solo del nombre del par, no de si esta vivo ni de como
# le fue. Se pueden aplicar al descargar sin introducir ningun sesgo.
#
# Los filtros que dependen de la FECHA (antiguedad minima, ranking por
# liquidez, top 20) van en otro lado y se evaluan en cada fecha de rebalanceo.
# Mezclarlos aca seria decidir hoy quien estaba en el universo en 2020, que es
# exactamente la forma en que el futuro se filtra hacia el pasado.

# Bases que no son una apuesta direccional: un par contra USDT donde la base
# tambien vale un dolar no tiene tendencia que capturar.
ESTABLES = frozenset({
    "USDC", "BUSD", "TUSD", "USDP", "PAX", "PAXG", "DAI", "FDUSD", "USDS",
    "USDSB", "SUSD", "USTC", "UST", "AEUR", "EURI", "XUSD", "USD1",
    "EUR", "GBP", "AUD", "TRY", "RUB", "BRL", "ZAR", "IDRT", "NGN", "UAH",
    "BIDR", "VAI", "PLN", "RON", "JPY", "MXN", "COP", "CZK", "ARS",
})

# Tokens apalancados: decaen todos los dias por como estan construidos, asi
# que su serie de precios no es la del activo subyacente.
SUFIJOS_APALANCADOS = ("UP", "DOWN", "BULL", "BEAR", "3L", "3S", "5L", "5S")


def es_apuesta_direccional(simbolo: str, cotizacion: str = "USDT") -> bool:
    """
    True si el par sirve para una estrategia direccional sobre el activo.

    No mira si el par sigue vivo ni como le fue: solo el nombre. Esa es la
    condicion para que se pueda usar al descargar sin sesgar nada.
    """
    if not simbolo.endswith(cotizacion):
        return False
    base = simbolo[: -len(cotizacion)]
    if not base or base in ESTABLES:
        return False
    return not any(base.endswith(s) for s in SUFIJOS_APALANCADOS)
