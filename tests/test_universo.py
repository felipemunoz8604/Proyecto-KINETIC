"""
Pruebas de la reconstruccion del universo.

La mas importante de todas es `test_un_simbolo_que_muere_despues_entra_igual`.
Ese comportamiento es la razon entera por la que existe este modulo, y es el
que la Fase 1 no tenia: alla el universo se armo con la lista de hoy, o sea
preguntandole al presente quien existia en 2020 -- y el presente contesta con
los sobrevivientes, que ganaron por eso mismo.

Las otras giran alrededor de la misma idea: **en la fecha t no se puede mirar
nada posterior a t.** La prueba que lo verifica de frente es
`test_agregar_datos_del_futuro_no_cambia_ninguna_decision`, que corre el mismo
universo sobre dos paneles identicos salvo por lo que viene despues.
"""

from __future__ import annotations

import pandas as pd
import pytest

from core import universo as uni


def panel_de(datos: dict[str, dict], volumenes: dict[str, dict] | None = None
             ) -> uni.Panel:
    """
    Arma un panel a mano. `datos` es {simbolo: {fecha: cierre}}.

    Si no se dan volumenes, se usa uno constante distinto por simbolo, en el
    orden en que aparecen: el primero es el mas liquido. Asi el ranking es
    predecible sin tener que escribirlo en cada prueba.
    """
    cierres = pd.DataFrame(
        {s: pd.Series(v) for s, v in datos.items()}
    ).sort_index()
    cierres.index = pd.DatetimeIndex(cierres.index).tz_localize("UTC")

    if volumenes is None:
        vol = pd.DataFrame(
            {s: cierres[s].notna() * (len(datos) - i) * 1000.0
             for i, s in enumerate(datos)},
            index=cierres.index,
        ).replace(0.0, float("nan"))
    else:
        vol = pd.DataFrame({s: pd.Series(v) for s, v in volumenes.items()})
        vol.index = pd.DatetimeIndex(vol.index).tz_localize("UTC")
        vol = vol.reindex(cierres.index)

    return uni.Panel(cierres, vol)


def dias(desde: str, n: int) -> list[str]:
    return [str(d.date()) for d in pd.date_range(desde, periods=n, freq="D")]


def serie(desde: str, n: int, valor: float = 100.0) -> dict:
    return {d: valor for d in dias(desde, n)}


# --- LA PRUEBA QUE JUSTIFICA EL MODULO ------------------------------------

def test_un_simbolo_que_muere_despues_entra_igual():
    """
    El comportamiento por el que existe este modulo entero.

    MUERTOUSDT opera desde 2019 y se deslista en julio de 2020. En el universo
    de marzo de 2020 tiene que estar: en marzo de 2020 estaba vivo y era
    liquido. Que despues se muera es informacion del futuro.

    Si esta prueba se pone roja, volvimos al universo de la Fase 1.
    """
    panel = panel_de({
        "MUERTOUSDT": serie("2019-01-01", 550),   # hasta ~2020-07
        "VIVOUSDT": serie("2019-01-01", 900),     # sigue despues
    })
    seleccion = uni.universo_en(panel, pd.Timestamp("2020-03-01", tz="UTC"))
    assert "MUERTOUSDT" in seleccion


def test_el_que_ya_murio_no_entra():
    """La otra mitad: en 2021 ese mismo simbolo ya no puede estar."""
    panel = panel_de({
        "MUERTOUSDT": serie("2019-01-01", 550),
        "VIVOUSDT": serie("2019-01-01", 900),
    })
    seleccion = uni.universo_en(panel, pd.Timestamp("2021-03-01", tz="UTC"))
    assert "MUERTOUSDT" not in seleccion
    assert "VIVOUSDT" in seleccion


# --- No mirar al futuro ---------------------------------------------------

