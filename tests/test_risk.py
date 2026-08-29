"""
Pruebas de la capa de riesgo.

Es la capa que tiene que ser paranoica: un error en la estrategia hace
perder oportunidades, un error aca hace perder dinero. Cada prueba dice en
su nombre que desastre esta previniendo.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from risk import portfolio_guard, position_sizing, risk_limits, stop_manager  # noqa: E402

UTC = timezone.utc
REGLAS_BTC = position_sizing.ReglasSimbolo(
    paso_cantidad=0.00001, cantidad_minima=0.00001, compra_minima=5.0
)


# ===========================================================================
# Tamano de posicion
# ===========================================================================

def test_el_caso_normal_arriesga_lo_configurado():
    """500 USDT, 1% de riesgo, stop 3% abajo: se pierden ~5 USDT si pega."""
    r = position_sizing.calcular(
        capital=500.0, riesgo_pct=1.0,
        precio_entrada=100_000.0, precio_stop=97_000.0,
        reglas=REGLAS_BTC, comision_pct=0.1,
    )
    assert r.aprobado, r.motivo
    assert r.riesgo_real_pct == pytest.approx(1.0, abs=0.01)
    # La compra tiene que estar muy por encima del minimo de 5 USDT.
    assert 100 < r.valor_compra < 200


def test_el_riesgo_real_nunca_supera_al_configurado():
    """
    Barrido de distancias de stop. Si alguna combinacion se pasa aunque sea
    un poco del riesgo autorizado, es un error grave y silencioso.
    """
    for stop_pct in (0.5, 1, 2, 3, 5, 8, 12, 20, 35, 50):
        entrada = 50_000.0
        stop = entrada * (1 - stop_pct / 100)
        r = position_sizing.calcular(
            capital=500.0, riesgo_pct=1.0,
            precio_entrada=entrada, precio_stop=stop,
            reglas=REGLAS_BTC,
        )
        if r.aprobado:
            assert r.riesgo_real_pct <= 1.0 + 1e-9, (
                f"con stop a {stop_pct}% el riesgo real fue {r.riesgo_real_pct}%"
            )


def test_las_comisiones_entran_en_la_cuenta():
    """
    Ignorar el 0,1% de ida y el 0,1% de vuelta hace que la perdida real
    supere siempre el 1% que creiamos arriesgar.
    """
    argumentos = dict(
        capital=500.0, riesgo_pct=1.0,
        precio_entrada=100_000.0, precio_stop=97_000.0, reglas=REGLAS_BTC,
    )
    con = position_sizing.calcular(comision_pct=0.1, **argumentos)
    sin = position_sizing.calcular(comision_pct=0.0, **argumentos)

    assert con.cantidad < sin.cantidad, "las comisiones deberian achicar la compra"


def test_en_spot_no_se_puede_comprar_por_mas_del_capital():
    """
    Sin apalancamiento no hay forma de comprar 1000 USDT teniendo 500. Con
    un stop muy pegado la formula lo pide igual, y hay que recortar.
    """
    r = position_sizing.calcular(
        capital=500.0, riesgo_pct=1.0,
        precio_entrada=100_000.0, precio_stop=99_800.0,   # stop a 0,2%
        reglas=REGLAS_BTC,
    )
    assert r.aprobado, r.motivo
    assert r.valor_compra <= 500.0 + 1e-9, "se compro por mas dinero del que hay"
    assert r.recortado_por_capital
    assert r.riesgo_real_pct < 1.0, "al recortar, el riesgo real baja"
    assert r.avisos


def test_una_compra_por_debajo_del_minimo_se_rechaza_y_no_se_agranda():
    """
    Agrandar la compra para llegar al minimo de Binance seria romper el
    limite de riesgo para poder operar. Se rechaza y punto.
    """
    r = position_sizing.calcular(
        capital=500.0, riesgo_pct=1.0,
        precio_entrada=100_000.0, precio_stop=10_000.0,   # stop 90% abajo
        reglas=position_sizing.ReglasSimbolo(compra_minima=50.0),
    )
    assert not r.aprobado
    assert "minimo" in r.motivo.lower()
    assert r.cantidad == 0.0


def test_un_stop_por_encima_de_la_entrada_se_rechaza():
    r = position_sizing.calcular(500.0, 1.0, 100.0, 105.0, REGLAS_BTC)
    assert not r.aprobado
    assert "POR DEBAJO" in r.motivo


def test_un_stop_igual_a_la_entrada_se_rechaza():
    r = position_sizing.calcular(500.0, 1.0, 100.0, 100.0, REGLAS_BTC)
    assert not r.aprobado


def test_la_cantidad_siempre_es_multiplo_del_paso():
    reglas = position_sizing.ReglasSimbolo(paso_cantidad=0.001, cantidad_minima=0.001)
    r = position_sizing.calcular(500.0, 1.0, 3_000.0, 2_900.0, reglas)
    assert r.aprobado, r.motivo
    assert round(r.cantidad / 0.001) == pytest.approx(r.cantidad / 0.001, abs=1e-9)


def test_el_redondeo_es_siempre_hacia_abajo():
    """Hacia arriba seria arriesgar mas de lo autorizado."""
    assert position_sizing._redondear_al_paso(0.123456, 0.001) == pytest.approx(0.123)
    assert position_sizing._redondear_al_paso(0.999999, 0.01) == pytest.approx(0.99)
    assert position_sizing._redondear_al_paso(5.0, 1.0) == pytest.approx(5.0)


def test_reglas_desde_binance_lee_los_filtros_reales():
    """Formato exacto que devuelve get_symbol_info de BTCUSDT."""
    info = {
        "filters": [
            {"filterType": "LOT_SIZE", "minQty": "0.00001000", "stepSize": "0.00001000"},
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
        ]
    }
    reglas = position_sizing.ReglasSimbolo.desde_binance(info)
    assert reglas.paso_cantidad == pytest.approx(0.00001)
    assert reglas.compra_minima == pytest.approx(5.0)


# ===========================================================================
# Stops
# ===========================================================================

def test_el_stop_inicial_esta_a_dos_atr():
    assert stop_manager.stop_inicial(100.0, 5.0, 2.0) == pytest.approx(90.0)


def test_un_atr_invalido_no_produce_un_stop_inventado():
    with pytest.raises(ValueError, match="ATR"):
        stop_manager.stop_inicial(100.0, 0.0)


def test_un_atr_gigante_frente_al_precio_se_rechaza():
    with pytest.raises(ValueError, match="negativo"):
        stop_manager.stop_inicial(10.0, 20.0, 2.0)


def test_el_trailing_sube_cuando_el_precio_sube():
    estado = stop_manager.abrir(100.0, 5.0)
    assert estado.stop_actual == pytest.approx(90.0)

    estado = stop_manager.actualizar(estado, cierre=110.0, atr=5.0)
    assert estado.stop_actual == pytest.approx(100.0)
    assert estado.veces_movido == 1


def test_el_trailing_NUNCA_baja():
    """
    La propiedad que define un trailing. Si retrocede, no es un trailing:
    es una forma elegante de ampliar la perdida cada vez que va en contra.
    """
    estado = stop_manager.abrir(100.0, 5.0)
    estado = stop_manager.actualizar(estado, cierre=120.0, atr=5.0)
    maximo_alcanzado = estado.stop_actual
    assert maximo_alcanzado == pytest.approx(110.0)

    # El precio se derrumba y la volatilidad explota.
    for cierre, atr in [(115.0, 6.0), (105.0, 9.0), (101.0, 12.0), (95.0, 20.0)]:
        estado = stop_manager.actualizar(estado, cierre=cierre, atr=atr)
        assert estado.stop_actual >= maximo_alcanzado, "el stop retrocedio"
    assert estado.stop_actual == pytest.approx(maximo_alcanzado)


def test_el_trailing_se_cuelga_del_cierre_no_del_maximo():
    """
    Una mecha larga de un minuto raro subiria el stop a un nivel que el
    precio nunca sostuvo, y la proxima vela normal lo tocaria.
    """
    estado = stop_manager.abrir(100.0, 5.0)
    # Vela con mecha hasta 200 pero cierre en 101.
    estado = stop_manager.actualizar(estado, cierre=101.0, atr=5.0)
    assert estado.stop_actual == pytest.approx(91.0)  # 101 - 10, no 200 - 10


def test_el_stop_llega_a_asegurar_ganancia():
    estado = stop_manager.abrir(100.0, 5.0)
    assert not estado.en_ganancia_asegurada
    estado = stop_manager.actualizar(estado, cierre=115.0, atr=5.0)
    assert estado.en_ganancia_asegurada
    assert estado.stop_actual == pytest.approx(105.0)


def test_un_atr_invalido_deja_el_stop_donde_estaba():
    estado = stop_manager.abrir(100.0, 5.0)
    igual = stop_manager.actualizar(estado, cierre=120.0, atr=0.0)
    assert igual.stop_actual == pytest.approx(estado.stop_actual)


def test_actualizar_no_modifica_el_estado_que_recibe():
    estado = stop_manager.abrir(100.0, 5.0)
    original = estado.stop_actual
    stop_manager.actualizar(estado, cierre=150.0, atr=5.0)
    assert estado.stop_actual == pytest.approx(original)


def test_el_stop_se_evalua_contra_el_minimo_de_la_vela():
    """
    Si el precio bajo hasta el stop en algun momento, la orden se ejecuto,
    aunque la vela rebotara y cerrara arriba. Mirar solo el cierre salva al
    backtest de perdidas que en la realidad ocurrieron.
    """
    estado = stop_manager.abrir(100.0, 5.0)   # stop en 90
    assert stop_manager.toco_el_stop(estado, minimo_de_la_vela=89.0)
    assert stop_manager.toco_el_stop(estado, minimo_de_la_vela=90.0)
    assert not stop_manager.toco_el_stop(estado, minimo_de_la_vela=91.0)


# ===========================================================================
# Limites duros
# ===========================================================================

def momento(dia: int = 1, hora: int = 12) -> datetime:
    return datetime(2026, 8, dia, hora, tzinfo=UTC)


def control() -> risk_limits.ControlDeRiesgo:
    return risk_limits.ControlDeRiesgo(capital=500.0, perdida_diaria_max_pct=3.0)


def test_sin_perdidas_se_puede_abrir():
    assert control().puede_abrir(momento=momento()).permitido


def test_el_limite_diario_frena_al_llegar_al_tope():
    c = control()   # tope = 15 USDT
    c.registrar_cierre(-5.0, momento())
    assert c.puede_abrir(momento=momento()).permitido

    c.registrar_cierre(-5.0, momento())
    c.registrar_cierre(-5.0, momento())
    veredicto = c.puede_abrir(momento=momento())
    assert not veredicto.permitido
    assert veredicto.limite_alcanzado == "perdida_diaria"


def test_las_ganancias_del_dia_no_desbloquean_el_limite_de_forma_rara():
    """Se mide el resultado NETO del dia, no la suma de las perdidas."""
    c = control()
    c.registrar_cierre(-20.0, momento())
    assert not c.puede_abrir(momento=momento()).permitido

    c.registrar_cierre(+10.0, momento())   # neto: -10, por debajo del tope de 15
    assert c.puede_abrir(momento=momento()).permitido


def test_el_limite_se_reinicia_al_dia_siguiente():
    c = control()
    c.registrar_cierre(-20.0, momento(dia=1))
    assert not c.puede_abrir(momento=momento(dia=1)).permitido
    assert c.puede_abrir(momento=momento(dia=2)).permitido


def test_el_dia_se_corta_en_utc():
    """
    A las 23:00 UTC del dia 1 el limite sigue puesto; a las 00:30 UTC del
    dia 2 ya se reinicio. Con hora local el corte caeria en cualquier lado.
    """
    c = control()
    c.registrar_cierre(-20.0, momento(dia=1, hora=23))
    assert not c.puede_abrir(momento=datetime(2026, 8, 1, 23, 59, tzinfo=UTC)).permitido
    assert c.puede_abrir(momento=datetime(2026, 8, 2, 0, 30, tzinfo=UTC)).permitido


def test_un_momento_sin_zona_horaria_se_rechaza():
    c = control()
    with pytest.raises(ValueError, match="zona horaria"):
        c.puede_abrir(momento=datetime(2026, 8, 1, 12, 0))


def test_el_kill_switch_frena_todo():
    c = control()
    c.kill_switch = True
    veredicto = c.puede_abrir(momento=momento())
    assert not veredicto.permitido
    assert veredicto.limite_alcanzado == "kill_switch"


def test_el_kill_switch_manda_incluso_con_el_dia_en_ganancia():
    c = control()
    c.kill_switch = True
    c.registrar_cierre(+100.0, momento())
    assert not c.puede_abrir(momento=momento()).permitido


def test_el_maximo_de_posiciones_se_respeta():
    c = control()
    c.max_posiciones = 2
    assert c.puede_abrir(posiciones_abiertas=1, momento=momento()).permitido
    veredicto = c.puede_abrir(posiciones_abiertas=2, momento=momento())
    assert not veredicto.permitido
    assert veredicto.limite_alcanzado == "max_posiciones"


def test_sin_maximo_configurado_no_se_limita_por_cantidad():
    c = control()   # max_posiciones = None
    assert c.puede_abrir(posiciones_abiertas=99, momento=momento()).permitido


def test_el_margen_restante_se_calcula_bien():
    c = control()
    assert c.margen_restante(momento()) == pytest.approx(15.0)
    c.registrar_cierre(-6.0, momento())
    assert c.margen_restante(momento()) == pytest.approx(9.0)


# ===========================================================================
# Guardia de cartera
# ===========================================================================

def guardia() -> portfolio_guard.GuardiaDeCartera:
    return portfolio_guard.GuardiaDeCartera(distancia_maxima_bajo_sma_pct=10.0)


def test_precio_sobre_la_media_larga_siempre_pasa():
    assert guardia().revisar_macro(precio=110.0, sma_macro=100.0).permitido


def test_precio_apenas_debajo_de_la_media_pasa():
    assert guardia().revisar_macro(precio=95.0, sma_macro=100.0).permitido


def test_precio_muy_hundido_se_veta():
    veredicto = guardia().revisar_macro(precio=80.0, sma_macro=100.0)
    assert not veredicto.permitido
    assert veredicto.filtro == "macro"


def test_sin_sma_todavia_no_se_opera():
    veredicto = guardia().revisar_macro(precio=100.0, sma_macro=None)
    assert not veredicto.permitido


def test_umbral_macro_sin_definir_avisa_en_vez_de_inventar():
    g = portfolio_guard.GuardiaDeCartera(distancia_maxima_bajo_sma_pct=None)
    with pytest.raises(ValueError, match="sin definir"):
        g.revisar_macro(100.0, 100.0)


def test_no_se_abren_dos_posiciones_de_la_misma_apuesta():
    """
    El bug F de TITAN: SELL en EURUSD y SELL en GOLD el 19-ago-2026 eran una
    sola apuesta al dolar tomada dos veces. Pegaron en su stop con 118
    segundos de diferencia. En cripto es peor: casi todo sigue a Bitcoin.
    """
    veredicto = guardia().revisar_correlacion("ETHUSDT", ["BTCUSDT"])
    assert not veredicto.permitido
    assert veredicto.filtro == "correlacion"


def test_sin_posiciones_abiertas_no_hay_conflicto():
    assert guardia().revisar_correlacion("ETHUSDT", []).permitido


def test_pares_de_grupos_distintos_pueden_convivir():
    g = portfolio_guard.GuardiaDeCartera(
        distancia_maxima_bajo_sma_pct=10.0,
        grupos={"BTCUSDT": "cripto_grande", "ALGOUSDT": "otra_cosa"},
    )
    assert g.revisar_correlacion("ALGOUSDT", ["BTCUSDT"]).permitido


def test_el_filtro_de_correlacion_se_puede_apagar():
    g = portfolio_guard.GuardiaDeCartera(
        distancia_maxima_bajo_sma_pct=10.0, una_posicion_por_grupo=False
    )
    assert g.revisar_correlacion("ETHUSDT", ["BTCUSDT"]).permitido


def test_revisar_aplica_los_dos_filtros_y_el_macro_manda():
    g = guardia()
    # Macro malo Y correlacion mala: tiene que reportar el macro, que se
    # evalua primero.
    veredicto = g.revisar("ETHUSDT", precio=80.0, sma_macro=100.0, pares_abiertos=["BTCUSDT"])
    assert not veredicto.permitido
    assert veredicto.filtro == "macro"

    # Macro bien, correlacion mal.
    veredicto = g.revisar("ETHUSDT", precio=110.0, sma_macro=100.0, pares_abiertos=["BTCUSDT"])
    assert not veredicto.permitido
    assert veredicto.filtro == "correlacion"

    # Los dos bien.
    assert g.revisar("ETHUSDT", precio=110.0, sma_macro=100.0, pares_abiertos=[]).permitido


# ===========================================================================
# Las tres capas juntas
# ===========================================================================

def test_el_riesgo_veta_una_senal_perfecta_si_ya_se_perdio_el_dia():
    """
    La estrategia puede tener toda la razon y aun asi no operarse. Esa es la
    separacion de responsabilidades funcionando.
    """
    c = control()
    c.registrar_cierre(-15.0, momento())

    tamano = position_sizing.calcular(500.0, 1.0, 100_000.0, 97_000.0, REGLAS_BTC)
    assert tamano.aprobado, "el dimensionamiento en si es correcto"
    assert not c.puede_abrir(momento=momento()).permitido, "pero el portero no deja pasar"
