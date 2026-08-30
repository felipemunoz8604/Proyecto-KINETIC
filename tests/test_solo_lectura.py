"""
Guardian de la regla mas importante de KINETIC hasta la Fase 2:
ningun modulo escrito hasta ahora puede enviar una orden a Binance.

Esta prueba no ejecuta el bot: LEE EL CODIGO FUENTE y busca llamadas
peligrosas. Es la misma idea que usa TITAN para vigilar su Torre de Control.
Si una sesion futura agrega una compra "de prueba" en el cliente, esto se
pone en rojo antes de que llegue a ningun lado.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Metodos de python-binance que mueven dinero de verdad.
#
# AMPLIADO EN LA FASE 2 (MEGAPROMPT v2.0, regla 8). Abrir el alcance a
# perpetuos sin ampliar este cerrojo habria dejado un hueco justo en la
# garantia de que el bot no puede operar: la lista original solo cubria
# `futures_create_order`, y en futuros hay varias formas de tomar riesgo que
# no son "crear una orden" -- cambiar el apalancamiento, por ejemplo, altera
# el riesgo de una posicion existente sin enviar ninguna orden nueva.
LLAMADAS_PROHIBIDAS = [
    # --- Spot ---
    "create_order",
    "order_market",
    "order_limit",
    "order_oco",
    "create_test_order",
    "cancel_order",
    "withdraw",
    "universal_transfer",
    # --- Futuros: abrir, cerrar o cancelar ---
    "futures_create_order",
    "futures_create_test_order",
    "futures_cancel_order",
    "futures_cancel_all_open_orders",
    "futures_place_batch_order",
    # --- Futuros: tomar riesgo sin enviar una orden ---
    "futures_change_leverage",
    "futures_change_margin_type",
    "futures_change_position_mode",
    "futures_change_multi_assets_mode",
    "futures_transfer",
    # --- Margen ---
    "create_margin_order",
    "create_margin_loan",
    "repay_margin_loan",
]

# Carpetas que hasta que exista un modulo de ejecucion aprobado deben ser
# 100% inofensivas. `execution/` y `journal/` estan vacias hoy y se vigilan
# igual: son justo donde aparecerian las llamadas peligrosas, asi que si
# alguien las llena, esto lo ve.
CARPETAS_VIGILADAS = [
    "core", "strategy", "risk", "backtesting", "tools", "metrics",
    "execution", "journal",
]


def _archivos_python() -> list[Path]:
    archivos: list[Path] = []
    for carpeta in CARPETAS_VIGILADAS:
        ruta = RAIZ / carpeta
        if ruta.exists():
            archivos.extend(ruta.rglob("*.py"))
    return archivos


def test_hay_codigo_para_revisar():
    """Si encontrara cero archivos, las pruebas de abajo pasarian en falso."""
    assert _archivos_python(), "No se encontro ningun .py en las carpetas vigiladas."


@pytest.mark.parametrize("llamada", LLAMADAS_PROHIBIDAS)
def test_ningun_modulo_puede_enviar_ordenes(llamada: str):
    culpables = []
    for archivo in _archivos_python():
        texto = archivo.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), start=1):
            sin_comentario = linea.split("#", 1)[0]
            if "." + llamada + "(" in sin_comentario:
                culpables.append(str(archivo.relative_to(RAIZ)) + ":" + str(numero))

    assert not culpables, (
        "Se encontro una llamada capaz de mover dinero ('"
        + llamada
        + "') en codigo que debe ser de solo lectura: "
        + str(culpables)
    )


def test_el_cliente_no_expone_metodos_de_trading():
    """El objeto ClienteBinance no debe tener nada que suene a operar."""
    from core.exchange_client import ClienteBinance

    prohibidas = ("orden", "order", "comprar", "vender", "buy", "sell", "retir")
    sospechosos = [
        nombre
        for nombre in dir(ClienteBinance)
        if any(p in nombre.lower() for p in prohibidas)
    ]
    assert not sospechosos, "ClienteBinance expone metodos de trading: " + str(sospechosos)


def test_mainnet_requiere_autorizacion_explicita():
    from core.exchange_client import ClienteBinance, ModoRealNoAutorizado

    with pytest.raises(ModoRealNoAutorizado):
        ClienteBinance("llave_falsa", "secreto_falso", modo="MAINNET")


def test_config_apunta_a_testnet():
    """
    Vigila que nadie deje el repo apuntando a dinero real sin querer.
    Cuando Felipe active la Fase 3 a proposito, esta prueba se cambia
    tambien a proposito, y queda registrado en el commit.
    """
    from core import config_loader

    cfg = config_loader.cargar()
    assert cfg["entorno"]["modo"] == "TESTNET", (
        "config.yaml apunta a MAINNET (dinero real). Si no fue a proposito, "
        "revertilo ya."
    )


def test_tope_diario_no_puede_ser_menor_al_riesgo_por_operacion():
    from core import config_loader

    cfg = config_loader.cargar()
    assert (
        cfg["riesgo"]["perdida_diaria_max_pct"] >= cfg["riesgo"]["por_operacion_pct"]
    )


# --- La lista blanca del cliente ------------------------------------------

def test_la_lista_blanca_no_deja_pasar_nada_que_escriba():
    """
    Vigila la lista blanca en si misma, no solo las llamadas en el codigo.

    Es la otra mitad del cerrojo: el codigo de hoy puede no llamar a nada
    peligroso, pero si la lista blanca lo permite, `llamar_solo_lectura()`
    seria una puerta abierta -- alcanza una linea en cualquier script futuro.

    Se compara por PALABRA y no por subcadena. La primera version usaba
    subcadena y marcaba `get_exchange_info` como peligroso, porque
    "ex-change-info" contiene "change". Un cerrojo que da falsos positivos se
    termina desactivando, y ahi si queda abierto de verdad.

    Nota: algun endpoint de solo lectura puede caer aca igual -- por ejemplo
    `get_open_orders`, que contiene "orders". Es a proposito: agregarlo tiene
    que ser una decision consciente con su excepcion escrita, no un descuido.
    """
    from core.exchange_client import _METODOS_PERMITIDOS

    verbos_de_escritura = {
        "create", "cancel", "withdraw", "transfer", "order", "orders",
        "change", "loan", "repay", "borrow", "close", "set", "new",
    }
    peligrosos = [
        m for m in _METODOS_PERMITIDOS
        if verbos_de_escritura & set(m.lower().split("_"))
    ]
    assert not peligrosos, (
        "La lista blanca de endpoints permite metodos que suenan a escritura: "
        + str(sorted(peligrosos))
    )


def test_los_endpoints_de_futuros_permitidos_son_solo_de_lectura():
    """
    La decision D1 abrio futuros. Estos son los unicos que entraron, y la
    prueba existe para que la lista no crezca sin que nadie lo note.
    """
    from core.exchange_client import _METODOS_PERMITIDOS

    de_futuros = {m for m in _METODOS_PERMITIDOS if m.startswith("futures_")}
    esperados = {
        "futures_klines",
        "futures_historical_klines",
        "futures_exchange_info",
        "futures_funding_rate",
        "futures_mark_price",
        "futures_symbol_ticker",
    }
    assert de_futuros == esperados, (
        "La lista de endpoints de futuros cambio. Agregar uno es una decision "
        "de seguridad: revisala a mano y actualiza esta prueba a proposito. "
        f"Sobran {sorted(de_futuros - esperados)}, "
        f"faltan {sorted(esperados - de_futuros)}."
    )


def test_no_hay_apalancamiento_activable_desde_el_codigo():
    """
    Regla 7 del MEGAPROMPT v2.0: k_max = 1,0 es tope duro.

    Los perpetuos entran para habilitar la pata corta y bajar comisiones, no
    para apalancar. Como `futures_change_leverage` ya esta en la lista
    prohibida, esta prueba cubre el otro camino: que nadie lo llame por la
    escotilla de `llamar_solo_lectura`.
    """
    from core.exchange_client import _METODOS_PERMITIDOS

    assert "futures_change_leverage" not in _METODOS_PERMITIDOS
    assert "futures_change_margin_type" not in _METODOS_PERMITIDOS
