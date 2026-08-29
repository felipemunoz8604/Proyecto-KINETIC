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
LLAMADAS_PROHIBIDAS = [
    "create_order",
    "order_market",
    "order_limit",
    "order_oco",
    "create_test_order",
    "cancel_order",
    "withdraw",
    "universal_transfer",
    "futures_create_order",
]

# Carpetas que hasta la Fase 2 deben ser 100% inofensivas.
CARPETAS_VIGILADAS = ["core", "strategy", "risk", "backtesting", "tools"]


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
