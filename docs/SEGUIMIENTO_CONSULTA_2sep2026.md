# KINETIC — Seguimiento de la respuesta del 2-sep-2026

**Fecha:** 3 de septiembre de 2026
**Para:** análisis cuantitativo externo
**De:** Felipe Muñoz
**Sobre:** su respuesta del 2-sep-2026, tras ejecutar los pasos 1 a 4 de su §8

---

## 0. Qué se hizo

Se ejecutaron **los cuatro pasos que usted marcó con costo cero**: medir U, D y
R; recalcular `c_up` y `c_down` con la partición por signo del propio mes;
implementar la CDaR al 95%; y correr B3 y B4 con la atribución.

**El contador de configuraciones probadas sigue en seis.** No se corrió A1 ni
A2. Ninguno de los cuatro pasos selecciona nada: tres miden lo ya corrido con
otra vara y el cuarto resuelve una ecuación con una incógnita.

Y salió una quinta cosa que usted no pidió: **la identidad de su §5.1 ya
contesta A1 sin correrla.** Está en la §7 de este documento, y ahorra una de
las dos pruebas de Deflated Sharpe.

**Antes de nada: su §1 y su §5.1 son correctas y son el aporte de este
intercambio.** La frontera derivada verifica exacto, y hay una prueba
automática que exige que pasar la frontera y superar el retorno total de B1
sean el mismo evento. El "no" dejó de depender de un número elegido.

Este documento trae **tres correcciones** y un resultado que cierra bastante.

---

## 1. Lo que verificamos y está bien

**La derivación de §5.1 es exacta.** Despejando `c_up·U + c_down·D ≥ U + D` con
`R = |D|/U` sale `c_up ≥ 1 − (1−c_down)·R`, sin aproximaciones. Se comprobó
sobre 25 curvas al azar que las dos preguntas —"¿pasa la frontera?" y "¿le ganó
a B1 en retorno total?"— dan **siempre la misma respuesta**.

**Su §2.1 verifica.** E0 ganó **+65,3%** en los meses que la regla vieja llamó
bajistas mientras B1 perdía **−12,4%** (usted reportó +65,1% y −12,5%). E0 no
es un seguro: produce retorno donde el mercado no lo produce.

**Su §3 es correcta.** C-A como cociente de log-retornos da **0,340** para E0
sobre el régimen de 12 meses, igual que usted.

**Y tiene razón en algo que nosotros reportamos mal.** El IC de C-C de E0 era
`[−0,532, 0,628]`. Escribimos "excluye 1,0" y no señalamos que **también
contiene cero**. La captura de E0 no se distingue ni de igualar al mercado ni
de no ganar nada. Se nos pasó y usted lo vio.

---

## 2. Corrección 1 — su §5.1 mezcla dos particiones

En §5.1 evalúa contra la frontera un `c_up ≈ 0,34`. Ese número sale de la
partición **vieja** —régimen de 12 meses— y la frontera está definida sobre la
partición **nueva**, la de su propia §4.3.

| | E0 |
|---|---|
| C-A vieja (régimen 12m), en log-retornos | 0,3398 |
| **`c_up` nuevo (signo del propio mes)** | **0,4413** |
| **Frontera exigida a E0** | **0,6348** |

**E0 falla igual, pero por 0,194 y no por 0,295.** El veredicto no cambia; el
margen sí, y le baja un tercio.

---

## 3. Corrección 2 — la compuerta aporta 11,7%, no 37%

Su §2.3 estima B3 en `k ≈ 0,55` con Calmar 0,594, y concluye que la compuerta
aporta +37% de Calmar.

B3 no se estimó: **se calibró corriendo el motor**, con los mismos costos,
filtros y rebalanceo diario que E0, y resolviendo por bisección qué exposición
constante iguala el CAGR de E0.

| | CAGR | Caída máx. | Calmar | vs B1 |
|---|---|---|---|---|
| **B1** comprar y mantener | +66,97% | −76,6% | **0,874** | 1,000 |
| **B4** solo volatilidad objetivo, sin compuerta | +45,57% | −59,2% | 0,769 | 0,880 |
| **B3** exposición constante **k = 0,449** | +32,80% | −44,9% | 0,731 | 0,836 |
| **E0** | +32,80% | −40,2% | **0,816** | 0,934 |

**La compuerta aporta +11,7% de Calmar sobre exposición constante del mismo
CAGR**, y +6,1% sobre B4. No +37%.

La diferencia está en `k`: la exposición constante que iguala el CAGR de E0 es
**0,449, no 0,55**. Con el rebalanceo diario y los costos, `k = 0,55` da más
CAGR que E0 y la comparación deja de ser a igual retorno.

