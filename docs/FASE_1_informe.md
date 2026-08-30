# Fase 1 — Backtest local. Informe de cierre

**Abierta:** 28 de agosto de 2026
**Cerrada:** 29 de agosto de 2026, por decisión explícita de Felipe
**Estado:** CERRADA con hallazgo negativo calificado

---

## El hallazgo, en una frase

**La estrategia de rupturas con confirmación de volumen no paga sus costos en
cripto.** Sobrevive un solo caso marginal —BTCUSDT en 1 hora— y ese caso
descansa en demasiado pocas operaciones como para confiarle dinero.

**Ningún parámetro se promueve a `config.yaml`. Los `null` siguen en `null`.**
No es un trámite pendiente: es el resultado. No hubo configuración que se
ganara el derecho a quedar escrita.

---

## Qué se midió

Dos pares (BTCUSDT, ETHUSDT) en dos temporalidades (15m, 1h), sobre **829.930
velas** descargadas del endpoint público de Binance Mainnet, desde el
2017-08-17.

Todo **neto** de comisión (0,1% por lado) y slippage (0,05% por lado, medido
empíricamente, no supuesto). Entrada a la apertura de la vela siguiente. Stop
ejecutado en `min(stop, apertura)`. Primeros 30 días de cada par descartados.

Validación **walk-forward**: entrenar 3 años, probar 1, avanzar 1. El
parámetro se reelige cada año usando solo el pasado, y el capital se arrastra
entre ventanas.

---

## Resultados fuera de muestra

| Par / TF | Resultado | PF | Ops | Estabilidad | Concentración |
|---|---|---|---|---|---|
| BTC 15m | **−351.20** (−70.24%) | 0.854 | 976 | ESTABLE | — |
| **BTC 1h** | **+267.15** (+53.43%) | 1.560 | 117 | **DUDOSA** | **50%** |
| ETH 15m | **−224.20** (−44.84%) | 0.908 | 811 | ESTABLE | — |
| ETH 1h | **+10.00** (+2.00%) | 1.051 | 59 | **INESTABLE** | **920%** |

---

## Las cuatro conclusiones, con la evidencia que las sostiene

### 1. Los 15m no pagan el peaje

BTC 15m pierde el 70%, ETH 15m el 45%. **Con la mejor evidencia de las
cuatro** — entre 300 y 562 operaciones de entrenamiento por ventana.

La ventaja bruta existe: sin costos, BTC 15m daba PF 1.292 y +498%. Con
costos reales, los 718.63 USDT de comisión sobre 1.496 operaciones equivalen
al 144% del capital inicial. **La ventaja por operación no paga el peaje**, y
ninguna cantidad de aire en el trailing cambia cuántas veces se paga.

### 2. El mecanismo del trailing ancho es real

Fue la única hipótesis que se probó, con razón mecánica previa: con 20-25% de
acierto, el resultado depende de que las pocas ganadoras corran, y 2×ATR
corta ganadoras que aún tenían recorrido.

Se confirmó:

- Aportó **+100, +256 y +197 USDT** fuera de muestra en tres de los cuatro
  tramos, contra dejar el trailing en 2×.
- La matriz de candidatos es **monótona creciente en 6 de 6 ventanas** en los
  dos tramos de 15m. No es un ranking que se reordena por año: es la misma
  pendiente, seis veces, con datos distintos.
- **Sobrevivió al arreglo de un bug que movió todos los números.**

**Advertencia para quien retome esto:** en los 15m el ganador fue 6.0× —el
borde del rango probado— en casi todas las ventanas. **El óptimo está fuera
del rango 2-6 y nunca se encontró el techo.** Que gane 6.0 no significa que
6.0 sea la respuesta; significa que el rango era corto.

### 3. ETH 1h está descartado por falta de muestra, no por mala suerte

59 operaciones fuera de muestra, 9-33 por ventana de entrenamiento. Una
ventana eligió 2.0× —el extremo opuesto del menú— **sobre nueve operaciones**.

Su matriz de candidatos **no tiene patrón**: una ventana invertida, tres en
forma de U (ambos extremos mejor que el medio), todo dentro de rangos de 17 a
48 USDT. Es la firma del ruido.

El contraste decisivo: **ETH 15m es el mismo par y la misma estrategia**, y su
matriz es monótona creciente en las seis ventanas. La única diferencia es
cuántas operaciones hay para medir.

