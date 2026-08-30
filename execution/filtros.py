r"""
Filtros de intercambio -- lo que Binance NO te deja pedir.

POR QUE ESTO ESTA EN EL BACKTEST Y NO SOLO EN LA EJECUCION
-----------------------------------------------------------
Un backtest que calcula "compro 0,0347291 BTC" esta comprando una cantidad
que Binance rechaza. La orden real se redondea hacia abajo al `stepSize`, y
si lo que queda no llega al `minNotional` la orden **no existe**.

En una cartera de 20 activos con pesos por inversa de volatilidad esto no es
cosmetico: los pesos chicos son justamente los de los activos mas volatiles,
que son los que mas mueven el resultado. Si el backtest los toma y la cuenta
real no puede, el backtest esta operando una cartera que no se puede armar.

Con 500 USDT y 5 posiciones cada una ronda los 100 USDT, muy por encima del
minimo de 5. El caso que muerde no es ese: es el rebalanceo, donde el ajuste
de una posicion que ya existe puede ser de 3 USDT y no poder ejecutarse.

EL REDONDEO SIEMPRE VA HACIA ABAJO
-----------------------------------
Nunca hacia el mas cercano. Redondear para arriba es comprar mas de lo que el
efectivo alcanza, y en un backtest eso se paga solo (el patrimonio absorbe la
diferencia sin quejarse) mientras que en vivo la orden es rechazada.

LOS DESLISTADOS SI ESTAN EN exchangeInfo -- MEDIDO EL 30-ago-2026
------------------------------------------------------------------
Suponiamos que no. Estan: `exchangeInfo` devuelve 3.685 simbolos, y LUNAUSDT,
LINAUSDT, RENUSDT y UNFIUSDT vienen con su `stepSize` real. La cobertura sobre
los 116 simbolos que pasaron por el universo reconstruido es del **100%**.

Es la misma leccion que el archivo de velas: los deslistados estan ahi si uno
no filtra por `status == "TRADING"`. Por eso `desde_exchange_info()` no filtra
por status, aunque en este archivo pareciera inofensivo hacerlo.

`FiltroSimbolo.generico()` queda igual como red de seguridad, y `cobertura()`
existe para poder decir con numero cuando deja de ser 100%.

PERO LOS FILTROS SON DE DISTINTA EPOCA, Y ESO NO ESTA CORREGIDO
-----------------------------------------------------------------
Binance no versiona `exchangeInfo`: no hay forma de pedir los filtros que
regian en 2019. Lo que devuelve hoy es una mezcla:

- Los simbolos **vivos** traen el minimo de **hoy** (5 USDT, o 1 USDT en las
  memecoins de precio muy bajo: SHIB, PEPE, BONK, DOGE...).
- Los **muertos** quedaron congelados en el minimo que regia cuando los
  deslistaron: BCHABCUSDT, BTTUSDT y ERDUSDT todavia dicen **10 USDT**.

O sea que en la parte vieja de la ventana el backtest deja pasar ordenes de
5 USDT que en su momento habrian sido rechazadas por no llegar a 10. Es un
sesgo **optimista**, chico (con 500 USDT en 5 posiciones cada una ronda los
100) pero real, y esta declarado en vez de corregido porque el dato para
corregirlo no existe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from pathlib import Path

# El minimo tipico de Spot. Vale como default declarado, no como medicion.
NOCIONAL_MINIMO_TIPICO = 5.0

# Tolerancia relativa para no perder un paso entero por el ultimo bit de un
# float. Sin esto, una cantidad que "es" 3,0 pero vale 2,9999999999999996
# se redondea a 2,9 y desaparece un paso completo.
_TOLERANCIA = Decimal("1e-9")


def _piso_a_paso(valor: float, paso: float) -> float:
    """Redondea `valor` hacia abajo al multiplo de `paso` mas cercano."""
    if paso <= 0:
        return float(valor)
    v = Decimal(str(valor))
    p = Decimal(str(paso))
    razon = v / p
    entero = razon.to_integral_value(rounding=ROUND_FLOOR)
    # Si estabamos a un pelo del siguiente multiplo, era ese multiplo.
    if razon - entero > Decimal(1) - _TOLERANCIA:
        entero += 1
    return float(entero * p)


@dataclass(frozen=True)
class FiltroSimbolo:
    """Los tres filtros de Binance que cambian lo que se puede ejecutar."""

    paso_cantidad: float = 0.0      # LOT_SIZE.stepSize (0 = desconocido)
    cantidad_minima: float = 0.0    # LOT_SIZE.minQty
    nocional_minimo: float = NOCIONAL_MINIMO_TIPICO   # NOTIONAL.minNotional
    paso_precio: float = 0.0        # PRICE_FILTER.tickSize (0 = desconocido)

    @classmethod
    def generico(cls) -> "FiltroSimbolo":
        """
        Para los simbolos sin `exchangeInfo` (los deslistados). Solo el minimo
        de nocional; no redondea porque no sabe a que paso.
        """
        return cls()

    @property
    def es_real(self) -> bool:
        """False si es el generico -- o sea, si el redondeo no se esta aplicando."""
        return self.paso_cantidad > 0

    def ajustar_cantidad(self, cantidad: float) -> float:
        return _piso_a_paso(cantidad, self.paso_cantidad)

    def ajustar_precio(self, precio: float) -> float:
        return _piso_a_paso(precio, self.paso_precio)


@dataclass(frozen=True)
class OrdenAjustada:
    """
    Lo que de verdad se puede mandar. `ejecutable=False` no es un error: es un
    resultado, y la cartera tiene que decidir que hace con ese peso.
    """

    cantidad: float
    nocional: float
    ejecutable: bool
    motivo: str = ""

    def __bool__(self) -> bool:
        return self.ejecutable


def ajustar_orden(nocional_deseado: float, precio: float,
                  filtro: FiltroSimbolo) -> OrdenAjustada:
    """
    Convierte "quiero mover N USDT" en la orden que Binance aceptaria.

    Devuelve el nocional REAL despues del redondeo, que siempre es menor o
    igual al pedido. La diferencia queda en efectivo; no se la regala nadie.
    """
    if precio <= 0:
        raise ValueError(f"precio invalido: {precio}")
    if nocional_deseado < 0:
        raise ValueError("el nocional se pasa en valor absoluto")

    cantidad = filtro.ajustar_cantidad(nocional_deseado / precio)
    nocional = cantidad * precio

    if cantidad <= 0:
        return OrdenAjustada(0.0, 0.0, False,
                             "la cantidad se redondea a cero")
    if cantidad < filtro.cantidad_minima:
        return OrdenAjustada(0.0, 0.0, False,
                             f"cantidad {cantidad:g} bajo el minimo "
                             f"{filtro.cantidad_minima:g}")
    if nocional < filtro.nocional_minimo:
        return OrdenAjustada(0.0, 0.0, False,
                             f"nocional {nocional:.2f} bajo el minimo "
                             f"{filtro.nocional_minimo:.2f} USDT")
    return OrdenAjustada(cantidad, nocional, True)


# --- Tabla de filtros ----------------------------------------------------

class TablaDeFiltros:
    """
    Los filtros de todos los simbolos, con el generico como red de seguridad.

    Se construye desde el JSON que escribe `tools/bajar_filtros.py`.
    """

    def __init__(self, filtros: dict[str, FiltroSimbolo] | None = None):
        self._filtros = dict(filtros or {})

    def __len__(self) -> int:
        return len(self._filtros)

    def __contains__(self, simbolo: str) -> bool:
        return simbolo in self._filtros

    def de(self, simbolo: str) -> FiltroSimbolo:
        return self._filtros.get(simbolo, FiltroSimbolo.generico())

    def cobertura(self, simbolos) -> tuple[int, int]:
        """
        (cuantos tienen filtro real, cuantos se pidieron). El numero que hay
        que reportar antes de creerle a un backtest que usa esta tabla.
        """
        simbolos = list(simbolos)
        reales = sum(1 for s in simbolos if self.de(s).es_real)
        return reales, len(simbolos)

    @classmethod
    def desde_json(cls, ruta: Path | str) -> "TablaDeFiltros":
        crudo = json.loads(Path(ruta).read_text(encoding="utf-8"))
        return cls({s: FiltroSimbolo(**d) for s, d in crudo.items()})

    def a_json(self, ruta: Path | str) -> Path:
        ruta = Path(ruta)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps({s: vars(f) for s, f in sorted(self._filtros.items())},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return ruta


def desde_exchange_info(info: dict) -> TablaDeFiltros:
    """
    Traduce la respuesta cruda de `exchangeInfo` a la tabla.

    Toma TODOS los simbolos que vengan, sin filtrar por `status`. Filtrar por
    `status == "TRADING"` fue exactamente el error que metio el sesgo de
    supervivencia en la Fase 1, y no se repite ni siquiera aca, donde parece
    inofensivo.
    """
    tabla: dict[str, FiltroSimbolo] = {}
    for simbolo in info.get("symbols", []):
        por_tipo = {f["filterType"]: f for f in simbolo.get("filters", [])}
        lote = por_tipo.get("LOT_SIZE", {})
        nocional = por_tipo.get("NOTIONAL") or por_tipo.get("MIN_NOTIONAL") or {}
        precio = por_tipo.get("PRICE_FILTER", {})
        tabla[simbolo["symbol"]] = FiltroSimbolo(
            paso_cantidad=float(lote.get("stepSize", 0.0)),
            cantidad_minima=float(lote.get("minQty", 0.0)),
            nocional_minimo=float(nocional.get("minNotional",
                                               NOCIONAL_MINIMO_TIPICO)),
            paso_precio=float(precio.get("tickSize", 0.0)),
        )
    return TablaDeFiltros(tabla)
