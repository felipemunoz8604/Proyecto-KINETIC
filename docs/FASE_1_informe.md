# Fase 1 — Backtest y validación. Informe de cierre

**Proyecto:** KINETIC — bot de trading algorítmico para Binance Spot
**Abierta:** 28 de agosto de 2026
**Cerrada:** 30 de agosto de 2026, por decisión explícita de Felipe Muñoz
**Estado:** CERRADA con hallazgo negativo, sobre muestra suficiente

> **Este documento está escrito para ser leído fuera del proyecto.** No supone
> conocimiento del repositorio ni de las conversaciones previas. Si lo estás
> leyendo como analista externo, lo que más te va a servir no es el veredicto
> —la estrategia no funciona— sino la sección **«Las seis restricciones
> medidas»**: son límites cuantificados que cualquier estrategia nueva sobre
> este mercado va a tener que respetar, y que costaron tres corridas de
> validación descubrir.

---

## 1. El veredicto, en una frase

**La estrategia de rupturas de rango con confirmación de volumen no tiene
ventaja explotable en Binance Spot después de costos.**

Sobre **500 operaciones fuera de muestra** en 15 pares y 6 años, el resultado
agregado es **+193 USDT sobre 7.500 de capital: 2,6% total, unos 0,4%
anual** — y eso *antes* de descontar el sesgo de supervivencia del universo.
La mediana de los pares es negativa. Una sola operación explica el 36% de
todo lo ganado.

**Ningún parámetro se promovió a la configuración.** No es un pendiente: es el
resultado. Ninguna configuración se ganó el derecho a quedar escrita.

---

## 2. El contexto operativo (las restricciones que no son negociables)

Importan para cualquier propuesta nueva:

| | |
|---|---|
| **Mercado** | Binance **Spot**, sin apalancamiento |
| **Dirección** | **Solo largos.** No se puede ganar con la bajada: se compra y después se vende lo comprado |
| **Capital** | 500 USDT |
| **Riesgo por operación** | 1% (5 USDT de pérdida máxima si pega el stop) |
| **Pérdida diaria máxima** | 3% (15 USDT; corta la apertura de posiciones nuevas hasta el día siguiente UTC) |
| **Comisión** | 0,1% por lado, sin descuentos |
| **Slippage asumido** | 0,05% por lado |
| **Peaje total ida y vuelta** | **0,30% del precio de entrada** |
| **Datos** | Endpoint público de velas de Binance Mainnet, desde 2017-08-17 |
| **Estado del bot** | No puede operar. Sin módulo de ejecución, y con tres cerrojos en código que lo garantizan |

**Sobre el 0,05% de slippage:** no es un supuesto de manual. Se midió sobre
las 659 velas de señal de BTCUSDT y ETHUSDT en 1h (2017-2026). El salto entre
el cierre de la vela de señal y la apertura de la siguiente tiene mediana
0,0000% —en cripto no hay huecos de fin de semana, el mercado es continuo—
así que ese costo es cero. Lo que se paga es spread más impacto: el spread de
BTCUSDT ronda 0,01%, y compras de 100-250 USDT sobre un libro de millones no
mueven nada. **0,05% es cinco veces el spread típico**, elegido pesimista a
propósito porque las rupturas ocurren justo cuando el spread se abre.

---

## 3. Qué estrategia se probó, exactamente

Entrada larga cuando se dan **las cuatro** condiciones sobre una vela cerrada:

1. **Régimen apto** — ADX(14) por encima de un mínimo.
2. **Consolidación previa** — dispersión de las últimas 50 velas por debajo de
   un umbral.
3. **Ruptura con volumen** — el **cierre** (no la mecha) supera el techo del
   rango de 50 velas, **y** el volumen supera 2x el promedio de 50.
4. **Dirección** — EMA(9) por encima de EMA(21).

**Salida:** stop inicial en `entrada − 2 × ATR(14)`, y trailing tipo
chandelier a 2 × ATR sobre el máximo cierre desde la entrada. No hay salida
por señal ni objetivo de ganancia.

**Tamaño:** el que hace que la distancia al stop valga el 1% del capital.

---

## 4. Cómo se midió, y qué hay contra el autoengaño

Esta sección es la que decide si el resto del documento vale algo.

- **Nada mira al futuro.** Hay una prueba automatizada que recalcula los 13
  indicadores cortando la serie en varios puntos: si un valor cambia según
  cuántas velas *posteriores* existan, estaba espiando. Los suavizados usan
  Wilder (α = 1/p) y las series derivadas van con `.shift(1)`.
