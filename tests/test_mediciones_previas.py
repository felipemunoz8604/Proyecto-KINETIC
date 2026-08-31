"""
Pruebas de la compuerta de regimen (5.4) y del corte transversal (5.2).

La que mas importa es `test_la_compuerta_usa_el_cierre_de_ayer`: sin ese
desfase de un dia la compuerta esquiva caidas que en vivo no habria
esquivado, y el backtest sale precioso sin que nada parezca roto.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import transversal as tr  # noqa: E402
from risk import compuerta as cp  # noqa: E402


def _dias(n: int, desde: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


class _PanelFalso:
    """Lo minimo que `transversal` le pide a un Panel."""

    def __init__(self, cierres: pd.DataFrame):
        self.cierres = cierres

    @property
    def ultima_vela(self) -> pd.Series:
        return self.cierres.apply(lambda c: c.last_valid_index())


# --- Compuerta de regimen (5.4) -------------------------------------------

def test_sin_doscientos_dias_la_compuerta_esta_apagada():
    """Sin dato no se opera. Lo contrario seria suponer que estabamos adentro."""
    precios = pd.Series(np.arange(1, 151, dtype=float), index=_dias(150))
    g = cp.compuerta_de_regimen(precios)
    assert (g == 0).all()


def test_una_serie_que_sube_siempre_termina_con_la_compuerta_encendida():
    precios = pd.Series(np.arange(1, 401, dtype=float), index=_dias(400))
    g = cp.compuerta_de_regimen(precios)
    assert g.iloc[-1] == 1
    assert g.iloc[:200].sum() == 0


def test_la_compuerta_usa_el_cierre_de_ayer():
    """
    El dia en que el precio cruza por encima de su media, la compuerta todavia
    esta apagada: recien se entera al dia siguiente.

    Sin este desfase el backtest compra el mismo dia que se conoce el cierre,
    cosa imposible: cuando conoces el cierre, el dia ya termino.
    """
    # 250 dias planos en 100, despues un salto sostenido a 200.
    valores = np.concatenate([np.full(250, 100.0), np.full(50, 200.0)])
    precios = pd.Series(valores, index=_dias(300))
    g = cp.compuerta_de_regimen(precios)

    primer_encendido = g[g == 1].index[0]
    dia_del_salto = precios.index[250]
    assert primer_encendido == dia_del_salto + pd.Timedelta(days=1)


def test_agregar_datos_del_futuro_no_cambia_las_decisiones_pasadas():
    """
    La compuerta de una fecha no puede depender de cuantas velas vinieron
    despues. Es la misma prueba que protege a los indicadores y al universo.
    """
    rng = np.random.default_rng(20260830)
    precios = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600))),
                        index=_dias(600))
    completa = cp.compuerta_de_regimen(precios)
    cortada = cp.compuerta_de_regimen(precios.iloc[:400])
    pd.testing.assert_series_equal(completa.iloc[:400], cortada)


def test_los_tramos_cubren_todos_los_dias_sin_solaparse():
    rng = np.random.default_rng(1)
    precios = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.03, 800))),
                        index=_dias(800))
    g = cp.compuerta_de_regimen(precios)
    t = cp.tramos(g)
    assert t["dias"].sum() == len(g)
    assert (t["estado"].diff().dropna() != 0).all()   # alternan de verdad


def test_los_latigazos_son_los_tramos_cortos():
    g = pd.Series([0] * 20 + [1] * 3 + [0] * 20 + [1] * 40,
                  index=_dias(83))
    cortos = cp.latigazos(g, dias_minimos=10)
    assert len(cortos) == 1
    assert cortos.iloc[0]["dias"] == 3


def test_el_ultimo_tramo_no_cuenta_como_latigazo():
    """
    El ultimo tramo esta cortado por el final de los datos, no por el mercado.
    Contarlo seria un artefacto de donde termina la ventana.
    """
    g = pd.Series([0] * 50 + [1] * 2, index=_dias(52))
    assert len(cp.latigazos(g, dias_minimos=10)) == 0


def test_los_cierres_desordenados_levantan():
    precios = pd.Series([1.0, 2.0], index=_dias(2)[::-1])
    with pytest.raises(ValueError):
        cp.compuerta_de_regimen(precios)


# --- Corte transversal (5.2) ----------------------------------------------

def test_el_retorno_hacia_adelante_mide_lo_que_paso_despues():
    idx = _dias(60)
    cierres = pd.DataFrame({
        "AUSDT": np.linspace(100, 200, 60),    # duplica
        "BUSDT": np.full(60, 50.0),            # plano
    }, index=idx)
    seleccion = {idx[0]: ["AUSDT", "BUSDT"]}
    r = tr.retornos_hacia_adelante(_PanelFalso(cierres), seleccion, dias=28)

    fila = r.retornos.iloc[0]
    assert fila["BUSDT"] == pytest.approx(0.0)
    assert fila["AUSDT"] > 0.4
    assert r.truncados == 0


def test_un_simbolo_que_muere_a_mitad_de_camino_cuenta_como_truncado():
    """
    Se mide contra su ultimo cierre, que es optimista: no incluye la
    penalizacion por deslistado. Por eso hay que saber cuantos son.
    """
    idx = _dias(60)
    cierres = pd.DataFrame({
        "VIVOUSDT": np.full(60, 100.0),
        "MUERTOUSDT": [100.0] * 10 + [np.nan] * 50,
    }, index=idx)
    seleccion = {idx[0]: ["VIVOUSDT", "MUERTOUSDT"]}
    r = tr.retornos_hacia_adelante(_PanelFalso(cierres), seleccion, dias=28)
    assert r.truncados == 1
    assert r.observaciones == 2


def test_si_todas_se_mueven_igual_la_dispersion_es_cero():
    """El caso que mataria a E1: elegir bien y elegir mal dan lo mismo."""
    idx = _dias(60)
    cierres = pd.DataFrame({s: np.linspace(100, 150, 60)
                            for s in ("AUSDT", "BUSDT", "CUSDT")}, index=idx)
    seleccion = {idx[0]: ["AUSDT", "BUSDT", "CUSDT"]}
    r = tr.retornos_hacia_adelante(_PanelFalso(cierres), seleccion, dias=28)
    assert tr.dispersion(r.retornos).iloc[0] == pytest.approx(0.0, abs=1e-12)


def test_la_brecha_perfecta_es_mejores_menos_peores():
    retornos = pd.DataFrame(
        [[0.50, 0.40, -0.10, -0.20]],
        columns=["A", "B", "C", "D"], index=_dias(1))
    brecha = tr.brecha_perfecta(retornos, k=2)
    assert brecha.iloc[0] == pytest.approx(0.45 - (-0.15))


def test_la_ventaja_del_mejor_grupo_es_contra_el_promedio():
    """
    El techo que le corresponde a E1, que va solo largo: cuanto le saca elegir
    perfecto a comprar la canasta entera.
    """
    retornos = pd.DataFrame(
        [[0.50, 0.40, -0.10, -0.20]],
        columns=["A", "B", "C", "D"], index=_dias(1))
    ventaja = tr.ventaja_del_mejor_grupo(retornos, k=2)
    assert ventaja.iloc[0] == pytest.approx(0.45 - 0.15)


def test_elegir_todo_no_da_ninguna_ventaja():
    """Si k es el universo entero no hay seleccion, y el techo tiene que ser 0."""
    retornos = pd.DataFrame([[0.5, 0.1, -0.2]],
                            columns=["A", "B", "C"], index=_dias(1))
    assert len(tr.ventaja_del_mejor_grupo(retornos, k=3)) == 0


def test_la_brecha_no_se_calcula_sin_suficientes_simbolos():
    retornos = pd.DataFrame([[0.5, -0.2, np.nan]],
                            columns=["A", "B", "C"], index=_dias(1))
    assert len(tr.brecha_perfecta(retornos, k=2)) == 0


def test_dos_series_identicas_correlacionan_uno():
    idx = _dias(200)
    rng = np.random.default_rng(7)
    base = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 200)))
    cierres = pd.DataFrame({"AUSDT": base, "BUSDT": base * 3}, index=idx)
    seleccion = {idx[150]: ["AUSDT", "BUSDT"]}
    c = tr.correlacion_media_por_pares(_PanelFalso(cierres), seleccion, dias=90)
    assert c.iloc[0] == pytest.approx(1.0)


def test_la_correlacion_solo_mira_hacia_atras():
    """
    Si lo que pasa despues de la fecha cambiara la correlacion, estaria
    espiando. Se rompe el futuro entero y el numero tiene que quedar igual.
    """
    idx = _dias(300)
    rng = np.random.default_rng(11)
    a = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300)))
    b = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300)))
    cierres = pd.DataFrame({"AUSDT": a, "BUSDT": b}, index=idx)
    fecha = idx[200]
    seleccion = {fecha: ["AUSDT", "BUSDT"]}

    original = tr.correlacion_media_por_pares(_PanelFalso(cierres), seleccion)

    roto = cierres.copy()
    roto.loc[roto.index >= fecha, "BUSDT"] = a[200:]   # copia exacta de A
    despues = tr.correlacion_media_por_pares(_PanelFalso(roto), seleccion)

    pd.testing.assert_series_equal(original, despues)