def test_agregar_datos_del_futuro_no_cambia_ninguna_decision():
    """
    La propiedad de no-anticipacion, verificada de frente.

    Dos paneles identicos hasta el 1-jun-2020 y distintos despues: en uno,
    CHICOUSDT explota en volumen. El universo del 1-jun no puede enterarse.
    """
    fechas = dias("2019-01-01", 700)
    base_cierres = {
        "GRANDEUSDT": {d: 100.0 for d in fechas},
        "CHICOUSDT": {d: 100.0 for d in fechas},
    }
    corte = pd.Timestamp("2020-06-01", tz="UTC")

    tranquilo = {
        "GRANDEUSDT": {d: 9_000.0 for d in fechas},
        "CHICOUSDT": {d: 1_000.0 for d in fechas},
    }
    explota = {
        "GRANDEUSDT": {d: 9_000.0 for d in fechas},
        "CHICOUSDT": {d: (1_000.0 if pd.Timestamp(d, tz="UTC") < corte
                          else 9_999_999.0) for d in fechas},
    }

    a = uni.universo_en(panel_de(base_cierres, tranquilo), corte)
    b = uni.universo_en(panel_de(base_cierres, explota), corte)
    assert a == b == ["GRANDEUSDT", "CHICOUSDT"]


def test_el_volumen_del_dia_mismo_no_cuenta():
    """
    `_hasta` corta ESTRICTAMENTE antes de la fecha.

    Un dia de diferencia parece nada y no lo es: el 1 de mes es justo el dia
    del rebalanceo, y contarlo seria decidir con el volumen que todavia no
    ocurrio cuando hay que poner la orden.
    """
    fechas = dias("2019-01-01", 400)
    corte = pd.Timestamp("2020-02-04", tz="UTC")
    volumenes = {
        "AUSDT": {d: (1.0 if pd.Timestamp(d, tz="UTC") < corte else 1e12)
                  for d in fechas},
        "BUSDT": {d: 500.0 for d in fechas},
    }
    cierres = {"AUSDT": {d: 1.0 for d in fechas},
               "BUSDT": {d: 1.0 for d in fechas}}
    assert uni.universo_en(panel_de(cierres, volumenes), corte) == ["BUSDT", "AUSDT"]


# --- Antigüedad -----------------------------------------------------------

def test_un_recien_listado_no_entra():
    """Los primeros meses tras el listado son libro vacio, no mercado."""
    panel = panel_de({
        "VIEJOUSDT": serie("2019-01-01", 600),
        "NUEVOUSDT": serie("2020-06-01", 200),
    })
    seleccion = uni.universo_en(panel, pd.Timestamp("2020-08-01", tz="UTC"))
    assert seleccion == ["VIEJOUSDT"]


def test_entra_cuando_cumple_la_antiguedad():
    panel = panel_de({
        "VIEJOUSDT": serie("2019-01-01", 900),
        "NUEVOUSDT": serie("2020-01-01", 500),
    })
    temprano = uni.universo_en(panel, pd.Timestamp("2020-03-01", tz="UTC"))
    tarde = uni.universo_en(panel, pd.Timestamp("2020-08-01", tz="UTC"))
    assert "NUEVOUSDT" not in temprano
    assert "NUEVOUSDT" in tarde


# --- Ranking por liquidez -------------------------------------------------

def test_se_toman_los_mas_liquidos_y_en_orden():
    cierres = {f"S{i}USDT": serie("2019-01-01", 600) for i in range(5)}
    volumenes = {f"S{i}USDT": {d: (5 - i) * 1000.0 for d in dias("2019-01-01", 600)}
                 for i in range(5)}
    seleccion = uni.universo_en(panel_de(cierres, volumenes),
                                pd.Timestamp("2020-06-01", tz="UTC"), tamano=3)
    assert seleccion == ["S0USDT", "S1USDT", "S2USDT"]