- **La entrada se ejecuta a la apertura de la vela siguiente**, nunca al
  cierre de la vela que dio la señal.
- **El stop no siempre se ejecuta en su precio:** si la vela abre por debajo,
  sale ahí, peor.
- **Los costos se cobran de los dos lados**, siempre.
- **Se descartan los primeros 30 días de cada par** (libro vacío tras el
  listado).
- **Validación walk-forward:** entrenar 3 años → probar 1 → avanzar 1. El
  parámetro se reelige cada año usando **solo el pasado de esa ventana**, y el
  capital se arrastra entre ventanas. Hay una prueba que espía el proceso para
  verificar que el tramo de prueba no se toca al elegir. *Un «fuera de
  muestra» contaminado se ve exactamente igual que uno limpio; por eso hace
  falta la prueba y no la buena intención.*
- **Dos referencias en cada corrida:** (a) no elegir nada, y (b) **el mejor
  visto en retrospectiva** sobre todo el período, que es lo que daría un
  barrido tramposo. La distancia entre esa cifra y la del walk-forward es,
  literalmente, cuánto nos habríamos engañado.
- **Cuatro indicadores de fragilidad por corrida**, no solo el resultado:
  cantidad de operaciones, **concentración** (cuánto aporta la mejor
  operación), **estabilidad** (cuánto del menú de candidatos abarcan las
  elecciones) y **respaldo** (con cuántas operaciones de entrenamiento se
  eligió el parámetro de cada ventana).
- **El motor rápido no puede divergir del lento.** La versión vectorizada que
  hace posible el walk-forward se compara vela por vela contra la
  implementación de referencia, sobre datos reales, en una prueba.
- **Los criterios de la última corrida se escribieron y se commitearon ANTES
  de bajar los datos.** Están en el historial de git con fecha anterior a la
  ejecución. Se falló uno de ellos por un solo par y no se tocó.

**194 pruebas automatizadas, todas en verde.**

---

## 5. Las tres corridas y lo que dio cada una

### Corrida 1 — Barrido del trailing, 15m y 1h, BTC y ETH

Hipótesis: con 24-27% de acierto, el resultado depende de que las pocas
ganadoras corran mucho; un trailing a 2×ATR corta ganadoras vivas.

| Par / TF | Resultado | PF | Ops | Estabilidad | Concentración |
|---|---|---|---|---|---|
| BTC 15m | −351.20 (−70,2%) | 0.854 | 976 | ESTABLE | — |
| BTC 1h | +267.15 (+53,4%) | 1.560 | 117 | DUDOSA | **50%** |
| ETH 15m | −224.20 (−44,8%) | 0.908 | 811 | ESTABLE | — |
| ETH 1h | +10.00 (+2,0%) | 1.051 | 59 | INESTABLE | **920%** |

El mecanismo resultó **real pero insuficiente**: dar aire al trailing aportó
+134, +154 y +247 USDT en tres tramos contra el trailing fijo. No rescató
nada. ETH 1h lo refutó directamente (−157 contra no hacer nada), y la bandera
de estabilidad lo había anticipado antes de mirar el resultado.

### Corrida 2 — Barrido del umbral de consolidación, 1h y 4h, BTC y ETH

Hipótesis: el peaje es fijo y la ventaja por operación crece con la
temporalidad, así que 4h debería pagarlo.

| | BTC 1h | BTC 4h | ETH 1h | ETH 4h |
|---|---|---|---|---|
| Ops por año | 33 | 10 | 36 | 9 |
| Estabilidad | INESTABLE | **ESTABLE** | INESTABLE | **ESTABLE** |
| Concentración | (neto negativo) | **28%** | 49% | **31%** |
| PF | 0.81 | 1.64 | 1.17 | 1.94 |
| Capital, 6 años | −17,6% | +18,9% | +17,1% | +15,1% |
| Inflación del barrido tramposo | +57 USDT | +18 | +58 | +24 |

La prueba más limpia es sin ningún parámetro elegido —apagando el filtro de
consolidación no hay nada que sobreajustar—: **BTC 4h +106 contra 1h −51; ETH
4h +102 contra 1h +24.** El efecto de la temporalidad es real.

