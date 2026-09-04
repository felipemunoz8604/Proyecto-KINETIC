# KINETIC — Criterios de M3, escritos ANTES de correr

**Fecha:** 4 de septiembre de 2026
**Origen:** §5.3 y §6 de `KINETIC_Respuesta_Seguimiento_3sep2026.md`
**Estado:** commiteado antes de ejecutar M3a y M3b

---

## Por qué existe este archivo

Porque a este proyecto ya le funcionó una vez y es la única defensa real que
tiene: **un criterio escrito después de ver el resultado no es un criterio, es
una justificación.** Se hizo así en la corrida de 15 pares (commit `d52a127`,
anterior a la ejecución), se falló un criterio por un solo par y no se tocó.

Acá hay cuatro valores de N y una decisión binaria. Sin esto escrito de
antemano, "elegir el N que cumple" sería exactamente el barrido que las cuatro
fases existen para evitar.

---

## Qué se va a medir

**M3a — la condición de retorno.** Para la compuerta de E0 des-parpadeada con
N = 5, 10, 20 y 30 días: **el log-retorno de BTC en los días que deja afuera.**

**M3b — la condición de caída.** Para los mismos cuatro N: **la caída máxima de
BTC restringida a los días que la compuerta deja adentro.** Más, como cota, la
caída máxima de BTC sobre 2020-2024 excluyendo 2022 entero — la compuerta
oráculo.

Las dos son **particiones de la serie de BTC, no corridas de estrategia**, de
la misma naturaleza que el cálculo de A1 del 3-sep. **Cuestan cero pruebas de
Deflated Sharpe.** El contador de configuraciones probadas sigue en seis.

---

## Las dos condiciones, y de dónde salen

Las dos son consecuencias de la identidad, no umbrales elegidos:

**Condición de retorno (C-A′).** Una compuerta de encendido y apagado a
exposición plena pasa la frontera **si y solo si los días que deja afuera suman
log-retorno negativo, por más que el costo de las transiciones.**

**Condición de caída (C-B′).** La misma compuerta pasa C-B′ si y solo si la
curva armada con los días que deja **adentro** no tiene una caída mayor a

    0,50 × 76,6%  =  **38,3%**

donde 76,6% es la caída máxima de B1 y 0,50 es "la mitad de la caída", el
objetivo declarado por Felipe.

**Se reporta además sobre la media de los 3 peores episodios**, que es la
medida que el analista propone en su §4 para reemplazar a la CDaR degenerada.
El umbral es el mismo 0,50, aplicado a la misma medida sobre B1. **La decisión
formal se toma sobre la caída máxima**, que es como el analista escribió la
condición.

---

## La regla de decisión

Copiada de su §5.3, sin cambiarle nada:

1. **Si ningún N deja afuera un log-retorno negativo** → A2 falla la condición
   de retorno. **Cerrar.**
2. **Si ningún N deja adentro una caída menor a 38,3%** → A2 falla la condición
   de caída. **Cerrar.**
3. **Si alguno cumple las dos**, eso **no autoriza a elegir el que cumple.** Se
   toma el N declarado de antemano —**fijo en 10 días**, la consolidación
   estándar de la literatura de tendencia— y solo si ese cumple las dos
   condiciones se corre A2, con una prueba de DSR.

---

## Lo que agrega la ingeniería, y por qué

**El des-parpadeo por consolidación de tramos mira al futuro.** Fusionar un
tramo de salida con el estado que lo rodea exige saber que el tramo fue corto,
y eso no se sabe hasta que terminó. **No es implementable como regla de
trading.**

Eso no invalida M3a: la vuelve un **techo**. Dice lo mejor que podría haber
hecho un des-parpadeo con conocimiento perfecto de la duración de los tramos.
Como falsador es válido y es de una sola cara: **si ni el techo pasa, ninguna
versión implementable pasa.** Como validador no sirve.

Por eso se mide también la versión implementable:

**Confirmación de N días.** La señal tiene que sostenerse N días antes de
actuar. Solo usa el pasado, se puede operar mañana, y es el des-parpadeo
estándar cuando no se puede mirar adelante.

**Regla adicional, declarada acá y antes de correr:** si el techo (consolidación
con N = 10) cumple las dos condiciones **pero la versión con confirmación de 10
días no las cumple**, tampoco se corre A2 — porque A2 tendría que ser
implementable, y ya se sabría que no llega. Es estrictamente más estricto que
la regla del analista y va en la misma dirección.

---

## Lo que NO se hace

**No se corre A2** salvo que la regla lo autorice, y con decisión explícita de
Felipe encima.

**No se corren M1 ni M2.** El analista los retira en su §6 y la razón es buena:
si la muestra no puede certificar nada, buscar mejor no la arregla.

**No se elige el N que dé mejor.** El N es 10, declarado acá.

**No se toca el holdout.**

---

## Lo que se verifica de paso

La traducción de C-C′ a "cuánto exceso anual haría falta para ser detectable".
El analista reporta 29,8% / 41,2% / 49,3% / 66,6% para B4 / B3 / E0 / E1. Es
aritmética sobre intervalos ya medidos y **no cambia ningún veredicto**; se
comprueba porque es el número que él propone como hallazgo central del
proyecto, y un hallazgo central se verifica.