def test_se_usa_la_mediana_y_no_la_media():
    """
    Un solo dia de volumen anormal no puede meter una moneda iliquida.

    TRANQUILOUSDT mueve 1.000 todos los dias. PUMPUSDT mueve 1 todos los dias
    salvo uno, en que mueve un millon. Por media, PUMPUSDT gana; por mediana,
    pierde -- y la mediana tiene razon, porque esa moneda no se puede vender.
    """
    fechas = dias("2019-01-01", 600)
    cierres = {"TRANQUILOUSDT": {d: 1.0 for d in fechas},
               "PUMPUSDT": {d: 1.0 for d in fechas}}
    volumenes = {
        "TRANQUILOUSDT": {d: 1_000.0 for d in fechas},
        "PUMPUSDT": {d: (1_000_000.0 if i == 590 else 1.0)
                     for i, d in enumerate(fechas)},
    }
    seleccion = uni.universo_en(panel_de(cierres, volumenes),
                                pd.Timestamp("2020-08-23", tz="UTC"), tamano=1)
    assert seleccion == ["TRANQUILOUSDT"]


def test_un_simbolo_sin_volumen_no_entra():
    fechas = dias("2019-01-01", 600)
    cierres = {"AUSDT": {d: 1.0 for d in fechas}, "MUDOUSDT": {d: 1.0 for d in fechas}}
    volumenes = {"AUSDT": {d: 100.0 for d in fechas},
                 "MUDOUSDT": {d: 0.0 for d in fechas}}
    seleccion = uni.universo_en(panel_de(cierres, volumenes),
                                pd.Timestamp("2020-06-01", tz="UTC"))
    assert seleccion == ["AUSDT"]


# --- Bordes ---------------------------------------------------------------

def test_antes_del_primer_dato_el_universo_esta_vacio():
    panel = panel_de({"AUSDT": serie("2020-01-01", 400)})
    assert uni.universo_en(panel, pd.Timestamp("2019-01-01", tz="UTC")) == []


def test_si_nadie_cumple_la_antiguedad_el_universo_esta_vacio():
    panel = panel_de({"AUSDT": serie("2020-01-01", 400)})
    assert uni.universo_en(panel, pd.Timestamp("2020-02-01", tz="UTC")) == []


# --- Fechas de rebalanceo -------------------------------------------------

def test_las_fechas_son_el_primer_dia_de_cada_mes():
    panel = panel_de({"AUSDT": serie("2019-01-15", 200)})
    fechas = uni.fechas_de_rebalanceo(panel)
    assert all(f.day == 1 for f in fechas)
    assert all(str(f.tz) == "UTC" for f in fechas)
    assert fechas[0] == pd.Timestamp("2019-02-01", tz="UTC")


# --- Rotacion y deslistados -----------------------------------------------

def test_la_rotacion_mide_lo_que_entra_nuevo():
    seleccion = {
        pd.Timestamp("2020-01-01", tz="UTC"): ["A", "B", "C", "D"],
        pd.Timestamp("2020-02-01", tz="UTC"): ["A", "B", "C", "E"],
        pd.Timestamp("2020-03-01", tz="UTC"): ["A", "B", "C", "E"],
    }
    r = uni.rotacion(seleccion)
    assert r.iloc[0] == pytest.approx(0.25)   # entro E
    assert r.iloc[1] == pytest.approx(0.0)    # no cambio nada


def test_se_detecta_quien_murio_estando_en_el_universo():
    """La cuenta que la Fase 1 no pudo hacer: cuantos muertos se atravesaron."""
    panel = panel_de({
        "MUERTOUSDT": serie("2019-01-01", 550),
        "VIVOUSDT": serie("2019-01-01", 900),
    })
    seleccion = {pd.Timestamp("2020-03-01", tz="UTC"): ["MUERTOUSDT", "VIVOUSDT"]}
    muertos = uni.deslistados_en(panel, seleccion)
    assert "MUERTOUSDT" in muertos
    assert "VIVOUSDT" not in muertos