Pero 10 y 9 operaciones por año no alcanzan para confiar en nada, y apagando
el filtro son 14 y 13: **es el techo estructural de la estrategia en 4h**, no
un problema de calibración.

### Corrida 3 — El mismo método sobre 15 pares en 4h

Para conseguir muestra sin barrer más parámetros. Universo elegido por una
**regla mecánica ciega al resultado**: par contra USDT operable, base que no
sea stablecoin ni fiat, sin tokens apalancados, y primera vela anterior al
1-ene-2019 para que tenga el mismo período que BTC y ETH. De 476 pares
calificaron 15.

```
Par          Ops  Ops/año       Neto  Sin filtro  Mejor op  Estabilidad
BTCUSDT       61       10     +94.42     +106.01    +26.17  ESTABLE
ADAUSDT       40        7     +78.15     +108.41    +49.57  INESTABLE
ETHUSDT       52        9     +75.33     +101.96    +23.08  ESTABLE
XRPUSDT       25        4     +65.45      +61.76    +70.06  INESTABLE
XLMUSDT       22        4     +56.42      +65.58    +36.26  ESTABLE
BNBUSDT       25        4     +27.42      +75.64    +28.58  DUDOSA
VETUSDT       45        8      +5.31       -5.99    +48.73  INESTABLE
ETCUSDT       52        9      -5.79      -21.46    +49.21  INESTABLE
ICXUSDT       20        3     -11.76      -86.35    +11.40  ESTABLE
NEOUSDT       17        3     -14.14     -138.96     +8.77  ESTABLE
IOTAUSDT      28        5     -17.66      -47.13    +25.49  INESTABLE
ONTUSDT        7        1     -22.94     -124.23     +3.89  ESTABLE
LTCUSDT       47        8     -23.93      -92.38    +16.00  INESTABLE
TRXUSDT       19        3     -28.14       +1.56     +8.24  INESTABLE
QTUMUSDT      40        7     -84.76      -73.37    +10.37  INESTABLE
AGREGADO     500        6    +193.39      -68.96
```

**Los cuatro criterios, fijados y commiteados antes de bajar los datos:**

| Criterio | Resultado | |
|---|---|---|
| 1. Al menos 8 de 15 pares en positivo | **7 de 15** | NO PASA |
| 2. Ningún par aporta más del 50% del neto | BTC aporta 49% | PASA |
| 3. Ninguna operación aporta más del 20% | **la mejor aporta 36%** | NO PASA |
| 4. Neto agregado positivo | +193.39 | PASA |

El criterio 1 se falló **por un solo par**, y no se movió. El criterio 3 no se
falló por poco: una operación explica más de un tercio de seis años de
resultado sobre quince mercados.

---

## 6. Las seis restricciones medidas

**Esta es la parte del documento que sobrevive al cierre.** Son límites
cuantificados sobre este mercado y esta estructura de costos, no opiniones.

### 6.1 El peaje es fijo y la ventaja por operación tiene que superarlo

El costo no es un monto: es **0,30% del precio, cobrado siempre**. Entonces la
pregunta correcta no es «cuánto gano por operación» sino **cuánto se mueve el
precio en porcentaje comparado con ese 0,30%**.

Movimiento bruto capturado promedio, medido:

| Par / TF | Capturado | Peaje | Ratio |
|---|---|---|---|
| BTC 15m | +0,024% | 0,30% | **0,08** |
| BTC 1h | +0,316% | 0,30% | **1,05** |
| ETH 15m | +0,042% | 0,30% | **0,14** |
| ETH 1h | +0,656% | 0,30% | **2,19** |

**En 15m la ventaja es doce veces más chica que el costo.** Eso no lo arregla
ningún filtro, ninguna calibración y ninguna gestión de salida. De 15m a 1h el
movimiento capturado se multiplica por 13 en BTC y por 15 en ETH.

**Consecuencia para cualquier estrategia nueva:** en Spot con 0,1% por lado,
**una estrategia intradía de alta frecuencia está muerta antes de empezar**, a
menos que la ventaja por operación se mida en porcentaje y supere el 0,30% con
margen. Ese cálculo se puede hacer antes de escribir una línea de código.

### 6.2 Entre el 24% y el 29% de las operaciones que aciertan la dirección igual pierden plata

Porque capturan menos del 0,30%. **Acertar no es ganar.** Cualquier métrica de
«tasa de acierto» sobre este mercado es engañosa si no está medida en
porcentaje del precio y neta de costos.

