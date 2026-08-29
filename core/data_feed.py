"""
Capa de datos de KINETIC: de donde salen las velas.

Dos ideas gobiernan este archivo.

1. LOS DATOS DEL BACKTEST VIENEN DE MAINNET, Y SIN LLAVES.
   El endpoint de velas de Binance es publico: no requiere API key ni firma.
   Asi que el backtest se alimenta de precios reales de mercado sin que haya
   ninguna credencial involucrada. Testnet NO se usa como fuente de datos:
   sigue el precio real de cerca, pero su libro de ordenes es ficticio.

2. UN BACKTEST CON DATOS SUCIOS DA UN NUMERO PRECIOSO Y FALSO.
   Por eso todo lo que se descarga pasa por una auditoria (`auditar`) antes
   de guardarse, y `cargar` vuelve a auditar al leer. Los tres problemas que
   se vigilan son velas duplicadas, huecos en la serie, y desorden temporal.

LA VELA EN CURSO SE DESCARTA SIEMPRE
------------------------------------
La ultima vela que devuelve Binance todavia se esta formando: su cierre y su
volumen no son los definitivos. Si el backtest la usa, "ve" un cierre que en
ese momento no existia. Es una de las formas mas comunes de que un backtest
mienta a favor, y es silenciosa. Aca se descarta sin excepcion, comparando
el `close_time` de la vela contra la hora actual.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from binance.client import Client

log = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_POR_DEFECTO = RAIZ / "data" / "historico"

# Cuantos milisegundos dura cada vela. Se usa para detectar huecos.
DURACION_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

COLUMNAS_CRUDAS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_base", "taker_quote", "ignorar",
]

COLUMNAS_UTILES = ["open", "high", "low", "close", "volume", "trades"]


class DatosInvalidos(Exception):
    """La serie de velas tiene un problema que invalidaria el backtest."""


@dataclass
class Auditoria:
    """Resultado de revisar una serie de velas."""

    par: str
    temporalidad: str
    velas: int
    desde: pd.Timestamp | None
    hasta: pd.Timestamp | None
    duplicadas: int
    huecos: int
    velas_faltantes: int
    desordenada: bool

    @property
    def limpia(self) -> bool:
        return (
            self.duplicadas == 0
            and not self.desordenada
            and self.velas > 0
        )

    def informe(self) -> str:
        lineas = [
            f"{self.par} {self.temporalidad}: {self.velas:,} velas",
            f"  Rango:       {self.desde}  ->  {self.hasta}",
            f"  Duplicadas:  {self.duplicadas}",
            f"  Desordenada: {'SI' if self.desordenada else 'no'}",
            f"  Huecos:      {self.huecos} ({self.velas_faltantes:,} velas ausentes)",
        ]
        if self.huecos:
            lineas.append(
                "  Nota: los huecos suelen ser paradas de mantenimiento de Binance. "
                "No invalidan el backtest, pero conviene saber que existen."
            )
        return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def _cliente_publico() -> Client:
    """Cliente sin llaves. Solo puede leer datos publicos de mercado."""
    return Client()


def _normalizar_indice(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deja el indice siempre en UTC y con resolucion de milisegundos.

    Por que hace falta: pandas le pone milisegundos a un indice creado desde
    un timestamp de Binance, pero microsegundos a uno leido de un CSV. Los
    instantes son los mismos, pero los tipos no coinciden, y la actualizacion
    incremental pega justamente una serie leida del disco con una recien
    bajada. Normalizar aca evita ese choque.
    """
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.as_unit("ms")
    df.index.name = "open_time"
    return df


def _a_dataframe(crudas: list[list]) -> pd.DataFrame:
    df = pd.DataFrame(crudas, columns=COLUMNAS_CRUDAS)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["trades"] = df["trades"].astype(int)
    df["close_time"] = df["close_time"].astype("int64")
    df.index = pd.to_datetime(df["open_time"].astype("int64"), unit="ms", utc=True)
    return _normalizar_indice(df)


