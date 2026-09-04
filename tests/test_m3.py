"""
Pruebas del des-parpadeo y de las medidas de M3.

LA QUE MAS IMPORTA
-------------------
`test_consolidar_mira_al_futuro_y_confirmar_no`. Es la distincion entera de
esta etapa: consolidar tramos cortos exige saber que fueron cortos, y eso no
se sabe hasta que terminaron. La prueba lo demuestra cortando la serie: la
compuerta consolidada CAMBIA hacia atras cuando llegan datos nuevos, y la
confirmada no.

Si esa prueba se rompiera, `consolidar` habria dejado de ser un techo y
alguien podria confundirlo con una estrategia.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metrics import frontera, metricas  # noqa: E402
from risk import compuerta as cp  # noqa: E402


def _dias(n: int, desde: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.date_range(desde, periods=n, freq="D", tz="UTC")


def _puerta(patron: str) -> pd.Series:
    valores = [int(c) for c in patron]
    return pd.Series(valores, index=_dias(len(valores)))


# --- Consolidacion ----------------------------------------------------------

def test_consolidar_se_come_los_tramos_cortos():
    # Dos dias adentro en medio de un mar de ceros: con N=5 desaparecen.
    g = _puerta("0000110000000000")
    assert list(cp.consolidar(g, 5)) == [0] * 16


def test_consolidar_no_toca_el_primero_ni_el_ultimo_tramo():
    """
    Los dos estan cortados por la ventana y no por el mercado: no se sabe
    cuanto duraron de verdad. Fusionarlos seria inventar, y la primera version
    de `consolidar` lo hacia con el primero -- esta prueba lo agarro.
    """
    # Primer tramo de 2 dias y ultimo de 2 dias, los dos mas cortos que N=5.
    g = _puerta("0011111111110011")
    salida = cp.consolidar(g, 5)
    assert list(salida[:2]) == [0, 0]
    assert list(salida[-2:]) == [1, 1]


def test_consolidar_no_toca_los_tramos_largos():
    g = _puerta("0000111111110000")
    pd.testing.assert_series_equal(cp.consolidar(g, 5), g, check_dtype=False)


def test_consolidar_repite_hasta_que_no_queden_cortos():
    """
    Fusionar dos tramos puede dejar al vecino todavia corto. Una sola pasada
    lo dejaria pasar, y el des-parpadeo quedaria a medias.
    """
    g = _puerta("111101011110000000000000")
    salida = cp.consolidar(g, 4)
    t = cp.tramos(salida)
    # El primero y el ultimo quedan como estan a proposito: los corta la
    # ventana, no el mercado.
    assert (t.iloc[1:-1]["dias"] >= 4).all()


def test_consolidar_con_n_de_uno_no_hace_nada():
    g = _puerta("0101101000111")
    pd.testing.assert_series_equal(cp.consolidar(g, 1), g)


# --- Confirmacion -----------------------------------------------------------

def test_confirmar_entra_tarde_y_sale_tarde():
    """
    Es el precio de no mirar adelante, y tiene que pagarse de los dos lados:
    si solo entrara tarde seria una compuerta mejor, no una mas honesta.
    """
    g = _puerta("00001111111111000000")
    salida = cp.con_confirmacion(g, 3)
    # Entra dos dias despues de que la señal se enciende...
    assert salida.iloc[4] == 0 and salida.iloc[6] == 1
    # ...y sigue adentro dos dias despues de que se apaga.
    assert salida.iloc[14] == 1 and salida.iloc[16] == 0


def test_confirmar_ignora_un_parpadeo_mas_corto_que_la_confirmacion():
    g = _puerta("111111101111111")
    salida = cp.con_confirmacion(g, 3)
    assert (salida.iloc[3:] == 1).all()


def test_confirmar_arranca_afuera():
    """Sin N dias de señal no hay confirmacion, y sin confirmacion no se opera."""
    g = _puerta("111111111")
    assert cp.con_confirmacion(g, 4).iloc[0] == 0


def test_consolidar_mira_al_futuro_y_confirmar_no():
    """
    LA PRUEBA QUE SOSTIENE LA DISTINCION.

    Se corta la serie antes de que un tramo termine y se compara con la serie
    entera. `consolidar` cambia hacia atras cuando llegan datos nuevos --o sea
    que usa el futuro-- y `con_confirmacion` no.

    Es la misma prueba de no-anticipacion que tienen los 13 indicadores, y
    esta por la misma razon: un calculo que cambia segun cuantas velas
    posteriores existan estaba espiando.
    """
    # Un tramo de 3 dias adentro que arranca en la posicion 10.
    g = _puerta("0000000000111000000000")
    corte = 13                      # justo cuando el tramo todavia no termino

    entera_c = cp.consolidar(g, 5)
    parcial_c = cp.consolidar(g.iloc[:corte], 5)
    assert not entera_c.iloc[:corte].equals(parcial_c), (
        "consolidar dio lo mismo con y sin el futuro: dejo de ser un techo "
        "y alguien lo va a confundir con una estrategia.")

    entera_f = cp.con_confirmacion(g, 3)
    parcial_f = cp.con_confirmacion(g.iloc[:corte], 3)
    pd.testing.assert_series_equal(entera_f.iloc[:corte], parcial_f)


# --- Episodios de caida -----------------------------------------------------

def _curva(valores) -> pd.Series:
    return pd.Series(np.asarray(valores, dtype=float),
                     index=_dias(len(valores)))


def test_el_peor_episodio_es_la_caida_maxima():
    rng = np.random.default_rng(4)
    curva = _curva(1000 * np.exp(np.cumsum(rng.normal(0.0, 0.03, 800))))
    peor, _, _, _ = metricas.caida_maxima(curva)
    assert frontera.episodios_de_caida(curva, 1)[0] == pytest.approx(peor)


def test_los_episodios_no_se_superponen():
    """
    Si se superpusieran, el mismo derrumbe partido en dos contaria dos veces y
    la media de los 3 peores seria una sola caida disfrazada de tres.
    """
    # Tres derrumbes separados por recuperaciones completas.
    tramo = list(np.linspace(100, 200, 60)) + list(np.linspace(200, 120, 30))
    curva = _curva(tramo + [x * 2 for x in tramo] + [x * 4 for x in tramo])
    episodios = frontera.episodios_de_caida(curva, 3)
    assert len(episodios) == 3
    # Los tres derrumbes son iguales en porcentaje, asi que los tres valores
    # tienen que parecerse. Si se superpusieran, el tercero seria mucho menor.
    assert min(episodios) == pytest.approx(max(episodios), rel=0.05)


def test_los_episodios_vienen_del_peor_al_menos_malo():
    rng = np.random.default_rng(11)
    curva = _curva(1000 * np.exp(np.cumsum(rng.normal(0.0, 0.03, 900))))
    episodios = frontera.episodios_de_caida(curva, 3)
    assert episodios == sorted(episodios)


def test_una_curva_que_solo_sube_no_tiene_episodios():
    assert frontera.episodios_de_caida(_curva(np.linspace(100, 500, 200))) == []
    assert frontera.caida_por_episodios(_curva(np.linspace(100, 500, 200))) == 0.0


def test_la_media_de_episodios_es_menos_extrema_que_la_caida_maxima():
    """
    Promediar tres episodios no puede dar peor que el peor de los tres, que es
    la caida maxima. Es el invariante que hace que la medida tenga sentido.
    """
    rng = np.random.default_rng(21)
    curva = _curva(1000 * np.exp(np.cumsum(rng.normal(0.0, 0.03, 900))))
    peor, _, _, _ = metricas.caida_maxima(curva)
    assert peor <= frontera.caida_por_episodios(curva) <= 0.0


def test_la_fraccion_por_episodios_contra_si_mismo_da_uno():
    rng = np.random.default_rng(31)
    curva = _curva(1000 * np.exp(np.cumsum(rng.normal(0.0, 0.03, 900))))
    assert frontera.fraccion_por_episodios(curva, curva) == pytest.approx(1.0)


def test_pedir_cero_episodios_falla_fuerte():
    with pytest.raises(ValueError, match="al menos 1"):
        frontera.episodios_de_caida(_curva(np.linspace(100, 50, 100)), 0)


# --- Exceso detectable ------------------------------------------------------

def test_el_exceso_detectable_es_el_semiancho_anualizado():
    # Un intervalo simetrico de +-0,01 al mes: 12% en log, 12,75% simple.
    assert frontera.exceso_detectable(-0.01, 0.01) == pytest.approx(
        np.expm1(0.12))


def test_un_intervalo_de_ancho_cero_no_exige_nada():
    assert frontera.exceso_detectable(0.0, 0.0) == pytest.approx(0.0)


def test_un_intervalo_mas_ancho_exige_mas():
    angosto = frontera.exceso_detectable(-0.01, 0.01)
    ancho = frontera.exceso_detectable(-0.05, 0.05)
    assert ancho > angosto


def test_un_intervalo_indefinido_devuelve_nan():
    assert np.isnan(frontera.exceso_detectable(float("nan"), 0.02))


# --- Las dos condiciones de una compuerta ----------------------------------

def test_las_dos_condiciones_tiran_de_los_mismos_dias():
    """
    El hallazgo de fondo de M3, comprobado sobre una serie construida a mano.

    Se arma un mercado que sube fuerte, se derrumba en el medio y se recupera.
    Sacar el derrumbe mejora la caida y CUESTA retorno; dejarlo adentro hace
    lo contrario. Ninguna compuerta consigue las dos cosas sobre los mismos
    dias, y eso no es un accidente de estos datos.
    """
    subida = np.full(200, 0.004)
    derrumbe = np.full(60, -0.012)
    recuperacion = np.full(200, 0.005)
    log = np.concatenate([subida, derrumbe, recuperacion])
    indice = _dias(len(log))

    def evaluar(dentro):
        curva = pd.Series(1000 * np.exp(np.cumsum(np.where(dentro, log, 0.0))),
                          index=indice)
        caida, _, _, _ = metricas.caida_maxima(curva)
        return float(log[~dentro].sum()), caida

    afuera_del_derrumbe = np.ones(len(log), dtype=bool)
    afuera_del_derrumbe[200:260] = False
    siempre_dentro = np.ones(len(log), dtype=bool)

    fuera_a, caida_a = evaluar(afuera_del_derrumbe)
    fuera_b, caida_b = evaluar(siempre_dentro)

    # Salirse: la caida mejora y el retorno dejado afuera se vuelve negativo.
    assert caida_a > caida_b          # menos profunda
    assert fuera_a < 0 < fuera_b + 1e-12
    # Quedarse: no deja nada afuera pero come la caida entera.
    assert fuera_b == pytest.approx(0.0)