Usted corrigió su §2.2 anterior *hacia arriba* para devolverle mérito a la
compuerta. Medido, el número original estaba más cerca. **La compuerta aporta,
y es lo único de todo lo probado que aporta — pero aporta un tercio de lo que
dice su §2.3.**

---

## 4. Corrección 3 — la CDaR no entrega las observaciones que promete

Su §5.2 propone reemplazar la caída máxima por la CDaR al 95% porque *"tiene
cientos de observaciones en vez de una"*. Se implementó, y ese argumento **no
se sostiene justo para el tipo de estrategia que se está evaluando.**

Contamos cuántos valores **distintos** hay en la cola del peor 5%:

| | Días en la cola | Valores distintos |
|---|---|---|
| B1 | 91 | 91 |
| B3 constante | 91 | 91 |
| B4 sin compuerta | 91 | 91 |
| **E0** | 91 | **1** |
| E1 / R1 / R2 | 91 | 34 |
| E2 | 91 | 91 |

**Mientras una estrategia está afuera del mercado su patrimonio no se mueve**,
así que su caída contra el máximo previo es idéntica todos esos días. La cola
de E0 son **91 copias del mismo número**, y su CDaR da −40,2%, exactamente su
caída máxima.

O sea: **para una estrategia con compuerta a efectivo, la CDaR degenera en la
caída máxima.** El veredicto no cambia —E0 falla C-B′ con las dos medidas— pero
la razón para cambiar de medida sí. Si el objetivo era poder ponerle un
intervalo de confianza al criterio de caída, la CDaR no lo consigue en las
configuraciones que tienen compuerta, que son cinco de las seis.

---

## 5. El resultado de los pasos 1 y 2

**Paso 1 — la frontera queda fijada.** En log-retornos mensuales sobre
2020-2024:

| | |
|---|---|
| **U** — meses en que B1 subió (n = 35) | **+5,9174** |
| **D** — meses en que B1 bajó (n = 25) | **−3,3528** |
| **R = \|D\|/U** | **0,5666** |

Una estrategia que no perdiera **nada** en ningún mes bajista todavía
necesitaría capturar el **43,3%** de la subida solo para empatar.

**Paso 2 — las ocho configuraciones contra la frontera:**

| | `c_up` | `c_down` | Frontera | Margen | |
|---|---|---|---|---|---|
| **B1** | 1,000 | 1,000 | 1,000 | +0,000 | — |
| B4 sin compuerta | **0,686** | 0,650 | 0,802 | −0,116 | **NO** |
| B3 constante k=0,449 | 0,470 | 0,406 | 0,664 | −0,194 | **NO** |
| **E0** | 0,441 | **0,356** | 0,635 | −0,194 | **NO** |
| R1 | 0,317 | 0,301 | 0,604 | −0,286 | **NO** |
| R2 | 0,309 | 0,279 | 0,591 | −0,283 | **NO** |
| E1 | 0,274 | 0,270 | 0,586 | −0,312 | **NO** |
| E2 | −0,063 | −0,012 | 0,427 | −0,489 | **NO** |

**Ninguna pasa.** Y el veredicto no se mueve en semanal ni en trimestral: las
ocho fallan en las tres periodicidades, con el mismo orden.

**Paso 3 — C-B′ con CDaR:** solo **R1** la pasa (0,417). E0 da 0,542, del lado
equivocado con las dos medidas. R1 falla C-A′ por 0,286, así que pasar C-B′ no
la salva.

**C-C′ — el intervalo del exceso mensual de log-retorno contra B1:** **las
siete configuraciones contienen cero.** Incluidas B3 y B4, que no son
estrategias. Con 60 meses y bloques de 3, nada de lo construido se distingue de
comprar y no tocar. Es su argumento de fondo, ahora confirmado también con la
métrica nueva.

---

## 6. Lo que la frontera es, dicho de frente

Vale la pena escribirlo porque cambia qué se está pidiendo. La frontera sale de
`c_up·U + c_down·D ≥ U + D` y de nada más. Eso es, literalmente, **"igualar el
retorno total de comprar y no tocar"**, reescrito en las dos cantidades que
C-A′ y C-B′ miden.

Junto con C-B′, la vara nueva dice: **igualar a B1 en retorno con la mitad de
su caída.** Eso es un cociente de 2,0 contra el 1,8 del criterio 1 original.
**La vara nueva es algo más dura que la vieja**, como usted sospechaba.

Y por eso el valor de este cambio no es el veredicto —E0 ya fallaba el
criterio 1— sino que **el veredicto dejó de depender de números elegidos.**

---

## 7. A1 no hace falta correrla: la identidad ya la contesta

Esto es lo que no pidió y ahorra una prueba de Deflated Sharpe.

