"""
Pruebas de la capa de datos del archivo historico.

Casi todas trabajan sobre bytes armados a mano en vez de pegarle al bucket
real. Una prueba que necesita internet es una prueba que algun dia falla por
una razon que no tiene nada que ver con el codigo, y esas terminan
desactivadas.

Las dos que si tocan la red estan marcadas con `pytest.mark.red` y se saltean
solas si no hay conexion. Existen porque hay supuestos sobre el formato del
archivo que solo se pueden verificar contra el archivo de verdad.
"""

from __future__ import annotations

import hashlib
import io
import zipfile

import pandas as pd
import pytest

from core import archivo_binance as arch


def _zip_de(filas: list[str]) -> bytes:
    """Un mensual falso, con el mismo formato que sirve Binance."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("BTCUSDT-1d-2020-01.csv", "\n".join(filas))
    return buffer.getvalue()


def _fila(ms: int, cierre: float, volumen_cotizado: float = 1000.0) -> str:
    return (f"{ms},100.0,110.0,90.0,{cierre},50.0,{ms + 86_399_999},"
            f"{volumen_cotizado},10,25.0,500.0,0")


# --- Conversion del CSV crudo ---------------------------------------------

def test_se_queda_solo_con_las_columnas_utiles():
    crudo = pd.DataFrame(
        [[1577836800000, 1, 2, 3, 4, 5, 1577923199999, 6, 7, 8, 9, 0]],
        columns=arch.COLUMNAS,
    )
    df = arch._a_indice_temporal(crudo)
    assert list(df.columns) == arch.UTILES
    assert "ignore" not in df.columns


def test_detecta_milisegundos():
    crudo = pd.DataFrame(
        [[1577836800000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0]], columns=arch.COLUMNAS
    )
    df = arch._a_indice_temporal(crudo)
    assert df.index[0] == pd.Timestamp("2020-01-01", tz="UTC")


def test_las_dos_unidades_pueden_convivir_en_el_mismo_archivo():
    """
    El caso real que rompio la primera version, y el mas caro de encontrar.

    Binance cambio la unidad de `open_time` a mitad de camino, y en el mes del
    cambio **las dos conviven en el mismo mensual**. Caso concreto: KLAYUSDT
    2024-10, donde la primera fila tiene 13 digitos y la ultima 16.

    La deteccion original miraba el maximo del archivo entero, asi que el
    maximo mandaba a leer todo como microsegundos y las 30 filas en
    milisegundos caian en **1970**. El codigo no fallaba: la serie quedaba con
    fechas imposibles y solo se descubrio auditando las 650 descargadas.

    Por eso la conversion es fila por fila.
    """
    crudo = pd.DataFrame(
        [
            [1727740800000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0],      # ms
            [1730246400000000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0],   # us
        ],
        columns=arch.COLUMNAS,
    )
    df = arch._a_indice_temporal(crudo)
    assert df.index[0] == pd.Timestamp("2024-10-01", tz="UTC")
    assert df.index[1] == pd.Timestamp("2024-10-30", tz="UTC")
    assert (df.index.year == 2024).all()


def test_tambien_entiende_segundos_y_nanosegundos():
    """
    Las cuatro bandas, por las dudas. Estan muy separadas: para cualquier
    fecha entre 2001 y 2286 no hay ambiguedad posible entre ellas.
    """
    esperado = pd.Timestamp("2020-01-01", tz="UTC")
    for valor in (1577836800, 1577836800000, 1577836800000000,
                  1577836800000000000):
        crudo = pd.DataFrame([[valor, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0]],
                             columns=arch.COLUMNAS)
        assert arch._a_indice_temporal(crudo).index[0] == esperado, valor


def test_una_fila_con_timestamp_ilegible_se_descarta():
    """Mejor perder una vela que arrastrar un NaT hasta el backtest."""
    crudo = pd.DataFrame(
        [[1577836800000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0],
         ["basura", 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0]],
        columns=arch.COLUMNAS,
    )
    df = arch._a_indice_temporal(crudo)
    assert len(df) == 1
    assert not df.index.isna().any()


def test_detecta_microsegundos():
    """
    Binance cambio la unidad de `open_time` a mitad de camino.

    Si no se detecta, las fechas nuevas caen en el año 56.000 y la serie queda
    inutilizable de una forma que NO salta a la vista: el codigo no falla,
    simplemente ningun dato coincide con ninguna fecha.
    """
    crudo = pd.DataFrame(
        [[1577836800000000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0]],
        columns=arch.COLUMNAS,
    )
    df = arch._a_indice_temporal(crudo)
    assert df.index[0] == pd.Timestamp("2020-01-01", tz="UTC")


def test_el_indice_queda_ordenado_y_en_utc():
    crudo = pd.DataFrame(
        [[1577923200000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0],
         [1577836800000, 1, 2, 3, 4, 5, 0, 6, 7, 8, 9, 0]],
        columns=arch.COLUMNAS,
    )
    df = arch._a_indice_temporal(crudo)
    assert df.index.is_monotonic_increasing
    assert str(df.index.tz) == "UTC"


# --- Checksum -------------------------------------------------------------

def test_un_zip_corrupto_no_pasa(monkeypatch):
    """
    El checksum no es ceremonia: un zip truncado se descomprime igual.

    Sin esta verificacion, los datos falsos entran sin avisar y despues
    aparecen como un hallazgo raro que nadie sabe de donde salio.
    """
    contenido = _zip_de([_fila(1577836800000, 100.0)])

    def falso(url, timeout=60):
        if url.endswith(".CHECKSUM"):
            return b"0000000000000000000000000000000000000000000000000000000000000000  x"
        return contenido

    monkeypatch.setattr(arch, "_leer", falso)
    with pytest.raises(arch.ChecksumInvalido, match="no coincide"):
        arch.bajar_mes("BTCUSDT", "BTCUSDT-1d-2020-01.zip")


def test_un_zip_integro_pasa(monkeypatch):
    contenido = _zip_de([_fila(1577836800000, 100.0),
                         _fila(1577923200000, 105.0)])
    sha = hashlib.sha256(contenido).hexdigest()

    def falso(url, timeout=60):
        return (sha + "  x").encode() if url.endswith(".CHECKSUM") else contenido

    monkeypatch.setattr(arch, "_leer", falso)
    df = arch.bajar_mes("BTCUSDT", "BTCUSDT-1d-2020-01.zip")
    assert len(df) == 2
    assert df["close"].tolist() == [100.0, 105.0]


# --- Pegado de meses ------------------------------------------------------

def test_un_mes_roto_no_tumba_el_simbolo_entero(monkeypatch):
    """
    Perder un simbolo completo por un mes roto seria reintroducir sesgo.

    Un par deslistado hace años tiene mas chances de tener un mensual raro, y
    justamente esos son los que este modulo existe para rescatar. Se saltea el
    mes, se deja constancia, y se sigue.
    """
    def falso_bajar(simbolo, archivo, tf="1d", mercado=arch.SPOT):
        if "2020-02" in archivo:
            raise arch.ChecksumInvalido("roto a proposito")
        return pd.DataFrame(
            {c: [1.0] for c in arch.UTILES},
            index=pd.DatetimeIndex([pd.Timestamp("2020-01-01", tz="UTC")]),
        )

    monkeypatch.setattr(arch, "bajar_mes", falso_bajar)
    df = arch.bajar_simbolo(
        "MUERTOUSDT",
        meses=["M-2020-01.zip", "M-2020-02.zip", "M-2020-03.zip"],
    )
    assert df.attrs["meses_fallados"] == ["M-2020-02.zip"]
    assert len(df) >= 1


def test_si_fallan_todos_los_meses_avisa(monkeypatch):
    def siempre_falla(*a, **k):
        raise arch.ArchivoNoDisponible("no hay")

    monkeypatch.setattr(arch, "bajar_mes", siempre_falla)
    with pytest.raises(arch.ArchivoNoDisponible, match="ningun mensual"):
        arch.bajar_simbolo("X", meses=["a.zip", "b.zip"])


def test_sin_meses_avisa_en_vez_de_devolver_vacio():
    with pytest.raises(arch.ArchivoNoDisponible, match="ningun mensual"):
        arch.bajar_simbolo("NOEXISTEUSDT", meses=[])


def test_no_quedan_velas_duplicadas(monkeypatch):
    """Los mensuales pueden solaparse un dia en los bordes."""
    def repetido(simbolo, archivo, tf="1d", mercado=arch.SPOT):
        return pd.DataFrame(
            {c: [1.0, 2.0] for c in arch.UTILES},
            index=pd.DatetimeIndex(
                [pd.Timestamp("2020-01-31", tz="UTC"),
                 pd.Timestamp("2020-02-01", tz="UTC")]
            ),
        )

    monkeypatch.setattr(arch, "bajar_mes", repetido)
    df = arch.bajar_simbolo("X", meses=["a.zip", "b.zip"])
    assert not df.index.duplicated().any()


# --- Guardar y cargar -----------------------------------------------------

def test_ida_y_vuelta_por_disco(tmp_path):
    idx = pd.date_range("2020-01-01", periods=5, freq="D", tz="UTC")
    original = pd.DataFrame({c: [1.0, 2.0, 3.0, 4.0, 5.0] for c in arch.UTILES},
                            index=idx)
    original.index.name = "open_time"

    arch.guardar(original, "TESTUSDT", "1d", tmp_path)
    leido = arch.cargar("TESTUSDT", "1d", tmp_path)

    assert leido.index.equals(original.index)
    assert leido["close"].tolist() == original["close"].tolist()


def test_cargar_algo_que_no_existe_explica_como_bajarlo(tmp_path):
    with pytest.raises(FileNotFoundError, match="descargar_archivo"):
        arch.cargar("NOEXISTE", "1d", tmp_path)


# --- Las rutas de cada mercado --------------------------------------------

def test_spot_y_perpetuo_apuntan_a_ramas_distintas():
    assert arch.SPOT.ruta_simbolo("BTCUSDT", "1d") == \
        "data/spot/monthly/klines/BTCUSDT/1d/"
    assert arch.PERPETUO.ruta_simbolo("BTCUSDT", "1d") == \
        "data/futures/um/monthly/klines/BTCUSDT/1d/"


# --- Contra el archivo real -----------------------------------------------

@pytest.mark.red
def test_el_listado_incluye_pares_deslistados():
    """
    La razon de ser del modulo, verificada contra el bucket real.

    NBTUSDT no esta en `exchangeInfo` -- no existe ni siquiera con estado
    BREAK -- y sin embargo el archivo tiene su historico. Si esta prueba se
    pone roja, la correccion del sesgo de supervivencia dejo de funcionar y
    hay que enterarse.
    """
    try:
        simbolos = arch.simbolos_disponibles()
    except arch.ArchivoNoDisponible:
        pytest.skip("sin conexion al archivo de Binance")
    assert len(simbolos) > 3000
    assert "NBTUSDT" in simbolos


@pytest.mark.red
def test_un_deslistado_baja_con_checksum_valido():
    try:
        meses = arch.meses_disponibles("NBTUSDT")
        df = arch.bajar_simbolo("NBTUSDT", meses=meses[-2:])
    except arch.ArchivoNoDisponible:
        pytest.skip("sin conexion al archivo de Binance")
    assert not df.empty
    assert df["close"].gt(0).all()
    assert df.attrs["meses_fallados"] == []


# --- Filtros estaticos ----------------------------------------------------

def test_pasan_los_pares_direccionales_normales():
    for s in ("BTCUSDT", "ETHUSDT", "ADAUSDT", "NBTUSDT"):
        assert arch.es_apuesta_direccional(s), s


def test_no_pasan_las_stablecoins():
    """Un par donde la base tambien vale un dolar no tiene tendencia."""
    for s in ("USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "EURUSDT"):
        assert not arch.es_apuesta_direccional(s), s


def test_no_pasan_los_tokens_apalancados():
    """Decaen a diario por construccion: su precio no es el del activo."""
    for s in ("BTCUPUSDT", "BTCDOWNUSDT", "ETHBULLUSDT", "ADABEARUSDT",
              "BTC3LUSDT", "ETH3SUSDT"):
        assert not arch.es_apuesta_direccional(s), s


def test_no_pasan_los_pares_de_otra_cotizacion():
    for s in ("BTCBUSD", "ETHBTC", "BNBEUR"):
        assert not arch.es_apuesta_direccional(s), s


def test_el_filtro_no_mira_si_el_par_sigue_vivo():
    """
    La propiedad que evita repetir el error de la Fase 1.

    Estos filtros dependen SOLO del nombre. Si alguna vez alguien les agrega
    una consulta de estado, esta prueba no lo va a ver -- pero el nombre del
    test si, y por eso esta escrito asi.
    """
    import inspect
    fuente = inspect.getsource(arch.es_apuesta_direccional)
    for palabra in ("TRADING", "BREAK", "status", "exchange_info"):
        assert palabra not in fuente, (
            f"El filtro estatico consulta '{palabra}'. Eso lo vuelve dependiente "
            "de que el par siga vivo, que es exactamente como entro el sesgo de "
            "supervivencia en la Fase 1."
        )


# --- Escapado de URLs -----------------------------------------------------

def test_la_ruta_del_simbolo_queda_cruda():
    """
    Sin escapar, a proposito. `_listar` escapa lo que recibe, asi que una
    ruta ya escapada se escaparia dos veces -- el `%` pasa a `%25` -- y el
    listado devuelve cero meses SIN ningun error visible. Paso el
    30-ago-2026.
    """
    assert arch.SPOT.ruta_simbolo("ABCUSDT", "1d") == \
        "data/spot/monthly/klines/ABCUSDT/1d/"


def test_la_url_de_descarga_escapa_los_nombres_no_ascii():
    """
    Binance lista pares con caracteres no ASCII. Sin escapar, `urllib` ni
    siquiera puede armar la peticion, y la descarga del 30-ago-2026 perdio un
    simbolo entero por eso.

    Un modulo que existe para no dejar simbolos afuera no puede dejarlos
    afuera por como se escriben.
    """
    url = arch._url_de(arch.SPOT, "币安人生USDT", "1d", "x.zip")
    assert url.isascii(), "la URL quedo con caracteres que urllib no puede enviar"
    assert "%E5%B8%81" in url
    assert url.endswith("/1d/x.zip")


def test_la_url_no_rompe_los_nombres_normales():
    url = arch._url_de(arch.SPOT, "BTCUSDT", "1d", "BTCUSDT-1d-2020-01.zip")
    assert url == (
        "https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1d/"
        "BTCUSDT-1d-2020-01.zip"
    )
