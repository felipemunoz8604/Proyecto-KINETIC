"""
Pruebas de la vara corregida: c_up, c_down, la frontera derivada y la CDaR.

LA QUE SOSTIENE TODO
---------------------
`test_la_frontera_es_exactamente_ganarle_a_b1`. El analista afirma que la
frontera no es un umbral sino una identidad. Esa prueba lo verifica sobre
curvas al azar: pasar la frontera y superar el retorno total de B1 tienen que
ser **el mismo evento**, no dos parecidos. Si algun dia se separan, la
derivacion se rompio y el criterio volvio a ser un numero elegido.

LAS OTRAS TRES QUE IMPORTAN
-----------------------------
- `test_exposicion_constante_no_puede_pasar` -- la consecuencia incomoda de la
  identidad, y la razon por la que la vara es una vara.
- `test_el_benchmark_contra_si_mismo_esta_justo_en_la_frontera` -- el
  invariante de escala, el mismo que en `test_regimen.py`.
- `test_la_cdar_nunca_es_peor_que_la_caida_maxima` -- si se rompiera, la CDaR
  no seria un promedio de cola y el reemplazo de C-B' no tendria sentido.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import benchmarks, frontera, metricas  # noqa: E402


def _dias(n: int, desde: str = "2019-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _curva_al_azar(n: int = 1200, semilla: int = 3,
                   deriva: float = 0.0015, sigma: float = 0.03) -> pd.Series:
    rng = np.random.default_rng(semilla)
    pasos = rng.normal(deriva, sigma, n)
    return pd.Series(1000 * np.exp(np.cumsum(pasos)), index=_dias(n))


def _b1(n: int = 1200) -> pd.Series:
    return _curva_al_azar(n, semilla=20260903)


# --- Log-retornos por periodo ----------------------------------------------

def test_los_log_retornos_suman_el_retorno_total():
    """
    Es la propiedad de la que cuelga toda la vara nueva: si los log-retornos
    por periodo no sumaran el total, particionar la muestra en dos conjuntos y
    sumar cada uno no reconstruiria el resultado, y la frontera seria falsa.
    """
    curva = _curva_al_azar()
    total = float(frontera.log_por_periodo(curva).sum())
    esperado = float(np.log(curva.iloc[-1] / curva.iloc[0]))
    assert total == pytest.approx(esperado, rel=1e-12)


def test_no_se_pierde_el_tramo_inicial():
    """
    Mismo error que ya costo una prueba roja en `retiro_top_k` y otra en
    `regimen._mensual`: `resample().last()` descarta el primer valor y con el
    se va el tramo del inicio al primer cierre de periodo.
    """
    # Sube fuerte los primeros 20 dias y despues queda plano. Si el tramo
    # inicial se perdiera, el total daria cero.
    valores = np.concatenate([1000 * 1.02 ** np.arange(21),
                              np.full(400, 1000 * 1.02 ** 20)])
    curva = pd.Series(valores, index=_dias(len(valores)))
    total = float(frontera.log_por_periodo(curva).sum())
    assert total == pytest.approx(float(np.log(1.02 ** 20)), rel=1e-9)


def test_una_periodicidad_desconocida_falla_fuerte():
    with pytest.raises(ValueError, match="Periodicidad desconocida"):
        frontera.log_por_periodo(_curva_al_azar(60), regla="anual")


# --- La frontera ------------------------------------------------------------

def test_u_es_positivo_y_d_negativo():
    f = frontera.frontera(_b1())
    assert f.u > 0
    assert f.d < 0
    assert f.periodos_arriba > 0 and f.periodos_abajo > 0
    assert f.r == pytest.approx(abs(f.d) / f.u)


def test_u_mas_d_es_el_retorno_total_de_b1():
    """U y D particionan la muestra entera: no se descarta ningun periodo."""
    b1 = _b1()
    f = frontera.frontera(b1)
    assert f.u + f.d == pytest.approx(
        float(np.log(b1.iloc[-1] / b1.iloc[0])), rel=1e-12)


def test_la_frontera_es_exactamente_ganarle_a_b1():
    """
    LA PRUEBA QUE SOSTIENE EL CRITERIO.

    El analista afirma que `c_up >= 1 - (1-c_down)*R` no es un umbral elegido
    sino la condicion de igualar el retorno de B1. Si es cierto, sobre
    cualquier curva las dos preguntas tienen que dar la misma respuesta:

        - la del criterio:  c_up >= exigido
        - la de la realidad: la estrategia termino arriba de B1

    Se prueba sobre 25 curvas al azar de todas las formas -- algunas ganan,
    otras pierden -- para que no pase por casualidad.
    """
    b1 = _b1()
    ganadas = perdidas = 0
    for semilla in range(25):
        # Derivas distintas a proposito: algunas curvas le ganan a B1 y otras
        # no. Si todas cayeran del mismo lado la prueba no probaria nada.
        curva = _curva_al_azar(len(b1), semilla=semilla,
                               deriva=0.0005 + 0.0001 * semilla)
        c = frontera.capturas(curva, b1, f"azar{semilla}")
        gano = (float(np.log(curva.iloc[-1] / curva.iloc[0]))
                >= float(np.log(b1.iloc[-1] / b1.iloc[0])))
        assert c.pasa == gano, (
            f"semilla {semilla}: el criterio dice {c.pasa} y la realidad "
            f"dice {gano}. La frontera dejo de ser la identidad.")
        ganadas += gano
        perdidas += not gano
    assert ganadas > 0 and perdidas > 0, (
        "Todas las curvas cayeron del mismo lado: la prueba no distingue nada.")


def test_el_benchmark_contra_si_mismo_esta_justo_en_la_frontera():
    """
    El invariante de escala: si la estrategia ES B1, captura 1,0 arriba y 1,0
    abajo, y queda exactamente sobre la frontera con margen cero.
    """
    b1 = _b1()
    c = frontera.capturas(b1, b1, "B1")
    assert c.c_up == pytest.approx(1.0)
    assert c.c_down == pytest.approx(1.0)
    assert c.exigido == pytest.approx(1.0)
    assert c.margen == pytest.approx(0.0, abs=1e-12)
    assert c.pasa


def test_exposicion_constante_no_puede_pasar():
    """
    La consecuencia incomoda de la identidad, y la que hace que la vara sea
    vara: una estrategia que toma la fraccion `b` de los log-retornos de B1
    puntua c_up = c_down = b, y con R < 1 solo pasa si b >= 1.

    **Media exposicion no puede pasar por construccion.** No hace falta
    medirla para saberlo, y por eso el hallazgo de que "todo lo probado es
    media exposicion disfrazada" cierra la pregunta en vez de abrirla.
    """
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0)
    for b in (0.3, 0.5, 0.8, 0.99):
        curva = pd.Series(1000 * np.exp(np.cumsum(b * logs.to_numpy())),
                          index=b1.index)
        c = frontera.capturas(curva, b1, f"b={b}")
        assert c.c_up == pytest.approx(b, rel=1e-9)
        assert c.c_down == pytest.approx(b, rel=1e-9)
        assert not c.pasa
        assert c.margen < 0


def test_ganar_donde_el_mercado_pierde_da_c_down_negativo():
    """
    Es lo que hace E0, y la razon por la que la palabra "proteccion" se le
    quedaba corta: no evita perdidas, produce retorno donde B1 no lo produce.
    """
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0).to_numpy()
    mensual = frontera.log_por_periodo(b1)
    bajaron = set(mensual[mensual < 0].index)
    periodo = pd.Series(b1.index.to_period("M"), index=b1.index).to_numpy()
    # Se invierte el signo del retorno en los meses que B1 bajo.
    propios = np.where([p in bajaron for p in periodo], -logs, logs)
    curva = pd.Series(1000 * np.exp(np.cumsum(propios)), index=b1.index)
    c = frontera.capturas(curva, b1, "invertida")
    assert c.c_down < 0


def test_agregar_datos_del_futuro_no_cambia_lo_ya_medido():
    """
    Particionar por el signo del propio mes es evaluacion, no una regla de
    trading -- pero la particion de un mes tampoco puede depender de meses
    posteriores, o el numero cambiaria segun cuando se lo mire.
    """
    b1 = _b1()
    entera = frontera.frontera(b1)
    cortada = frontera.frontera(b1.iloc[:800])
    parcial = frontera.log_por_periodo(b1.iloc[:800])
    completa = frontera.log_por_periodo(b1)
    comunes = parcial.index.intersection(completa.index)[:-1]  # el ultimo mes
    pd.testing.assert_series_equal(                            # esta a medias
        (parcial.loc[comunes] > 0), (completa.loc[comunes] > 0))
    assert entera.periodos_arriba + entera.periodos_abajo > (
        cortada.periodos_arriba + cortada.periodos_abajo)


def test_el_veredicto_se_reporta_en_las_tres_periodicidades():
    """
    El analista pidio semanal y trimestral como control. No son criterio: si
    el veredicto cambiara con el periodo, hay que decirlo, no elegir el que
    convenga.
    """
    b1 = _b1()
    curva = _curva_al_azar(len(b1), semilla=11)
    for regla in (frontera.MENSUAL, frontera.SEMANAL, frontera.TRIMESTRAL):
        c = frontera.capturas(curva, b1, "x", regla)
        assert np.isfinite(c.c_up) and np.isfinite(c.c_down)
        assert c.regla == regla


# --- CDaR -------------------------------------------------------------------

def test_una_curva_que_solo_sube_no_tiene_cdar():
    curva = pd.Series(np.linspace(1000, 5000, 500), index=_dias(500))
    assert frontera.cdar(curva) == pytest.approx(0.0)


def test_la_cdar_nunca_es_peor_que_la_caida_maxima():
    """
    La CDaR promedia la peor cola; la caida maxima se queda con el minimo. El
    promedio de una cola no puede ser mas extremo que su peor elemento. Si
    esto se rompiera, la CDaR no seria lo que dice ser y el reemplazo de C-B'
    no tendria sentido.
    """
    for semilla in range(8):
        curva = _curva_al_azar(900, semilla=semilla, deriva=0.0)
        peor, _, _, _ = metricas.caida_maxima(curva)
        c = frontera.cdar(curva)
        assert peor <= c <= 0.0


def test_la_cdar_tiene_muchas_observaciones_y_la_caida_maxima_una():
    """
    Es el motivo entero del cambio: la caida maxima sale de un solo dia.
    """
    curva = _curva_al_azar(1200, deriva=0.0)
    caidas = frontera.caida_diaria(curva)
    cuantos = max(1, int(round(len(caidas) * 0.05)))
    assert cuantos >= 50
    # Y el promedio de esos 60 dias es el numero que devuelve la funcion.
    assert frontera.cdar(curva) == pytest.approx(
        float(np.sort(caidas.to_numpy())[:cuantos].mean()))


def test_la_fraccion_de_cdar_contra_si_mismo_da_uno():
    b1 = _b1()
    assert frontera.fraccion_de_cdar(b1, b1) == pytest.approx(1.0)


def test_media_exposicion_baja_la_cdar_a_la_mitad_aproximadamente():
    """
    Ancla de escala: si la caida escala con la exposicion, medio adentro
    deberia dar cerca de media CDaR. Es la relacion en la que se apoya el
    analista para pedir que sigma objetivo se derive de la caida objetivo.
    """
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0).to_numpy()
    mitad = pd.Series(1000 * np.exp(np.cumsum(0.5 * logs)), index=b1.index)
    assert 0.35 < frontera.fraccion_de_cdar(mitad, b1) < 0.65


def test_un_nivel_fuera_de_rango_falla_fuerte():
    with pytest.raises(ValueError, match="entre 0 y 1"):
        frontera.cdar(_curva_al_azar(100), nivel=1.0)


# --- C-C': el intervalo del exceso ------------------------------------------

def test_el_exceso_contra_si_mismo_es_cero_exacto():
    b1 = _b1()
    bajo, alto = frontera.intervalo_de_exceso(b1, b1)
    assert bajo == pytest.approx(0.0, abs=1e-12)
    assert alto == pytest.approx(0.0, abs=1e-12)


def test_una_ventaja_grande_y_pareja_se_distingue_de_cero():
    """Control positivo: si ni esto excluye cero, la prueba no detecta nada."""
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0).to_numpy()
    mejor = pd.Series(1000 * np.exp(np.cumsum(logs + 0.004)), index=b1.index)
    bajo, alto = frontera.intervalo_de_exceso(mejor, b1)
    assert bajo > 0.0


def test_una_serie_muy_corta_devuelve_nan_en_vez_de_inventar():
    curva = _curva_al_azar(40)
    bajo, alto = frontera.intervalo_de_exceso(curva, curva)
    assert np.isnan(bajo) and np.isnan(alto)


# --- B3: la calibracion -----------------------------------------------------

def test_la_calibracion_encuentra_la_exposicion_del_cagr_pedido():
    """
    Sin motor: una curva sintetica donde `k` escala los log-retornos. La
    biseccion tiene que devolver el `k` que da el CAGR pedido.
    """
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0).to_numpy()

    def curva_de(k: float) -> pd.Series:
        return pd.Series(1000 * np.exp(np.cumsum(k * logs)), index=b1.index)

    objetivo = metricas.cagr(curva_de(0.42))
    k, curva = benchmarks.calibrar_exposicion_constante(curva_de, objetivo)
    assert k == pytest.approx(0.42, abs=0.01)
    assert metricas.cagr(curva) == pytest.approx(objetivo, abs=1e-3)


def test_la_exposicion_constante_es_constante():
    indice = _dias(100)
    marco = benchmarks.exposicion_constante(indice, 0.45)
    assert list(marco.columns) == ["BTCUSDT"]
    assert (marco["BTCUSDT"] == 0.45).all()


def test_calibrar_sin_una_funcion_falla_fuerte():
    with pytest.raises(TypeError):
        benchmarks.calibrar_exposicion_constante("no soy una funcion", 0.3)


# --- B4: E0 sin compuerta ---------------------------------------------------

def test_b4_esta_siempre_dentro_y_e0_no():
    """
    B4 se define como "E0 sin la compuerta". Tiene que estar dentro todos los
    dias en que hay volatilidad medida, y E0 no.
    """
    from strategy import e0  # importado aca para no cargarlo si no hace falta

    rng = np.random.default_rng(5)
    cierres = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0.0005, 0.03, 900))),
        index=_dias(900))
    con = e0.exposicion_objetivo(cierres)
    sin = e0.exposicion_objetivo(cierres, con_compuerta=False)
    # Donde E0 esta dentro, las dos coinciden exactamente: la compuerta es un
    # multiplicador de 0 o 1 y no toca el dimensionamiento.
    dentro = con > 0
    assert dentro.sum() > 0
    pd.testing.assert_series_equal(con[dentro], sin[dentro])
    # Y B4 esta dentro estrictamente mas dias.
    assert (sin > 0).sum() > dentro.sum()


def test_los_dos_caminos_de_b4_coinciden():
    """
    La misma exigencia que ya tenia E0: el camino rapido y el lento tienen que
    dar lo mismo, ahora tambien sin compuerta. Si no, la bandera se aplico en
    un solo lado.
    """
    from strategy import e0

    rng = np.random.default_rng(9)
    cierres = pd.Series(
        100 * np.exp(np.cumsum(rng.normal(0.001, 0.025, 400))),
        index=_dias(400))
    rapido = e0.exposicion_objetivo(cierres, con_compuerta=False)
    lento = e0.exposicion_objetivo_lenta(cierres, con_compuerta=False)
    pd.testing.assert_series_equal(rapido, lento, check_names=False,
                                   rtol=1e-12)


# --- La condicion que vale para cualquier compuerta de prendido y apagado ---

def test_una_compuerta_a_exposicion_plena_pasa_solo_si_lo_que_deja_afuera_baja():
    """
    La afirmacion que se le manda al analista sobre A1, comprobada.

    A exposicion 1,0 una compuerta no dimensiona: solo elige dias. Su
    log-retorno es el del activo en los dias que deja adentro. Como la
    frontera es exactamente igualar el retorno total de B1, la compuerta pasa
    **si y solo si** los dias que deja AFUERA suman negativo.

    Se prueba con compuertas al azar -- ni buenas ni malas, solo distintas --
    para que la equivalencia no dependa de ninguna en particular.
    """
    b1 = _b1()
    logs = np.log(b1 / b1.shift(1)).fillna(0.0).to_numpy()
    rng = np.random.default_rng(2026)
    pasaron = fallaron = 0
    for _ in range(20):
        # Compuerta al azar con rachas, para que se parezca a una de verdad.
        estado = rng.random(len(b1)) < rng.uniform(0.25, 0.75)
        abierta = pd.Series(estado, index=b1.index).rolling(
            20, min_periods=1).mean().to_numpy() > 0.5
        curva = pd.Series(1000 * np.exp(np.cumsum(np.where(abierta, logs, 0.0))),
                          index=b1.index)
        c = frontera.capturas(curva, b1, "compuerta")
        afuera = float(logs[~abierta].sum())
        assert c.pasa == (afuera <= frontera.TOLERANCIA), (
            f"la compuerta dejo afuera {afuera:+.4f} y el criterio dijo "
            f"{c.pasa}. La equivalencia se rompio.")
        pasaron += c.pasa
        fallaron += not c.pasa
    assert pasaron > 0 and fallaron > 0, (
        "Todas las compuertas cayeron del mismo lado: no se probo nada.")


def test_estar_afuera_del_mercado_degenera_la_cola_de_la_cdar():
    """
    El defecto de la CDaR que se le reporta al analista, comprobado.

    Mientras una estrategia esta AFUERA del mercado su patrimonio no se mueve,
    asi que su caida contra el maximo previo es identica todos esos dias. La
    cola del peor 5% pasa a ser el MISMO numero repetido, y la CDaR degenera
    en la caida maxima -- justo lo que el cambio de medida queria evitar.
    """
    # Sube, se derrumba, y despues queda plana 300 dias: la compuerta cerro.
    valores = np.concatenate([
        np.linspace(1000, 2000, 200),      # sube
        np.linspace(2000, 1200, 100),      # se derrumba
        np.full(300, 1200.0),              # afuera, en efectivo
    ])
    curva = pd.Series(valores, index=_dias(len(valores)))
    caidas = frontera.caida_diaria(curva).to_numpy()
    cola = np.sort(caidas)[:max(1, int(round(len(caidas) * 0.05)))]
    assert len(np.unique(np.round(cola, 12))) == 1
    peor, _, _, _ = metricas.caida_maxima(curva)
    assert frontera.cdar(curva) == pytest.approx(peor)

    # Y el contraste: una curva que nunca se queda quieta si da una cola con
    # muchos valores distintos, que es lo que la CDaR promete.
    viva = _curva_al_azar(600, deriva=0.0)
    cola_viva = np.sort(frontera.caida_diaria(viva).to_numpy())[:30]
    assert len(np.unique(np.round(cola_viva, 12))) > 20