A1 es *"E0 con `k_max` sin objetivo de volatilidad (exposición 1,0 cuando está
dentro)"*. A exposición 1,0 el rebalanceo diario es no hacer nada, así que **el
log-retorno de A1 es exactamente el de BTC en los días con la compuerta
abierta**, menos el costo de las transiciones. Y la frontera es exactamente
igualar el retorno total de B1.

Entonces *"¿pasa A1?"* es la misma pregunta que *"¿los días que la compuerta
dejó afuera sumaron negativo?"*. Medido:

| | |
|---|---|
| Días con la compuerta abierta | 1.128 de 1.827 (61,7%) |
| Transiciones | 39 |
| log-retorno de BTC con la compuerta **abierta** | **+2,0727** |
| log-retorno de BTC con la compuerta **cerrada** | **+0,4919** |
| log-retorno total de B1 | +2,5646 |

**BTC subió +0,4919 en log-retorno mientras E0 estaba afuera.** Quedarse afuera
costó eso, antes de cualquier costo de operación.

**A1 termina con el 80,8% del log-retorno total de B1 y la frontera pide el
100%. A1 falla, y no por poco.** No hace falta correrla.

**Esto no consume presupuesto de DSR**, y conviene decir por qué: no se corrió
ninguna configuración nueva. Es la compuerta de E0 —que ya está entre las
seis— descompuesta según su propio estado.

**Pero hay una asimetría y la anotamos:** si esto hubiera dado que A1 pasa,
correrla después sería confirmar algo ya sabido, no explorar. Dio que no pasa,
así que ahorra la prueba en vez de gastarla — pero la asimetría existe.

Y de ahí sale una condición general, para **cualquier** compuerta de encendido
y apagado a exposición plena:

> **pasa la frontera ⟺ los días que deja afuera suman negativo, por más que el
> costo de las transiciones.**

Es necesaria y suficiente, y sale de la identidad. En una ventana donde BTC
multiplicó por 13, es una condición muy dura — y dice exactamente lo que usted
escribió en §7.3: el problema no es detectar techos, es **no soltar la posición
en un mercado que sube.**

---

## 8. Las preguntas

1. **¿Acepta las tres correcciones?** En particular la de la compuerta (+11,7%
   contra +37%), porque su §2.3 apoya en ese número el argumento de que hay
   algo genuino que rescatar.

2. **¿Qué se hace con C-B′ dado que la CDaR degenera?** Vemos tres salidas y no
   sabemos cuál prefiere: volver a la caída máxima y **declarar que tiene una
   observación**; usar la CDaR sobre los días **con posición** únicamente; o
   medir la caída con un estadístico que no se congele cuando la estrategia
   está en efectivo.

3. **¿A2 sigue valiendo una prueba?** Es la única de las dos que queda. Por §7
   sabemos que ninguna compuerta de encendido y apagado pasa si los días que
   deja afuera suman positivo. A2 cambia el estimador de régimen, así que
   cambia *qué* días deja afuera — pero la condición que tiene que cumplir es
   muy dura y está escrita. **Si usted cree que no la puede cumplir, el paso 7
   de su §8 se puede tomar ahora y con esto alcanza para cerrar.**

---

## 9. Lo que no se hizo, y por qué

**No se corrió A1** — la identidad la contesta, §7.

**No se corrió A2** — cuesta una prueba de DSR y ninguna configuración nueva se
corre sin decisión explícita de Felipe.

**No se corrió M1 ni M2** — su §8 los pone después del paso 7.

**No se eligió ningún umbral nuevo.** El 0,50 de C-B′ es el objetivo declarado
por Felipe escrito como cociente, y la frontera de C-A′ es una identidad. No
hay ningún número elegido en esta vara, que era el punto.

**No se tocó el holdout.** Sigue cerrado por código en `metrics/ventana.py`.

---

### Evidencia

| Archivo | Qué contiene |
|---|---|
| `salida_frontera_3sep2026.txt` | Los cuatro pasos completos, la mezcla de particiones, la degeneración de la CDaR y el cálculo de A1 |
| `salida_repuntaje_1sep2026.txt` | El paso 1 anterior, con la vara vieja, para contrastar |

**491 pruebas automáticas en verde**, incluidas 27 nuevas sobre la vara
corregida. Las dos que sostienen lo que se afirma acá:

- `test_la_frontera_es_exactamente_ganarle_a_b1` — sobre 25 curvas al azar,
  pasar la frontera y superar el retorno total de B1 son el mismo evento.
- `test_una_compuerta_a_exposicion_plena_pasa_solo_si_lo_que_deja_afuera_baja`
  — la condición general de §7, comprobada sobre 20 compuertas al azar.

Y una tercera que fija la lectura incómoda de la identidad:
`test_exposicion_constante_no_puede_pasar` — con R < 1, **media exposición no
puede pasar la frontera por construcción**, sin importar cómo se la consiga.
