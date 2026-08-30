"""
Pruebas del modelo de costos v2 y de los filtros de intercambio.

Las que importan de verdad son cuatro, y las tres primeras cubren errores que
NO se ven en el resultado de un backtest:

1. `test_reproduce_la_tabla_de_la_especificacion` -- los cinco escenarios de
   peaje salen exactos. Si alguien toca un tramo de slippage, esto se cae.
2. `test_el_signo_de_la_financiacion` -- invertir ese signo convierte un costo
   en un ingreso y el backtest se ve mejor, no peor.
3. `test_una_tasa_faltante_levanta` -- suponer cero cuando falta un dato de
   financiacion es la forma mas facil de validar un perpetuo invalido.
4. `test_el_redondeo_no_pierde_un_paso_por_un_float` -- el clasico
   floor(0,3/0,1) = 2.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from execution import costos as c  # noqa: E402
from execution import filtros as f  # noqa: E402


# --- Comisiones y slippage -----------------------------------------------

def test_reproduce_la_tabla_de_la_especificacion():
    """
    Los cinco escenarios de peaje total, ida y vuelta, de la seccion 2.3.
    El rango 6 cae en el tramo del medio (0,05% por lado), que es el supuesto
    con el que estan calculados los numeros de la especificacion.
    """
    esperado = {
        (c.Venue.SPOT, c.TipoOrden.TAKER, False): 0.30,
        (c.Venue.SPOT, c.TipoOrden.TAKER, True): 0.25,
        (c.Venue.SPOT, c.TipoOrden.MAKER, True): 0.17,
        (c.Venue.PERPETUO_USDT_M, c.TipoOrden.TAKER, False): 0.20,
        (c.Venue.PERPETUO_USDT_M, c.TipoOrden.MAKER, False): 0.06,
    }
    for (venue, tipo, bnb), peaje in esperado.items():
        modelo = c.ModeloDeCostos(venue=venue, tipo_orden=tipo, con_bnb=bnb)
        assert modelo.peaje_ida_y_vuelta_pct(6) == pytest.approx(peaje, abs=1e-9), (
            f"{venue.value}/{tipo.value}/bnb={bnb}"
        )


@pytest.mark.parametrize("rango,esperado", [
    (1, 0.03), (5, 0.03),
    (6, 0.05), (12, 0.05),
    (13, 0.10), (20, 0.10),
    (21, 0.10),   # fuera del universo: paga el peor tramo, no el del puesto 20
])
def test_los_tramos_de_slippage_cortan_donde_dicen(rango, esperado):
    assert c.slippage_pct(rango) == esperado


def test_el_rango_es_uno_based():
    with pytest.raises(ValueError):
        c.slippage_pct(0)


def test_maker_no_paga_el_spread_pero_taker_si():
    assert c.slippage_pct(20, c.TipoOrden.MAKER) < c.slippage_pct(1)


def test_en_spot_maker_y_taker_cobran_la_misma_comision():
    """
    A nivel VIP 0 es asi. Si esto se cae es porque alguien creyo que la ventaja
    de maker estaba en la comision; esta en el spread.
    """
    esquema = c.COMISIONES[c.Venue.SPOT]
    assert esquema.maker_pct == esquema.taker_pct


def test_el_descuento_por_bnb_viene_apagado():
    """No esta verificado contra la cuenta real. Hasta entonces, el caro."""
    assert c.ModeloDeCostos().con_bnb is False
    assert c.ModeloDeCostos().comision_pct == 0.10


def test_comprar_es_mas_caro_y_vender_mas_barato():
    modelo = c.ModeloDeCostos()
    assert modelo.precio_efectivo(100.0, 1, comprando=True) > 100.0
    assert modelo.precio_efectivo(100.0, 1, comprando=False) < 100.0


def test_el_costo_de_un_lado_no_acepta_nocional_negativo():
    with pytest.raises(ValueError):
        c.ModeloDeCostos().costo_de_lado(-100.0, 1)


def test_el_costo_escala_con_el_nocional():
    modelo = c.ModeloDeCostos()
    assert modelo.costo_de_lado(1_000.0, 1) == pytest.approx(
        10 * modelo.costo_de_lado(100.0, 1))


# --- Financiacion ---------------------------------------------------------

def _t(texto: str) -> pd.Timestamp:
    return pd.Timestamp(texto, tz="UTC")


def test_solo_cuenta_los_cortes_que_la_posicion_atraviesa():
    cortes = c.momentos_de_financiacion(_t("2024-01-01 07:00"),
                                        _t("2024-01-01 09:00"))
    assert list(cortes) == [_t("2024-01-01 08:00")]


def test_una_posicion_entre_dos_cortes_no_paga_nada():
    cortes = c.momentos_de_financiacion(_t("2024-01-01 09:00"),
                                        _t("2024-01-01 15:00"))
    assert len(cortes) == 0


def test_abrir_en_el_corte_no_paga_y_cerrar_en_el_corte_si():
    """
    La convencion es `desde < corte <= hasta`. Cerrar justo en el corte paga:
    es el lado pesimista de una ambiguedad real.
    """
    abre = c.momentos_de_financiacion(_t("2024-01-01 08:00"),
                                      _t("2024-01-01 15:00"))
    cierra = c.momentos_de_financiacion(_t("2024-01-01 09:00"),
                                        _t("2024-01-01 16:00"))
    assert len(abre) == 0
    assert list(cierra) == [_t("2024-01-01 16:00")]


def test_un_mes_entero_son_noventa_y_pico_de_cortes():
    """
    El numero de la especificacion: ~90 cobros en un mes. Si esto da 30, la
    financiacion se esta aplicando diaria y el costo esta dividido por tres.
    """
    cortes = c.momentos_de_financiacion(_t("2024-01-01 00:00"),
                                        _t("2024-01-31 00:00"))
    assert len(cortes) == 90


def test_el_signo_de_la_financiacion():
    """
    Tasa positiva => los largos le pagan a los cortos.

    Invertir esto no rompe nada visible: el backtest simplemente rinde mas.
    """
    assert c.flujo_de_financiacion(1_000.0, 0.0001) < 0    # largo paga
    assert c.flujo_de_financiacion(-1_000.0, 0.0001) > 0   # corto cobra
    assert c.flujo_de_financiacion(1_000.0, -0.0001) > 0   # tasa negativa: al reves


def test_la_financiacion_acumulada_suma_todos_los_cortes():
    cortes = c.momentos_de_financiacion(_t("2024-01-01 00:00"),
                                        _t("2024-01-02 00:00"))
    tasas = pd.Series(0.0001, index=cortes)
    total = c.financiacion_acumulada(1_000.0, tasas,
                                     _t("2024-01-01 00:00"),
                                     _t("2024-01-02 00:00"))
    assert total == pytest.approx(-3 * 1_000.0 * 0.0001)


def test_una_tasa_faltante_levanta():
    """
    Y NO devuelve cero. Un cero silencioso convierte un backtest de perpetuos
    invalido en uno que se ve impecable.
    """
    cortes = c.momentos_de_financiacion(_t("2024-01-01 00:00"),
                                        _t("2024-01-02 00:00"))
    tasas = pd.Series(0.0001, index=cortes[:-1])
    with pytest.raises(c.FinanciacionFaltante):
        c.financiacion_acumulada(1_000.0, tasas,
                                 _t("2024-01-01 00:00"),
                                 _t("2024-01-02 00:00"))


def test_sin_cortes_no_hace_falta_ninguna_tasa():
    vacio = pd.Series(dtype="float64")
    assert c.financiacion_acumulada(1_000.0, vacio,
                                    _t("2024-01-01 09:00"),
                                    _t("2024-01-01 15:00")) == 0.0


def test_no_se_puede_cerrar_antes_de_abrir():
    with pytest.raises(ValueError):
        c.momentos_de_financiacion(_t("2024-01-02"), _t("2024-01-01"))


# --- Filtros de intercambio -----------------------------------------------

def test_el_redondeo_no_pierde_un_paso_por_un_float():
    """
    El clasico: en float, 0,3 / 0,1 vale 2,9999999999999996, y un floor ingenuo
    devuelve 0,2 en vez de 0,3. Perder un paso entero por el ultimo bit.
    """
    filtro = f.FiltroSimbolo(paso_cantidad=0.1)
    assert filtro.ajustar_cantidad(0.3) == pytest.approx(0.3)
    assert filtro.ajustar_cantidad(0.7) == pytest.approx(0.7)
    assert filtro.ajustar_cantidad(2.9999999999999996) == pytest.approx(3.0)


def test_pero_lo_que_de_verdad_esta_abajo_se_redondea_para_abajo():
    """La tolerancia del test anterior no puede tragarse un paso legitimo."""
    filtro = f.FiltroSimbolo(paso_cantidad=0.1)
    assert filtro.ajustar_cantidad(2.95) == pytest.approx(2.9)
    assert filtro.ajustar_cantidad(0.09) == pytest.approx(0.0)


def test_el_redondeo_nunca_da_mas_de_lo_pedido():
    filtro = f.FiltroSimbolo(paso_cantidad=0.001)
    for cantidad in (0.0347291, 1.9999, 123.456789, 0.001):
        assert filtro.ajustar_cantidad(cantidad) <= cantidad + 1e-12


def test_sin_paso_conocido_no_se_redondea():
    assert f.FiltroSimbolo.generico().ajustar_cantidad(0.0347291) == 0.0347291
    assert f.FiltroSimbolo.generico().es_real is False


def test_una_orden_chica_no_es_ejecutable():
    """
    3 USDT contra un minimo de 5. No es un error: es un peso que la cartera no
    puede armar, y tiene que enterarse.
    """
    orden = f.ajustar_orden(3.0, 100.0, f.FiltroSimbolo.generico())
    assert not orden
    assert orden.cantidad == 0.0
    assert "minimo" in orden.motivo


def test_una_orden_normal_de_la_cartera_pasa():
    """100 USDT sobre BTC: el caso comun, y no puede fallar."""
    filtro = f.FiltroSimbolo(paso_cantidad=0.00001, cantidad_minima=0.00001,
                             nocional_minimo=5.0)
    orden = f.ajustar_orden(100.0, 60_000.0, filtro)
    assert orden
    assert orden.nocional <= 100.0
    assert orden.nocional == pytest.approx(orden.cantidad * 60_000.0)


def test_el_redondeo_puede_tirar_una_orden_bajo_el_minimo():
    """
    El caso que muerde de verdad: la orden pedida supera el minimo, pero
    despues de redondear al paso ya no. Si esto no estuviera, el backtest
    ejecutaria una orden que Binance rechaza.
    """
    filtro = f.FiltroSimbolo(paso_cantidad=1.0, nocional_minimo=5.0)
    orden = f.ajustar_orden(5.5, 3.0, filtro)   # 1,83 unidades -> 1 -> 3 USDT
    assert not orden
    assert "nocional" in orden.motivo


def test_precio_invalido_levanta():
    with pytest.raises(ValueError):
        f.ajustar_orden(100.0, 0.0, f.FiltroSimbolo.generico())


# --- Tabla de filtros -----------------------------------------------------

_INFO = {
    "symbols": [
        {"symbol": "BTCUSDT", "status": "TRADING", "filters": [
            {"filterType": "LOT_SIZE", "stepSize": "0.00001", "minQty": "0.00001"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
        ]},
        {"symbol": "LUNAUSDT", "status": "BREAK", "filters": [
            {"filterType": "LOT_SIZE", "stepSize": "0.1", "minQty": "0.1"},
            {"filterType": "MIN_NOTIONAL", "minNotional": "10.0"},
        ]},
    ]
}


def test_la_tabla_no_filtra_por_status():
    """
    Filtrar por `status == "TRADING"` fue exactamente como entro el sesgo de
    supervivencia en la Fase 1. No se repite ni aca, donde parece inofensivo.
    """
    tabla = f.desde_exchange_info(_INFO)
    assert "LUNAUSDT" in tabla


def test_acepta_las_dos_formas_del_filtro_de_nocional():
    tabla = f.desde_exchange_info(_INFO)
    assert tabla.de("BTCUSDT").nocional_minimo == 5.0     # NOTIONAL
    assert tabla.de("LUNAUSDT").nocional_minimo == 10.0   # MIN_NOTIONAL


def test_un_simbolo_desconocido_cae_al_generico():
    tabla = f.desde_exchange_info(_INFO)
    assert tabla.de("NOEXISTEUSDT").es_real is False


def test_la_cobertura_dice_sobre_que_parte_el_filtro_es_real():
    tabla = f.desde_exchange_info(_INFO)
    reales, pedidos = tabla.cobertura(["BTCUSDT", "LUNAUSDT", "FANTASMAUSDT"])
    assert (reales, pedidos) == (2, 3)


def test_la_tabla_sobrevive_una_vuelta_por_json(tmp_path):
    original = f.desde_exchange_info(_INFO)
    ruta = original.a_json(tmp_path / "filtros.json")
    vuelta = f.TablaDeFiltros.desde_json(ruta)
    assert vuelta.de("BTCUSDT") == original.de("BTCUSDT")
    assert vuelta.de("LUNAUSDT") == original.de("LUNAUSDT")
