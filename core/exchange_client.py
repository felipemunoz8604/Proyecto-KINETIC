"""
Puerta de entrada UNICA a Binance. Y es de SOLO LECTURA.

Esta clase deliberadamente NO tiene ningun metodo capaz de enviar una orden,
cancelar una orden, ni mover fondos. Eso no es un olvido: es el diseno. El
envio de ordenes vive en execution/order_manager.py, que se escribe recien en
Fase 2 y solo despues de que Felipe confirme que entiende los riesgos.

Si alguna vez alguien (o alguna sesion futura de Claude) agrega un metodo de
compra aca, el test tests/test_solo_lectura.py se pone en rojo.

Proteccion de MAINNET
---------------------
Construir un cliente apuntando a dinero real requiere pasar explicitamente
`permitir_mainnet=True`. Con la config en MAINNET pero sin esa bandera, el
constructor se cae. Es un segundo cerrojo, a proposito redundante con el
`entorno.modo` del config.yaml.
"""

from __future__ import annotations

import logging
from typing import Any

from binance.client import Client

log = logging.getLogger(__name__)

# Endpoints que esta clase tiene permitido tocar. Cualquier otro no pasa.
# LISTA BLANCA. Todo lo que no este aca lanza PermissionError.
#
# La regla para agregar algo: tiene que ser IMPOSIBLE que mueva dinero. Si
# hay que pensarlo dos veces, no entra. Un endpoint de lectura de mas cuesta
# una linea; uno de escritura de mas cuesta la garantia entera.
_METODOS_PERMITIDOS = frozenset(
    {
        # --- Spot, solo lectura ---
        "ping",
        "get_server_time",
        "get_account",
        "get_symbol_info",
        "get_exchange_info",
        "get_klines",
        "get_historical_klines",
        "get_symbol_ticker",
        "get_api_key_permission",
        # --- Futuros USDT-M, solo lectura (MEGAPROMPT v2.0, decision D1) ---
        # Entran por la pata corta y el carry de financiacion. Ninguno de
        # estos abre, cierra ni modifica una posicion: son velas, informacion
        # del mercado y el historico de tasas de financiacion, que es un dato
        # imprescindible -- sin el, cualquier backtest con perpetuos es
        # ficcion, porque la financiacion se cobra cada 8 horas y puede
        # superar largamente el ahorro en comisiones.
        "futures_klines",
        "futures_historical_klines",
        "futures_exchange_info",
        "futures_funding_rate",
        "futures_mark_price",
        "futures_symbol_ticker",
    }
)


class ModoRealNoAutorizado(RuntimeError):
    """Se intento abrir una conexion a dinero real sin autorizacion explicita."""


class ClienteBinance:
    """Cliente de solo lectura contra Binance Spot (Testnet o Mainnet)."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        modo: str = "TESTNET",
        permitir_mainnet: bool = False,
    ) -> None:
        modo = modo.upper()
        if modo not in ("TESTNET", "MAINNET"):
            raise ValueError(f"modo debe ser TESTNET o MAINNET, no {modo!r}")

        if modo == "MAINNET" and not permitir_mainnet:
            raise ModoRealNoAutorizado(
                "Estas intentando conectarte a Binance MAINNET (dinero real).\n"
                "Esta conexion requiere pasar permitir_mainnet=True de forma "
                "explicita. Ningun script de KINETIC lo hace por su cuenta."
            )

        self.modo = modo
        self.es_testnet = modo == "TESTNET"
        self._cliente = Client(api_key, api_secret, testnet=self.es_testnet)
        log.info("Cliente Binance creado en modo %s (solo lectura)", modo)

    # -- Comprobaciones de salud -------------------------------------------

    def ping(self) -> bool:
        """True si Binance responde. No requiere llaves validas."""
        self._cliente.ping()
        return True

    def hora_servidor(self) -> int:
        """Hora de Binance en milisegundos. Sirve para detectar reloj desfasado."""
        return int(self._cliente.get_server_time()["serverTime"])

    def desfase_de_reloj_ms(self) -> int:
        """
        Diferencia entre el reloj de esta maquina y el de Binance.

        Importa: si tu reloj se atrasa mas de 1000 ms, Binance rechaza las
        llamadas firmadas con un error de timestamp que parece un problema de
        llaves y no lo es.
        """
        import time

        local_ms = int(time.time() * 1000)
        return local_ms - self.hora_servidor()

    # -- Estado de la cuenta ------------------------------------------------

    def cuenta(self) -> dict[str, Any]:
        """Datos de la cuenta. Requiere llaves validas."""
        return self._cliente.get_account()

    def saldos_no_cero(self) -> dict[str, float]:
        """Solo los activos con saldo distinto de cero, como {simbolo: cantidad}."""
        saldos: dict[str, float] = {}
        for activo in self.cuenta().get("balances", []):
            total = float(activo["free"]) + float(activo["locked"])
            if total > 0:
                saldos[activo["asset"]] = total
        return saldos

    def permisos_de_la_llave(self) -> dict[str, Any] | None:
        """
        Que tiene permitido hacer la API key (leer / operar / RETIRAR).

        Devuelve None en Testnet: ese endpoint es de la API de Mainnet y el
        servidor de pruebas no lo expone. No es un error.
        """
        if self.es_testnet:
            return None
        return self._cliente.get_api_key_permission()

    # -- Datos de mercado ---------------------------------------------------

    def info_simbolo(self, par: str) -> dict[str, Any] | None:
        """Reglas del par: tamano minimo, paso de cantidad, notional minimo."""
        return self._cliente.get_symbol_info(par)

    def precio(self, par: str) -> float:
        return float(self._cliente.get_symbol_ticker(symbol=par)["price"])

    def velas(self, par: str, temporalidad: str, limite: int = 500) -> list[list]:
        """Ultimas `limite` velas OHLCV crudas, como las devuelve Binance."""
        return self._cliente.get_klines(
            symbol=par, interval=temporalidad, limit=limite
        )

    # -- Escotilla de escape controlada -------------------------------------

    def llamar_solo_lectura(self, metodo: str, **kwargs: Any) -> Any:
        """
        Llama un endpoint de python-binance, pero solo si esta en la lista
        blanca de arriba. Existe para no tener que ir agregando envoltorios
        de uno en uno, sin abrir la puerta a los metodos de trading.
        """
        if metodo not in _METODOS_PERMITIDOS:
            raise PermissionError(
                f"'{metodo}' no esta en la lista de metodos de solo lectura. "
                "Si necesitas enviar ordenes, eso vive en "
                "execution/order_manager.py (Fase 2), no aca."
            )
        return getattr(self._cliente, metodo)(**kwargs)
