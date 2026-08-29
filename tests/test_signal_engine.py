"""
Pruebas del motor de senal.

Cada prueba arma una vela a medida donde se cumple todo MENOS una cosa, y
verifica que el motor rechace por esa cosa y no por otra. Si el motor
rechazara por el motivo equivocado, el diagnostico del backtest ("el 99% se
cayo en el filtro de regimen") apuntaria al lugar incorrecto y se terminaria
ajustando el parametro que no era.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from strategy import regime_filter  # noqa: E402
from strategy.signal_engine import (  # noqa: E402
    TipoSenal,
    evaluar_serie,
    evaluar_vela,
    resumen_de_rechazos,
)


@pytest.fixture
def cfg() -> dict:
    """Config con TODOS los umbrales puestos. El real los tiene en null."""
    return {
        "estrategia": {
            "tendencia": {"ema_rapida": 9, "ema_lenta": 21},
            "consolidacion": {"velas": 50, "umbral_desviacion_pct": 2.0},
            "volumen": {"periodo_promedio": 50, "multiplicador_minimo": 2.0},
            "regimen": {"metodo": "adx", "adx_periodo": 14, "adx_minimo": 20.0},
            "portfolio_guard": {"sma_periodo": 200},
        },
        "stops": {"atr_periodo": 14},
    }


def vela(**cambios) -> pd.Series:
    """Vela donde se cumplen las cuatro condiciones. Se rompe una a la vez."""
    base = {
        "close": 110.0,
        "volume": 3000.0,
        "techo": 100.0,        # el cierre lo supera
        "piso": 90.0,
        "vol_promedio": 1000.0,  # 3000 = 3x, supera el 2x pedido
        "ema_rapida": 105.0,
        "ema_lenta": 100.0,
        "desv_pct": 1.0,       # por debajo del umbral de 2.0
        "atr": 3.0,
        "adx": 30.0,           # por encima del minimo de 20
    }
    base.update(cambios)
    serie = pd.Series(base)
    serie.name = pd.Timestamp("2026-08-28 12:00", tz="UTC")
    return serie


# --- El caso que si opera --------------------------------------------------

def test_con_las_cuatro_condiciones_hay_compra(cfg):
    senal = evaluar_vela(vela(), cfg)
    assert senal.tipo is TipoSenal.COMPRAR
    assert senal.hay_entrada
    assert senal.fallo_en is None
    assert senal.precio == pytest.approx(110.0)
    assert senal.datos["atr"] == pytest.approx(3.0)
    # Cinco anotaciones y no cuatro: la condicion 3 del MEGAPROMPT son en
    # realidad dos revisiones (que el CIERRE supere el techo, y que el
    # volumen acompane), y cada una se registra por separado.
    assert len(senal.motivos) == 5
    assert [m.split(":")[0].split(" ")[0] for m in senal.motivos] == [
        "ADX", "consolidacion", "ruptura", "volumen", "EMA",
    ]


# --- Cada condicion, rechazando por su propio motivo -----------------------

def test_sin_regimen_apto_no_se_evalua_nada_mas(cfg):
    senal = evaluar_vela(vela(adx=10.0), cfg)
    assert senal.tipo is TipoSenal.ESPERAR
    assert senal.fallo_en == "regimen"


def test_sin_consolidacion_previa_se_rechaza(cfg):
    """Sin una pausa antes, una 'ruptura' es solo el precio siguiendo su marcha."""
    senal = evaluar_vela(vela(desv_pct=5.0), cfg)
    assert senal.fallo_en == "consolidacion"


def test_si_el_cierre_no_supera_el_techo_se_rechaza(cfg):
    senal = evaluar_vela(vela(close=95.0), cfg)
    assert senal.fallo_en == "ruptura"


def test_una_ruptura_por_MECHA_no_cuenta(cfg):
    """
    El MEGAPROMPT pide CIERRE fuera del rango, no mecha. Una mecha que
    perfora el techo y vuelve adentro es justamente la ruptura falsa que se
    quiere evitar: el motor solo mira el cierre, asi que un maximo altisimo
    con cierre por debajo del techo tiene que quedar afuera.
    """
    senal = evaluar_vela(vela(close=99.0), cfg)   # techo 100: la mecha llego, el cierre no
    assert senal.fallo_en == "ruptura"
    assert senal.tipo is TipoSenal.ESPERAR


def test_ruptura_justo_en_el_techo_no_alcanza(cfg):
    """Igualar el techo no es superarlo."""
    assert evaluar_vela(vela(close=100.0), cfg).fallo_en == "ruptura"


def test_sin_volumen_que_confirme_se_rechaza(cfg):
    senal = evaluar_vela(vela(volume=1500.0), cfg)   # 1,5x, hace falta 2x
    assert senal.fallo_en == "volumen"
    assert "1.50x" in " ".join(senal.motivos)


def test_volumen_justo_en_el_doble_alcanza(cfg):
    assert evaluar_vela(vela(volume=2000.0), cfg).tipo is TipoSenal.COMPRAR


def test_volumen_promedio_cero_no_divide_por_cero(cfg):
    senal = evaluar_vela(vela(vol_promedio=0.0), cfg)
    assert senal.fallo_en == "volumen"


def test_sin_la_direccion_correcta_se_rechaza(cfg):
    senal = evaluar_vela(vela(ema_rapida=95.0), cfg)
    assert senal.fallo_en == "direccion"


def test_emas_iguales_no_alcanzan(cfg):
    assert evaluar_vela(vela(ema_rapida=100.0, ema_lenta=100.0), cfg).fallo_en == "direccion"


# --- Calentamiento ---------------------------------------------------------

def test_con_indicadores_sin_calentar_no_se_opera(cfg):
    senal = evaluar_vela(vela(techo=float("nan")), cfg)
    assert senal.fallo_en == "calentamiento"


def test_falta_de_columna_tambien_es_calentamiento(cfg):
    incompleta = vela()
    senal = evaluar_vela(incompleta.drop("atr"), cfg)
    assert senal.fallo_en == "calentamiento"


# --- Umbrales sin definir --------------------------------------------------

def test_umbral_de_consolidacion_sin_definir_avisa(cfg):
    cfg["estrategia"]["consolidacion"]["umbral_desviacion_pct"] = None
    with pytest.raises(ValueError, match="sin definir"):
        evaluar_vela(vela(), cfg)


def test_adx_minimo_sin_definir_avisa(cfg):
    cfg["estrategia"]["regimen"]["adx_minimo"] = None
    with pytest.raises(ValueError, match="sin definir"):
        evaluar_vela(vela(), cfg)


def test_metodo_de_regimen_desconocido_avisa(cfg):
    cfg["estrategia"]["regimen"]["metodo"] = "bola_de_cristal"
    with pytest.raises(ValueError, match="desconocido"):
        evaluar_vela(vela(), cfg)


# --- Filtro de regimen por separado ---------------------------------------

def test_el_filtro_por_pendiente_mide_la_direccion_grande():
    fila = pd.Series({"pendiente_sma": 3.0})
    assert regime_filter.evaluar_pendiente(fila, umbral=0.0).apto
    assert not regime_filter.evaluar_pendiente(pd.Series({"pendiente_sma": -2.0}), 0.0).apto


def test_el_filtro_avisa_cuando_el_indicador_no_calento():
    resultado = regime_filter.evaluar_adx(pd.Series({"adx": float("nan")}), 20.0)
    assert not resultado.apto
    assert "calentar" in resultado.motivo


# --- Serie completa y diagnostico -----------------------------------------

def test_evaluar_serie_devuelve_una_senal_por_vela(cfg):
    df = pd.DataFrame([vela(), vela(adx=5.0), vela(volume=100.0)])
    df.index = pd.date_range("2026-08-28", periods=3, freq="1h", tz="UTC")

    senales = evaluar_serie(df, cfg)
    assert len(senales) == 3
    assert [s.fallo_en for s in senales] == [None, "regimen", "volumen"]


def test_el_resumen_de_rechazos_dice_donde_se_cae_todo(cfg):
    df = pd.DataFrame([vela(), vela(adx=5.0), vela(adx=5.0), vela(volume=100.0)])
    df.index = pd.date_range("2026-08-28", periods=4, freq="1h", tz="UTC")

    resumen = resumen_de_rechazos(evaluar_serie(df, cfg))
    assert resumen == {"ENTRADA": 1, "regimen": 2, "volumen": 1}


def test_la_senal_registra_el_porque_de_cada_rechazo(cfg):
    """
    Cuando Felipe pregunte "por que no entro aca", la respuesta tiene que
    estar guardada, no reconstruida a mano despues.
    """
    senal = evaluar_vela(vela(volume=1200.0), cfg)
    texto = " ".join(senal.motivos)
    assert "ADX" in texto            # el regimen paso, y quedo anotado
    assert "consolidacion" in texto  # la consolidacion paso, y quedo anotada
    assert "ruptura" in texto        # la ruptura paso, y quedo anotada
    assert "volumen flojo" in texto  # y aca se cayo