def test_la_matriz_de_disponibilidad_marca_los_meses_con_datos():
    panel = panel_de({
        "AUSDT": serie("2019-01-01", 60),
        "BUSDT": serie("2019-03-01", 60),
    })
    m = uni.matriz_disponibilidad(panel)
    assert m.loc["2019-01-01", "AUSDT"]
    assert not m.loc["2019-01-01", "BUSDT"]
    assert m.loc["2019-03-01", "BUSDT"]


# --- Renombramientos ------------------------------------------------------

def test_un_renombramiento_no_cuenta_como_muerte():
    """
    Cinco de los 22 "muertos" reales resultaron ser cambios de nombre.

    MATIC->POL, RNDR->RENDER, FTM->S, BTT->BTTC, BCHABC->BCH: el ticker viejo
    deja de operar y el nuevo arranca entre 0 y 8 dias despues, y el que tenia
    la moneda no perdio nada.

    La especificacion pide medir el impacto de los deslistados castigando con
    -20% y -50%. Aplicarle eso a un cambio de nombre no es ser conservador: es
    estar equivocado, y encima empujando el resultado hacia el lado que uno
    cree seguro.
    """
    panel = panel_de({
        "MATICUSDT": serie("2019-01-01", 550),
        "VIVOUSDT": serie("2019-01-01", 900),
    })
    seleccion = {pd.Timestamp("2020-03-01", tz="UTC"): ["MATICUSDT", "VIVOUSDT"]}
    assert "MATICUSDT" not in uni.deslistados_en(panel, seleccion)
    # Y se puede ver igual cuando se quiere revisar si la lista esta al dia.
    todos = uni.deslistados_en(panel, seleccion, excluir_renombrados=False)
    assert "MATICUSDT" in todos


def test_una_muerte_de_verdad_si_cuenta():
    panel = panel_de({
        "MUERTOUSDT": serie("2019-01-01", 550),
        "VIVOUSDT": serie("2019-01-01", 900),
    })
    seleccion = {pd.Timestamp("2020-03-01", tz="UTC"): ["MUERTOUSDT", "VIVOUSDT"]}
    assert "MUERTOUSDT" in uni.deslistados_en(panel, seleccion)


def test_el_detector_propone_candidatos_pero_no_decide():
    """
    Propone; una persona confirma. Una heuristica que decidiera sola
    convertiria cada coincidencia temporal en un renombramiento inventado, y
    en cripto nacen monedas todas las semanas.
    """
    panel = panel_de({
        "VIEJOUSDT": serie("2019-01-01", 400),      # muere ~2020-02-04
        "NUEVOUSDT": serie("2020-02-06", 500),      # nace 2 dias despues
        "APARTEUSDT": serie("2019-01-01", 900),
    })
    candidatos = uni.detectar_renombramientos_candidatos(panel)
    pares = {(v, n) for v, n, _ in candidatos}
    assert ("VIEJOUSDT", "NUEVOUSDT") in pares
    # Y no se agrego solo a la lista: eso lo hace una persona.
    assert "VIEJOUSDT" not in uni.RENOMBRAMIENTOS


def test_la_rotacion_anual_no_es_la_mensual_por_doce():
    """
    Las dos miden cosas distintas y no son comparables.

    La mensual sumada doce veces cuenta varias veces al simbolo que entra y
    sale; la anual mira solo las dos puntas. Confundirlas seria comparar
    nuestro numero con el 37% anual de la literatura sin que signifiquen lo
    mismo.
    """
    seleccion = {}
    for i, mes in enumerate(pd.date_range("2020-01-01", periods=13, freq="MS",
                                          tz="UTC")):
        # Uno entra y sale alternadamente: mucha rotacion mensual, cero anual.
        seleccion[mes] = ["A", "B"] if i % 2 == 0 else ["A", "C"]

    mensual = uni.rotacion(seleccion)
    anual = uni.rotacion_anual(seleccion)
    assert mensual.mean() > 0.4          # se mueve todos los meses
    assert anual.iloc[0] == pytest.approx(0.0)   # y al año esta igual que al principio