### 6.3 Los umbrales absolutos no son comparables entre temporalidades — y este error casi cierra el proyecto con una conclusión falsa

El filtro de consolidación exigía dispersión ≤ 0,75%, **un umbral en % del
precio**. La volatilidad escala con la temporalidad, así que ese número
significa cosas distintas en cada una:

| Par / TF | Velas que pasaban el filtro |
|---|---|
| BTC 15m | **65,2%** |
| BTC 1h | 25,5% |
| BTC 4h | **2,4%** |
| ETH 15m | 51,2% |
| ETH 1h | 13,7% |
| ETH 4h | **0,7%** |

**El mismo filtro estaba prácticamente apagado en 15m y bloqueando el 99,3% en
4h.** Durante días, «4h da 0 a 3 operaciones» estuvo anotado como *falta de
señales en el mercado*. Era el filtro.

El arreglo: dividir la dispersión por el ATR%. La medida queda **sin
unidades**, y las distribuciones se vuelven casi idénticas (mediana 1,50 a
1,57 en las seis combinaciones, contra un rango de 0,54 a 3,60 en la medida
absoluta).

**Consecuencia:** cualquier umbral de una estrategia nueva debería expresarse
en unidades de volatilidad del propio activo, no en porcentaje del precio ni
en valores absolutos. Si no, no es un parámetro: es seis parámetros distintos
disfrazados de uno.

### 6.4 La concentración es el indicador que más veces detectó el problema

En cada corrida, la pregunta *«¿cuánto aporta la mejor operación?»* fue más
informativa que el profit factor, el retorno y la tasa de acierto juntos:

- ETH 1h en la corrida 1: **920%** del neto en una operación.
- BTC 1h en la corrida 1: 50%.
- La corrida 3, con quince pares y seis años: **36%**.

Un resultado positivo que depende de una operación no es una ventaja, es una
observación afortunada. Y no lo detecta ninguna métrica agregada estándar.

### 6.5 El barrido en retrospectiva infla entre un 20% y un 200%

Medido directamente en cada corrida, comparando el walk-forward contra el
mejor parámetro visto conociendo todo el período: **+18 a +24 USDT en 4h, +57
a +58 USDT en 1h**, sobre netos del orden de 75-95 USDT.

**Ese es el tamaño real del autoengaño de un backtest optimizado.** Cualquier
cifra que venga de un barrido sobre el período completo hay que descontarla en
ese orden de magnitud antes de creerle.

### 6.6 Un filtro puede ser un limitador de daño en vez de un generador de señal

Con dos pares, apagar el filtro de consolidación daba mejor en 3 de 4 casos, y
la conclusión que sacamos —anotada y después corregida— fue que *no aportaba
información*.

Con quince pares se da vuelta: en agregado el filtro convierte **−69 en
+193**. Lo que hace no es mejorar las buenas, es **recortar las malas** (NEO de
−139 a −14, ONT de −124 a −23, ICX de −86 a −12) a costa de las buenas (ADA de
+108 a +78, BNB de +76 a +27).

**Consecuencia doble.** Primero: un componente puede ganarse el lugar por
reducir varianza, no por añadir señal, y hay que evaluarlo con esa vara.
Segundo, y más importante: **cuatro mediciones no alcanzaron para sostener una
conclusión.** La conclusión con dos pares era falsa y sobrevivió hasta que
hubo quince.

---

## 7. Los dos sesgos que este trabajo NO corrige

Van pegados a cualquier cifra de arriba.

**Sesgo de supervivencia.** El endpoint de Binance solo sirve velas de los
pares que hoy existen. Las monedas listadas en 2018 que se murieron y se
deslistaron no están en el universo y no hay forma de traerlas desde ahí. El
universo es *«las que sobrevivieron ocho años»*, y eso **favorece a cualquier
estrategia larga**. El +193 agregado está inflado por una cantidad que no se
puede medir con estos datos.

**No es una simulación de cartera.** Los 15 pares corrieron con 500 USDT cada
uno y contabilidad independiente; después se sumaron los netos. Eso mide el
efecto, pero no modela capital compartido, ni tope de posiciones simultáneas,
ni el hecho de que **quince criptos contra el dólar suben y bajan casi todas
juntas** — es una apuesta tomada quince veces, no quince apuestas
independientes. Un backtest de cartera real daría peor, no mejor.

---

## 8. Qué quedó construido y sirve para lo que venga

