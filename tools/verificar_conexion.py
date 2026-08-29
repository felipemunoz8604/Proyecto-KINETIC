"""
Verificacion de conexion de KINETIC - Fase 0.

Comprueba, SIN operar ni mover un centavo, que:
  1. Hay un archivo .env con llaves.
  2. Binance responde.
  3. El reloj de esta maquina esta sincronizado con el de Binance.
  4. Las llaves son validas y podemos leer la cuenta.
  5. Se pueden bajar velas (los datos que va a usar la estrategia).
  6. La llave NO tiene permiso de retiro (solo comprobable en Mainnet).

Se corre asi, parado en la carpeta del proyecto:

    venv\\Scripts\\python.exe tools\\verificar_conexion.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from core import config_loader as cfgmod  # noqa: E402
from core.exchange_client import ClienteBinance  # noqa: E402

# Par usado UNICAMENTE para probar que llegan datos. No es el par elegido
# para operar: ese se decide con el backtest de la Fase 1.
PAR_DE_PRUEBA = "BTCUSDT"

# La cuenta de Testnet viene con cientos de monedas de regalo. Solo estas
# nos interesan; el resto se cuenta pero no se lista.
DESTACADOS = ("USDT", "BTC", "ETH", "BNB", "USDC")


def titulo(texto: str) -> None:
    print("\n" + texto)
    print("-" * len(texto))


def main() -> int:
    print("=" * 62)
    print(" KINETIC - verificacion de conexion (solo lectura, no opera nada)")
    print("=" * 62)

    ruta_env = RAIZ / ".env"
    if not ruta_env.exists():
        print("\n[X] No existe el archivo .env")
        print("    Copia .env.example como .env y pega ahi tus llaves de TESTNET.")
        print("    Se sacan gratis en https://testnet.binance.vision/")
        return 1
    load_dotenv(ruta_env)
    print("\n[OK] Archivo .env encontrado: " + str(ruta_env))

    try:
        cfg = cfgmod.cargar()
    except cfgmod.ErrorDeConfiguracion as e:
        print("\n[X] Configuracion invalida:\n    " + str(e))
        return 1

    modo = cfg["entorno"]["modo"]
    print("[OK] config.yaml valido - modo: " + modo)
    if modo == "MAINNET":
        print("\n[!] La configuracion apunta a DINERO REAL.")
        print("    Este script es de solo lectura, pero si no esperabas ver")
        print("    MAINNET aca, para y revisa config/config.yaml antes de seguir.")

    try:
        clave, secreto = cfgmod.credenciales(cfg)
    except cfgmod.ErrorDeConfiguracion as e:
        print("\n[X] " + str(e))
        return 1
    print("[OK] Llaves cargadas desde .env (empiezan con " + clave[:4] + "...)")

    cliente = ClienteBinance(
        clave, secreto, modo=modo, permitir_mainnet=(modo == "MAINNET")
    )

    titulo("1. Binance responde")
    cliente.ping()
    print("[OK] ping correcto")

    titulo("2. Sincronizacion de reloj")
    desfase = cliente.desfase_de_reloj_ms()
    print("    Desfase con Binance: " + str(desfase) + " ms")
    if abs(desfase) > 1000:
        print("[X] Tu reloj esta desfasado mas de 1 segundo. Binance va a rechazar")
        print("    las llamadas firmadas con un error que PARECE de llaves y no lo es.")
        print("    Arreglo: Configuracion > Hora e idioma > Sincronizar ahora.")
        return 1
    print("[OK] reloj dentro de tolerancia")

    titulo("3. Lectura de la cuenta")
    cuenta = cliente.cuenta()
    print("    Tipo de cuenta:            " + str(cuenta.get("accountType")))
    print("    Puede operar (canTrade):   " + str(cuenta.get("canTrade")))
    print("    Puede retirar (canWithdraw): " + str(cuenta.get("canWithdraw")))
    saldos = cliente.saldos_no_cero()
    if not saldos:
        print("    (sin saldos - normal en una cuenta de Testnet recien creada)")
    elif "--todos-los-saldos" in sys.argv:
        for activo, cantidad in sorted(saldos.items()):
            print("      " + activo.ljust(10) + " " + str(cantidad))
    else:
        # La cuenta de Testnet viene con cientos de monedas de regalo.
        # Listarlas todas hace ilegible la salida, asi que mostramos las que
        # de verdad importan y contamos el resto.
        print("    Activos con saldo: " + str(len(saldos)))
        for activo in DESTACADOS:
            if activo in saldos:
                print("      " + activo.ljust(10) + " " + str(saldos[activo]))
        otros = len(saldos) - sum(1 for a in DESTACADOS if a in saldos)
        if otros > 0:
            print("      (+" + str(otros) + " mas - usa --todos-los-saldos para verlos)")
    print("[OK] lectura de cuenta correcta")

    titulo("4. Permisos de la llave")
    permisos = cliente.permisos_de_la_llave()
    if permisos is None:
        print("    No comprobable en Testnet (ese endpoint es solo de Mainnet).")
        print("    Se vuelve obligatorio antes de la Fase 3.")
    else:
        print("    Lectura:  " + str(permisos.get("enableReading")))
        print("    Spot:     " + str(permisos.get("enableSpotAndMarginTrading")))
        print("    RETIRO:   " + str(permisos.get("enableWithdrawals")))
        if permisos.get("enableWithdrawals"):
            print("\n[X] ALTO. Esta llave PUEDE RETIRAR FONDOS.")
            print("    Borrala en Binance y crea una nueva con el retiro apagado.")
            return 1
        print("[OK] la llave no puede retirar fondos")

    titulo("5. Datos de mercado (" + PAR_DE_PRUEBA + ", solo prueba de conexion)")
    velas = cliente.velas(PAR_DE_PRUEBA, "1h", limite=5)
    print("    Velas recibidas: " + str(len(velas)))
    print("    Precio actual:   " + str(cliente.precio(PAR_DE_PRUEBA)))
    info = cliente.info_simbolo(PAR_DE_PRUEBA)
    if info:
        for filtro in info.get("filters", []):
            if filtro["filterType"] == "LOT_SIZE":
                print(
                    "    Cantidad minima: "
                    + str(filtro["minQty"])
                    + "  paso: "
                    + str(filtro["stepSize"])
                )
            if filtro["filterType"] in ("NOTIONAL", "MIN_NOTIONAL"):
                print("    Compra minima:   " + str(filtro.get("minNotional")) + " USDT")
    print("[OK] datos de mercado disponibles")

    titulo("6. Parametros todavia sin definir")
    faltantes = cfgmod.pendientes(cfg)
    if faltantes:
        print("    Estos se deciden con el backtest de la Fase 1, no antes:")
        for pendiente in faltantes:
            print("      - " + pendiente)
    else:
        print("    Ninguno.")

    print("\n" + "=" * 62)
    print(" FASE 0 VERIFICADA - conexion de solo lectura funcionando")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
