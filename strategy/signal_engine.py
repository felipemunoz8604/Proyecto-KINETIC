"""
Motor de senal: mira una vela y dice si hay ruptura.

LO QUE ESTE ARCHIVO NO HACE, Y ES A PROPOSITO
---------------------------------------------
No sabe cuanto capital hay. No sabe cuanto se arriesga. No sabe si ya hay
tres posiciones abiertas ni si hoy se perdio el limite diario. No decide si
se opera.

Solo dice "aca hay una ruptura con estas caracteristicas" o "aca no hay
nada". Quien decide si eso se ejecuta, y con que tamano, es el Risk Manager
(carpeta risk/), que es el portero. Es la Regla 3 del MEGAPROMPT y es la
separacion que hace que se pueda cambiar la estrategia sin tocar el riesgo,
y al reves.

LAS CUATRO CONDICIONES (seccion 7 del MEGAPROMPT)
--------------------------------------------------
1. Regimen apto            -> lo resuelve regime_filter.py
2. Hubo consolidacion      -> volatilidad de las ultimas N velas por debajo
                              de un umbral
3. Ruptura con volumen     -> el CIERRE (no la mecha) supera el techo del
                              rango, Y el volumen supera 200% del promedio
4. Direccion               -> EMA rapida por encima de la lenta

Las cuatro tienen que darse. Si falla una, la senal es ESPERAR y queda
registrado cual fallo -- eso importa despues, cuando haya que entender por
que el bot no opero en un dia que "obviamente" habia una ruptura.

SOLO LARGOS
-----------
Esto es Binance SPOT sin apalancamiento: se compra y despues se vende lo
comprado. No se puede ganar con la bajada. Por eso el motor solo emite
COMPRAR. VENDER existe en el enum porque el MEGAPROMPT lo nombra y porque
una version futura podria cerrar por senal, pero en la v1 la salida la
maneja el stop (risk/stop_manager.py), no este archivo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from strategy import regime_filter


class TipoSenal(str, Enum):
    COMPRAR = "COMPRAR"
    ESPERAR = "ESPERAR"
    VENDER = "VENDER"  # reservado: la salida v1 la maneja el stop


@dataclass(frozen=True)
class Senal:
    """
    Lo que el motor concluyo sobre una vela.

    `motivos` lista TODAS las condiciones evaluadas, cumplidas o no. Sirve
    para el diario de operaciones y para contestar la pregunta mas comun
    cuando algo no opera: "por que no entro aca".
    """

    tipo: TipoSenal
    momento: pd.Timestamp
    precio: float
    motivos: list[str] = field(default_factory=list)
    fallo_en: str | None = None
    datos: dict = field(default_factory=dict)

    @property
    def hay_entrada(self) -> bool:
        return self.tipo is TipoSenal.COMPRAR


def _esperar(momento, precio, motivos, fallo_en, datos) -> Senal:
    return Senal(
        tipo=TipoSenal.ESPERAR,
        momento=momento,
        precio=precio,
        motivos=motivos,
        fallo_en=fallo_en,
        datos=datos,
    )


def evaluar_vela(fila: pd.Series, cfg: dict) -> Senal:
    """
    Evalua UNA vela ya cerrada, con sus indicadores ya calculados.

    `fila` tiene que venir de un DataFrame pasado por
    `indicators.agregar_indicadores()`.
    """
    est = cfg["estrategia"]
    momento = fila.name
    precio = float(fila["close"])
    motivos: list[str] = []
    datos: dict = {}

    # --- 0. Calentamiento -------------------------------------------------
    necesarias = ("techo", "vol_promedio", "ema_rapida", "ema_lenta", "desv_pct", "atr")
    faltantes = [c for c in necesarias if c not in fila or pd.isna(fila[c])]
    if faltantes:
        return _esperar(
            momento, precio,
            [f"indicadores sin calentar: {', '.join(faltantes)}"],
            "calentamiento", datos,
        )

    # --- 1. Regimen -------------------------------------------------------
    regimen = regime_filter.evaluar(fila, est["regimen"])
    motivos.append(regimen.motivo)
    datos["regimen_valor"] = regimen.valor
    if not regimen.apto:
        return _esperar(momento, precio, motivos, "regimen", datos)

    # --- 2. Consolidacion previa -----------------------------------------
    umbral_cons = est["consolidacion"]["umbral_atr_pct"]
    if umbral_cons is None:
        raise ValueError(
            "estrategia.consolidacion.umbral_atr_pct esta sin definir en "
            "config.yaml. Es un pendiente de la Fase 1: lo decide el backtest."
        )
    desviacion = float(fila["desv_pct"])
    datos["desv_pct"] = desviacion
    if desviacion > umbral_cons:
        motivos.append(
            f"no hubo consolidacion: desviacion {desviacion:.2f}% > {umbral_cons}%"
        )
        return _esperar(momento, precio, motivos, "consolidacion", datos)
    motivos.append(f"consolidacion previa: desviacion {desviacion:.2f}% <= {umbral_cons}%")

    # --- 3. Ruptura por CIERRE, no por mecha ------------------------------
    techo = float(fila["techo"])
    datos["techo"] = techo
    if precio <= techo:
        motivos.append(f"el cierre {precio:.2f} no supero el techo {techo:.2f}")
        return _esperar(momento, precio, motivos, "ruptura", datos)
    motivos.append(f"ruptura: cierre {precio:.2f} > techo {techo:.2f}")

    # --- 3b. Volumen que confirme -----------------------------------------
    multiplicador = est["volumen"]["multiplicador_minimo"]
    promedio = float(fila["vol_promedio"])
    volumen = float(fila["volume"])
    datos["volumen"] = volumen
    datos["vol_promedio"] = promedio
    if promedio <= 0 or volumen < multiplicador * promedio:
        veces = volumen / promedio if promedio > 0 else 0.0
        motivos.append(
            f"volumen flojo: {veces:.2f}x el promedio, hace falta {multiplicador}x"
        )
        return _esperar(momento, precio, motivos, "volumen", datos)
    motivos.append(f"volumen {volumen / promedio:.2f}x el promedio (minimo {multiplicador}x)")

    # --- 4. Direccion -----------------------------------------------------
    rapida, lenta = float(fila["ema_rapida"]), float(fila["ema_lenta"])
    datos["ema_rapida"] = rapida
    datos["ema_lenta"] = lenta
    if rapida <= lenta:
        motivos.append(f"EMA rapida {rapida:.2f} no supera a la lenta {lenta:.2f}")
        return _esperar(momento, precio, motivos, "direccion", datos)
    motivos.append(f"EMA rapida {rapida:.2f} > lenta {lenta:.2f}")

    datos["atr"] = float(fila["atr"])
    return Senal(
        tipo=TipoSenal.COMPRAR,
        momento=momento,
        precio=precio,
        motivos=motivos,
        fallo_en=None,
        datos=datos,
    )


def evaluar_serie(df: pd.DataFrame, cfg: dict) -> list[Senal]:
    """
    Recorre un DataFrame entero vela por vela.

    Se usa en el backtest. En vivo se llama `evaluar_vela` con la ultima
    vela cerrada, que es exactamente el mismo codigo -- y esa es la idea:
    que el backtest y el bot en vivo no puedan divergir.
    """
    return [evaluar_vela(fila, cfg) for _, fila in df.iterrows()]


def resumen_de_rechazos(senales: list[Senal]) -> dict[str, int]:
    """
    Cuenta en que condicion se cayo cada senal.

    Es el diagnostico mas util del backtest: si el 99% se cae en 'regimen',
    el filtro esta demasiado apretado y no es que la estrategia no sirva.
    """
    conteo: dict[str, int] = {}
    for senal in senales:
        clave = senal.fallo_en or "ENTRADA"
        conteo[clave] = conteo.get(clave, 0) + 1
    return conteo
