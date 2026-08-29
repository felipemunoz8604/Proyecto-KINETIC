"""
Guardia de cartera: el filtro macro, y el filtro de correlacion.

DOS TRABAJOS
------------

1. NO COMPRAR RUPTURAS DENTRO DE UNA CAIDA GENERAL.
   Una ruptura al alza en medio de un mercado que se desploma casi siempre
   es un rebote que dura poco. El filtro: si el precio esta demasiado por
   debajo de su SMA(200), no se abre nada, por linda que sea la senal.

2. NO TOMAR LA MISMA APUESTA DOS VECES.
   Esto viene directo de TITAN. El 19 de agosto de 2026, TITAN tenia un
   SELL en EURUSD y un SELL en GOLD al mismo tiempo -- que no eran dos
   apuestas, era una sola apuesta al dolar tomada dos veces. Las dos
   pegaron en su stop con 118 segundos de diferencia, y la perdida fue el
   doble de la presupuestada.

   En cripto el problema es peor, no mejor: casi todo se mueve con Bitcoin.
   Comprar BTC y ETH a la vez no es diversificar, es duplicar la apuesta.
   Por eso hay un grupo de correlacion: dos pares del mismo grupo no pueden
   estar abiertos a la vez.

   Que TITAN haya descubierto esto operando y KINETIC lo tenga desde el
   primer dia es la unica ventaja de haber cometido el error una vez.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


# Que pares compiten por el mismo riesgo. Todo lo grande de cripto se mueve
# con Bitcoin, asi que por defecto BTC y ETH son el mismo grupo.
GRUPOS_POR_DEFECTO: dict[str, str] = {
    "BTCUSDT": "cripto_grande",
    "ETHUSDT": "cripto_grande",
    "BNBUSDT": "cripto_grande",
    "SOLUSDT": "cripto_grande",
    "XRPUSDT": "cripto_grande",
}


@dataclass
class Veredicto:
    permitido: bool
    motivo: str
    filtro: str | None = None


@dataclass
class GuardiaDeCartera:
    """Decide si una senal aprobada puede convivir con lo que ya esta abierto."""

    distancia_maxima_bajo_sma_pct: float | None = None
    grupos: dict[str, str] = field(default_factory=lambda: dict(GRUPOS_POR_DEFECTO))
    una_posicion_por_grupo: bool = True

    # -- Filtro macro ------------------------------------------------------

    def revisar_macro(self, precio: float, sma_macro: float | None) -> Veredicto:
        """
        El precio esta demasiado hundido respecto de su media larga.

        Un precio POR ENCIMA de la SMA200 nunca se veta: ahi el filtro no
        tiene nada que decir.
        """
        if self.distancia_maxima_bajo_sma_pct is None:
            raise ValueError(
                "estrategia.portfolio_guard.distancia_maxima_bajo_sma_pct esta "
                "sin definir en config.yaml. Es un pendiente de la Fase 1."
            )
        if sma_macro is None or pd.isna(sma_macro) or sma_macro <= 0:
            return Veredicto(
                False,
                "la SMA larga todavia no tiene valor (faltan velas)",
                "macro_sin_datos",
            )

        distancia = (precio / sma_macro - 1.0) * 100.0
        if distancia >= 0:
            return Veredicto(True, f"el precio esta {distancia:+.2f}% sobre su media larga")

        if distancia < -abs(self.distancia_maxima_bajo_sma_pct):
            return Veredicto(
                False,
                f"el precio esta {distancia:.2f}% por debajo de su media larga "
                f"(maximo tolerado: -{abs(self.distancia_maxima_bajo_sma_pct)}%). "
                "Comprar rupturas dentro de una caida general es comprar rebotes.",
                "macro",
            )
        return Veredicto(True, f"el precio esta {distancia:+.2f}% de su media larga")

    # -- Filtro de correlacion ---------------------------------------------

    def grupo_de(self, par: str) -> str:
        """El grupo de riesgo del par. Si no esta mapeado, es su propio grupo."""
        return self.grupos.get(par, par)

    def revisar_correlacion(self, par: str, pares_abiertos: list[str]) -> Veredicto:
        """No abrir un par que apuesta a lo mismo que otro ya abierto."""
        if not self.una_posicion_por_grupo or not pares_abiertos:
            return Veredicto(True, "sin conflicto de correlacion")

        grupo = self.grupo_de(par)
        chocan = [p for p in pares_abiertos if self.grupo_de(p) == grupo]
        if chocan:
            return Veredicto(
                False,
                f"{par} pertenece al grupo '{grupo}', y ya hay una posicion "
                f"abierta en {', '.join(chocan)}. Abrir las dos no es "
                "diversificar: es la misma apuesta tomada dos veces.",
                "correlacion",
            )
        return Veredicto(True, f"ningun conflicto: grupo '{grupo}' esta libre")

    # -- Las dos juntas ----------------------------------------------------

    def revisar(
        self,
        par: str,
        precio: float,
        sma_macro: float | None,
        pares_abiertos: list[str] | None = None,
    ) -> Veredicto:
        macro = self.revisar_macro(precio, sma_macro)
        if not macro.permitido:
            return macro
        return self.revisar_correlacion(par, pares_abiertos or [])

    @classmethod
    def desde_config(cls, cfg: dict) -> "GuardiaDeCartera":
        guard = cfg["estrategia"]["portfolio_guard"]
        return cls(
            distancia_maxima_bajo_sma_pct=guard.get("distancia_maxima_bajo_sma_pct"),
            una_posicion_por_grupo=guard.get("una_posicion_por_grupo", True),
        )
