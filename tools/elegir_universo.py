r"""
Elige el universo de pares con una regla mecanica y CIEGA AL RESULTADO.

POR QUE EXISTE
--------------
La Fase 1 midio dos pares, BTC y ETH, y en 4h dieron 10 y 9 operaciones por
anio: no alcanza para confiar en ninguna cifra. La forma honesta de conseguir
mas muestra no es barrer mas parametros, es mirar mas mercado.

Pero "mirar mas mercado" se convierte en trampa en el momento en que uno
elige los pares. Si yo escribo una lista a mano, esa lista ya viene teñida
por lo que se de cada moneda. Por eso el universo lo decide una regla, y la
regla no puede consultar ningun resultado de backtest.

LA REGLA
--------
1. Par contra USDT, en estado TRADING, con spot habilitado.
2. La moneda base no es una stablecoin ni una moneda fiat: un par
   USDC/USDT no es una apuesta direccional, es ruido alrededor de 1,00.
3. No es un token apalancado (UP, DOWN, BULL, BEAR): son productos derivados
   con decaimiento diario, no el activo.
4. Su primera vela es ANTERIOR al corte configurado (por defecto el
   1-ene-2019), para que tenga aproximadamente el mismo periodo que BTC y
   ETH y por lo tanto la misma estructura de ventanas. Sin esto, un par
   listado en 2022 aportaria solo el mercado bajista y la comparacion entre
   pares dejaria de significar lo mismo.

Ninguno de los cuatro criterios mira si el par gano o perdio plata.

EL SESGO QUE ESTA REGLA NO PUEDE ARREGLAR, Y HAY QUE DECIR EN VOZ ALTA
----------------------------------------------------------------------
**Sesgo de supervivencia.** Binance solo sirve velas de los pares que hoy
existen. Las monedas que se listaron en 2018, se murieron y se deslistaron no
estan en esta lista y no hay forma de traerlas desde este endpoint.

Eso favorece a cualquier estrategia que compre y aguante: el universo es
"las que sobrevivieron ocho anios". No lo corrige ningun filtro de los de
arriba, asi que cualquier resultado agregado que salga de aca esta inflado
por una cantidad desconocida, y esa advertencia tiene que viajar pegada al
numero.

Se corre asi:

    venv\Scripts\python.exe tools\elegir_universo.py
    venv\Scripts\python.exe tools\elegir_universo.py --corte 2020-01-01
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import pandas as pd  # noqa: E402

from core import data_feed  # noqa: E402

# Bases que no son una apuesta direccional. Un par contra USDT donde la base
# tambien vale un dolar no tiene tendencia que capturar.
ESTABLES = {
    "USDC", "BUSD", "TUSD", "USDP", "PAX", "DAI", "FDUSD", "USDS", "USDSB",
    "SUSD", "EUR", "GBP", "AUD", "TRY", "RUB", "BRL", "ZAR", "IDRT", "NGN",
    "UAH", "BIDR", "DAIB", "VAI", "USTC", "UST", "AEUR", "PLN", "RON", "JPY",
    "MXN", "COP", "CZK", "ARS",
}

# Tokens apalancados: decaen todos los dias por como estan construidos, asi
# que su serie de precios no es la del activo.
SUFIJOS_APALANCADOS = ("UPUSDT", "DOWNUSDT", "BULLUSDT", "BEARUSDT")


def candidatos(cliente) -> list[str]:
    """Pares USDT operables hoy, sin stablecoins ni tokens apalancados."""
    info = cliente.get_exchange_info()
    salida = []
    for s in info["symbols"]:
        if s["quoteAsset"] != "USDT":
            continue
        if s["status"] != "TRADING" or not s.get("isSpotTradingAllowed", False):
            continue
        if s["baseAsset"] in ESTABLES:
            continue
        if s["symbol"].endswith(SUFIJOS_APALANCADOS):
            continue
        salida.append(s["symbol"])
    return sorted(salida)


def primera_vela(cliente, par: str) -> pd.Timestamp | None:
    """
    Cuando empieza el historico de un par.

    Se pide en velas MENSUALES a proposito: una sola llamada alcanza para
    saber el mes de listado, y con eso basta para decidir. Pedirlo en 4h
    seria el mismo dato a un costo mucho mayor de llamadas.
    """
    velas = cliente.get_klines(symbol=par, interval="1M", startTime=0, limit=1)
    if not velas:
        return None
    return pd.to_datetime(velas[0][0], unit="ms", utc=True)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--corte", default="2019-01-01",
                        help="el par tiene que existir antes de esta fecha")
    parser.add_argument("--pausa", type=float, default=0.06,
                        help="segundos entre llamadas, para no chocar el limite")
    args = parser.parse_args()

    corte = pd.Timestamp(args.corte, tz="UTC")
    cliente = data_feed._cliente_publico()

    print("=" * 72)
    print(" KINETIC - eleccion del universo (regla mecanica, ciega al resultado)")
    print("=" * 72)
    print(f"  Corte de antiguedad: primera vela anterior a {corte.date()}")
    print("  Endpoint publico de Binance: NO se usan llaves.")
    print()

    todos = candidatos(cliente)
    print(f"  {len(todos)} pares USDT operables, sin stablecoins ni apalancados.")
    print("  Consultando la fecha de listado de cada uno...\n", flush=True)

    elegidos: list[tuple[str, pd.Timestamp]] = []
    fallos: list[str] = []
    for i, par in enumerate(todos, 1):
        try:
            desde = primera_vela(cliente, par)
        except Exception as e:  # noqa: BLE001 - un par que falla no frena el resto
            fallos.append(f"{par}: {e}")
            continue
        if desde is not None and desde < corte:
            elegidos.append((par, desde))
        if i % 50 == 0:
            print(f"    {i}/{len(todos)} consultados, {len(elegidos)} califican",
                  flush=True)
        time.sleep(args.pausa)

    elegidos.sort(key=lambda x: x[1])

    print()
    print("=" * 72)
    print(f" UNIVERSO: {len(elegidos)} pares")
    print("=" * 72)
    for par, desde in elegidos:
        print(f"  {par:<14} desde {desde.date()}")

    if fallos:
        print(f"\n  ({len(fallos)} pares no se pudieron consultar)")
        for f in fallos[:10]:
            print(f"    {f}")

    print("\n  Para pegar en config.yaml o en el runner:")
    print("  " + repr([p for p, _ in elegidos]))
    print("\n  OJO: esta lista tiene sesgo de supervivencia. Son los pares que")
    print("  llegaron vivos hasta hoy; los que se deslistaron no estan y no")
    print("  hay forma de traerlos. Cualquier resultado agregado esta inflado")
    print("  por una cantidad que no se puede medir desde aca.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