Su +2.00% final tiene **920% de concentración**: el neto es +10 USDT y la
mejor operación aportó ~+92, o sea que las otras 58 juntas perdieron ~82.

### 4. BTCUSDT 1h sobrevive, y no alcanza

Es el único caso positivo defendible. A favor:

- +267.15 USDT (+53.43%) en seis años, PF 1.560, fuera de muestra.
- **La elección del parámetro está justificada.** La distancia entre el mejor
  de {2,3} y el peor de {4,5,6} es −11 / +21 / +24 / +64 / +85 / +158: en
  cinco de seis ventanas los grupos no se tocan, y la separación crece.
- **Cero operaciones cortadas** por los bordes de ventana: el resultado no es
  un artefacto del método.
- Los 126 USDT de brecha contra un barrido tramposo están explicados: son el
  precio de no conocer el futuro, un 32% de inflación que el barrido habría
  mostrado de más.

En contra, y es lo que decide:

- **~19 operaciones por año.** 117 en seis años.
- **50% de concentración**: una sola operación aporta la mitad del neto. Sin
  ella quedan ~133 USDT en seis años.
- **Estabilidad DUDOSA**: las elecciones abarcan la mitad del menú.
- Su ventana 1 es la excepción a todo lo anterior: ahí los grupos de
  candidatos se solapan y no hay señal.

**Diecinueve operaciones por año, con la mitad del resultado en una sola, no
es una base para arriesgar dinero.** Ni siquiera los 5 USD de la Fase 3.

---

## Lo que la Fase 1 enseñó además del resultado

**El backtest simple habría elegido el peor tramo.** ETH 1h era el de mejor PF
(1.675) en el backtest simple del 28-ago. Fuera de muestra pierde. Elegir par
y temporalidad sin walk-forward habría elegido exactamente mal.

**Cuatro defectos de medición aparecieron por tirar de datos que no cerraban**,
no por mirar el resultado final:

1. **El recorte de 30 días se aplicaba a cada tramo del walk-forward**, no
   solo al histórico. Costaba 4.609 velas de prueba en BTC 1h (9% del
   período), un mes ciego después de cada costura, y la última ventana
   descartada entera. **También mutilaba el entrenamiento**, así que la
   elección del parámetro estaba contaminada.
2. **Un rótulo que interpretaba mal su propio número**: comparaba contra el
   valor dominante en vez de contra todas las ventanas, y mandó a buscar la
   causa de una brecha a donde no estaba.
3. **La bandera de estabilidad declaraba «sí» por mayoría mínima.** El mismo
   tramo daba veredictos opuestos según tuviera 6 o 7 ventanas.
4. **La bandera `ARBITRARIA` no sirvió**: cero activaciones, y no detecta el
   caso de elegir sobre nueve operaciones. Queda documentada como limitación,
   con una prueba que lo deja por escrito.

**185 pruebas automatizadas.** Las dos del arreglo del recorte se verificaron
fallando sin él: una prueba que pasa igual con y sin el arreglo no prueba
nada.

---

## Qué NO habilita este cierre

**Nada.** Cerrar la Fase 1 con hallazgo negativo **no** abre la Fase 2.

El repositorio **sigue sin poder operar** y los tres cerrojos siguen puestos y
vigilados por pruebas. Cualquier avance de fase requiere decisión explícita de
Felipe, y hoy no hay una estrategia validada que llevar a Testnet.

---

## Si algún día se retoma

Por orden de lo que la evidencia sugiere, sin recomendar ninguna:

1. **El problema es el costo por operación, no la señal.** La ventaja bruta
   existe en 15m y es grande. Cualquier idea que no reduzca el peaje por
   operación choca contra el mismo muro.
2. **El rango del trailing se quedó corto.** El óptimo está más allá de 6×ATR
   y nunca se acotó.
3. **1 hora tiene muy pocas operaciones y 15 minutos tiene demasiadas.** 4h no
   se llegó a evaluar (daba 0-3 operaciones en el backtest simple).
4. **Los filtros nunca se decidieron por evidencia.** ADX ≥ 20 y consolidación
   ≤ 0,75% se usaron como valores provisorios fijos en `main_walkforward.py`;
   nunca se promovieron a `config.yaml` ni se validaron.

**Y la regla que gobierna todo lo anterior:** una hipótesis por vez, con razón
mecánica propia, validada con walk-forward. Dos hipótesis seguidas sobre los
mismos datos son un barrido con otro nombre.