def _quitar_vela_en_curso(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina del final las velas que todavia no cerraron.

    Se compara el `close_time` que reporta Binance contra la hora actual.
    Una vela solo entra si su periodo ya termino de verdad.
    """
    if df.empty:
        return df
    ahora_ms = int(time.time() * 1000)
    cerradas = df["close_time"] < ahora_ms
    descartadas = int((~cerradas).sum())
    if descartadas:
        log.info("Descartadas %d vela(s) todavia en formacion", descartadas)
    return df[cerradas]


def descargar(
    par: str,
    temporalidad: str,
    desde: str = "1 Jan 2017",
    cliente: Client | None = None,
) -> pd.DataFrame:
    """
    Baja el historico completo de un par desde Binance Mainnet.

    `desde` acepta texto tipo "1 Jan 2017" o "2021-01-01". python-binance
    se encarga de pedir de a 1000 velas hacia adelante hasta llegar a hoy.
    """
    if temporalidad not in DURACION_MS:
        raise ValueError(
            f"Temporalidad {temporalidad!r} desconocida. "
            f"Validas: {sorted(DURACION_MS)}"
        )

    cliente = cliente or _cliente_publico()
    log.info("Descargando %s %s desde %s ...", par, temporalidad, desde)
    crudas = cliente.get_historical_klines(par, temporalidad, desde)
    if not crudas:
        raise DatosInvalidos(
            f"Binance no devolvio ninguna vela para {par} {temporalidad}. "
            "Revisa que el par exista y este escrito igual que en Binance "
            "(por ejemplo BTCUSDT, sin barra ni guion)."
        )

    df = _quitar_vela_en_curso(_a_dataframe(crudas))
    return df[COLUMNAS_UTILES + ["close_time"]]


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------

def auditar(df: pd.DataFrame, par: str, temporalidad: str) -> Auditoria:
    """Revisa una serie de velas y describe lo que encuentra. No la modifica."""
    if df.empty:
        return Auditoria(par, temporalidad, 0, None, None, 0, 0, 0, False)

    duplicadas = int(df.index.duplicated().sum())
    desordenada = not df.index.is_monotonic_increasing

    paso = DURACION_MS[temporalidad]
    diferencias = df.index.to_series().diff().dt.total_seconds().mul(1000).dropna()
    saltos = diferencias[diferencias > paso]
    huecos = int(len(saltos))
    faltantes = int(((saltos - paso) / paso).sum()) if huecos else 0

    return Auditoria(
        par=par,
        temporalidad=temporalidad,
        velas=len(df),
        desde=df.index[0],
        hasta=df.index[-1],
        duplicadas=duplicadas,
        huecos=huecos,
        velas_faltantes=faltantes,
        desordenada=desordenada,
    )


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Arregla lo que se puede arreglar sin inventar datos: quita duplicados y
    ordena por tiempo. Los huecos NO se rellenan: inventar una vela que no
    existio seria fabricar precio.
    """
    return df[~df.index.duplicated(keep="first")].sort_index()


# ---------------------------------------------------------------------------
# Disco
# ---------------------------------------------------------------------------

def ruta_archivo(par: str, temporalidad: str, carpeta: Path | None = None) -> Path:
    carpeta = carpeta or CARPETA_POR_DEFECTO
    return carpeta / f"{par}_{temporalidad}.csv"


def guardar(
    df: pd.DataFrame, par: str, temporalidad: str, carpeta: Path | None = None
) -> Path:
    ruta = ruta_archivo(par, temporalidad, carpeta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta)
    return ruta


def cargar(
    par: str, temporalidad: str, carpeta: Path | None = None
) -> pd.DataFrame:
    """
    Lee del disco las velas ya descargadas.

    Vuelve a auditar al leer: si el archivo se corrompio o alguien lo edito
    a mano en Excel, es mejor enterarse aca que en medio de un backtest.
    """
    ruta = ruta_archivo(par, temporalidad, carpeta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No hay historico guardado para {par} {temporalidad}.\n"
            "Bajalo con:  venv\\Scripts\\python.exe tools\\descargar_historico.py"
        )
    df = _normalizar_indice(
        pd.read_csv(ruta, index_col="open_time", parse_dates=["open_time"])
    )

    reporte = auditar(df, par, temporalidad)
    if not reporte.limpia:
        raise DatosInvalidos(
            f"El archivo {ruta.name} tiene problemas:\n{reporte.informe()}\n"
            "Volve a bajarlo con tools/descargar_historico.py --rehacer"
        )
    return df


def actualizar(
    par: str,
    temporalidad: str,
    desde: str = "1 Jan 2017",
    carpeta: Path | None = None,
    rehacer: bool = False,
    cliente: Client | None = None,
) -> tuple[pd.DataFrame, Auditoria, int]:
    """
    Baja lo que falte y lo deja guardado.

    Si ya hay un archivo, solo pide las velas posteriores a la ultima que
    tenemos, en vez de rebajar nueve anios de historia cada vez.

    Devuelve (velas, auditoria, cuantas velas son nuevas).
    """
    ruta = ruta_archivo(par, temporalidad, carpeta)
    previas: pd.DataFrame | None = None

    if ruta.exists() and not rehacer:
        previas = _normalizar_indice(
            pd.read_csv(ruta, index_col="open_time", parse_dates=["open_time"])
        )
        if not previas.empty:
            ultima = previas.index[-1]
            # Se pide desde la ultima vela conocida: se solapa una, y el
            # deduplicado de `limpiar` la resuelve. Es mas seguro que
            # calcular el "siguiente" instante y arriesgar saltarse una.
            desde = ultima.strftime("%d %b %Y %H:%M:%S")
            log.info("Ya hay historico hasta %s; se pide solo lo nuevo", ultima)

    nuevas = descargar(par, temporalidad, desde, cliente=cliente)

    if previas is not None and not previas.empty:
        combinado = limpiar(pd.concat([previas, nuevas]))
        agregadas = len(combinado) - len(previas)
    else:
        combinado = limpiar(nuevas)
        agregadas = len(combinado)

    reporte = auditar(combinado, par, temporalidad)
    if not reporte.limpia:
        raise DatosInvalidos(
            f"La serie descargada de {par} {temporalidad} no paso la auditoria:\n"
            f"{reporte.informe()}"
        )

    guardar(combinado, par, temporalidad, carpeta)
    return combinado, reporte, agregadas
