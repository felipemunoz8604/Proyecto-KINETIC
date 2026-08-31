"""
Pruebas del historico de financiacion.

La que mas importa es `test_el_intervalo_de_cuatro_horas_no_se_anualiza_como_ocho`:
suponer tres cobros diarios es la forma facil de subestimar a la mitad el
carry de los simbolos que Binance paso a 4 horas, y no se nota en ningun lado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import financiacion as fin  # noqa: E402


def _crudo(momentos_ms: list[int], tasas: list[float],
           horas: list[int]) -> pd.DataFrame:
    return pd.DataFrame({
        "calc_time": momentos_ms,
        "funding_interval_hours": horas,
        "last_funding_rate": tasas,
    })


def test_la_ruta_no_tiene_temporalidad():
    """
    La rama de financiacion es `.../fundingRate/{simbolo}/`, sin carpeta de
    temporalidad. Meterle una dejaria el listado vacio sin ningun error.
    """
    ruta = fin.FINANCIACION.ruta_simbolo("BTCUSDT")
    assert ruta.endswith("fundingRate/BTCUSDT/")
    assert "1d" not in ruta


def test_el_indice_queda_en_utc_y_ordenado():
    df = fin._a_indice(_crudo([1600000000000, 1599971200000],
                              [0.0001, 0.0002], [8, 8]))
    assert str(df.index.tz) == "UTC"
    assert df.index.is_monotonic_increasing


def test_las_unidades_mezcladas_se_normalizan_fila_por_fila():
    """
    Es el mismo error que costo caro con las velas el 30-ago-2026: dentro de
    un mismo archivo mensual conviven milisegundos y microsegundos, y elegir
    la unidad por el maximo del archivo tira filas a 1970 sin avisar.
    """
    # Dos instantes DISTINTOS, uno en milisegundos y otro en microsegundos.
    # (Si fueran el mismo instante en dos unidades, el deduplicador se
    # quedaria con uno solo -- que es lo correcto, pero no prueba nada.)
    en_ms = 1600000000000
    en_us = 1600028800000 * 1000          # ocho horas despues
    df = fin._a_indice(_crudo([en_ms, en_us], [0.0001, 0.0002], [8, 8]))
    assert len(df) == 2
    assert df.index[0].year == 2020
    assert df.index[1].year == 2020
    assert (df.index[1] - df.index[0]) == pd.Timedelta(hours=8)


def test_las_filas_repetidas_se_descartan():
    df = fin._a_indice(_crudo([1600000000000, 1600000000000],
                              [0.0001, 0.0009], [8, 8]))
    assert len(df) == 1
    assert df["tasa"].iloc[0] == 0.0001   # se queda la primera


def test_anualizar_con_ocho_horas_son_tres_cobros_por_dia():
    df = fin._a_indice(_crudo([1600000000000], [0.0001], [8]))
    assert fin.anualizar(df).iloc[0] == pytest.approx(0.0001 * 3 * 365)


def test_el_intervalo_de_cuatro_horas_no_se_anualiza_como_ocho():
    """
    A igual tasa por cobro, un simbolo de 4 horas cobra el DOBLE por año.
    Anualizarlo con la constante de 8 le borra la mitad del carry.
    """
    de_ocho = fin._a_indice(_crudo([1600000000000], [0.0001], [8]))
    de_cuatro = fin._a_indice(_crudo([1600000000000], [0.0001], [4]))
    assert (fin.anualizar(de_cuatro).iloc[0]
            == pytest.approx(2 * fin.anualizar(de_ocho).iloc[0]))


def test_una_tasa_negativa_anualiza_negativo():
    """Cuando la tasa es negativa, el corto paga en vez de cobrar."""
    df = fin._a_indice(_crudo([1600000000000], [-0.0003], [8]))
    assert fin.anualizar(df).iloc[0] < 0


def test_el_resumen_trae_lo_que_pide_la_medicion():
    momentos = [1600000000000 + i * 8 * 3600 * 1000 for i in range(100)]
    rng = np.random.default_rng(20260830)
    tasas = rng.normal(0.0001, 0.0002, 100).tolist()
    r = fin.resumen(fin._a_indice(_crudo(momentos, tasas, [8] * 100)))
    assert r["cobros"] == 100
    assert 0.0 <= r["fraccion_positiva"] <= 1.0
    assert r["p10"] < r["mediana"] < r["p90"]
    assert r["intervalos"] == [8.0]


def test_el_resumen_de_una_serie_vacia_no_rompe():
    vacio = pd.DataFrame({"tasa": [], "horas": []},
                         index=pd.DatetimeIndex([], tz="UTC"))
    assert fin.resumen(vacio) == {}


def test_guardar_y_cargar_conservan_la_zona_horaria(tmp_path):
    df = fin._a_indice(_crudo([1600000000000, 1600028800000],
                              [0.0001, 0.0002], [8, 8]))
    fin.guardar(df, "BTCUSDT", tmp_path)
    vuelta = fin.cargar("BTCUSDT", tmp_path)
    assert str(vuelta.index.tz) == "UTC"
    # `check_index_type=False`: al volver del CSV pandas usa microsegundos en
    # vez de milisegundos. Es la misma fecha; la resolucion no cambia nada.
    pd.testing.assert_frame_equal(df, vuelta, check_freq=False,
                                  check_index_type=False)