Nada de esto se tira. Es infraestructura agnóstica a la estrategia, con 194
pruebas:

| | |
|---|---|
| **Datos** | Descarga incremental desde el endpoint público, con auditoría de huecos y duplicados por serie |
| **Indicadores** | 13, calculados a mano (sin dependencias externas de análisis técnico), con prueba de no-anticipación |
| **Motor de señal** | Camino de referencia y camino vectorizado, con prueba de equivalencia vela por vela |
| **Riesgo** | Capa independiente de la estrategia: tamaño por % de riesgo, pérdida diaria máxima, kill switch |
| **Backtest** | Costos de los dos lados, entrada a la apertura siguiente, stop en `min(stop, apertura)`, descarte de listado |
| **Walk-forward** | Genérico sobre cualquier parámetro, con concentración, estabilidad, respaldo y dos referencias |
| **Herramientas** | Anatomía de costos, elección mecánica de universo, medición de cierres de ventana |
| **Seguridad** | Cliente de solo lectura con lista blanca de endpoints; conectarse a dinero real exige autorización explícita; prueba que lee el código fuente y falla si aparece una orden |

Cambiar de estrategia significa reescribir **`strategy/`**. Todo lo demás se
reusa tal cual.

---

## 9. Qué NO habilita este cierre

- **No habilita operar.** No existe módulo de ejecución, y no debe escribirse
  ninguno hasta que haya una estrategia validada.
- **No habilita completar la configuración.** Los valores siguen sin definir
  a propósito: ninguno se ganó el lugar.
- **No abre la fase siguiente.** Requiere decisión explícita.

---

## 10. Preguntas abiertas, para quien diseñe la próxima estrategia

Salen de lo medido, no de la teoría:

1. **¿Qué familia de estrategias tiene una ventaja por operación que supere el
   0,30% con margen en Spot?** El cálculo se puede hacer antes de programar: si
   el movimiento típico capturado no llega al 0,6%, no hay margen para errores.
2. **Solo largos cambia todo.** Buena parte de la literatura de seguimiento de
   tendencia asume que se puede vender en corto. ¿Qué sobrevive cuando la mitad
   del ciclo es inoperable?
3. **¿Cómo se consigue muestra sin barrer?** Fue el cuello de botella de las
   tres corridas: las temporalidades que pagan el peaje dan pocas operaciones,
   y las que dan muchas no lo pagan. Más pares es la salida obvia y trae sesgo
   de supervivencia.
4. **Con 500 USDT y 1% de riesgo, cada operación arriesga 5 USDT.** ¿Qué
   estrategias siguen teniendo sentido con ese tamaño, considerando los
   mínimos de orden de Binance?
5. **¿Vale la pena mirar temporalidades de 1 día?** La corrida 2 mostró que la
   economía por operación mejora monótonamente con la temporalidad. 1d no se
   evaluó: en el universo elegido, pocos pares tendrían ventanas suficientes.
6. **¿Y una estrategia que no dependa de acertar la dirección?** Todo lo
   medido acá supone predecir hacia dónde va el precio, con 24-37% de acierto.

---

## 11. Cierre

La Fase 1 se cierra con un **hallazgo negativo sobre muestra suficiente**, que
es un resultado y no un fracaso: 500 operaciones fuera de muestra dicen que
esta estrategia no tiene ventaja, y decirlo con evidencia vale más que un
backtest optimizado que hubiera dicho lo contrario.

**Se probaron dos hipótesis de rescate sobre los mismos datos.** Las dos
resultaron en mecanismos reales que no alcanzaron. Una tercera habría sido un
barrido con otro nombre.

**Decisión de Felipe Muñoz, 30 de agosto de 2026: la estrategia de rupturas se
descarta y se busca otra.**

---

### Evidencia

Todo lo citado es reproducible desde el repositorio:

| Archivo | Qué contiene |
|---|---|
| `docs/salida_walkforward_29ago2026_con_matriz.txt` | Corrida 1, con matriz de candidatos |
| `docs/salida_walkforward_umbral_30ago2026.txt` | Corrida 2, 1h y 4h |
| `docs/salida_walkforward_universo_30ago2026.txt` | Corrida 3, 15 pares |
| `docs/BITACORA_KINETIC.md` | Registro cronológico, con los errores cometidos sin disimular |
| Historial de git | El compromiso previo de la corrida 3 está commiteado **antes** de su ejecución |
