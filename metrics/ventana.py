"""
La barrera del holdout. Un candado, no un acuerdo.

POR QUE ESTO ES UN ARCHIVO Y NO UNA NOTA EN LA BITACORA
--------------------------------------------------------
En la Fase 2 no se barren parametros: todos los valores salen de literatura
publicada. Eso saca el riesgo de sobreajuste de la maquina, pero **lo muda a
la persona que investiga**. Uno mira un resultado, no le gusta, cambia algo
"que no es un parametro", vuelve a correr. Nadie barrio nada y sin embargo se
ajusto al pasado igual.

La unica defensa contra eso es una ventana de datos que no se pueda mirar
mientras se desarrolla. Y una ventana que se puede mirar sin querer no
protege de nada: alcanza un `df.tail()` distraido para quemarla, y lo peor es
que uno **no se entera** de que la quemo.

Por eso es un candado en el codigo. Cualquier funcion que reciba datos
posteriores al fin de la ventana de diseño levanta `HoldoutBloqueado`, salvo
que quien llama pida explicitamente `permitir_holdout=True`. Ese argumento
existe para un solo momento en toda la Fase 2: la corrida final de la
estrategia ganadora, una sola vez.

QUE HACER SI LA BARRERA MOLESTA
-------------------------------
Molesta a proposito. Si estas escribiendo codigo nuevo y te salta, la
pregunta correcta no es "como la apago" sino "por que estoy leyendo datos de
2025 mientras desarrollo". La respuesta casi siempre es que hay que recortar
la serie con `recortar_a_diseño()`, no que haya que abrir el candado.
"""

from __future__ import annotations

import pandas as pd

# Ventana de diseño, de la especificacion de la Fase 2 seccion 7.3. Fijadas
# antes de bajar ningun dato de la Fase 2, que es lo que les da validez.
DISENO_DESDE = pd.Timestamp("2019-01-01", tz="UTC")
DISENO_HASTA = pd.Timestamp("2024-12-31 23:59:59", tz="UTC")


class HoldoutBloqueado(RuntimeError):
    """Alguien intento leer datos del holdout sin pedirlo explicitamente."""


def _a_utc(momento) -> pd.Timestamp:
    t = pd.Timestamp(momento)
    return t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")


def verificar(
    datos: pd.DataFrame | pd.Series | None = None,
    *,
    hasta=None,
    permitir_holdout: bool = False,
    contexto: str = "",
) -> None:
    """
    Levanta `HoldoutBloqueado` si los datos entran en la ventana reservada.

    Se le puede pasar un DataFrame/Series con indice de fechas, o una fecha
    suelta en `hasta`. No devuelve nada: o pasa en silencio, o corta.
    """
    if permitir_holdout:
        return

    ultimo = None
    if datos is not None and len(datos) > 0:
        ultimo = _a_utc(datos.index[-1])
    if hasta is not None:
        candidato = _a_utc(hasta)
        ultimo = candidato if ultimo is None else max(ultimo, candidato)
    if ultimo is None or ultimo <= DISENO_HASTA:
        return

    detalle = f" ({contexto})" if contexto else ""
    raise HoldoutBloqueado(
        f"Los datos llegan hasta {ultimo.date()}{detalle}, y la ventana de "
        f"diseño termina el {DISENO_HASTA.date()}.\n"
        "El holdout se mira UNA sola vez, sobre la estrategia ganadora, y "
        "despues no se reajusta.\n"
        "Si estas desarrollando, lo que corresponde es recortar la serie con "
        "metrics.ventana.recortar_a_diseño(df), no abrir el candado.\n"
        "Si de verdad es la corrida final, pasa permitir_holdout=True y "
        "dejalo anotado en la bitacora."
    )


def recortar_a_diseno(datos: pd.DataFrame | pd.Series):
    """La serie recortada a la ventana de diseño. Es lo que se usa a diario."""
    inicio = _a_utc(datos.index[0]) if len(datos) else DISENO_DESDE
    desde = max(inicio, DISENO_DESDE)
    return datos[(datos.index >= desde) & (datos.index <= DISENO_HASTA)]


# Alias con la eñe, porque el resto del proyecto escribe en español y el
# mensaje de error de arriba la nombra asi. Los dos nombres apuntan a lo
# mismo: que nadie pierda tiempo adivinando cual era.
recortar_a_diseño = recortar_a_diseno
