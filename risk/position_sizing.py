"""
Cuanto comprar. El calculo mas importante del bot.

LA IDEA
-------
No se decide "compro 100 dolares de BTC". Se decide "estoy dispuesto a
perder 5 dolares si me equivoco", y de ahi sale cuanto comprar:

    cantidad = dinero_en_riesgo / distancia_al_stop

Con 500 USDT y 1% de riesgo, el dinero en riesgo son 5 USDT SIEMPRE, opere
lo que opere. Lo que cambia es el tamano de la compra: si el stop esta
lejos se compra poco, si esta cerca se compra mas. Asi todas las
operaciones pesan lo mismo, y una racha de perdidas es aritmetica en vez de
catastrofe.

LAS COMISIONES ENTRAN EN LA CUENTA
----------------------------------
Binance cobra 0,1% al comprar y 0,1% al vender. Si dimensionamos ignorando
eso, la perdida real al tocar el stop es siempre un poco mayor que el 1%
que creiamos arriesgar. Aca se despeja con las comisiones adentro:

    perdida_total = cantidad x distancia + comision_compra + comision_venta
                  = cantidad x (distancia + c x (entrada + stop))

    => cantidad = dinero_en_riesgo / (distancia + c x (entrada + stop))

Es una diferencia chica, pero es una diferencia que siempre va en contra.

LOS TRES LIMITES QUE PUEDEN ACHICAR O ANULAR LA COMPRA
-------------------------------------------------------
1. EL CAPITAL. Esto es SPOT sin apalancamiento: no se puede comprar por mas
   dinero del que hay. Si el stop esta muy pegado al precio, la formula
   pide una compra mayor al capital. Ahi se recorta al capital disponible y
   se avisa: el riesgo real queda POR DEBAJO del configurado, que es el
   lado seguro del error, pero hay que saberlo.
2. EL PASO DE CANTIDAD (stepSize). Binance solo acepta multiplos. Siempre se
   redondea HACIA ABAJO -- redondear hacia arriba seria arriesgar mas de lo
   autorizado.
3. LA COMPRA MINIMA (minNotional, 5 USDT en BTCUSDT). Si despues de todo lo
   anterior la compra queda por debajo, la operacion se RECHAZA. No se
   agranda para llegar al minimo: eso seria romper el limite de riesgo para
   poder operar, que es exactamente al reves de como tiene que ser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal


@dataclass(frozen=True)
class ReglasSimbolo:
    """Los limites que impone Binance para un par. Salen de `get_symbol_info`."""

    paso_cantidad: float = 0.00001
    cantidad_minima: float = 0.00001
    compra_minima: float = 5.0

    @classmethod
    def desde_binance(cls, info: dict) -> "ReglasSimbolo":
        paso, minima, notional = 0.00001, 0.00001, 5.0
        for filtro in info.get("filters", []):
            if filtro["filterType"] == "LOT_SIZE":
                paso = float(filtro["stepSize"])
                minima = float(filtro["minQty"])
            elif filtro["filterType"] in ("NOTIONAL", "MIN_NOTIONAL"):
                if filtro.get("minNotional") is not None:
                    notional = float(filtro["minNotional"])
        return cls(paso_cantidad=paso, cantidad_minima=minima, compra_minima=notional)


@dataclass(frozen=True)
class Tamano:
    """El resultado del calculo, con todo lo necesario para auditarlo."""

    aprobado: bool
    cantidad: float
    valor_compra: float
    riesgo_dinero: float
    riesgo_real_pct: float
    motivo: str
    recortado_por_capital: bool = False
    avisos: list[str] = field(default_factory=list)


def _redondear_al_paso(cantidad: float, paso: float) -> float:
    """
    Redondea HACIA ABAJO al multiplo del paso.

    Con Decimal y no con float: 0.1 + 0.2 no da 0.3 en coma flotante, y aca
    un redondeo hacia arriba por error de representacion significa arriesgar
    mas de lo autorizado.
    """
    if paso <= 0:
        return cantidad
    d_cantidad = Decimal(str(cantidad))
    d_paso = Decimal(str(paso))
    pasos = (d_cantidad / d_paso).to_integral_value(rounding=ROUND_DOWN)
    return float(pasos * d_paso)


def calcular(
    capital: float,
    riesgo_pct: float,
    precio_entrada: float,
    precio_stop: float,
    reglas: ReglasSimbolo | None = None,
    comision_pct: float = 0.1,
    capital_disponible: float | None = None,
) -> Tamano:
    """
    Devuelve cuanto comprar, o un rechazo explicando por que no se puede.

    `capital` es el capital total del bot (base del % de riesgo).
    `capital_disponible` es lo que hay libre ahora mismo; si no se pasa, se
    asume que es todo el capital.
    """
    reglas = reglas or ReglasSimbolo()
    disponible = capital if capital_disponible is None else capital_disponible
    avisos: list[str] = []

    if precio_entrada <= 0:
        return Tamano(False, 0.0, 0.0, 0.0, 0.0, "el precio de entrada tiene que ser > 0")

    distancia = precio_entrada - precio_stop
    if distancia <= 0:
        return Tamano(
            False, 0.0, 0.0, 0.0, 0.0,
            f"el stop ({precio_stop}) tiene que estar POR DEBAJO de la entrada "
            f"({precio_entrada}); si no, no hay perdida que limitar",
        )

    riesgo_dinero = capital * riesgo_pct / 100.0
    if riesgo_dinero <= 0:
        return Tamano(False, 0.0, 0.0, 0.0, 0.0, "el riesgo configurado es cero")

    # Las comisiones de ida y vuelta entran en el denominador.
    c = comision_pct / 100.0
    costo_por_unidad = distancia + c * (precio_entrada + precio_stop)
    cantidad = riesgo_dinero / costo_por_unidad

    # --- Limite 1: el capital. Spot, sin apalancamiento. ------------------
    recortado = False
    if cantidad * precio_entrada > disponible:
        cantidad = disponible / precio_entrada
        recortado = True
        avisos.append(
            "la compra se recorto al capital disponible: el stop esta tan cerca "
            "del precio que arriesgar el % completo exigiria mas dinero del que hay"
        )

    # --- Limite 2: el paso de cantidad ------------------------------------
    cantidad = _redondear_al_paso(cantidad, reglas.paso_cantidad)

    if cantidad < reglas.cantidad_minima or cantidad <= 0:
        return Tamano(
            False, 0.0, 0.0, riesgo_dinero, 0.0,
            f"la cantidad calculada ({cantidad}) queda por debajo del minimo "
            f"del par ({reglas.cantidad_minima})",
            recortado, avisos,
        )

    valor_compra = cantidad * precio_entrada

    # --- Limite 3: la compra minima ---------------------------------------
    if valor_compra < reglas.compra_minima:
        return Tamano(
            False, 0.0, 0.0, riesgo_dinero, 0.0,
            f"la compra ({valor_compra:.2f} USDT) queda por debajo del minimo "
            f"de Binance ({reglas.compra_minima} USDT). NO se agranda para "
            f"llegar: eso romperia el limite de riesgo",
            recortado, avisos,
        )

    # Riesgo que de verdad se corre, ya con todos los recortes aplicados.
    perdida_real = cantidad * costo_por_unidad
    riesgo_real_pct = perdida_real / capital * 100.0

    if riesgo_real_pct > riesgo_pct + 1e-9:
        return Tamano(
            False, 0.0, 0.0, riesgo_dinero, riesgo_real_pct,
            f"el calculo dio un riesgo real de {riesgo_real_pct:.3f}%, por encima "
            f"del {riesgo_pct}% autorizado. Se rechaza por seguridad",
            recortado, avisos,
        )

    if recortado:
        avisos.append(
            f"riesgo real {riesgo_real_pct:.3f}% en vez del {riesgo_pct}% "
            "configurado (por debajo, no por encima)"
        )

    return Tamano(
        aprobado=True,
        cantidad=cantidad,
        valor_compra=valor_compra,
        riesgo_dinero=riesgo_dinero,
        riesgo_real_pct=riesgo_real_pct,
        motivo=(
            f"comprar {cantidad} por {valor_compra:.2f} USDT; "
            f"perdida maxima {perdida_real:.2f} USDT ({riesgo_real_pct:.3f}% del capital)"
        ),
        recortado_por_capital=recortado,
        avisos=avisos,
    )
