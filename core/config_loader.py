"""
Lector de config/config.yaml.

Por que existe este archivo y no un simple yaml.safe_load() suelto por ahi:
si cada modulo lee el YAML por su cuenta, tarde o temprano dos modulos leen
versiones distintas del mismo numero. Aca se lee una sola vez y se valida.

La validacion es a proposito PARANOICA con los parametros de riesgo: si
falta uno o viene fuera de rango, el programa se cae al arrancar en vez de
operar con un valor raro.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIG_POR_DEFECTO = RAIZ / "config" / "config.yaml"


class ErrorDeConfiguracion(Exception):
    """La configuracion falta, esta mal formada, o tiene un valor imposible."""


def cargar(ruta: Path | str | None = None) -> dict[str, Any]:
    """Lee y valida config.yaml. Devuelve un diccionario."""
    ruta = Path(ruta) if ruta else RUTA_CONFIG_POR_DEFECTO
    if not ruta.exists():
        raise ErrorDeConfiguracion(f"No encuentro el archivo de configuracion: {ruta}")

    with open(ruta, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not isinstance(cfg, dict):
        raise ErrorDeConfiguracion(f"{ruta} no contiene un diccionario YAML valido.")

    _validar(cfg, ruta)
    return cfg


def _validar(cfg: dict[str, Any], ruta: Path) -> None:
    for seccion in ("meta", "entorno", "capital", "riesgo", "stops", "costos"):
        if seccion not in cfg:
            raise ErrorDeConfiguracion(f"Falta la seccion '{seccion}' en {ruta}")

    modo = cfg["entorno"].get("modo")
    if modo not in ("TESTNET", "MAINNET"):
        raise ErrorDeConfiguracion(
            f"entorno.modo debe ser TESTNET o MAINNET, no {modo!r}"
        )

    capital = cfg["capital"].get("monto")
    if not isinstance(capital, (int, float)) or capital <= 0:
        raise ErrorDeConfiguracion(f"capital.monto debe ser un numero > 0, no {capital!r}")

    riesgo_op = cfg["riesgo"].get("por_operacion_pct")
    if not isinstance(riesgo_op, (int, float)) or not (0 < riesgo_op <= 5):
        raise ErrorDeConfiguracion(
            "riesgo.por_operacion_pct debe estar entre 0 y 5 (por ciento). "
            f"Recibi {riesgo_op!r}. Si de verdad queres arriesgar mas del 5% por "
            "operacion, hay que cambiar esta validacion a proposito, no de pasada."
        )

    perdida_dia = cfg["riesgo"].get("perdida_diaria_max_pct")
    if not isinstance(perdida_dia, (int, float)) or not (0 < perdida_dia <= 20):
        raise ErrorDeConfiguracion(
            f"riesgo.perdida_diaria_max_pct debe estar entre 0 y 20. Recibi {perdida_dia!r}"
        )

    if perdida_dia < riesgo_op:
        raise ErrorDeConfiguracion(
            f"El tope diario ({perdida_dia}%) es menor que el riesgo de UNA sola "
            f"operacion ({riesgo_op}%). Asi el bot se apagaria antes de poder abrir "
            "la primera posicion."
        )


def pendientes(cfg: dict[str, Any]) -> list[str]:
    """Devuelve la lista de parametros todavia sin definir (valor null)."""
    encontrados: list[str] = []

    def recorrer(nodo: Any, camino: str) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                recorrer(valor, f"{camino}.{clave}" if camino else clave)
        elif nodo is None:
            encontrados.append(camino)

    recorrer(cfg, "")
    return encontrados


def modo_es_real(cfg: dict[str, Any]) -> bool:
    """True solo si la config apunta a dinero real."""
    return cfg["entorno"]["modo"] == "MAINNET"


def credenciales(cfg: dict[str, Any]) -> tuple[str, str]:
    """
    Lee las llaves del entorno (.env) segun el modo configurado.

    Nunca devuelve las llaves en un mensaje de error ni las escribe en un log.
    """
    if modo_es_real(cfg):
        clave, secreto = "BINANCE_API_KEY", "BINANCE_API_SECRET"
    else:
        clave, secreto = "BINANCE_TESTNET_API_KEY", "BINANCE_TESTNET_API_SECRET"

    valor_clave = os.getenv(clave, "").strip()
    valor_secreto = os.getenv(secreto, "").strip()

    if not valor_clave or not valor_secreto:
        raise ErrorDeConfiguracion(
            f"Faltan {clave} y/o {secreto} en tu archivo .env.\n"
            "Copia .env.example como .env y pega ahi tus llaves. "
            "El archivo .env no se sube a git."
        )
    return valor_clave, valor_secreto
