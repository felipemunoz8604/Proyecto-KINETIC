r"""
Motor de cartera -- simula una cartera que persigue una exposicion objetivo.

EN QUE SE DIFERENCIA DEL MOTOR DE LA FASE 1
---------------------------------------------
El de la Fase 1 piensa en operaciones: hay una señal, se entra, hay un stop,
se sale. Sirve para rupturas y no sirve para nada de la Fase 2.

Este piensa en **exposicion**. Cada dia recibe "quiero tener esta fraccion del
patrimonio en cada activo" y compra o vende lo que haga falta para llegar. La
compuerta, el escalar de volatilidad y los pesos ya vienen resueltos desde
`risk/`; aca solo se ejecuta y se cobra.

LA REGLA DE ORO: LO DE HOY SE DECIDE CON LO DE AYER
-----------------------------------------------------
`exposiciones.loc[t]` se ejecuta a la **apertura del dia t**, y quien la
calculo solo puede haber mirado hasta el cierre de t-1. El motor no puede
verificar eso por si mismo -- lo verifica la prueba de cada estrategia -- pero
si garantiza la otra mitad: nunca usa el cierre del dia t para decidir nada
del dia t, solo para valuar la cartera al final.

EL SLIPPAGE SE COBRA COMO COMISION, NO COMO PRECIO
----------------------------------------------------
Se ejecuta al precio de apertura y el slippage se cobra aparte, sobre el
nocional movido. Es equivalente en plata a ejecutar peor, y tiene una ventaja:
el costo total queda contado en un solo lugar. El criterio 6 pide "costo total
pagado" y con esta forma es exacto, no una estimacion.

LOS DESLISTADOS SE LIQUIDAN CON PENALIZACION
----------------------------------------------
Si un simbolo que se tiene en cartera deja de tener precio, se vende al ultimo
precio conocido **menos una penalizacion**. Vender al ultimo precio a secas
seria suponer que se alcanzo a salir en el ultimo minuto antes de que cerrara
el mercado, y eso casi nunca pasa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from execution.costos import ModeloDeCostos
from execution.filtros import FiltroSimbolo, TablaDeFiltros, ajustar_orden

# Base de la especificacion. El 50% se corre como sensibilidad.
PENALIZACION_DESLISTADO_PCT = 20.0

# Si no se dice el rango de liquidez, se cobra el peor tramo. Suponer que todo
# es tan liquido como BTC seria regalarse el slippage.
RANGO_POR_DEFECTO = 20


@dataclass
class ResultadoCartera:
    """Todo lo que hace falta para calcular las metricas obligatorias."""

    patrimonio: pd.Series
    efectivo: pd.Series
    costos: pd.Series          # USDT pagados cada dia
    negociado: pd.Series       # nocional movido cada dia, en USDT
    financiacion: pd.Series    # cobrado (+) o pagado (-) por financiacion
    exposicion: pd.DataFrame   # la que quedo de verdad, al cierre
    deslistados: list[dict] = field(default_factory=list)
    ordenes_rechazadas: int = 0

    @property
    def costo_total(self) -> float:
        """
        Comisiones y slippage. La financiacion va aparte porque puede ser un
        INGRESO: sumarla al costo daria un costo negativo sin sentido.
        """
        return float(self.costos.sum())

    @property
    def financiacion_total(self) -> float:
        return float(self.financiacion.sum())

    @property
    def rotacion_anual(self) -> float:
        """Nocional movido en un año, como multiplo del patrimonio medio."""
        anios = len(self.patrimonio) / 365.0
        medio = float(self.patrimonio.mean())
        if anios <= 0 or medio <= 0:
            return float("nan")
        return float(self.negociado.sum() / medio / anios)

    @property
    def costo_anual_pct(self) -> float:
        """Costo total como % del patrimonio medio, por año. Criterio 6."""
        anios = len(self.patrimonio) / 365.0
        medio = float(self.patrimonio.mean())
        if anios <= 0 or medio <= 0:
            return float("nan")
        return float(self.costo_total / medio / anios * 100.0)

    @property
    def tiempo_en_mercado_pct(self) -> float:
        return float((self.exposicion.abs().sum(axis=1) > 1e-9).mean() * 100.0)


def _rango_de(rangos, simbolo: str, fecha: pd.Timestamp) -> int:
    if rangos is None:
        return RANGO_POR_DEFECTO
    if isinstance(rangos, dict):
        return int(rangos.get(simbolo, RANGO_POR_DEFECTO))
    if simbolo not in rangos.columns or fecha not in rangos.index:
        return RANGO_POR_DEFECTO
    valor = rangos.at[fecha, simbolo]
    return RANGO_POR_DEFECTO if not np.isfinite(valor) else int(valor)


def simular(
    aperturas: pd.DataFrame,
    cierres: pd.DataFrame,
    exposiciones: pd.DataFrame,
    capital_inicial: float,
    modelo: ModeloDeCostos,
    *,
    rangos=None,
    filtros: TablaDeFiltros | None = None,
    penalizacion_deslistado_pct: float = PENALIZACION_DESLISTADO_PCT,
    permitir_cortos: bool = False,
    financiacion_de_cortos: dict | None = None,
) -> ResultadoCartera:
    """
    Corre la simulacion dia por dia.

    `exposiciones` son fracciones del patrimonio, una columna por simbolo. La
    suma de una fila es la exposicion bruta y no deberia pasar de 1: si pasa,
    es apalancamiento y el motor levanta, porque `k_max = 1,0` es tope duro.
    """
    if capital_inicial <= 0:
        raise ValueError("el capital inicial tiene que ser positivo")
    dias = exposiciones.index
    if not dias.is_monotonic_increasing:
        raise ValueError("las exposiciones tienen que venir ordenadas")
    # BRUTA = suma de VALORES ABSOLUTOS. Con posiciones cortas, sumar con
    # signo dejaria pasar +3 y -3 como si fuera exposicion cero, que es
    # apalancamiento 6 a 1 disfrazado de neutralidad.
    bruta = exposiciones.abs().sum(axis=1)
    if (bruta > 1.0 + 1e-9).any():
        peor = bruta.idxmax()
        raise ValueError(
            f"exposicion bruta {bruta.max():.3f} el {peor.date()}: eso es "
            "apalancamiento, y k_max = 1,0 es tope duro (MEGAPROMPT regla 7)"
        )

    simbolos = list(exposiciones.columns)
    ultimo_precio = cierres[simbolos].ffill()

    cantidades = {s: 0.0 for s in simbolos}
    efectivo = float(capital_inicial)

    patrimonio_diario: list[float] = []
    efectivo_diario: list[float] = []
    costos_diarios: list[float] = []
    negociado_diario: list[float] = []
    exposicion_real: list[dict[str, float]] = []
    deslistados: list[dict] = []
    financiacion_diaria: list[float] = []
    rechazadas = 0

    for fecha in dias:
        costo_hoy = 0.0
        movido_hoy = 0.0

        # Solo importan los que se tienen y los que se quieren. Con un universo
        # de 116 columnas y 5 posiciones, recorrerlas todas multiplicaba por
        # veinte el tiempo de una corrida sin cambiar un solo numero.
        objetivo = exposiciones.loc[fecha]
        en_juego = sorted({s for s in simbolos
                           if cantidades[s] != 0.0
                           or abs(float(objetivo.get(s, 0.0))) > 0.0})

        # --- 1. Los que murieron se liquidan antes de hacer nada -----------
        for s in en_juego:
            if cantidades[s] == 0.0:
                continue
            precio_cierre = cierres.at[fecha, s] if s in cierres.columns else np.nan
            if np.isfinite(precio_cierre):
                continue
            ultimo = ultimo_precio.at[fecha, s] if fecha in ultimo_precio.index else np.nan
            if not np.isfinite(ultimo):
                continue
            # La penalizacion siempre juega EN CONTRA: si estabas largo
            # recuperas menos, y si estabas corto recomprar te sale mas caro.
            signo = 1.0 if cantidades[s] > 0 else -1.0
            precio_salida = ultimo * (1.0 - signo * penalizacion_deslistado_pct / 100.0)
            nocional = cantidades[s] * precio_salida
            costo = modelo.costo_de_lado(abs(nocional), _rango_de(rangos, s, fecha))
            efectivo += nocional - costo
            costo_hoy += costo
            movido_hoy += abs(nocional)
            deslistados.append({"simbolo": s, "fecha": fecha,
                                "ultimo_precio": float(ultimo),
                                "recuperado": float(nocional - costo)})
            cantidades[s] = 0.0

        # --- 2. Rebalanceo a la apertura -----------------------------------
        precios_apertura = {s: aperturas.at[fecha, s]
                            if s in aperturas.columns else np.nan
                            for s in en_juego}
        patrimonio_apertura = efectivo + sum(
            cantidades[s] * precios_apertura[s]
            for s in en_juego if np.isfinite(precios_apertura[s]))

        for s in en_juego:
            precio = precios_apertura[s]
            if not np.isfinite(precio) or precio <= 0:
                continue
            # Si no hay cierre hoy, el simbolo esta muerto: no se compra algo
            # que no se va a poder valuar a fin del dia. Sin esto, un
            # deslistado con apertura pero sin cierre se recompra y se
            # reliquida todos los dias, pagando penalizacion cada vez.
            if s not in cierres.columns or not np.isfinite(cierres.at[fecha, s]):
                continue
            deseado = float(objetivo.get(s, 0.0)) * patrimonio_apertura
            actual = cantidades[s] * precio
            delta = deseado - actual
            if abs(delta) < 1e-12:
                continue

            rango = _rango_de(rangos, s, fecha)
            peaje = modelo.peaje_por_lado_pct(rango) / 100.0
            filtro = filtros.de(s) if filtros is not None else FiltroSimbolo.generico()
            if delta > 0 and cantidades[s] >= 0 and not permitir_cortos:
                # El costo tambien se paga con efectivo. Con exposicion 1,0 no
                # se puede comprar el 100% del patrimonio: hay que dejar con
                # que pagar el peaje. Se compra un poco menos, no se rechaza.
                delta = min(delta, efectivo / (1.0 + peaje))
            orden = ajustar_orden(abs(delta), precio, filtro)
            if not permitir_cortos and delta < 0:
                # Sin cortos no se puede vender mas de lo que se tiene.
                cantidad = min(filtro.ajustar_cantidad(-delta / precio),
                               cantidades[s])
                orden = ajustar_orden(cantidad * precio, precio, filtro)
            if not orden:
                rechazadas += 1
                continue

            costo = modelo.costo_de_lado(orden.nocional, rango)
            if delta > 0:
                if not permitir_cortos and orden.nocional + costo > efectivo + 1e-9:
                    rechazadas += 1
                    continue
                cantidades[s] += orden.cantidad
                efectivo -= orden.nocional + costo
            else:
                cantidades[s] -= orden.cantidad
                efectivo += orden.nocional - costo
            costo_hoy += costo
            movido_hoy += orden.nocional

        # --- 3. Financiacion de la pata corta ------------------------------
        #
        # Solo sobre las posiciones CORTAS, porque son las que estan en
        # perpetuo: en E2 la pata larga se ejecuta en Spot, que no paga
        # financiacion. Por eso el parametro se llama `financiacion_de_cortos`
        # y no `financiacion` a secas -- cobrarsela tambien a la pata larga
        # seria cobrar dos veces por el mismo dia.
        flujo_hoy = 0.0
        if financiacion_de_cortos:
            manana = fecha + pd.Timedelta(days=1)
            for s in en_juego:
                if cantidades[s] >= 0 or s not in financiacion_de_cortos:
                    continue
                precio = cierres.at[fecha, s] if s in cierres.columns else np.nan
                if not np.isfinite(precio):
                    continue
                tasas = financiacion_de_cortos[s]
                delta_dia = tasas.loc[(tasas.index >= fecha)
                                      & (tasas.index < manana)]
                if delta_dia.empty:
                    continue
                # Tasa positiva => los largos pagan a los cortos, asi que un
                # nocional negativo COBRA. El signo sale solo.
                nocional = cantidades[s] * precio
                flujo_hoy += float(-nocional * delta_dia.sum())
        efectivo += flujo_hoy

        # --- 4. Valuacion al cierre ----------------------------------------
        valores = {}
        for s in (s for s in en_juego if cantidades[s] != 0.0):
            precio = cierres.at[fecha, s] if s in cierres.columns else np.nan
            if not np.isfinite(precio):
                precio = ultimo_precio.at[fecha, s] if fecha in ultimo_precio.index else np.nan
            valores[s] = cantidades[s] * precio if np.isfinite(precio) else 0.0
        patrimonio = efectivo + sum(valores.values())

        patrimonio_diario.append(patrimonio)
        efectivo_diario.append(efectivo)
        costos_diarios.append(costo_hoy)
        negociado_diario.append(movido_hoy)
        financiacion_diaria.append(flujo_hoy)
        exposicion_real.append({s: (v / patrimonio if patrimonio > 0 else 0.0)
                                for s, v in valores.items()})

    return ResultadoCartera(
        patrimonio=pd.Series(patrimonio_diario, index=dias, name="patrimonio"),
        efectivo=pd.Series(efectivo_diario, index=dias, name="efectivo"),
        costos=pd.Series(costos_diarios, index=dias, name="costos"),
        negociado=pd.Series(negociado_diario, index=dias, name="negociado"),
        financiacion=pd.Series(financiacion_diaria, index=dias,
                               name="financiacion"),
        # Un simbolo sin posicion ese dia no aparece en el diccionario del dia:
        # eso es exposicion CERO, no dato faltante.
        exposicion=pd.DataFrame(exposicion_real, index=dias)
        .reindex(columns=simbolos).fillna(0.0),
        deslistados=deslistados,
        ordenes_rechazadas=rechazadas,
    )
