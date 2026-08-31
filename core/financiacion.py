r"""
Historico de tasas de financiacion de los perpetuos USDT-M.

POR QUE ES UN MODULO APARTE Y NO UNA RAMA MAS DEL ARCHIVO DE VELAS
--------------------------------------------------------------------
Porque es otro dato. Las velas viven en `.../klines/{simbolo}/{tf}/` y traen
doce columnas de precio; la financiacion vive en
`.../fundingRate/{simbolo}/` -- **sin temporalidad** -- y trae tres:

    calc_time, funding_interval_hours, last_funding_rate

Sin esto, cualquier backtest que use perpetuos es ficcion. La financiacion se
cobra cada pocas horas sobre el nocional y puede superar largamente el ahorro
en comisiones que motivo traer los perpetuos al proyecto.

EL INTERVALO ES UN DATO, NO UNA CONSTANTE
-------------------------------------------
La tentacion es anualizar multiplicando por 3 (tres cobros diarios) y por 365.
**Esta mal.** Binance cambio varios simbolos a intervalos de 4 horas, y el
archivo trae la columna justamente porque no es fijo. Un simbolo de 4 horas
anualizado como si fuera de 8 queda con la mitad del carry que de verdad tuvo.

Aca se usa siempre `funding_interval_hours` de cada fila.

SE REUSA LA NORMALIZACION DE TIEMPOS DE LAS VELAS
---------------------------------------------------
`archivo_binance._a_milisegundos` corrige que Binance cambio la unidad de los
timestamps a mitad de camino, y lo hace **fila por fila** porque llegan
mezcladas dentro de un mismo archivo mensual. Ese error costo caro el
30-ago-2026 (KLAYUSDT tiraba 30 filas a 1970 sin avisar) y no hay razon para
suponer que la rama de financiacion esta a salvo. Se reusa tal cual.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pandas as pd

from core.archivo_binance import (
    BASE,
    ChecksumInvalido,
    Mercado,
    _a_milisegundos,
    _leer,
    _listar,
    _url_de,
)

COLUMNAS = ["calc_time", "funding_interval_hours", "last_funding_rate"]
HORAS_POR_DIA = 24.0
DIAS_POR_ANIO = 365.0


class _SinTemporalidad(Mercado):
    """La rama de financiacion no tiene carpeta de temporalidad."""

    def ruta_simbolo(self, simbolo: str, tf: str = "") -> str:
        return f"{self.prefijo}{simbolo}/"


FINANCIACION = _SinTemporalidad("financiacion USDT-M",
                                "data/futures/um/monthly/fundingRate/")


def simbolos_disponibles() -> list[str]:
    """Todos los perpetuos con historico de financiacion, incluidos los muertos."""
    return sorted(_listar(FINANCIACION.prefijo, solo_carpetas=True))


def meses_disponibles(simbolo: str) -> list[str]:
    nombres = _listar(FINANCIACION.ruta_simbolo(simbolo), solo_carpetas=False)
    return sorted(n for n in nombres if n.endswith(".zip"))


def bajar_mes(simbolo: str, archivo: str, verificar: bool = True
              ) -> pd.DataFrame:
    """Un mensual, con checksum verificado y el indice ya en UTC."""
    url = _url_de(FINANCIACION, simbolo, "", archivo)
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

    # Algunos meses traen encabezado y otros no, igual que las velas.
    if not str(df["calc_time"].iloc[0]).replace("-", "").isdigit():
        df = df.iloc[1:].reset_index(drop=True)
    return _a_indice(df)


def _a_indice(df: pd.DataFrame) -> pd.DataFrame:
    ms = _a_milisegundos(df["calc_time"])
    indice = pd.DatetimeIndex(
        pd.to_datetime(ms.to_numpy(), unit="ms", utc=True), name="momento")
    salida = pd.DataFrame({
        "tasa": pd.to_numeric(df["last_funding_rate"], errors="coerce").to_numpy(),
        "horas": pd.to_numeric(df["funding_interval_hours"],
                               errors="coerce").to_numpy(),
    }, index=indice)
    salida = salida[~salida.index.duplicated(keep="first")].sort_index()
    return salida.dropna()


def bajar_simbolo(simbolo: str, verificar: bool = True) -> pd.DataFrame:
    """Todo el historico de un simbolo, mes por mes."""
    partes = [bajar_mes(simbolo, m, verificar)
              for m in meses_disponibles(simbolo)]
    if not partes:
        return pd.DataFrame(columns=["tasa", "horas"])
    todo = pd.concat(partes)
    return todo[~todo.index.duplicated(keep="first")].sort_index()


def guardar(df: pd.DataFrame, simbolo: str, carpeta: Path) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"{simbolo}.csv"
    df.to_csv(ruta, index_label="momento")
    return ruta


def cargar(simbolo: str, carpeta: Path) -> pd.DataFrame:
    """
    El historico guardado, con el indice siempre en UTC.

    Dos cosas que el dato real obliga a hacer a mano:

    - `parse_dates` devuelve un Index de objetos en esta version de pandas
      cuando los textos traen offset horario, y despues falla al preguntarle
      la zona.
    - `format="ISO8601"` porque **no todos los cobros caen en punto**: hay
      sellos como `12:00:00.001000+00:00`. Sin esto, pandas infiere el
      formato de la primera fila y revienta varias miles de filas despues.
    """
    df = pd.read_csv(carpeta / f"{simbolo}.csv")
    df.index = pd.DatetimeIndex(
        pd.to_datetime(df.pop("momento"), utc=True, format="ISO8601"),
        name="momento")
    return df.sort_index()


# --- Anualizacion ---------------------------------------------------------

def anualizar(df: pd.DataFrame) -> pd.Series:
    """
    Cada tasa llevada a su equivalente anual, usando SU intervalo.

        anual = tasa x (24 / horas) x 365

    Multiplicar por 3 fijo daria la mitad del carry real en los simbolos que
    Binance paso a intervalos de 4 horas.
    """
    cobros_por_anio = (HORAS_POR_DIA / df["horas"]) * DIAS_POR_ANIO
    return (df["tasa"] * cobros_por_anio).rename("anual")


def resumen(df: pd.DataFrame) -> dict[str, float]:
    """Los numeros que pide la medicion 5.1 para un simbolo."""
    anual = anualizar(df)
    if anual.empty:
        return {}
    return {
        "cobros": int(len(df)),
        "desde": df.index[0],
        "hasta": df.index[-1],
        "mediana": float(anual.median()),
        "media": float(anual.mean()),
        "p10": float(anual.quantile(0.10)),
        "p90": float(anual.quantile(0.90)),
        "fraccion_positiva": float((df["tasa"] > 0).mean()),
        "intervalos": sorted(df["horas"].unique().tolist()),
    }
