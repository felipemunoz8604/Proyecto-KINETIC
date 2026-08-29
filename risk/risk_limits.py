"""
Los limites duros. El portero del portero.

Aca no se opina sobre si la senal es buena: se cuenta cuanto se perdio hoy,
cuantas posiciones hay abiertas, y si alguien apago el bot. Cualquiera de
esas tres cosas puede vetar una operacion perfecta.

Por que existe esta capa aparte del dimensionamiento: dimensionar bien cada
operacion no impide perder diez veces seguidas en un mismo dia. El limite
diario es lo que convierte una racha mala en un mal dia en vez de en el
final del proyecto.

EL DIA ES UTC
-------------
El corte diario usa UTC, igual que Binance. Si usaramos la hora de Chile,
el "dia" del bot y el de los datos no coincidirian, y el limite se
reiniciaria a media tarde de la sesion asiatica sin ninguna razon.

LAS POSICIONES ABIERTAS NO SE TOCAN
------------------------------------
Cuando se alcanza el limite diario o se activa el kill switch, el bot deja
de ABRIR. Lo que ya esta abierto se sigue cuidando con su stop. Cerrar todo
de golpe al tocar un limite convierte una perdida flotante en una perdida
realizada, que es justo lo que el limite intenta evitar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone


@dataclass
class EstadoDiario:
    """Lo perdido y ganado en el dia UTC en curso."""

    dia: date
    resultado: float = 0.0          # negativo = perdida
    operaciones_cerradas: int = 0

    def registrar(self, resultado_operacion: float) -> None:
        self.resultado += resultado_operacion
        self.operaciones_cerradas += 1


@dataclass
class Veredicto:
    """La respuesta del portero: pasa o no pasa, y por que."""

    permitido: bool
    motivo: str
    limite_alcanzado: str | None = None


@dataclass
class ControlDeRiesgo:
    """
    Lleva la cuenta del dia y responde si se puede abrir una posicion nueva.

    Se le pasa el momento de forma explicita en vez de que lo lea del reloj:
    asi el backtest puede recorrer nueve anios de historia usando exactamente
    el mismo codigo que corre en vivo.
    """

    capital: float
    perdida_diaria_max_pct: float
    max_posiciones: int | None = None
    kill_switch: bool = False
    estado: EstadoDiario | None = field(default=None)

    # -- Manejo del dia ----------------------------------------------------

    def _dia_de(self, momento: datetime | None) -> date:
        momento = momento or datetime.now(timezone.utc)
        if momento.tzinfo is None:
            raise ValueError(
                "El momento tiene que venir con zona horaria. Sin eso no se "
                "puede saber a que dia UTC pertenece, y el corte diario deja "
                "de significar algo."
            )
        return momento.astimezone(timezone.utc).date()

    def _estado_del_dia(self, momento: datetime | None) -> EstadoDiario:
        hoy = self._dia_de(momento)
        if self.estado is None or self.estado.dia != hoy:
            self.estado = EstadoDiario(dia=hoy)
        return self.estado

    # -- Registro ----------------------------------------------------------

    def registrar_cierre(self, resultado: float, momento: datetime | None = None) -> None:
        """Anota el resultado de una operacion cerrada (negativo si perdio)."""
        self._estado_del_dia(momento).registrar(resultado)

    @property
    def perdida_maxima_dinero(self) -> float:
        return self.capital * self.perdida_diaria_max_pct / 100.0

    def perdida_de_hoy(self, momento: datetime | None = None) -> float:
        """Cuanto se perdio hoy, en positivo. Cero si el dia va ganando."""
        estado = self._estado_del_dia(momento)
        return max(0.0, -estado.resultado)

    def margen_restante(self, momento: datetime | None = None) -> float:
        return max(0.0, self.perdida_maxima_dinero - self.perdida_de_hoy(momento))

    # -- La pregunta que importa -------------------------------------------

    def puede_abrir(
        self, posiciones_abiertas: int = 0, momento: datetime | None = None
    ) -> Veredicto:
        """Se puede abrir una posicion nueva ahora mismo, si o no."""
        if self.kill_switch:
            return Veredicto(
                False,
                "kill switch activado: no se abre nada nuevo. Las posiciones "
                "abiertas siguen gestionadas por su stop.",
                "kill_switch",
            )

        perdido = self.perdida_de_hoy(momento)
        tope = self.perdida_maxima_dinero
        if perdido >= tope:
            return Veredicto(
                False,
                f"limite diario alcanzado: {perdido:.2f} USDT perdidos hoy, tope "
                f"{tope:.2f} USDT ({self.perdida_diaria_max_pct}% del capital). "
                "No se abre nada mas hasta manana (UTC).",
                "perdida_diaria",
            )

        if self.max_posiciones is not None and posiciones_abiertas >= self.max_posiciones:
            return Veredicto(
                False,
                f"ya hay {posiciones_abiertas} posiciones abiertas, el maximo es "
                f"{self.max_posiciones}",
                "max_posiciones",
            )

        return Veredicto(
            True,
            f"sin restricciones: quedan {self.margen_restante(momento):.2f} USDT "
            f"de margen diario",
        )

    @classmethod
    def desde_config(cls, cfg: dict) -> "ControlDeRiesgo":
        riesgo = cfg["riesgo"]
        return cls(
            capital=cfg["capital"]["monto"],
            perdida_diaria_max_pct=riesgo["perdida_diaria_max_pct"],
            max_posiciones=riesgo.get("max_posiciones_simultaneas"),
            kill_switch=bool(riesgo.get("kill_switch", False)),
        )
