"""
Pruebas de la capa de datos.

Ninguna toca la red: todas arman velas de mentira en memoria. La red se
prueba a mano con tools/descargar_historico.py, que si depende de Binance.

Lo que se vigila aca es lo que arruinaria un backtest en silencio:
la vela en curso, los huecos, los duplicados y el desorden temporal.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import data_feed  # noqa: E402

UNA_HORA_MS = 3_600_000


def velas_falsas(cantidad: int, arranque_ms: int, paso_ms: int = UNA_HORA_MS) -> list[list]:
    """Genera velas con el formato crudo exacto que devuelve Binance."""
    filas = []
    for i in range(cantidad):
        apertura = arranque_ms + i * paso_ms
        cierre = apertura + paso_ms - 1
        precio = 100.0 + i
        filas.append(
            [
                apertura, str(precio), str(precio + 2), str(precio - 2),
                str(precio + 1), "10.5", cierre, "1050.0", 42,
                "5.0", "500.0", "0",
            ]
        )
    return filas


# --- La vela en curso ------------------------------------------------------

def test_descarta_la_vela_que_todavia_no_cerro():
    """
    La ultima vela que devuelve Binance se esta formando: su cierre no es el
    definitivo. Si el backtest la usa, ve un precio que no existia todavia.
    """
    ahora_ms = int(time.time() * 1000)
    # Cuatro velas: las tres primeras ya cerraron, la cuarta esta en curso.
    arranque = ahora_ms - 3 * UNA_HORA_MS - UNA_HORA_MS // 2
    df = data_feed._a_dataframe(velas_falsas(4, arranque))
    assert len(df) == 4

    resultado = data_feed._quitar_vela_en_curso(df)
    assert len(resultado) == 3, "no se descarto la vela en formacion"
    assert resultado["close_time"].max() < ahora_ms


def test_no_descarta_nada_si_todo_ya_cerro():
    ahora_ms = int(time.time() * 1000)
    arranque = ahora_ms - 10 * UNA_HORA_MS
    df = data_feed._a_dataframe(velas_falsas(5, arranque))
    assert len(data_feed._quitar_vela_en_curso(df)) == 5


def test_vela_en_curso_con_serie_vacia_no_explota():
    vacia = data_feed._a_dataframe([])
    assert data_feed._quitar_vela_en_curso(vacia).empty


# --- Auditoria -------------------------------------------------------------

def test_serie_continua_no_reporta_huecos():
    df = data_feed._a_dataframe(velas_falsas(100, 1_500_000_000_000))
    reporte = data_feed.auditar(df, "BTCUSDT", "1h")
    assert reporte.velas == 100
    assert reporte.huecos == 0
    assert reporte.duplicadas == 0
    assert not reporte.desordenada
    assert reporte.limpia


def test_detecta_un_hueco_y_cuenta_las_velas_ausentes():
    arranque = 1_500_000_000_000
    df = data_feed._a_dataframe(velas_falsas(50, arranque))
    # Se borran 3 velas del medio: eso es un hueco de 3.
    df = pd.concat([df.iloc[:20], df.iloc[23:]])

    reporte = data_feed.auditar(df, "BTCUSDT", "1h")
    assert reporte.huecos == 1
    assert reporte.velas_faltantes == 3


def test_detecta_duplicados():
    df = data_feed._a_dataframe(velas_falsas(10, 1_500_000_000_000))
    con_duplicados = pd.concat([df, df.iloc[3:5]])

    reporte = data_feed.auditar(con_duplicados, "BTCUSDT", "1h")
    assert reporte.duplicadas == 2
    assert not reporte.limpia, "una serie con duplicados no puede darse por limpia"


def test_detecta_desorden_temporal():
    df = data_feed._a_dataframe(velas_falsas(10, 1_500_000_000_000))
    desordenada = df.iloc[::-1]

    reporte = data_feed.auditar(desordenada, "BTCUSDT", "1h")
    assert reporte.desordenada
    assert not reporte.limpia


def test_auditar_serie_vacia_no_explota():
    reporte = data_feed.auditar(data_feed._a_dataframe([]), "BTCUSDT", "1h")
    assert reporte.velas == 0
    assert not reporte.limpia


# --- Limpieza --------------------------------------------------------------

def test_limpiar_quita_duplicados_y_ordena():
    df = data_feed._a_dataframe(velas_falsas(10, 1_500_000_000_000))
    sucia = pd.concat([df.iloc[5:], df, df.iloc[2:4]])

    limpia = data_feed.limpiar(sucia)
    assert len(limpia) == 10
    assert limpia.index.is_monotonic_increasing
    assert not limpia.index.duplicated().any()


def test_limpiar_no_rellena_huecos():
    """
    Inventar una vela que no existio seria fabricar precio. Los huecos se
    reportan, nunca se tapan.
    """
    df = data_feed._a_dataframe(velas_falsas(20, 1_500_000_000_000))
    con_hueco = pd.concat([df.iloc[:10], df.iloc[15:]])

    limpia = data_feed.limpiar(con_hueco)
    assert len(limpia) == 15, "limpiar() invento velas que no existian"


# --- Disco -----------------------------------------------------------------

def test_guardar_y_cargar_conserva_los_datos(tmp_path):
    df = data_feed._a_dataframe(velas_falsas(30, 1_500_000_000_000))
    df = df[data_feed.COLUMNAS_UTILES + ["close_time"]]

    data_feed.guardar(df, "BTCUSDT", "1h", carpeta=tmp_path)
    recuperado = data_feed.cargar("BTCUSDT", "1h", carpeta=tmp_path)

    assert len(recuperado) == len(df)
    assert recuperado.index.equals(df.index)
    pd.testing.assert_series_equal(
        recuperado["close"], df["close"], check_freq=False
    )


def test_cargar_un_archivo_inexistente_explica_que_hacer(tmp_path):
    with pytest.raises(FileNotFoundError, match="descargar_historico"):
        data_feed.cargar("NOEXISTE", "1h", carpeta=tmp_path)


def test_cargar_rechaza_un_archivo_corrupto(tmp_path):
    """Si alguien edita el CSV a mano y rompe el orden, hay que enterarse."""
    df = data_feed._a_dataframe(velas_falsas(20, 1_500_000_000_000))
    df = df[data_feed.COLUMNAS_UTILES + ["close_time"]]
    data_feed.guardar(pd.concat([df, df.iloc[5:7]]), "BTCUSDT", "1h", carpeta=tmp_path)

    with pytest.raises(data_feed.DatosInvalidos):
        data_feed.cargar("BTCUSDT", "1h", carpeta=tmp_path)


# --- Validaciones de entrada ----------------------------------------------

def test_temporalidad_desconocida_se_rechaza():
    with pytest.raises(ValueError, match="Temporalidad"):
        data_feed.descargar("BTCUSDT", "7h")


def test_toda_temporalidad_conocida_tiene_duracion():
    for tf, ms in data_feed.DURACION_MS.items():
        assert ms > 0, f"{tf} sin duracion"
