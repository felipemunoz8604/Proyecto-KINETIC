"""
Motor de backtest: recorrer nueve anios vela por vela y contar la verdad.

LA REGLA DE ORO: EL MISMO CODIGO QUE EN VIVO
---------------------------------------------
Este motor no reimplementa la estrategia ni el riesgo. Llama a
`signal_engine.evaluar_vela()` y a los modulos de `risk/`, exactamente los
mismos que usaria el bot en produccion. Si el backtest y el bot en vivo
tuvieran cada uno su copia de las reglas, divergirian, y el backtest dejaria
de decir algo sobre el bot.

LAS CUATRO FORMAS EN QUE UN BACKTEST SE REGALA PLATA
-----------------------------------------------------
Las cuatro estan tapadas aca, y cada una tiene su prueba:

1. COMPRAR AL CIERRE DE LA VELA DE SENAL.
   Imposible: solo sabes cual fue el cierre cuando la vela ya cerro. Aca se
   entra a la APERTURA DE LA VELA SIGUIENTE. (Medido: en cripto ese salto es
   de mediana 0,0000%, asi que casi no cuesta -- pero se hace igual, porque
   lo correcto no depende de que sea barato.)

2. SUPONER QUE EL STOP SIEMPRE SE EJECUTA EN SU PRECIO.
   Si la vela ABRE por debajo del stop, la orden se ejecuta a la apertura,
   que es peor. Aca el precio de salida es `min(stop, apertura)`.

3. IGNORAR LOS COSTOS.
   Comision 0,1% por lado mas slippage, en la entrada Y en la salida.

4. OPERAR SOBRE DATOS QUE NO SIGNIFICAN NADA.
   Las primeras semanas de un par recien listado tienen precios de libro
   vacio. Se descartan.

ORDEN DE LOS EVENTOS DENTRO DE UNA VELA
----------------------------------------
Importa, y es esto:

  1. Si habia una entrada pendiente, se abre a la apertura de ESTA vela.
  2. Si hay posicion abierta, se revisa el stop contra el MINIMO de la vela.
     (Una posicion puede abrirse y morir en la misma vela. Pasa.)
  3. Si sigue viva, se mueve el trailing con el CIERRE de esta vela.
  4. Se evalua la senal de esta vela, que -- si hay -- se ejecuta en la
     siguiente.

Nunca se usa el cierre de la vela para decidir algo que ocurre dentro de la
vela: eso seria mirar al futuro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

import pandas as pd

from risk import portfolio_guard, position_sizing, risk_limits, stop_manager
from strategy import signal_engine


@dataclass
class Operacion:
    """Una operacion cerrada, con todo lo necesario para auditarla."""

    par: str
    temporalidad: str
    entrada_momento: pd.Timestamp
    entrada_precio: float
    salida_momento: pd.Timestamp
    salida_precio: float
    cantidad: float
    motivo_salida: str
    stop_inicial: float
    stop_final: float
    velas_abierta: int
    riesgo_pct_planeado: float
    costos: float
    resultado_bruto: float
    resultado_neto: float
    capital_antes: float

    @property
    def gano(self) -> bool:
        return self.resultado_neto > 0

    @property
    def retorno_pct(self) -> float:
        return self.resultado_neto / self.capital_antes * 100.0


@dataclass
class Metricas:
    """El resumen. Todo NETO de comisiones y slippage."""

    operaciones: int = 0
    ganadoras: int = 0
    perdedoras: int = 0
    capital_inicial: float = 0.0
    capital_final: float = 0.0
    ganancia_bruta: float = 0.0
    perdida_bruta: float = 0.0
    costos_totales: float = 0.0
    max_drawdown_pct: float = 0.0
    mejor: float = 0.0
    peor: float = 0.0
    desde: pd.Timestamp | None = None
    hasta: pd.Timestamp | None = None
    rechazos: dict[str, int] = field(default_factory=dict)

    @property
    def profit_factor(self) -> float:
        """Cuanto se gana por cada peso que se pierde. Por debajo de 1 se pierde."""
        if self.perdida_bruta == 0:
            return float("inf") if self.ganancia_bruta > 0 else 0.0
        return self.ganancia_bruta / self.perdida_bruta

    @property
    def tasa_acierto_pct(self) -> float:
        return self.ganadoras / self.operaciones * 100.0 if self.operaciones else 0.0

    @property
    def retorno_total_pct(self) -> float:
        if self.capital_inicial == 0:
            return 0.0
        return (self.capital_final / self.capital_inicial - 1) * 100.0

    @property
    def resultado_neto(self) -> float:
        return self.capital_final - self.capital_inicial

    @property
    def esperanza_por_operacion(self) -> float:
        return self.resultado_neto / self.operaciones if self.operaciones else 0.0

    def informe(self) -> str:
        if self.operaciones == 0:
            detalle = "\n".join(
                f"      {k:<16} {v:>7,}" for k, v in sorted(
                    self.rechazos.items(), key=lambda kv: -kv[1]
                )
            )
            return (
                "  Sin operaciones en el periodo.\n"
                "  Donde se cayeron las velas:\n" + detalle
            )

        pf = self.profit_factor
        pf_txt = "inf" if pf == float("inf") else f"{pf:.3f}"
        return "\n".join([
            f"  Periodo:          {self.desde}  ->  {self.hasta}",
            f"  Operaciones:      {self.operaciones:,}"
            f"  ({self.ganadoras} ganadas / {self.perdedoras} perdidas"
            f" = {self.tasa_acierto_pct:.1f}% de acierto)",
            f"  Profit factor:    {pf_txt}",
            f"  Capital:          {self.capital_inicial:,.2f} -> {self.capital_final:,.2f} USDT"
            f"  ({self.retorno_total_pct:+.2f}%)",
            f"  Resultado neto:   {self.resultado_neto:+,.2f} USDT",
            f"  Costos pagados:   {self.costos_totales:,.2f} USDT",
            f"  Max drawdown:     {self.max_drawdown_pct:.2f}%",
            f"  Por operacion:    {self.esperanza_por_operacion:+.3f} USDT"
            f"   (mejor {self.mejor:+.2f} / peor {self.peor:+.2f})",
        ])


@dataclass
class Resultado:
    metricas: Metricas
    operaciones: list[Operacion]
    curva_capital: pd.Series


# ---------------------------------------------------------------------------

def _recortar_inicio(df: pd.DataFrame, dias: int) -> pd.DataFrame:
    """Descarta los primeros dias de cotizacion (libro vacio, precios falsos)."""
    if df.empty or dias <= 0:
        return df
    corte = df.index[0] + timedelta(days=dias)
    return df[df.index >= corte]


def _drawdown_maximo_pct(curva: pd.Series) -> float:
    """La peor caida desde un pico, en %. Es lo que hay que aguantar sentado."""
    if curva.empty:
        return 0.0
    pico = curva.cummax()
    return float(((pico - curva) / pico * 100.0).max())


def correr(
    df: pd.DataFrame,
    cfg: dict,
    par: str,
    temporalidad: str,
    reglas_simbolo: position_sizing.ReglasSimbolo | None = None,
    rapido: bool = True,
) -> Resultado:
    """
    Recorre el DataFrame y devuelve el resultado neto.

    `df` tiene que venir con los indicadores ya calculados
    (`indicators.agregar_indicadores`).
    """
    motor = cfg.get("backtest_motor", {})
    df = _recortar_inicio(df, motor.get("descartar_dias_iniciales", 0))
    if df.empty:
        return Resultado(Metricas(), [], pd.Series(dtype=float))

    capital_inicial = float(cfg["capital"]["monto"])
    riesgo_pct = float(cfg["riesgo"]["por_operacion_pct"])
    comision = float(cfg["costos"]["comision_por_lado_pct"]) / 100.0
    slippage = float(cfg["costos"]["slippage_pct_por_lado"]) / 100.0
    mult_atr = float(cfg["stops"]["atr_multiplicador_sl"])
    mult_trailing = float(cfg["stops"].get("trailing_atr_multiplicador", mult_atr))
    compuesto = bool(motor.get("capital_compuesto", True))
    reglas_simbolo = reglas_simbolo or position_sizing.ReglasSimbolo()

    control = risk_limits.ControlDeRiesgo.desde_config(cfg)
    control.capital = capital_inicial
    guardia = portfolio_guard.GuardiaDeCartera.desde_config(cfg)
    usar_guardia = guardia.distancia_maxima_bajo_sma_pct is not None

    capital = capital_inicial
    operaciones: list[Operacion] = []
    rechazos: dict[str, int] = {}
    curva: list[float] = []
    momentos: list[pd.Timestamp] = []

    # Se precalcula la senal de todas las velas de una sola vez. El camino
    # lento (evaluar_vela) sigue disponible y es el de referencia; una
    # prueba exige que los dos coincidan.
    if rapido:
        mascara = signal_engine.mascara_de_senales(df, cfg)
        atr_col = df["atr"]
    posicion: dict | None = None
    entrada_pendiente: dict | None = None

    for indice, (momento, fila) in enumerate(df.iterrows()):
        # --- 1. Abrir lo que quedo pendiente de la vela anterior ----------
        if entrada_pendiente is not None and posicion is None:
            precio_bruto = float(fila["open"])
            precio_entrada = precio_bruto * (1 + slippage)
            atr_entrada = entrada_pendiente["atr"]

            try:
                estado_stop = stop_manager.abrir(
                    precio_entrada, atr_entrada, mult_atr, mult_trailing
                )
            except ValueError:
                estado_stop = None

            if estado_stop is not None:
                base = capital if compuesto else capital_inicial
                control.capital = base
                tamano = position_sizing.calcular(
                    capital=base,
                    riesgo_pct=riesgo_pct,
                    precio_entrada=precio_entrada,
                    precio_stop=estado_stop.stop_actual,
                    reglas=reglas_simbolo,
                    comision_pct=comision * 100.0,
                    capital_disponible=capital,
                )
                if tamano.aprobado:
                    costo_entrada = tamano.valor_compra * comision
                    posicion = {
                        "momento": momento,
                        "precio": precio_entrada,
                        "cantidad": tamano.cantidad,
                        "stop": estado_stop,
                        "costos": costo_entrada,
                        "velas": 0,
                        "capital_antes": capital,
                        "riesgo_pct": tamano.riesgo_real_pct,
                    }
                else:
                    rechazos["tamano_rechazado"] = rechazos.get("tamano_rechazado", 0) + 1
            entrada_pendiente = None

        # --- 2. El stop, contra el MINIMO de la vela ----------------------
        if posicion is not None:
            estado = posicion["stop"]
            if stop_manager.toco_el_stop(estado, float(fila["low"])):
                # Si la vela ABRE por debajo del stop, se ejecuta ahi, peor.
                precio_bruto = min(estado.stop_actual, float(fila["open"]))
                precio_salida = precio_bruto * (1 - slippage)
                valor_salida = precio_salida * posicion["cantidad"]
                costo_salida = valor_salida * comision
                costos = posicion["costos"] + costo_salida

                bruto = (precio_salida - posicion["precio"]) * posicion["cantidad"]
                neto = bruto - costos
                capital += neto
                control.registrar_cierre(neto, momento)

                operaciones.append(
                    Operacion(
                        par=par, temporalidad=temporalidad,
                        entrada_momento=posicion["momento"],
                        entrada_precio=posicion["precio"],
                        salida_momento=momento,
                        salida_precio=precio_salida,
                        cantidad=posicion["cantidad"],
                        motivo_salida=(
                            "stop (hueco a la baja)"
                            if float(fila["open"]) < estado.stop_actual
                            else "stop"
                        ),
                        stop_inicial=estado.stop_inicial,
                        stop_final=estado.stop_actual,
                        velas_abierta=posicion["velas"],
                        riesgo_pct_planeado=posicion["riesgo_pct"],
                        costos=costos,
                        resultado_bruto=bruto,
                        resultado_neto=neto,
                        capital_antes=posicion["capital_antes"],
                    )
                )
                posicion = None

        # --- 3. Trailing, con el CIERRE de esta vela ----------------------
        if posicion is not None:
            atr_actual = fila.get("atr")
            posicion["stop"] = stop_manager.actualizar(
                posicion["stop"],
                cierre=float(fila["close"]),
                atr=float(atr_actual) if pd.notna(atr_actual) else 0.0,
            )
            posicion["velas"] += 1

        # --- 4. La senal de esta vela, para ejecutar en la siguiente ------
        if posicion is None and entrada_pendiente is None:
            if rapido:
                hay = bool(mascara.iloc[indice])
                precio_senal = float(fila["close"])
                atr_senal = float(atr_col.iloc[indice]) if hay else 0.0
                rechazos["ENTRADA" if hay else "otro"] = (
                    rechazos.get("ENTRADA" if hay else "otro", 0) + 1
                )
            else:
                senal = signal_engine.evaluar_vela(fila, cfg)
                clave = senal.fallo_en or "ENTRADA"
                rechazos[clave] = rechazos.get(clave, 0) + 1
                hay = senal.hay_entrada
                precio_senal = senal.precio
                atr_senal = senal.datos.get("atr", 0.0)

            if hay:
                veredicto = control.puede_abrir(posiciones_abiertas=0, momento=momento)
                if not veredicto.permitido:
                    rechazos[f"riesgo:{veredicto.limite_alcanzado}"] = (
                        rechazos.get(f"riesgo:{veredicto.limite_alcanzado}", 0) + 1
                    )
                elif usar_guardia and not guardia.revisar_macro(
                    precio_senal, fila.get("sma_macro")
                ).permitido:
                    rechazos["guardia_macro"] = rechazos.get("guardia_macro", 0) + 1
                else:
                    entrada_pendiente = {"atr": atr_senal}

        curva.append(capital)
        momentos.append(momento)

    # --- Cierre forzado al final del periodo -------------------------------
    if posicion is not None:
        ultima = df.iloc[-1]
        precio_salida = float(ultima["close"]) * (1 - slippage)
        valor_salida = precio_salida * posicion["cantidad"]
        costos = posicion["costos"] + valor_salida * comision
        bruto = (precio_salida - posicion["precio"]) * posicion["cantidad"]
        neto = bruto - costos
        capital += neto
        operaciones.append(
            Operacion(
                par=par, temporalidad=temporalidad,
                entrada_momento=posicion["momento"],
                entrada_precio=posicion["precio"],
                salida_momento=df.index[-1],
                salida_precio=precio_salida,
                cantidad=posicion["cantidad"],
                motivo_salida="fin del periodo",
                stop_inicial=posicion["stop"].stop_inicial,
                stop_final=posicion["stop"].stop_actual,
                velas_abierta=posicion["velas"],
                riesgo_pct_planeado=posicion["riesgo_pct"],
                costos=costos,
                resultado_bruto=bruto,
                resultado_neto=neto,
                capital_antes=posicion["capital_antes"],
            )
        )
        curva[-1] = capital

    curva_serie = pd.Series(curva, index=pd.Index(momentos, name="momento"))
    ganancias = [o.resultado_neto for o in operaciones if o.resultado_neto > 0]
    perdidas = [o.resultado_neto for o in operaciones if o.resultado_neto <= 0]

    metricas = Metricas(
        operaciones=len(operaciones),
        ganadoras=len(ganancias),
        perdedoras=len(perdidas),
        capital_inicial=capital_inicial,
        capital_final=capital,
        ganancia_bruta=sum(ganancias),
        perdida_bruta=abs(sum(perdidas)),
        costos_totales=sum(o.costos for o in operaciones),
        max_drawdown_pct=_drawdown_maximo_pct(curva_serie),
        mejor=max((o.resultado_neto for o in operaciones), default=0.0),
        peor=min((o.resultado_neto for o in operaciones), default=0.0),
        desde=df.index[0],
        hasta=df.index[-1],
        rechazos=rechazos,
    )
    return Resultado(metricas, operaciones, curva_serie)


def operaciones_a_dataframe(operaciones: list[Operacion]) -> pd.DataFrame:
    """Para guardar el diario de operaciones en CSV."""
    if not operaciones:
        return pd.DataFrame()
    return pd.DataFrame([vars(o) for o in operaciones])
