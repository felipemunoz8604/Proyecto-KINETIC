"""
Pruebas de las cuatro herramientas de robustez.

Lo dificil de probar aca es que las cuatro contestan preguntas
probabilisticas, y una prueba no puede exigirle a un metodo estadistico que
devuelva un numero exacto. Lo que si se puede exigir es que **ordene bien**:
que una serie con ventaja de un intervalo distinto que una serie de ruido,
que sacar meses buenos baje el CAGR y no lo suba, y que probar mas
configuraciones baje el DSR y no lo suba.

Por eso casi todas comparan dos casos construidos a mano en vez de fijar
constantes. Una prueba con constantes se vuelve roja cada vez que alguien
mejora el metodo, y termina borrada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from metrics import metricas, robustez


def curva_desde_retornos(retornos, desde="2019-01-01") -> pd.Series:
    idx = pd.date_range(desde, periods=len(retornos) + 1, freq="D", tz="UTC")
    valores = 1000.0 * np.cumprod(np.concatenate([[1.0], 1.0 + np.asarray(retornos)]))
    return pd.Series(valores, index=idx)


def ruido(n=1200, semilla=1, deriva=0.0, sigma=0.02) -> pd.Series:
    rng = np.random.default_rng(semilla)
    return curva_desde_retornos(rng.normal(deriva, sigma, n))


# --- Bootstrap por bloques ------------------------------------------------

def test_bootstrap_de_ruido_puro_cruza_cero():
    """Sin deriva no hay ventaja, y el intervalo tiene que admitirlo."""
    ic = robustez.bootstrap_cagr(ruido(deriva=0.0), remuestreos=2000)
    assert not ic.excluye_cero


def test_bootstrap_de_una_deriva_fuerte_excluye_cero():
    """Con deriva clara y 1200 dias, el intervalo no deberia tocar cero."""
    ic = robustez.bootstrap_cagr(ruido(deriva=0.004, sigma=0.01),
                                 remuestreos=2000)
    assert ic.excluye_cero
    assert ic.bajo < ic.estimacion < ic.alto


def test_bootstrap_es_reproducible():
    """Un IC que cambia en cada corrida no se puede citar en un informe."""
    serie = ruido(deriva=0.001)
    a = robustez.bootstrap_cagr(serie, remuestreos=500)
    b = robustez.bootstrap_cagr(serie, remuestreos=500)
    assert a.bajo == b.bajo and a.alto == b.alto


def test_bootstrap_con_serie_muy_corta_no_explota():
    ic = robustez.bootstrap_cagr(curva_desde_retornos([0.01] * 10))
    assert ic.remuestreos == 0  # avisa que no pudo, en vez de inventar


# --- Curva de retiro top-k ------------------------------------------------

def test_sin_sacar_nada_da_exactamente_el_cagr():
    """
    El invariante que atrapo un bug de verdad.

    `retiro_top_k` encadena retornos MENSUALES, y la primera version usaba
    `resample("ME").last().pct_change()`. Eso descarta el primer valor y con el
    se pierde entero el tramo del inicio de la serie al primer fin de mes: en
    una serie de 1.200 dias, el retorno real era 0,461 y la cadena mensual
    daba 0,576. Toda la curva de retiro estaba corrida.

    Con k=0 no se saca nada, asi que tiene que dar el CAGR exacto. Es la forma
    mas barata de que ese bug no vuelva.
    """
    curva = ruido(n=1200, deriva=0.001, semilla=7)
    assert robustez.retiro_top_k(curva, (0,))[0] == pytest.approx(
        metricas.cagr(curva), abs=1e-9
    )


def test_sacar_meses_buenos_baja_el_cagr():
    curva = ruido(n=1200, deriva=0.002, sigma=0.015, semilla=7)
    completo = metricas.cagr(curva)
    retiros = robustez.retiro_top_k(curva)
    assert retiros[1] < completo
    assert retiros[10] < retiros[5] < retiros[3] < retiros[1]


def test_un_resultado_concentrado_se_derrumba_al_sacar_un_mes():
    """
    Dos curvas con CAGR parecido: una pareja, otra con un mes que lo explica
    todo. La curva de retiro tiene que distinguirlas, que es su unico trabajo.
    """
    pareja = curva_desde_retornos([0.0015] * 730)
    concentrada = curva_desde_retornos([0.0] * 700 + [0.035] * 30)

    caida_pareja = robustez.retiro_top_k(pareja)[1] / metricas.cagr(pareja)
    caida_concentrada = (robustez.retiro_top_k(concentrada)[1]
                         / metricas.cagr(concentrada))
    assert caida_concentrada < caida_pareja


# --- Deflated Sharpe Ratio ------------------------------------------------

def test_probar_mas_configuraciones_sube_la_vara():
    """
    El Sharpe esperado por azar crece con el numero de intentos.

    Es todo el punto del DSR: el mejor de veinte intentos sobre ruido se ve
    mejor que el mejor de tres, sin que haya ninguna ventaja.
    """
    pocos = robustez.sharpe_esperado_por_azar([0.02, 0.05, 0.08])
    muchos = robustez.sharpe_esperado_por_azar([0.02, 0.05, 0.08] * 7)
    assert muchos > pocos


def test_el_dsr_baja_cuando_se_probaron_mas_cosas():
    curva = ruido(n=1500, deriva=0.0015, sigma=0.02, semilla=3)
    sr = metricas.sharpe_por_observacion(curva)
    con_pocos = robustez.deflated_sharpe(curva, [sr, sr * 0.8, sr * 0.6])
    con_muchos = robustez.deflated_sharpe(
        curva, [sr] + [sr * f for f in np.linspace(0.1, 0.95, 30)]
    )
    assert con_muchos < con_pocos


def test_el_dsr_devuelve_una_probabilidad():
    curva = ruido(n=1000, deriva=0.001, semilla=11)
    sr = metricas.sharpe_por_observacion(curva)
    p = robustez.deflated_sharpe(curva, [sr, sr * 0.5])
    assert 0.0 <= p <= 1.0


def test_sin_configuraciones_suficientes_no_hay_correccion():
    assert robustez.sharpe_esperado_por_azar([0.05]) == 0.0


# --- Comparacion por pares ------------------------------------------------

def _velas(precios, desde="2019-01-01") -> pd.DataFrame:
    idx = pd.date_range(desde, periods=len(precios), freq="D", tz="UTC")
    return pd.DataFrame({"close": [float(p) for p in precios]}, index=idx)


def test_la_comparacion_por_pares_mide_las_dos_sobre_la_misma_ventana():
    """
    La estrategia es el propio benchmark: el cociente tiene que dar 1,0
    exacto en todos los arranques, sin importar cual sea la ventana.

    Es la prueba que demuestra que la fecha se cancela, que es la razon
    entera por la que se eligio comparar por pares.
    """
    rng = np.random.default_rng(5)
    precios = 100 * np.cumprod(1 + rng.normal(0.001, 0.03, 900))
    datos = _velas(precios)

    def curva(df):
        return df["close"] / float(df["close"].iloc[0]) * 500.0

    comp = robustez.comparar_por_pares(datos, curva, curva)
    assert len(comp.cocientes) >= 15
    assert all(c == pytest.approx(1.0) for c in comp.cocientes)
    assert comp.mediana == pytest.approx(1.0)


def test_una_estrategia_que_esquiva_el_derrumbe_supera_al_benchmark():
    """
    Construido a mano, sin azar: el mercado se derrumba y la estrategia esta
    afuera justo esos dias. Termina mas arriba y cae menos, asi que su Calmar
    tiene que ser mayor en TODOS los arranques, no en la mediana.

    Se arma deterministico a proposito. La primera version de esta prueba
    usaba media exposicion sobre ruido y fallaba: medido sobre 20 semillas,
    **la mitad de exposicion mejora el Calmar en 14 de 20, no siempre**. Que
    no sea una propiedad garantizada importa para el proyecto -- quiere decir
    que el escalar de volatilidad `k_t` por si solo no compra Calmar. El que
    hace el trabajo es la compuerta de regimen, que es justo lo que esta
    prueba modela.
    """
    # El benchmark tiene que terminar arriba: con Calmar <= 0 no sirve de
    # divisor y `comparar_por_pares` lo descarta, que fue como esta prueba
    # fallo la primera vez -- devolvia una lista vacia, no un cociente malo.
    subida = [100 * 1.002 ** i for i in range(300)]
    derrumbe = [subida[-1] * 0.99 ** i for i in range(1, 101)]
    recuperacion = [derrumbe[-1] * 1.004 ** i for i in range(1, 401)]
    datos = _velas(subida + derrumbe + recuperacion)
    inicio_derrumbe, fin_derrumbe = datos.index[300], datos.index[400]

    def benchmark(df):
        return df["close"] / float(df["close"].iloc[0]) * 500.0

    def esquiva(df):
        """Baja la exposicion al 20% durante el derrumbe, como haria la compuerta."""
        r = df["close"].pct_change().fillna(0.0)
        afuera = (df.index >= inicio_derrumbe) & (df.index < fin_derrumbe)
        return 500.0 * (1 + r.where(~afuera, r * 0.2)).cumprod()

    comp = robustez.comparar_por_pares(datos, esquiva, benchmark)
    assert comp.cocientes
    assert comp.peor > 1.0


def test_las_fechas_de_arranque_van_separadas_una_semana():
    datos = _velas([100.0] * 400)
    fechas = robustez.fechas_de_arranque(datos, cantidad=20, paso_dias=7)
    assert len(fechas) == 20
    assert (fechas[1] - fechas[0]).days == 7


def test_no_se_usan_arranques_que_dejan_la_ventana_vacia():
    datos = _velas([100.0] * 30)
    fechas = robustez.fechas_de_arranque(datos, cantidad=20, paso_dias=7)
    assert all(f < datos.index[-1] for f in fechas)
