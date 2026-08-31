# Bitácora KINETIC

Cronológico, más reciente arriba. Este es el documento que hay que leer
primero en cualquier sesión nueva, antes de tocar código.

---

## 31 de agosto de 2026 — E2 NO PASA los seis. El plan de la Fase 2 está agotado

> **Si estás retomando el proyecto, empezá por acá.**

`strategy/e2.py` con 14 pruebas propias, más soporte de cortos y financiación
en el motor. **451 en total, en verde.** Evidencia en
`docs/salida_e2_31ago2026.txt`.

**E2 falla los seis criterios y tampoco supera a E1.** Con esto, las cuatro
candidatas de la Fase 2 están medidas y ninguna pasa.

### El resultado

Ventana efectiva **2020-01-01 a 2024-12-31** — se pierde un año entero
respecto de la de diseño porque los perpetuos nacen después. Todos los
rivales están recalculados sobre esa misma ventana.

| | CAGR | Caída | **Calmar** | En dólares |
|---|---|---|---|---|
| **E2** | **−6,41%** | −60,9% | **−0,105** | **−137,52** |
| E1 | +15,38% | −44,7% | 0,344 | +522,91 |
| E0 | +32,80% | −40,2% | 0,816 | +1.567,00 |
| B1 | +66,97% | −76,6% | 0,874 | +5.989,44 |

**Pierde plata.** No es que rinda poco: sobre 500 USDT termina con 362.

| # | | |
|---|---|---|
| 1 | Calmar vs B1 por pares: **−0,123** vs 1,8 | NO PASA |
| 2 | Caída 60,9% vs 46,0% | NO PASA |
| 3 | Calmar −0,105 vs 1,005 | NO PASA |
| 4 | IC 95% **[−26,58%, +16,87%]** | NO PASA |
| 5 | Sin 3 meses: −13,51% | NO PASA |
| 6 | Costo 3,54% anual | NO PASA |

**Cero de seis.** Y su falsación propia también: Calmar −0,105 contra 0,344 de
E1, así que *la pata corta no justifica el riesgo operativo adicional*.

### La financiación SÍ funcionó. Lo demás se la comió

**La pata corta cobró +109,81 USDT de financiación — el 22% del capital
inicial en cinco años.** Sin ese ingreso, E2 habría dado −10,59% en vez de
−6,41%.

O sea que el único mecanismo nuevo que E2 traía **funcionó exactamente como
la medición 5.1 anticipaba**, y aun así la estrategia pierde. Lo que la hunde
es el momentum, que ya había fallado en E1.

### Los 67 stops de la pata corta

De 93 stops disparados, **67 fueron en la pata corta**: unos 13 por año sobre
5 posiciones. Un stop de catástrofe de 4×ATR debería ser rarísimo.

Es el desplome de momentum que la literatura advierte, visto desde el otro
lado: **las monedas de peor momentum son justamente las que rebotan más
violentamente.** Shortearlas es pararse delante de eso, y el stop lo único que
hace es realizar la pérdida y esperar al mes siguiente.

Y la rotación lo confirma: **25,5 vueltas al año** contra 11,7 de E1, con un
costo de 3,54% anual contra 1,57%.

### El año que lo dice todo

| Año | E2 | B1 |
|---|---|---|
| **2022** | **−25,4%** | **−65,3%** |

Una cartera neutral al mercado perdiendo 25% en el año en que el mercado cayó
65%. **Si la neutralidad funcionara, 2022 debería haber sido su mejor año.**
Que pierda ahí significa que el problema no es la exposición al mercado: es la
selección.

### El estado del plan, completo

| | Veredicto |
|---|---|
| **E0** BTC + compuerta + volatilidad objetivo | NO PASA — empata con comprar y esperar |
| **E1** momentum transversal largo | NO PASA — 4 de 6 criterios |
| **E2** momentum largo/corto con perpetuos | **NO PASA — 0 de 6** |
| **E3** carry de financiación | Sobrevive la falsación, rinde 25 USDT/año |

**Las cuatro candidatas están medidas. Ninguna pasa.**

La especificación decía: *"E0 es obligatoria… si nada la supera, se implementa
E0 y se cierra la investigación."* Nada la superó — pero **E0 tampoco alcanzó
su propia vara**: iguala a comprar BTC y esperar, no lo supera.

Deflated Sharpe de E2: **0,083** sobre tres configuraciones probadas.

### Lo que queda, y lo que no

Quedan las **dos hipótesis de rescate de E1** (R1: ventana de 90 días; R2: 8
posiciones), preautorizadas en la especificación. Sigo recomendando no
correrlas: a E1 le faltaba un factor de cuatro y su criterio 4 decía que no
hay señal, no que esté mal sintonizada.

**Lo que no queda es una candidata nueva.** Inventar una quinta después de ver
fallar cuatro es empezar el barrido que este proyecto existe para evitar, con
la diferencia de que ahora ya conocemos los datos — que es peor.

Lo que sí corresponde, y es decisión de Felipe, es **cerrar la Fase 2 con un
informe** como se cerró la Fase 1. Hay material medido de sobra: cinco
mediciones previas, cuatro estrategias, un universo sin sesgo de
supervivencia, y un modelo de costos verificado contra el archivo real.

### Cuatro decisiones de implementación que valían

- **La pata corta es otro instrumento**: `BTCUSDT` toma precios de Spot y
  `BTCUSDT.P` del perpetuo. Compartiendo columna, cada cambio de venue le
  metería al motor un salto de precio que nunca ocurrió.
- **La bruta se mide en valores absolutos**: +0,6 y −0,6 no son exposición
  cero, son 1,2 de bruta. El motor levanta.
- **El stop de un corto está arriba y mira el precio del perpetuo.** La
  pérdida de un corto no tiene techo.
- **No se fuerza la neutralidad.** Si a la pata corta le faltan nombres, queda
  más chica y se ve. Rellenar sería elegir por un motivo que no es el puntaje.

---

## 31 de agosto de 2026 — Medición 5.1: E3 sobrevive la falsación, pero rinde 25 USDT al año

`core/financiacion.py` con 10 pruebas propias, más 5 nuevas en costos.
**424 en total, en verde.** Evidencia en
`docs/salida_medicion_51_31ago2026.txt`.

**Las cinco mediciones previas están completas.** Esta era la única que
faltaba, y la única que podía cerrar una estrategia sin escribirla.

Se bajaron **624.755 cobros de financiación** de 107 perpetuos (autorizado por
la regla 8 del MEGAPROMPT: los cerrojos de futuros están verdes desde
`22eebf8`).

### El veredicto de E3, con las dos lecturas

La falsación de la especificación 6.4 dice: *"si la mediana de la financiación
anualizada neta de comisiones no supera con margen el costo de montar la
estructura, E3 no se codifica"*.

| | |
|---|---|
| Mediana de la financiación anualizada | **10,95%** sobre nocional |
| Costo de montar y desmontar | **0,36%** |

**Literalmente, E3 sobrevive**: 10,95% es treinta veces 0,36%.

Pero el número que decide es otro, y la especificación pedía calcularlo antes
de codificar:

| | |
|---|---|
| Carry sobre **capital** (las dos patas ocupan plata) | **5,47%** anual |
| Neto montando una vez al año y no tocando | **5,12%** anual |
| **En dinero, sobre 500 USDT** | **25,57 USDT al año** |

Contra E0 que rindió 37,23% y B1 que rindió 70,55%.

La especificación había anticipado exactamente este caso: *"el retorno
absoluto puede quedar demasiado bajo para tener sentido con 500 USDT de
capital. Ese caso hay que identificarlo y reportarlo explícitamente, no
esconderlo detrás de un buen ratio."* Identificado: **son 25 dólares al año.**

### Por qué la mediana da 10,95% exacto en todas las cortes

Salió idéntica en el agregado, por símbolo, en tramos alcistas y bajistas, y
en cuatro de cinco años. Eso parecía un error, así que lo verifiqué:

**El 54% de todos los cobros vale exactamente 0,01%** — la tasa base de
Binance. 0,01% × 3 × 365 = 10,95%. No es un error de cálculo: es el piso del
mercado asomando por la mediana.

**Consecuencia importante: la mediana subestima a E3**, que por diseño entra
solo cuando la financiación está alta. La cola es donde está el dinero: p90 =
39,7%, p95 = 72,9%, p99 = 190,5%.

### Pero el filtro tampoco lo rescata

| Umbral | % del tiempo | Tasa mientras dentro | Montajes/año | **Al año, neto** |
|---|---|---|---|---|
| 0% | 84,2% | 21,9% | 66 | **−14,5%** |
| 11% | 17,8% | 66,6% | 33 | **−6,0%** |
| 30% | 12,3% | 87,5% | 28 | **−4,9%** |
| 100% | 3,1% | 181,6% | 9 | **−0,6%** |

**Apretar el umbral sube la tasa y baja el tiempo adentro, y las dos cosas
casi se cancelan** — mientras el costo de montar crece con cada entrada.

*Con una advertencia que hay que leer: esa última columna cuenta un montaje
cada vez que la tasa cruza el umbral, aunque sea por un solo cobro de 8 horas.
Una implementación real pondría histeresis. Es una **cota pesimista de la
versión ingenua**, no el veredicto. El veredicto es el 5,12% de arriba.*

### El carry NO es direccional, y eso es a favor de E3

| | Mediana | Positiva |
|---|---|---|
| Tramos alcistas | 10,95% | 91% del tiempo |
| Tramos bajistas | 10,95% | 70% del tiempo |

Paga en los dos regímenes. Si solo pagara en los alcistas sería una apuesta al
mercado disfrazada; no lo es. El único año con compresión visible es **2022**:
mediana 8,64% y solo 65% de cobros positivos.

### Tres cosas que el dato real destapó

**1. El intervalo de cobro no es 8 horas para todos.** De 106 perpetuos, **21
cobran cada 4 horas y 5 cada 2**. Anualizar con la constante de 8 les borra la
mitad o más del carry. El archivo trae la columna justamente por eso, y ahora
se usa siempre.

**2. `execution/costos.py` estaba mal, y contra el dato real habría fallado en
todo.** La primera versión generaba los cortes en 00, 08 y 16 **en punto** y
exigía coincidencia exacta con el índice. El dato real trae sellos como
`12:00:00.001` y símbolos de 2 y 4 horas: **ningún cobro habría coincidido**, y
cada posición habría levantado `FinanciacionFaltante`. Ahora cobra los cobros
reales del archivo, y la verificación de huecos se hace contra el intervalo
declarado del símbolo.

**3. Cuatro monedas del universo no tienen perpetuo con ese ticker.** SHIB,
PEPE, BONK y FLOKI cotizan en futuros como `1000SHIBUSDT`, `1000PEPEUSDT`…
E2 y E3 necesitarían una tabla de mapeo a mano, igual que
`RENOMBRAMIENTOS`. Nueve del universo no tienen perpetuo en absoluto.

### La ventana de los perpetuos es más corta

El perpetuo más viejo arranca **2020-01**; la mediana arranca **2020-10**.
Todo resultado de E2 o E3 se lee sobre esa ventana, no sobre 2019-2024.

### Lo próximo, y una advertencia sobre el objetivo

Queda **E2** (largo/corto con perpetuos), la última candidata del plan. Usa la
misma compuerta que empató en E0 y el mismo universo donde la selección de E1
destruyó valor, así que conviene entrar con expectativas medidas.

Y algo que hay que decir con todas las letras, porque Felipe pidió "llegar a
una estrategia que pase": **eso no se puede perseguir como objetivo directo.**
Si se prueban configuraciones hasta que una pase, el criterio deja de
significar algo — es literalmente el error que el `CLAUDE.md` define como el
que este proyecto existe para evitar. Lo que sí se puede hacer, y es lo que se
viene haciendo, es agotar el plan preregistrado y anotar cada resultado, pase
o falle.

Hasta ahora: E0 empata, E1 destruye valor, E3 rinde 25 USDT al año. Son tres
resultados negativos **medidos**, que valen más que un PF 1,8 encontrado a
fuerza de intentos.

---

## 30 de agosto de 2026 — E1 NO PASA, y no por poco: 4 de 6 criterios

`strategy/e1.py` con 16 pruebas propias. **411 en total, en verde.**
Evidencia en `docs/salida_e1_30ago2026.txt`.

**Elegir por momentum resultó peor que no elegir.**

### El cuadro completo

| | CAGR | Caída | **Calmar** |
|---|---|---|---|
| **E1** (momentum transversal) | +12,1% | −45,1% | **0,268** |
| B0 = E0 | +37,2% | −40,2% | 0,927 |
| B1 comprar y mantener | +70,6% | −76,6% | 0,921 |
| **B2** canasta top-10 sin señal | +35,0% | −86,5% | **0,405** |

E1 queda **última**. Pierde contra E0, contra comprar BTC y esperar, y contra
la canasta equiponderada de los diez más líquidos — que no mira absolutamente
nada.

### Los seis criterios

| # | | |
|---|---|---|
| 1 | Calmar vs B1 por pares: mediana **0,293** vs 1,8 | **NO PASA** |
| 2 | Caída 45,1% vs 46,0% permitido | PASA |
| 3 | Calmar **0,268** vs **1,066** exigido (1,15 × E0) | **NO PASA** |
| 4 | IC 95% del CAGR **[−9,42%, +44,07%]** | **NO PASA** |
| 5 | Sin los 3 mejores meses: **−0,62%** vs +35,27% | **NO PASA** |
| 6 | Costo 1,57% anual vs 3,41% permitido | PASA |

**El criterio 4 es el que más pesa. El intervalo cruza cero.** No es que E1
rinda poco: es que **no hay evidencia estadística de que gane nada.**

Y el 5 lo remata: **sin los 3 mejores meses de 72, el CAGR es negativo.** Tres
meses son el resultado entero.

Deflated Sharpe 0,771, debajo del 0,95.

### Lo que la especificación pedía decir, dicho

> *"Si no supera a E0 por al menos 15% en Calmar, la selección transversal no
> está aportando nada sobre la compuerta de régimen, y hay que decirlo
> claramente en la bitácora."*

**No es que no aporte: resta.** El Calmar de E1 es el **29%** del de E0. Los
tres mecanismos apilados —selección por momentum, pesos por inversa de
volatilidad, compuerta— rinden menos que la compuerta sola.

Comparando E1 contra B2 se aísla qué mecanismo falla: los dos operan el mismo
universo con el mismo rebalanceo mensual, y la única diferencia es que E1
**elige cinco por momentum** y B2 se queda con los diez. B2 saca Calmar 0,405
y E1 0,268. **La selección es el mecanismo que destruye valor.**

### La conjetura de 5.2 quedó resuelta, y del lado que había avisado

La medición 5.2 encontró correlación media 0,59 y un techo de selección
perfecta de +22% cada 28 días — o sea, muchísimo espacio. Escribí entonces:

> *"No dice que exista señal para capturarlo. Un techo alto es condición
> necesaria, no suficiente."*

Era eso. **El espacio existe y el momentum a 28 días no lo encuentra.**

### Año por año

| Año | E1 | E0 | B1 | B2 |
|---|---|---|---|---|
| 2019 | −3,6% | +39,7% | +89,5% | +9,3% |
| 2020 | +33,2% | +109,0% | +301,7% | +137,0% |
| **2021** | **+28,6%** | **−15,2%** | +57,6% | +213,5% |
| 2022 | −0,0% | −0,0% | −65,3% | −79,0% |
| 2023 | +11,5% | +62,7% | +154,5% | +94,6% |
| 2024 | +4,0% | +59,2% | +111,8% | +63,6% |

**2021 es el único año en que E1 le gana a E0** — el año de los 19 latigazos,
donde tener cinco monedas repartidas amortiguó lo que a BTC solo lo mató. En
los otros cinco años pierde, y en 2023 y 2024 pierde por goleada.

### Tres explicaciones descartadas, no supuestas

**No son los costos.** 1,57% anual contra 3,41% permitido. Y la corrida maker
—cota optimista, no creíble— da Calmar 0,289 en vez de 0,268.

**No es el mínimo de 5 USDT.** 4.045 órdenes rechazadas asustaban, así que lo
medí: sin el mínimo, CAGR +12,19% en vez de +12,06%. Con 100 veces el capital,
+12,08%. Ni el filtro ni la escala mueven nada.

**No es el stop de catástrofe.** Se disparó 10 veces en seis años. No es lo
que explica una diferencia de este tamaño.

### Por qué corrió con costos taker, decidido antes de ver el resultado

La especificación pide órdenes maker *"con modelado de no ejecución"* pero
**no da la tasa de ejecución**. Inventarla viola la regla 1, y suponer que la
maker siempre entra es el sesgo que la propia especificación advierte.

Además, **E0 corrió con taker y el criterio 3 los compara entre sí**: si E1
pagara menos comisiones que E0, la comparación mediría el modelo de costos en
vez de la estrategia.

### Las dos hipótesis de rescate, y mi recomendación

La especificación preautoriza exactamente dos: **R1** (ventana de momentum de
90 días en vez de 28) y **R2** (8 posiciones en vez de 5).

**Recomiendo no correrlas.** Hacen falta 1,066 de Calmar y hay 0,268 — un
factor de cuatro. Ninguna ventana ni ningún conteo de posiciones cierra eso. Y
el criterio 4 dice que no hay señal, no que la señal esté mal sintonizada:
buscar la configuración que funcione sobre los mismos datos es exactamente el
error que este proyecto existe para evitar.

Están legítimamente preautorizadas y la decisión es de Felipe.

### Un error real que encontró una prueba

Cuando el stop de catástrofe sacaba una posición a mitad de mes,
`pesos_inversa_volatilidad` renormalizaba y **repartía el peso liberado entre
los que quedaban** — justo lo que la especificación prohíbe. Habría inflado el
resultado subiendo la exposición después de un derrumbe. Ahora los pesos se
calculan sobre la selección completa del mes y el que salió se pone en cero
sin renormalizar; ese peso se va a efectivo.

### Lo próximo, si Felipe decide seguir

Quedan **E2** (largo/corto con perpetuos) y **E3** (carry de financiación).
Las dos necesitan la **medición 5.1** —distribución de tasas de financiación—
que todavía no se hizo, y E3 tiene falsación previa: si el carry neto no cubre
el costo de montar la estructura, **no se codifica**.

Y hay que tener presente lo que ya sabemos: **E2 usa la misma compuerta que
empató en E0 y el mismo universo donde la selección de E1 destruyó valor.**

---

## 30 de agosto de 2026 — E0 NO PASA. La compuerta funciona, pero solo empata

`backtesting/motor_cartera.py` y `strategy/e0.py`, con 23 pruebas propias.
**395 en total, en verde.** Evidencia en `docs/salida_e0_30ago2026.txt`.

**La estrategia E0 falla su condición de falsación.** Es el hallazgo mayor
que la especificación anticipó y pidió anotar aunque doliera.

### El veredicto

| | |
|---|---|
| Calmar(E0) / Calmar(B1), mediana de 20 arranques | **1,017** |
| Umbral de la especificación 6.1 | **1,3** |
| Arranques que lo superan | **0 de 20** |

El rango va de 0,963 a 1,121. **No es que falle por poco en algún arranque:
no lo alcanza en ninguno.**

### E0 contra comprar y esperar, en una línea

| | CAGR | Caída máxima | **Calmar** |
|---|---|---|---|
| **E0** | +37,2% | **−40,2%** | **0,927** |
| **B1** (comprar y mantener BTC) | +70,6% | −76,6% | 0,921 |

**Exactamente la mitad del retorno con exactamente la mitad de la caída.** El
objetivo era "igualar al mercado con la mitad de la caída". Se consiguió la
mitad de la frase.

### El control nulo, que es lo que hace interpretable el resultado

Antes de concluir nada corrí el nulo: ¿y si E0 no fuera más que "menos BTC"?
E0 estuvo en promedio al 39% del capital, así que comparé contra tener ese
39% sin mirar absolutamente nada.

| | CAGR | Caída | **Calmar** |
|---|---|---|---|
| Nulo blando (39% rebalanceado a diario) | +29,8% | −40,3% | 0,740 |
| **Nulo duro** (39% comprado una vez, nunca tocado) | +47,4% | −70,5% | **0,673** |
| **E0** | +37,2% | −40,2% | **0,927** |

**La compuerta sí hace algo: +38% de Calmar sobre el nulo duro.** No es un
adorno. El problema es otro, y es más incómodo:

> Mezclar BTC con efectivo **baja** el Calmar (0,673 contra 0,921 de BTC
> puro). La compuerta recupera todo eso y un poco más — y ese "poco más" te
> deja justo donde estabas si simplemente comprabas BTC.

Todo el trabajo de la compuerta se gasta en compensar el costo de tener plata
quieta.

*(El nulo blando es flojo a propósito y está reportado como tal: rebalancear
a peso fijo todos los días obliga a comprar mientras el mercado cae, y por eso
su caída no es menor que la de E0. El nulo duro es el rival honesto.)*

### Dónde se gana y dónde se pierde: los dos años que explican todo

| Año | E0 | B1 | Exposición media |
|---|---|---|---|
| 2019 | +39,7% | +89,5% | 0,26 |
| 2020 | +109,0% | +301,7% | 0,53 |
| **2021** | **−15,2%** | **+57,6%** | 0,35 |
| **2022** | **−0,0%** | **−65,3%** | **0,00** |
| 2023 | +62,7% | +154,5% | 0,65 |
| 2024 | +59,2% | +111,8% | 0,58 |

**2022 es la compuerta haciendo exactamente su trabajo**: el mercado perdió
65% y E0 no perdió nada, porque estuvo afuera los 365 días.

**2021 es la factura.** El mercado subió 58% y E0 perdió 15%. Es el año que
la medición 5.4 había marcado con **19 cambios de compuerta** — los latigazos
dejaron de ser una estadística y se volvieron un número de resultado.

El seguro contra 2022 se paga con 2021. Al final del período, empatan.

### Los otros criterios

| # | | |
|---|---|---|
| 2 | Caída 40,2% vs 46,0% permitido | **PASA** |
| 4 | IC 95% del CAGR [+3,10%, +89,05%] | **PASA** (excluye cero) |
| 5 | Sin los 3 mejores meses: 17,5% vs 35,3% exigido | **NO PASA** |
| 6 | Costo 0,93% anual vs 9,54% permitido | **PASA** |

El 3 no aplica: E0 **es** la línea base.

**El criterio 5 vuelve a señalar concentración**, que es el mismo problema que
hundió la Fase 1. La curva de retiro:

```
  sin sacar nada    +37,23%   100%
  sin 1 mes         +29,40%    79%
  sin 3 meses       +17,48%    47%
  sin 5 meses        +8,20%    22%
  sin 10 meses       −6,65%   −18%
```

Diez meses de 72 explican más que el resultado entero.

### Lo que NO explica el fallo, y lo verifiqué

**No son los costos.** 0,93% anual, contra 9,54% permitido. La sensibilidad
sin el descuento por BNB da Calmar 0,917 en vez de 0,927: cambia el tercer
decimal, no el veredicto.

**No es el rebalanceo diario.** Sin el mínimo de 5 USDT que impone Binance
—o sea rebalanceando de verdad todos los días— el CAGR da +37,24% contra
+37,23%. Idéntico. La decisión de rebalanceo que se tomó antes de correr no
influyó en el resultado.

### Lo que esto significa para E1 y E2

La especificación lo dice sin vueltas: si E0 falla, **la compuerta de régimen
no está funcionando en este mercado, y E1 y E2 —que usan la misma compuerta—
quedan muy debilitadas antes de probarse.**

Matizado por lo que muestra el nulo: la compuerta **no es inútil**, aporta
+38% de Calmar sobre no hacer nada. Lo que no alcanza es a superar a BTC
puro en una ventana donde BTC hizo +2.364%.

Y ahí está el sesgo declarado en la sección 6 de los criterios: **la ventana
2019-2024 contiene un mercado alcista extraordinario**. B1 es un rival
durísimo acá y lo sería mucho menos en otra década. Eso **no rescata a E0** —
el criterio estaba escrito de antemano y no se toca — pero es parte honesta
de la lectura.

### La decisión es de Felipe

Por regla del proyecto, una hipótesis que falla **no se ajusta ni se vuelve a
correr**, y **no se encadena la siguiente sin preguntar**. E1 está
especificada y lista para escribirse, pero arrancarla es decisión de Felipe
sabiendo que su compuerta es la misma que acaba de empatar.

### De paso, dos errores reales que encontró el motor nuevo

- Un símbolo deslistado se **recompraba y se reliquidaba todos los días**,
  pagando la penalización una vez por jornada hasta el final de la serie. La
  regla que lo arregla: no se compra lo que no se va a poder valuar al cierre.
- Con exposición objetivo 1,0 **ninguna compra se ejecutaba**: el costo se
  paga con efectivo, así que no se puede invertir el 100% del patrimonio. Se
  compra un poco menos, no se rechaza la orden.

---

## 30 de agosto de 2026 — Riesgo v2: el capital que de verdad trabaja es 32%

`risk/pesos.py` y `risk/catastrofe.py`, con 29 pruebas propias. **372 en
total, en verde.** Evidencia en `docs/salida_riesgo_v2_30ago2026.txt`.

La sección 4.4 de la especificación, completa:

```
exposicion_i(t) = G(t) × k(t) × w_i(t)
```

Tres piezas independientes, y ninguna mira qué activo es. Eso lo decide
`strategy/`; `risk/` solo decide con cuánto. Es la regla 3 del proyecto.

### El hallazgo: la cartera corre al 32% del capital

Corrí la capa sobre los datos reales, sin comprar nada — solo calcular qué
exposición habría tenido en cada rebalanceo. Prender el motor en el taller
antes de sacar el auto a la ruta.

| | |
|---|---|
| σ mediana de **un activo** | 94% |
| σ de la **cartera** | 71% |
| **k(t)** = 0,35 / 0,71 | **mediana 0,49** |
| Rebalanceos con k pegado en 1,0 | **1 de 72** |
| Compuerta cerrada | 30 de 72 |
| **Exposición bruta final** | **mediana 0,39, media 0,32** |

**El escalar de volatilidad está abajo casi siempre.** Con una cartera al 71%
anualizado y un objetivo del 35%, `k` casi nunca puede llegar a 1. Sumado a
que la compuerta está cerrada el 42% del tiempo, **el capital que de verdad
trabaja promedia el 32%.**

Esto no está mal — es exactamente lo que un objetivo de volatilidad pide —
pero **cambia cómo hay que leer el resultado de E0.** Una estrategia que
rinda 30% sobre el capital desplegado va a mostrar ~10% sobre el capital
total. Mejor saberlo ahora que interpretando mal el CAGR después.

### El tope del 40% no hace absolutamente nada

| | |
|---|---|
| Peso máximo de un activo | mediana 0,091, **máximo 0,155** |
| Rebalanceos con alguien en el tope | **0 de 72** |

Con veinte activos, la inversa de la volatilidad reparte solo: el promedio es
5% y el más pesado que hubo en seis años fue 15,5%. **El tope nunca se tocó.**

Lo dejo porque la especificación lo fija y como red de seguridad no molesta,
pero **decir que "controla la concentración" sería falso**: no controla nada,
porque no hay nada que controlar. La concentración de esta cartera no viene de
los pesos, viene de la correlación.

### Diversificar ahorra un 25% de volatilidad

94% por activo contra 71% de cartera. Es la contracara del hallazgo de 5.2
(correlación media 0,59) medida en el número que importa. Por eso
`sigma_cartera` **no** se calcula como promedio ponderado de los sigmas: eso
la sobreestimaría y haría que `k` bajara de más todos los días.

### Dos cosas cerradas por código, no por memoria

**`k_max = 1,0` levanta una excepción si alguien pide más.** No es un valor
por defecto que se pisa pasando otro: es la regla 7 del MEGAPROMPT y ahora es
un cerrojo. Los perpetuos entraron para habilitar la pata corta, no para
apalancar.

**El umbral del cortacircuito diario no tiene valor por defecto.** El 3% de la
Fase 1 se medía sobre operaciones cerradas y no se traslada a patrimonio a
precio de mercado sin medirlo de nuevo. La especificación avisa: *"un
cortacircuito que se activa cada semana no es un cortacircuito, es un
parámetro escondido de la estrategia"*. La función para contarlo ya está; el
número sale de E0.

### El agujero de especificación que quedó resuelto

Qué pasa con el peso de una posición que el stop de catástrofe cierra a mitad
de mes. La especificación lo dice y yo lo había marcado como duda: *"el resto
de la cartera no se toca"*. **Ese peso se va a efectivo y ahí se queda hasta
el rebalanceo.** No se reparte entre los que quedan — repartirlo mejoraría el
resultado del backtest y sería aumentar la exposición justo después de que
algo se derrumbó. Hay una prueba que lo fija.

### Dos duplicaciones eliminadas de paso

- `compuerta.py` tenía su propia media móvil. Ahora usa la de
  `strategy/indicators.py`, que ya tiene encima la prueba de no-anticipación.
- La regla de "solo el pasado" (`universo.hasta`) se hizo pública y `risk/` la
  importa en vez de reimplementarla. Una regla de no-anticipación escrita en
  dos lugares se rompe en el segundo.

Los cuatro archivos viejos de `risk/` (Fase 1) siguen ahí porque el motor de
backtest viejo los usa y sus pruebas están en verde. Se retiran cuando se
retire ese motor, no antes.

### Lo próximo

**E0** — la línea base: BTC con filtro de tendencia y volatilidad objetivo.
Es la primera estrategia de la Fase 2, y además decide dos cosas que quedaron
abiertas a propósito: si hace falta el amortiguador de la compuerta, y en
cuánto se fija el cortacircuito diario.

Falta la medición 5.1 (financiación de perpetuos), que **no bloquea**: solo
hace falta para E2 y E3.

---

## 30 de agosto de 2026 — Mediciones 5.2 y 5.4: me equivoqué de dirección

`metrics/transversal.py` y `risk/compuerta.py`, con 17 pruebas propias.
**343 en total, en verde.** Evidencia en
`docs/salida_mediciones_previas_30ago2026.txt`.

### Primero la corrección

En la entrada anterior escribí que 5.2 podía reordenar el plan **a favor de
E0 y en contra de E1**. La medición dice lo contrario, y con margen amplio.
Lo dejo escrito acá en vez de borrarlo, igual que con el filtro de
consolidación de la Fase 1: era una conjetura armada con tres indicios
indirectos, y para eso están las mediciones.

### Medición 5.2 — Dispersión transversal

1.419 observaciones en 72 rebalanceos. Solo 3 quedaron cortadas por
deslistado (0,2%).

| | |
|---|---|
| Desviación estándar transversal a 28 días | **mediana 17,3%** (p10 9,2%, p90 38,0%) |
| **Correlación media por pares** (90 días) | **mediana 0,593** |
| Fechas con correlación sobre 0,80 | **5 de 72 (7%)** |

**El corte de la especificación no se dispara.** El umbral era ~0,80 y la
mediana está en 0,59. Las veinte monedas del universo **no** se mueven todas
juntas: la creencia de que sí venía de mirar quince pares grandes y
parecidos en la Fase 1, y con veinte y seis años no se sostiene.

Los techos, o sea lo que sacaría alguien que adivinara siempre:

| | Cada 28 días |
|---|---|
| Solo largo, mejores 5 contra la canasta | **+22,1%** |
| Largo/corto, mejores 5 menos peores 5 | **+40,9%** |

Contra un peaje de ida y vuelta del 0,33% (promedio de los 20 puestos), el
techo solo-largo **paga el peaje 67 veces**.

**Cuidado con lo que esto significa y con lo que no.** Dice que para la
selección transversal **el costo no es la restricción que manda**: hay
muchísimo espacio entre el peaje y el techo. **No dice que exista señal para
capturarlo.** Nadie llega ni cerca del techo, y un techo alto es condición
necesaria, no suficiente. Lo único que queda cerrado es que E1 no se muere
por comisiones.

Por año, la dispersión es estable (14,7% a 25,9%) y la correlación también
(0,54 a 0,65). No es un artefacto de 2021.

### Medición 5.4 — Frecuencia de la compuerta

BTC contra su media de 200 días, seis años. Y acá el número no es el
promedio: es la forma de la distribución.

| | |
|---|---|
| Cambios de estado | **43** (7,2 por año) |
| Fracción del tiempo dentro | 55% |
| Tramo DENTRO | mediana **6 días**, máximo 385 |
| Tramo FUERA | mediana **12 días**, máximo 381 |

**La mediana de una entrada son 6 días y el máximo son 385.** La compuerta no
es "adentro un año, afuera un año": es un par de regímenes largos de verdad
más una nube de entradas y salidas que no duran nada.

| Tramos que duraron menos de… | Cuántos |
|---|---|
| 5 días | **18** |
| 10 días | 22 |
| 20 días | 26 |
| 30 días | 30 |

**30 de los 44 tramos duran menos de un mes.** Y el reparto por año es brutal:

```
2019   ####                 4
2020   #####                5
2021   ###################  19
2022                        0
2023   #####                5
2024   ##########          10
```

**2022 tiene cero cambios**: BTC estuvo debajo de su media los 365 días. La
compuerta estuvo apagada todo el año bajista, que es exactamente para lo que
existe. Eso es una validación fuerte, no un detalle.

Costo: cada cambio mueve la cartera entera por un lado, **0,165%**. Los 43
cambios cuestan 7,10% del capital en seis años, o sea **1,18% por año solo
por la compuerta**.

### La decisión que NO tomé

Los 18 tramos de menos de 5 días piden un amortiguador a gritos. **No lo
implementé.** La especificación dice que si hace falta es un parámetro nuevo
y se cuenta como tal, y agregar un parámetro es exactamente lo que este
proyecto tiene que hacer despacio. El número ya está sobre la mesa; la
decisión es de Felipe.

Lo que sí conviene saber antes de decidir: **el amortiguador no es gratis.**
Retrasa las salidas, y la salida que importa es la de enero de 2022. Ahorrar
1,18% al año no sirve de nada si el precio es entrar tarde al único año en
que la compuerta hizo su trabajo. Eso se mide en E0, no se supone acá.

### Lo próximo

1. **Riesgo v2** — la reescritura de `risk/`. La compuerta ya está hecha y
   probada; faltan los pesos por inversa de volatilidad con tope del 40%, el
   escalar `k(t)` con σ objetivo 35% y `k_max = 1,0`, y el stop de catástrofe.
2. **E0** — la línea base, que además decide lo del amortiguador.

Medición 5.1 (financiación de perpetuos) sigue pendiente y **no bloquea**:
solo hace falta para E2 y E3.

---

## 30 de agosto de 2026 — Costos v2: lo que cuesta operar, por venue

`execution/costos.py` y `execution/filtros.py`, con 37 pruebas propias.
**326 en total, en verde.** Evidencia en `docs/salida_filtros_30ago2026.txt`.

Es el punto 4.3 de la especificación de la Fase 2. Reemplaza al modelo de la
Fase 1, que era un número solo (0,1% + 0,05%, igual para todo) y servía
porque solo había un venue, un tipo de orden y quince pares parecidos.

### Lo que ahora se distingue

| | |
|---|---|
| **Venue** | Spot (0,10% maker y taker) y perpetuo USDT-M (0,02% / 0,05%) |
| **Tipo de orden** | maker o taker, explícito |
| **Slippage** | por rango de liquidez: 0,03% / 0,05% / 0,10% por lado |
| **Financiación** | cada 8 horas (00, 08 y 16 UTC), con su signo |
| **Filtros** | `stepSize`, `minNotional`, `tickSize` |

Hay una prueba que **reproduce la tabla de peajes de la especificación**
completa, los cinco escenarios, exactos. Si alguien mueve un tramo de
slippage, se cae ahí y no seis meses después en un resultado raro.

### Tres decisiones que empujan hacia el lado caro

**El descuento por BNB viene apagado.** Binance descuenta 25% en Spot y 10%
en futuros, pero **eso todavía no está verificado contra la cuenta real** —
la especificación lo deja como pendiente de ingeniería. Un backtest que se
regala un 25% que después no existe miente a favor.

**Una tasa de financiación faltante levanta un error, no vale cero.** Un cero
silencioso convierte un backtest de perpetuos inválido en uno que se ve
impecable.

**El redondeo va siempre hacia abajo.** Redondear al más cercano es comprar
más de lo que el efectivo alcanza: en el backtest el patrimonio absorbe la
diferencia sin quejarse, y en vivo la orden es rechazada.

### El riesgo de no ejecución NO está modelado, y está declarado

Una orden maker puede no completarse nunca. Suponer que siempre entra es
quedarse con el ahorro del spread sin pagar su costo, y ese sesgo **se ve
igual que una estrategia buena**. Quien use órdenes maker tiene que modelar
el reintento por su cuenta. El módulo cobra lo que se le pide cobrar; no
averigua si la orden entró.

### Los deslistados SÍ están en exchangeInfo

Suponíamos que no, y por eso `filtros.py` tenía una red de seguridad para
ellos. Están: `exchangeInfo` devuelve 3.685 símbolos, y LUNAUSDT, LINAUSDT,
RENUSDT y UNFIUSDT vienen con su `stepSize` real. **Cobertura del 100% sobre
los 116 símbolos del universo reconstruido.**

Es la misma lección que el archivo de velas: los muertos están ahí si uno no
filtra por `status == "TRADING"`. Por eso el traductor no filtra por status,
aunque en ese archivo pareciera inofensivo hacerlo.

### Pero los filtros son de distinta época, y eso no se puede corregir

Binance no versiona `exchangeInfo`. Lo que devuelve hoy es una mezcla, y se
nota mirando los mínimos de nocional del universo:

| Mínimo | Símbolos | Qué son |
|---|---|---|
| 1 USDT | 10 | memecoins de precio muy bajo: SHIB, PEPE, BONK, DOGE, WIF… |
| 5 USDT | 103 | el mínimo vigente hoy |
| **10 USDT** | **3** | BCHABC, BTT y ERD — **muertos, congelados en el mínimo viejo** |

Esos tres son la prueba de que el mínimo de Spot **era 10 USDT** y bajó. O
sea que en la parte vieja de la ventana el backtest deja pasar órdenes de 5
USDT que en su momento habrían sido rechazadas. Es un sesgo **optimista**,
chico (con 500 USDT en 5 posiciones cada una ronda los 100), y queda
**declarado en vez de corregido porque el dato para corregirlo no existe**.

### Lo próximo

1. **Riesgo v2** — la reescritura de `risk/`, el pedazo más grande de la fase.
2. Mediciones 5.2 (dispersión transversal) y 5.4 (frecuencia de la compuerta).
3. Recién ahí, E0.

**5.2 puede reordenar el plan.** La especificación misma dice que si la
correlación media entre pares supera 0,80, E1 y E2 pierden prioridad frente a
E0. Y hay dos hallazgos previos que apuntan al mismo lado: *la restricción que
manda es la caída, no el retorno*, y *el escalar de volatilidad `k_t` por sí
solo no compra Calmar*. Los tres juntos sugieren que **E0 pesa más de lo que
el plan supone y la selección transversal de E1 menos.**

---

## 30 de agosto de 2026 — El universo reconstruido, y LUNA está adentro

`core/universo.py` con 19 pruebas propias. **289 en total, en verde.**
Evidencia en `docs/salida_universo_30ago2026.txt`.

### La prueba visible de que funciona

El top 10 por liquidez, reconstruido en cada enero mirando **solo el pasado**:

```
2019-01-01  BTC, ETH, EOS, XRP, TRX, BNB, ADA, XLM, LTC, NEO
2020-01-01  BTC, ETH, BNB, TRX, MATIC, XRP, EOS, LTC, VET, LINK
2022-01-01  BTC, ETH, LUNA, BNB, MATIC, SAND, SOL, SHIB, AVAX, XRP
2024-01-01  BTC, ETH, SOL, XRP, AVAX, BNB, ADA, DOGE, OP, MATIC
```

**LUNA está en el universo de enero de 2022** — la moneda que se fue a cero en
mayo de ese año. Con el universo de la Fase 1 nunca habría aparecido, y ese es
exactamente el tipo de posición que un backtest optimista no toma nunca.

Si en 2019 aparecieran los mismos nombres que hoy, la reconstrucción no
estaría funcionando.

### Medición 5.3 — Rotación del universo

| | |
|---|---|
| Mensual | mediana 15,0%, media 16,5%, máxima 40% |
| **Anual punta a punta** | **mediana 41%, media 43%** |

**Las dos no son comparables entre sí**, y confundirlas era fácil: la mensual
sumada doce veces cuenta varias veces al símbolo que entra y sale. La
literatura (Grobys) reporta **37% anual** sobre las 30 mayores por
capitalización, así que la que hay que comparar contra ese número es la anual
— y **41% contra 37% es un encaje muy bueno**, lo cual también valida que el
volumen cotizado no es un sustituto disparatado de la capitalización.

**Costo forzado: ~0,49% anual** antes de que la señal haga absolutamente nada.
Si un símbolo sale del top 20 hay que venderlo, opine lo que opine la
estrategia.

La rotación casi se duplica de 2019-2020 (8-12% mensual) a 2021-2024 (15-22%).

### Medición 5.5 — Y un hallazgo que la especificación no contempla

De 116 símbolos que pasaron por el universo, **22 desaparecieron del archivo.
Pero cinco de esos no murieron: se cambiaron de nombre.**

| Viejo | Nuevo | Días entre la última y la primera vela |
|---|---|---|
| MATICUSDT | POLUSDT | +3 |
| RNDRUSDT | RENDERUSDT | +4 |
| FTMUSDT | SUSDT | +3 |
| BTTUSDT | BTTCUSDT | +8 |
| BCHABCUSDT | BCHUSDT | +0 |

**Importa porque la especificación pide castigar cada deslistado con −20% y
−50% de sensibilidad.** Aplicarle eso a un cambio de nombre no es ser
conservador: es estar equivocado, y encima empujando el resultado hacia el
lado que uno cree seguro, que es la peor forma de equivocarse.

Quedan **17 muertes de verdad**, y son muertes en serio: LUNA −100% desde su
pico, LINA −99,8%, REN −97,6%, UNFI −96,8%.

**La lista de renombramientos es a mano y a propósito.** Detectarlos por
heurística —«murió uno y nació otro cerca»— daría falsos positivos todo el
tiempo, porque en cripto nacen monedas todas las semanas.
`detectar_renombramientos_candidatos()` **propone**; una persona confirma y
agrega la línea con su evidencia.

### La regla que gobierna el módulo

**En la fecha t solo se mira información anterior a t.** Está escrito una sola
vez, en `_hasta(panel, fecha)`, porque es el tipo de regla que se rompe en el
segundo lugar donde se reimplementa.

Hay dos pruebas que lo verifican de frente: una corre el mismo universo sobre
dos paneles idénticos salvo por lo que viene *después* y exige que la decisión
no cambie; la otra exige que un símbolo que muere en 2022 aparezca en el
universo de 2020.

Se agregó un filtro que la especificación no traía: **un par tiene que haber
operado en los últimos 7 días** para entrar. Sin eso, uno que murió en 2021
seguiría entrando al universo de 2023 con el volumen de su mejor momento. No
es mirar al futuro: que un par no tenga velas recientes se sabe en t.

### Tamaño efectivo

65 de 72 fechas tienen los 20 completos. Las 7 que no son de 2019, cuando
todavía no había 20 pares USDT con 180 días de historia — la primera arranca
con 15.

### Lo próximo

1. **Costos v2** — por venue, maker/taker, financiación, slippage por rango de
   liquidez, y los filtros de `LOT_SIZE`/`minNotional`.
2. **Riesgo v2** — la reescritura de `risk/`, el pedazo más grande de la fase.
3. Mediciones 5.2 (dispersión transversal) y 5.4 (frecuencia de la compuerta).
4. Recién ahí, E0.

---

## 30 de agosto de 2026 — 650 pares en disco, 190 de ellos muertos

**270 pruebas en verde.** Etapa 0 avanzada: compromiso previo commiteado,
cerrojos de futuros verdes, y la capa de datos del archivo funcionando.

### Los datos

| | |
|---|---|
| Símbolos | **650** |
| Velas diarias | **762.914** |
| **Deslistados** | **190 (29% del universo)** |
| Vivos hoy | 460 |
| Rango | 2017-08-17 a 2026-07-31 |
| Problemas de integridad | **0** |

**Ese 29% es exactamente lo que la Fase 1 no vio.** Y con universo
equiponderado, la literatura estima el sesgo en 62% anualizado.

### El compromiso previo y los cerrojos

`docs/FASE_2_criterios.md`, commiteado **antes** de bajar un solo dato. Con
dos correcciones sobre la especificación: **criterio 1 por pares** (decisión
tuya) y **criterio 3 con piso** en `max(Calmar(B0), Calmar(B1))`, porque si E0
sale malo superarlo por 15% es trivial y el criterio se queda sin dientes.

Los cerrojos ahora cubren futuros y **se verificaron en rojo**: se metió un
archivo temporal con `futures_change_leverage` y `futures_create_order`, los
dos dieron rojo, y se borró. Un cerrojo que nunca se vio fallar no es un
cerrojo. Se agregaron además dos pruebas sobre **la lista blanca en sí
misma** — el código de hoy puede no llamar a nada peligroso, pero si la lista
blanca lo permite, `llamar_solo_lectura()` es una puerta abierta a una línea
de distancia.

### Tres bugs propios, los tres del mismo tipo: fallan en silencio

**1. `.values` sobre un índice con zona horaria la descarta.** El código no
falla; el índice queda ingenuo y después no se puede comparar contra las
fechas de la ventana de diseño. Lo atrapó una prueba.

**2. Un símbolo con caracteres no ASCII rompía la descarga.** `urllib` no
puede ni armar la petición. Se perdió un símbolo entero en la primera corrida.
El primer arreglo fue peor: escapé en `Mercado.ruta_simbolo`, pero `_listar`
ya escapaba, así que el prefijo se escapaba **dos veces** y el listado
devolvía cero meses sin ningún error visible. El escapado va en el punto de
uso, una sola vez.

**3. El grave: las dos unidades de tiempo conviven en el mismo archivo.**

Binance cambió `open_time` de milisegundos a microsegundos a mitad de camino,
y **en el mes del cambio las dos están en el mismo mensual**. KLAYUSDT
2024-10:

```
1727740800000,0.13450000,...       <- 13 dígitos, milisegundos
1730246400000000,0.12550000,...    <- 16 dígitos, microsegundos
```

Mi detección miraba el máximo del archivo entero, así que mandaba a leer todo
como microsegundos y las 30 filas en milisegundos **caían en 1970**. El código
no fallaba. La serie quedaba con fechas imposibles y nadie se enteraba.

**Solo se descubrió auditando las 650 descargadas**, no revisando el código.
Ahora la conversión es fila por fila, con las cuatro bandas (segundos,
milisegundos, microsegundos, nanosegundos), y hay tres pruebas nuevas.

De 650 símbolos, **uno solo** estaba afectado. Se rehizo.

### La decisión de diseño que no hay que romper

`simbolos_disponibles()` **no filtra por estado**, y hay una prueba que exige
que el filtro estático no consulte `TRADING`, `BREAK`, `status` ni
`exchange_info`.

El sesgo de la Fase 1 no entró por usar el endpoint equivocado, entró por
filtrar `status == "TRADING"`. **Si alguien cambia la fuente de datos y
mantiene ese filtro, el sesgo vuelve entero.**

Los filtros que sí se aplican al descargar son **estáticos** —dependen solo
del nombre— y los que dependen de la fecha (antigüedad mínima, ranking por
liquidez, top 20) van aparte: decidir hoy quién estaba en el universo en 2020
sería filtrar el futuro hacia el pasado.

### Lo próximo

1. **Reconstrucción del universo mes a mes** — matriz de disponibilidad
   símbolo × mes, ranking por mediana del volumen cotizado de 30 días, top 20
   en cada fecha de rebalanceo.
2. Costos v2 (por venue, maker/taker, financiación, slippage por rango).
3. Riesgo v2 — la reescritura de `risk/`, el cambio más grande de la fase.
4. Las cinco mediciones previas, y recién ahí E0.

Perpetuos y tasas de financiación quedan para cuando haga falta E2/E3: los
cerrojos ya están listos, pero **no se baja nada de eso hasta que E0 y E1
justifiquen el trabajo**.

---

## 30 de agosto de 2026 — El criterio 1 se arregla por pares. Robustez lista

**229 pruebas en verde.** `metrics/robustez.py` nuevo, con las cuatro
herramientas que la especificación pide en la sección 3.2.

### La decisión de Felipe sobre el criterio 1

**Comparación por pares.** Para cada una de las 20 fechas de arranque que la
especificación ya pedía (sección 7.2), se compara el Calmar de la estrategia
contra el de B1 **sobre esa misma ventana**, y se exige que el cociente supere
1,8 en la mediana.

Así la fecha arbitraria se cancela sola, y no agrega trabajo: esas corridas ya
estaban planificadas para la prueba de robustez. Hay una prueba que lo fija —
si la estrategia *es* el benchmark, el cociente da 1,000 exacto en todos los
arranques, sin importar cuál sea la ventana.

### Las cuatro herramientas

- **Comparación por pares** — contesta si el resultado depende del calendario.
- **Bootstrap por bloques** (30 días, 10.000 remuestreos, semilla fija) —
  contesta si el CAGR podría ser cero y tuvimos suerte. Por bloques y no día a
  día porque la volatilidad viene en rachas; remuestrear días sueltos rompe esa
  estructura y devuelve un intervalo demasiado angosto, o sea optimista.
- **Curva de retiro top-k** — reemplaza la bandera de concentración de la
  Fase 1. No pregunta «hay un mes grande» sino **cuánto sobrevive sin él**.
- **Deflated Sharpe Ratio** — le pone número formal a lo que la Fase 1 midió a
  mano (el barrido inflaba entre 20% y 200%).

### Dos errores propios, anotados porque valen

**1. Un bug real en la curva de retiro.** Usaba
`resample("ME").last().pct_change()`, y eso descarta el primer valor: se
perdía entero el tramo del inicio de la serie al primer fin de mes. Medido
sobre 1.200 días, el retorno real era **0,461 y la cadena mensual daba
0,576**. Toda la curva estaba corrida.

Lo atrapó una prueba roja, no una revisión. Y quedó fijado con el invariante
más barato posible: **con k=0 no se saca nada, así que tiene que dar el CAGR
exacto.** Ahora coincide a 1e-9.

**2. Una suposición mía que era falsa.** Escribí una prueba dando por sentado
que media exposición mejora el Calmar. Falló, y al medirlo sobre 20 semillas:
**mejora en 14 de 20, no siempre.**

No es un detalle de la prueba, importa para el proyecto: **el escalar de
volatilidad `k_t` por sí solo no compra Calmar.** El que hace el trabajo es la
compuerta de régimen. Se suma a lo que ya decía la tabla de criterios — la
restricción que manda es la caída, no el retorno — y las dos apuntan a lo
mismo: **E0 es más importante de lo que el plan sugiere, y la selección
transversal de E1 menos.**

### Lo próximo

1. Cerrojos de futuros verdes. El MEGAPROMPT lo exige **antes** de bajar un
   solo dato de perpetuos.
2. Capa de datos desde el archivo, universo reconstruido mes a mes.
3. Costos v2 y riesgo v2.
4. Las cinco mediciones previas, y recién ahí E0.

Los criterios de la Fase 2 **todavía no se commitearon como compromiso
previo**. Falta hacerlo, con el criterio 1 ya en su forma por pares, antes de
bajar datos nuevos.

---

## 30 de agosto de 2026 — Calmar(B1) = 0,921, y el criterio 1 tiene un problema

Módulo `metrics/` nuevo (métricas, benchmarks y la barrera del holdout), con
20 pruebas propias. **214 pruebas en total, todas en verde.** Evidencia en
`docs/salida_benchmarks_30ago2026.txt`.

### El número que faltaba

**B1 — comprar BTCUSDT el 1-ene-2019 y no hacer nada hasta fin de 2024:**

| | |
|---|---|
| CAGR | **+70,55%** |
| Caída máxima | **−76,6%** (847 días sin recuperarse, nov-2021 a mar-2024) |
| **Calmar** | **0,921** |
| Volatilidad | 65,6% anualizada |

De ahí salen las dos varas: **criterio 1 pide Calmar ≥ 1,657** y **criterio 2
pide caída ≤ 46,0%**.

### Los criterios 1 y 2 no son independientes, y eso cambia la lectura

El Calmar tiene la caída en el denominador, así que cortar más la caída afloja
lo que el criterio 1 pide de retorno:

| Su caída | = × B1 | CAGR que necesita | = % de B1 |
|---|---|---|---|
| 46,0% | 0,60 | 76,2% | **108%** |
| 38,3% | 0,50 | 63,5% | 90% |
| 30,6% | 0,40 | 50,8% | 72% |
| 23,0% | 0,30 | 38,1% | 54% |
| 15,3% | 0,20 | 25,4% | 36% |

**En el tope de caída permitido hay que superar a comprar y esperar** — que es
justo la formulación literal que el analista advirtió que era casi con
seguridad inalcanzable. No se vuelve razonable hasta cortar la caída bastante
más abajo del tope.

**La restricción que manda es la caída, no el retorno.** Eso reordena el
trabajo: la compuerta de régimen y el escalar de volatilidad son la parte que
decide si algo pasa, no la selección de activos.

### El problema serio: la vara depende de una fecha arbitraria

Se midió Calmar(B1) arrancando cada mes entre ene-2019 y ene-2021, todos
terminando el 31-dic-2024:

| | |
|---|---|
| Calmar(B1) más bajo | **0,439** (arrancando ene-2021) |
| Calmar(B1) más alto | **0,973** (arrancando feb-2019) |
| Lo que exige el criterio 1 | entre **0,79 y 1,75** |

**El criterio 1 exige más del doble según de qué día arranque la ventana**, y
el 1-ene-2019 no se eligió por ninguna razón de fondo. Tal como está, ese
criterio mide en parte la estrategia y en parte el calendario.

**Propuesta, todavía sin decidir:** en vez de comparar contra un Calmar(B1)
fijo, comparar **por pares** — para cada fecha de arranque, el Calmar de la
estrategia contra el Calmar de B1 **sobre esa misma ventana**, y exigir que el
cociente supere 1,8 en la mediana de los arranques. La especificación ya pide
20 fechas de arranque para robustez (sección 7.2); esto es aplicarle lo mismo
al benchmark, y así la fecha arbitraria se cancela.

**Decisión de Felipe pendiente.** Importa resolverlo ahora: los criterios de
la Fase 2 todavía no se commitearon como compromiso previo, y una vez
commiteados no se tocan.

### Lo que se construyó

- **`metrics/ventana.py`** — la barrera del holdout, como candado y no como
  acuerdo. Cualquier función que reciba datos posteriores al 31-dic-2024
  levanta `HoldoutBloqueado` salvo `permitir_holdout=True` explícito. Un
  holdout que se puede mirar sin querer no protege de nada.
- **`metrics/metricas.py`** — CAGR, volatilidad, caída máxima con su duración,
  Calmar, Sortino, tiempo en mercado. Todo sobre **curva de patrimonio
  diaria**, no sobre operaciones: la decisión D2 cambia la contabilidad a
  pesos, y una métrica atada al concepto de operación habría que reescribirla
  de nuevo. Anualiza con 365, no 252 — cripto opera todos los días.
- **`metrics/benchmarks.py`** — B1. B2 y B0 entran cuando existan el universo
  reconstruido y E0.

### Lo próximo

1. **Resolver el criterio 1** (decisión de Felipe).
2. Cerrojos de futuros verdes — el MEGAPROMPT lo exige antes de bajar un solo
   dato de perpetuos.
3. Capa de datos desde el archivo, con el universo reconstruido mes a mes.
4. Resto de la etapa 0: costos v2, riesgo v2, robustez (bootstrap, top-k, DSR).

---

## 30 de agosto de 2026 — FASE 2 ABIERTA. MEGAPROMPT v2.0 y el sesgo, medido

### El MEGAPROMPT pasó a v2.0

Felipe aprobó incorporar las tres decisiones del analista (D1 perpetuos, D2
cartera con pesos, D3 la vara del Calmar). **Va en su propio commit
(`0882de5`) a propósito:** el MEGAPROMPT manda sobre todo lo demás y decía
«Binance Spot, sin apalancamiento». Cambiarlo escondido dentro de un commit
de infraestructura habría dejado dos documentos de gobernanza en desacuerdo.

**No se relajó ninguna restricción de seguridad — se agregaron dos reglas:**

- **Regla 7:** `k_max = 1,0` es tope duro. Los perpetuos entran para habilitar
  la pata corta y bajar comisiones, **no para apalancar**.
- **Regla 8:** los cerrojos cubren futuros igual que Spot. Abrir el alcance
  sin ampliar la prueba que lee el código fuente dejaría un hueco justo en la
  garantía de que el bot no puede operar. **Mientras esa prueba no esté verde,
  no se baja un solo dato de perpetuos.**

Y la llave de API pasa a exigirse sin permiso de futuros habilitado.

### Una colisión de nombres que había que resolver

El documento del analista llama «Fase 2» a la investigación de estrategias,
pero en la v1.0 **la Fase 2 era Testnet**. Se renumeraron **solo las fases que
todavía no ocurrieron**: Testnet pasa a Fase 3 y Mainnet a Fase 4. Las
cerradas quedan como estaban para no romper todo lo ya escrito.

### Se agregó algo que la especificación no traía

**El DSR se reporta siempre**, con el número de configuraciones probadas — no
solo «si se vuelve a barrer», como decía la especificación. Probar E0, E1,
E1-R1, E1-R2, E2 y E3 sobre la misma ventana **ya es comparación múltiple**
aunque cada valor venga de literatura. El riesgo se mudó de la máquina al
investigador; el holdout lo cubre en parte, el DSR le pone número.

### El supuesto del archivo: CONFIRMADO, y el sesgo por fin medido

Primera tarea de la Fase 2, y a propósito la más barata:
`tools/verificar_archivo_binance.py`. Evidencia en
`docs/salida_verificacion_archivo_30ago2026.txt`.

**6 de 6 pares deslistados bajaron con checksum válido.** El archivo sirve
velas de pares que ya no se operan. La etapa 0 puede construirse encima.

**Y ahora el sesgo de la Fase 1 tiene número:**

| | |
|---|---|
| Pares USDT operando hoy | 485 |
| Pares USDT deslistados | 250 |
| **La Fase 1 vio solo el** | **66% del mercado que existió** |

### Un matiz sobre dónde estaba realmente el agujero

La especificación dice que el archivo tiene símbolos que `exchangeInfo` no
tiene. **Eso es casi falso:** comparando contra todo `exchangeInfo` aparecen
apenas 25 símbolos extra, 1 solo contra USDT.

Lo que pasa de verdad es que **Binance no borra un par deslistado de
`exchangeInfo` — lo deja con estado `BREAK`**, a veces por años. Hay 2.327
símbolos en ese estado, 250 de ellos contra USDT.

**El sesgo de la Fase 1 no entró por usar el endpoint equivocado. Entró por
filtrar `status == "TRADING"`** en `tools/elegir_universo.py`. El arreglo
funciona igual, pero conviene saber dónde estaba el agujero: si alguien
«arregla» solo la fuente de datos y sigue filtrando por TRADING, el sesgo
vuelve entero.

*(La primera versión de este verificador cometió ese mismo error y reportó 25
deslistados. Queda anotado porque es el tipo de error que se repite.)*

### Lo próximo

**Calcular Calmar(B1)** — comprar BTC el 1-ene-2019 y no hacer nada hasta fin
de 2024. Es una hora de trabajo y decide si el criterio 1 (Calmar ≥ 1,8 ×
Calmar(B1)) es alcanzable o imposible. Antes de reescribir `risk/`, que es la
parte pesada.

Después, en orden: cerrojos de futuros verdes → capa de datos del archivo →
resto de la etapa 0.

---

## 30 de agosto de 2026 — FASE 1 CERRADA. La estrategia se descarta

### El veredicto

Corrieron los 15 pares en 4h. **De los cuatro criterios commiteados antes de
bajar los datos, fallan dos:**

| Criterio | Resultado | |
|---|---|---|
| 1. Al menos 8 de 15 en positivo | **7 de 15** | NO PASA |
| 2. Ningún par aporta >50% | BTC aporta 49% | PASA |
| 3. Ninguna operación aporta >20% | **la mejor aporta 36%** | NO PASA |
| 4. Neto agregado positivo | +193.39 | PASA |

El criterio 1 se falló **por un solo par**. No se tocó — para eso se escribió
antes. El criterio 3 no se falló por poco: una operación explica más de un
tercio de seis años de resultado sobre quince mercados.

### Y ahora sí había muestra, que era todo el punto

**500 operaciones fuera de muestra.** Ya no se puede decir «no sabemos porque
son pocas». Se sabe: **+193 USDT sobre 7.500 de capital en seis años, 2,6%
total, ~0,4% anual** — y antes de descontar el sesgo de supervivencia. La
mediana de los pares es negativa. La ventaja de 4h era real en BTC y ETH y
**no se generaliza**.

### Corrección de una conclusión anterior

Con dos pares se concluyó que **el filtro de consolidación no aportaba
información y solo sacaba operaciones**. Con quince se da vuelta: en agregado
convierte **−69 en +193**.

Lo que hace es **limitar daño**, no generar señal: recorta las pérdidas de los
pares malos (NEO −139 → −14, ONT −124 → −23, ICX −86 → −12) a costa de los
buenos (ADA +108 → +78, BNB +76 → +27).

**Queda como lección, no borrada:** aquella conclusión estaba armada sobre
cuatro mediciones, y cuatro no alcanzaron. Está escrita en el informe.

### La decisión

**Felipe cerró la Fase 1 y descartó la estrategia de rupturas.** Va a llevar
el informe a una consulta externa con perfil de analista de cripto para
definir qué estrategia probar después.

`docs/FASE_1_informe.md` se reescribió entero para eso: **está escrito para
sostenerse fuera del repo**, sin suponer conocimiento del proyecto. Su
**sección 6 son las seis restricciones medidas** —el peaje del 0,30% contra la
ventaja por operación, que acertar la dirección no es ganar, que los umbrales
absolutos no son comparables entre temporalidades, que la concentración
detecta lo que el PF no, cuánto infla un barrido en retrospectiva, y que un
filtro puede valer por reducir varianza— que es lo que sobrevive al cierre.

### Lo próximo

**Nada, hasta que Felipe traiga la definición de la estrategia nueva.** No
propongas una por tu cuenta ni empieces a escribir `strategy/`.

Cuando llegue: cambiar de estrategia significa reescribir **solo**
`strategy/`. Datos, indicadores, riesgo, backtest, walk-forward y los tres
cerrojos se reusan tal cual, con 194 pruebas.

---

## 30 de agosto de 2026 — COMPROMISO PREVIO: 15 pares en 4h

**Esta entrada se escribió y se commiteó ANTES de bajar los datos y ANTES de
correr nada.** Ese es todo el punto: un criterio escrito después de ver el
resultado no es un criterio, es una justificación.

### Qué se va a hacer, y por qué no es una tercera hipótesis

La hipótesis de la temporalidad (entrada de abajo) quedó sostenida pero sin
muestra: 10 y 9 operaciones por año en dos pares. **No se cambia la
hipótesis ni el método — se le da más mercado a la misma pregunta.** Mismo
walk-forward, mismo barrido de un solo parámetro, mismos candidatos, mismo
trailing fijo. Lo único que cambia es cuántos pares se miran.

Decisión de Felipe del 30-ago-2026, después de que se le presentaran las
cuatro opciones incluida la de cerrar.

### El universo, elegido por una regla ciega al resultado

`tools/elegir_universo.py`. La regla no consulta ningún backtest: par contra
USDT operable hoy, base que no sea stablecoin ni fiat, que no sea token
apalancado, y con primera vela anterior al 1-ene-2019 para que tenga el mismo
período que BTC y ETH. De 476 pares USDT, califican **15**:

```
BTCUSDT ETHUSDT BNBUSDT NEOUSDT LTCUSDT QTUMUSDT ADAUSDT IOTAUSDT
XLMUSDT XRPUSDT ETCUSDT ICXUSDT ONTUSDT TRXUSDT VETUSDT
```

**No los elegí yo.** Si hubiera escrito la lista a mano vendría teñida por lo
que sé de cada moneda.

### El sesgo que esta regla NO arregla

**Supervivencia.** Binance solo sirve velas de los pares que hoy existen. Las
monedas que se listaron en 2018 y se murieron no están acá y no hay forma de
traerlas desde ese endpoint. El universo es «las que sobrevivieron ocho
años», y eso favorece a cualquier estrategia que compre y aguante.

**Cualquier número que salga de esto está inflado por una cantidad que no se
puede medir.** La advertencia viaja pegada al resultado, siempre.

### Los cuatro criterios, fijados ahora

Se juzga **el agregado de los 15**, no el mejor. Para dar la hipótesis por
sostenida tienen que cumplirse los cuatro:

1. **Amplitud.** Al menos **8 de los 15** pares con neto positivo fuera de
   muestra. Si el efecto es real se ve en la mayoría, no en tres.
2. **Ningún par domina.** El de mejor resultado aporta **menos del 50%** del
   neto agregado.
3. **Ninguna operación domina.** La mejor operación individual aporta **menos
   del 20%** del neto agregado.
4. **El neto agregado es positivo**, y se reporta al lado de la referencia
   SIN FILTRO sobre el mismo universo.

**Si no se cumplen los cuatro, la hipótesis no se sostiene y la Fase 1 se
cierra.** No se ajusta el criterio, no se saca el par que molesta, no se
prueba otra temporalidad. Queda escrito acá para que no haya discusión
después.

Solo 4h: el control de 1h ya se corrió y está en la entrada de abajo.

---

## 30 de agosto de 2026 — 4h es mejor de verdad, y aun así no alcanza

Se corrió el walk-forward de la segunda hipótesis: **«las temporalidades más
altas pagan el peaje»**. Evidencia completa en
`docs/salida_walkforward_umbral_30ago2026.txt`, generada por
`main_walkforward_umbral.py`. 194 pruebas en verde.

### Qué se barrió, y por qué solo eso

Decisión de Felipe: se barre **un solo parámetro**, el umbral relativo de
consolidación, con el trailing fijo en 2xATR. Barrer dos a la vez habría dado
25 combinaciones por ventana en lugar de 5, y con eso cinco veces más chances
de encontrar algo lindo por azar.

El menú `[1.0, 1.2, 1.4, 1.6, 1.8]` salió de la distribución real de
`desv_rel` (1.0 ≈ percentil 10 de las velas, 1.8 ≈ percentil 65), no de la
intuición. Cuál se usa lo eligió el walk-forward ventana por ventana.

**1h fue incluido como control**, para poder distinguir «mejoró la
temporalidad» de «mejoró el filtro».

### El resultado

| | BTC 1h | BTC 4h | ETH 1h | ETH 4h |
|---|---|---|---|---|
| Ops por año | 33 | **10** | 36 | **9** |
| Estabilidad | INESTABLE (100%) | ESTABLE (25%) | INESTABLE (100%) | ESTABLE (25%) |
| Concentración | (neto negativo) | **28%** | 49% | **31%** |
| PF | 0.81 | 1.64 | 1.17 | 1.94 |
| Capital 6 años | −17.6% | +18.9% | +17.1% | +15.1% |
| Inflación del barrido tramposo | +57 USDT | +18 | +58 | +24 |

### La hipótesis se sostiene. La forma limpia de verlo

La comparación con el filtro elegido está contaminada por la elección del
parámetro. La comparación **sin filtro** no: ahí no se elige nada.

| Sin filtro de consolidación | 1h | 4h |
|---|---|---|
| BTC | −50.84 (370 ops) | **+106.01** (85 ops) |
| ETH | +23.81 (364 ops) | **+101.96** (77 ops) |

**4h le gana a 1h en los dos pares, con cero parámetros elegidos.** Es lo que
predecía la anatomía del peaje del 29-ago. Y los otros tres indicadores
apuntan al mismo lado: 4h es ESTABLE en los dos pares y 1h INESTABLE en los
dos; la concentración baja a 28-31% (contra 161% y 82% en la Fase 1); y el
barrido tramposo infla 18-24 USDT en 4h contra 57-58 en 1h.

**Es el primer resultado del proyecto que no se cae al mirarlo de cerca.**

### Y aun así no alcanza. Dos razones

**1. La cantidad de operaciones**, que era el criterio escrito *antes* de
correr: 10 y 9 por año contra las ~15 pedidas. **No es culpa del filtro**:
apagándolo del todo, 4h da 14 y 13 por año. Es el techo estructural de la
estrategia en esa temporalidad. Seis años fuera de muestra dan 52-61
operaciones en total — unas 20-25 ganadoras. El margen de error sobre eso es
enorme.

**2. Anualizado, el resultado es muy chico:** +18.9% en seis años son **2,9%
anual** (BTC) y +15.1% son **2,4% anual** (ETH). Positivo, pero no paga el
riesgo de tener capital en cripto, ni se acerca a comprar y esperar.

### Hallazgo aparte: el filtro de consolidación no aporta información

No era la hipótesis; salió de la referencia de control. **En 3 de los 4 casos
apagar el filtro da mejor que elegirlo con walk-forward** (BTC 4h, ETH 4h,
BTC 1h; solo en ETH 1h se paga a sí mismo).

Y la matriz de candidatos en 4h es **monótona creciente en las 12 ventanas**:
el walk-forward eligió 1.8 —el borde de arriba del menú— en 9 de 12. No está
buscando un óptimo, está caminando hacia la salida. Le preguntamos «cuánto
filtro querés» y contesta «cada vez menos», hasta donde lo dejamos.

Importa porque la consolidación es **una de las cuatro condiciones de entrada
de la estrategia**, y resulta que solo saca operaciones.

### Estado

**Fase 1 sigue REABIERTA.** Los `null` siguen en `null`.

**Cuenta de hipótesis sobre estos datos: van 2, y las dos terminaron igual —
un mecanismo real que no alcanza.** La regla del proyecto es no encadenar una
tercera sin decisión de Felipe. **Queda pendiente esa decisión.**

Nada de lo medido antes cambió: `main_walkforward.py` (modo absoluto, barrido
del trailing) quedó intacto para poder reproducir la Fase 1, y el runner nuevo
es un archivo aparte.

---

## 29 de agosto de 2026 — FASE 1 REABIERTA. Un error de unidades

Felipe pidió poner KINETIC a operar con dinero real. Se le respondió que la
evidencia de hoy dice que eso sería comprar una pérdida, y que además es
imposible por estado: no existe `execution/`, no hay par ni temporalidad
configurados, y la Fase 2 nunca se hizo. **Eligió volver a la estrategia.**

### El diagnóstico que faltaba

Se midió la anatomía del peaje (`tools/anatomia_de_costos.py`, descriptivo,
no prueba hipótesis). El número que ordena todo:

| Par / TF | Movimiento capturado promedio | Peaje | Ratio |
|---|---|---|---|
| BTC 15m | +0.024% | 0.30% | **0.08** |
| BTC 1h | +0.316% | 0.30% | **1.05** |
| ETH 15m | +0.042% | 0.30% | **0.14** |
| **ETH 1h** | **+0.656%** | 0.30% | **2.19** |

**El peaje es fijo y la ventaja por operación crece con la temporalidad**: de
15m a 1h se multiplica por 13 en BTC y por 15 en ETH. En 15m la ventaja es
doce veces más chica que el costo — eso no lo arregla ningún filtro.

Dato incómodo: **ETH 1h tiene la mejor ventaja por operación de las cuatro.**
Estuvo bien descartarlo por muestra, pero su problema nunca fue la señal.

Otro síntoma: **entre el 24% y el 29% de las operaciones que acertaron la
dirección igual perdieron plata**, porque capturaron menos de 0,30%.

### El error de unidades

Todo apunta a temporalidades más altas. Pero 4h nunca se pudo evaluar: daba
0-3 operaciones, y estaba anotado como «no hay señales». **Estaba mal leído.**

El filtro de consolidación exigía desviación ≤ 0,75%, un umbral **en % del
precio**. La volatilidad escala con la temporalidad, así que ese número
significa cosas distintas en cada una. Medido:

| Par / TF | Velas que pasaban ≤0.75% |
|---|---|
| BTC 15m | **65.2%** |
| BTC 1h | 25.5% |
| BTC 4h | **2.4%** |
| ETH 15m | 51.2% |
| ETH 1h | 13.7% |
| **ETH 4h** | **0.7%** |

**El mismo filtro estaba prácticamente apagado en 15m y bloqueando casi todo
en 4h.** Los «0-3 operaciones» eran el filtro tapando el 99,3% del mercado.

E implica algo hacia atrás: **en 15m el filtro tampoco filtraba gran cosa**,
dejaba pasar dos de cada tres velas. Buena parte de las 1.496 operaciones que
pagaron peaje entraron por ahí.

**Es el mismo error que TITAN tenía con `MAX_SPREAD = 2.0`**: una constante
pensada para EURUSD que no significa nada para GOLD.

### El arreglo

`indicators.desviacion_relativa()`: dispersión de N velas dividida por el
ATR%. Sin unidades, causal, y significa lo mismo en cualquier temporalidad.
Verificado — las medianas quedan entre 1.40 y 1.57 en las seis combinaciones,
contra un rango de 0.54 a 3.60 en la medida absoluta.

`config.yaml` gana `estrategia.consolidacion.modo`: `absoluto` (como toda la
Fase 1, se conserva para poder reproducirla) o `relativo`. **El default es
`absoluto`, así que nada de lo medido antes cambió**, y hay una prueba que lo
fija. Un `modo` con typo lanza error en vez de caer en un default silencioso.

**Nueve pruebas nuevas** (194 en total), incluidas: que los dos caminos del
motor de señal siguen coincidiendo vela por vela en modo relativo, y una que
deja constancia del problema original —que la medida absoluta NO es
comparable entre temporalidades— para que se vea que el arreglo era necesario
y no una preferencia estética.

### Estado

**Fase 1 REABIERTA.** Los `null` siguen en `null`. El informe
`docs/FASE_1_informe.md` sigue siendo válido para lo que midió, pero su
conclusión queda **en revisión**: se cerró sin haber podido evaluar 4h.

**Lo que sigue, y todavía no se hizo:** evaluar 4h (y quizá 1d) con
walk-forward, ahora que son comparables. Ojo: elegir el `umbral_relativo` es
una decisión que debe salir del walk-forward, no de la intuición.

**Cuenta de hipótesis sobre estos datos: van 2.** La primera (trailing ancho)
resultó ser un mecanismo real que no alcanzó. La segunda es «temporalidades
más altas pagan el peaje». Cada intento adicional aumenta la chance de
encontrar algo lindo por azar.

### CIERRE DE SESIÓN — lo primero de mañana

**Correr el walk-forward sobre 4h en modo relativo.** No está hecho: hoy solo
se arregló la herramienta de medición, todavía no se midió nada con ella.

Antes de correrlo hay que resolver una cosa de diseño, y **no la decidas por
tu cuenta**: `main_walkforward.py` hoy fija `UMBRAL_CONSOLIDACION = 0.75` como
constante y barre el multiplicador del trailing. Para esta hipótesis el
candidato a elegir por ventana es el **umbral relativo**, no el trailing. Hay
que decidir con Felipe si se barre uno, el otro, o los dos — y ojo, barrer
dos parámetros a la vez multiplica las combinaciones y con eso la chance de
encontrar algo por azar.

**Qué exigirle al resultado cuando salga**, más que la vez pasada:

1. **Cantidad de operaciones.** Si 4h da menos de ~15 por año, ya sabemos
   cómo termina: es el problema de ETH 1h otra vez.
2. **Concentración.** Si vuelve a depender de una sola operación, no
   aprendimos nada.
3. **Estabilidad y respaldo por ventana**, que ahora el informe muestra solos.
4. **Recién al final, el resultado neto.**

**Si 4h tampoco pasa, la respuesta es cerrar de nuevo y en serio.** Sería la
segunda hipótesis fallida sobre los mismos datos, y una tercera ya sería un
barrido con otro nombre. No encadenes sin preguntarle a Felipe.

---

## 29 de agosto de 2026 — FASE 1 CERRADA (y reabierta más tarde el mismo día)
> El informe formal del cierre está en **`docs/FASE_1_informe.md`**. Esta
> entrada es el resumen; ese documento es la fuente.

**Decisión explícita de Felipe: cerrar la Fase 1 con el hallazgo.**

### El hallazgo

**La estrategia de rupturas con confirmación de volumen no paga sus costos en
cripto.** Sobrevive un solo caso marginal —BTCUSDT 1h— y descansa en
demasiado pocas operaciones para confiarle dinero: ~19 por año, con el 50%
del resultado en una sola.

**Ningún parámetro se promovió a `config.yaml`. Los `null` siguen en `null`,
y eso es el resultado, no un pendiente.** Ninguna configuración se ganó el
derecho a quedar escrita. Se actualizaron los comentarios del archivo para
que no digan «PENDIENTE FASE 1», que ya sería mentira.

### Esto NO abre la Fase 2

El repositorio sigue sin poder operar. Los tres cerrojos siguen puestos y
vigilados por pruebas. **No hay una estrategia validada que llevar a
Testnet**, y cualquier avance de fase necesita decisión explícita de Felipe.

### Estado final

- **Fase 0:** CERRADA (28-ago)
- **Fase 1:** CERRADA (29-ago), hallazgo negativo calificado
- **Fases 2 y 3:** sin abrir
- **185 pruebas** en verde
- Cinco módulos construidos y probados: datos, indicadores, señal, riesgo,
  backtest y walk-forward

Lo construido queda sano y sirve para cualquier estrategia futura. Lo que no
sirvió fue la estrategia, y saberlo con evidencia costó dos días en vez de
descubrirlo con dinero real.

---

## 29 de agosto de 2026 (cierre 5) — La matriz de candidatos. Último pendiente, resuelto

Se imprimió el puntaje de **cada candidato en cada tramo de entrenamiento**.
Salida cruda en `docs/salida_walkforward_29ago2026_con_matriz.txt`. Los
resultados son idénticos a la corrida anterior — verificado con `diff` — la
matriz es puramente informativa.

**No se implementó como «grupo 4-6 contra grupo 2-3»**, que era como estaba
planteada la pregunta. Partir el menú en esos dos grupos habría sido elegir
la partición mirando resultados que ya conocíamos. La matriz no impone
ninguna agrupación.

### BTCUSDT 1h: gana la lectura benigna

```
Ventana       2.0x       3.0x       4.0x       5.0x       6.0x   mejor-peor
      1       37.8       21.3       43.6*      39.6       26.5        22.4
      2       11.5       93.1      113.7      127.7      128.7*      117.3
      3       47.6      150.0      174.0      178.6*     175.6       131.1
      4      -57.6       29.1      104.3*      97.4       93.3       161.9
      5        4.3       -6.0       89.2      152.2*     126.7       158.2
      6      -28.8      -53.2      128.8      202.2*     199.4       255.4
```

Distancia entre el mejor de {2,3} y el peor de {4,5,6}: **−11.3 / +20.6 /
+24.0 / +64.2 / +84.9 / +157.6**. En cinco de las seis ventanas los grupos
**no se tocan**, y la separación crece con el tiempo.

**Los márgenes de 1 a 7 USDT que preocupaban eran entre miembros casi
equivalentes del grupo de arriba.** La decisión que importaba — no elegir 2x
ni 3x — se tomó con holgura. Encaja con los +256 USDT contra FIJO 2x fuera
de muestra, porque FIJO 2x *es* el grupo de abajo.

**La ventana 1 es la excepción y no se barre bajo la alfombra:** ahí los
grupos se solapan (2x da 37.8, mejor que 6x con 26.5) y todo cabe en 22 USDT.
Es la ventana más antigua y la de menos evidencia (31 operaciones).

### ETHUSDT 1h: no hay patrón, y esa es la respuesta

```
Ventana       2.0x       3.0x       4.0x       5.0x       6.0x   mejor-peor
      1       42.7       56.6       52.1       89.5*      82.9        46.8
      2       46.2       58.0       55.2       94.6*      88.9        48.4
      3       27.8*      16.0       20.5       18.7        9.9        17.9
      4       17.8       13.9        8.6       -7.9       38.9*       46.9
      5        8.8       -8.1      -21.2      -18.5       24.4*       45.6
      6        1.1      -10.7      -28.3      -30.2        3.3*       33.5
```

La ventana 3 está **invertida** (2x gana y el puntaje baja al ensanchar). Las
ventanas 4, 5 y 6 tienen forma de **U** — los dos extremos mejor que el
medio — que es la firma del ruido, no de un mecanismo. Y todo dentro de
rangos de 17 a 48 USDT.

### La conclusión que cierra la Fase 1

| Par / TF | Forma de la matriz | Ops de entrenamiento |
|---|---|---|
| BTC 15m | monótona ↑ en 6 de 6 | 300–562 |
| BTC 1h | grupo 4-6 arriba en 5 de 6 | 30–77 |
| ETH 15m | monótona ↑ en 6 de 6 | ~300–500 |
| **ETH 1h** | **sin patrón: invertida y en U** | **9–33** |

**El mecanismo del trailing es real y aparece en los tres tramos que tienen
muestra suficiente para verlo.** ETH 15m y ETH 1h son el mismo par y la misma
estrategia: la única diferencia es cuántas operaciones hay para medir. ETH 1h
no contradice el mecanismo, simplemente no tiene con qué mostrarlo.

Y una advertencia que sale gratis: ETH 15m marcó **+1257 USDT de
entrenamiento** en su ventana 2 y fuera de muestra pierde el 45%. Un número
grande en entrenamiento no significa nada por sí solo.

### Estado

**Fase 1 sigue ABIERTA. Los `null` de `config.yaml` siguen en `null`.**
**185 pruebas.** **No queda nada pendiente de medición.**

Lo que quedó probado, con evidencia y no con intuición:

1. **El mecanismo del trailing ancho es real.** Monótono en 6 de 6 ventanas
   en los dos tramos de 15m, y con separación limpia de grupos en 5 de 6 en
   BTC 1h. Sobrevivió al arreglo de un bug que movió todos los números.
2. **Los 15m no pagan sus costos.** Con la mejor evidencia de las cuatro, y
   dicen que no.
3. **ETH 1h está descartado por falta de muestra**, no por mala suerte.
4. **BTCUSDT 1h es el único candidato vivo**: +267.15 USDT (+53.43%), PF
   1.560, con elecciones de parámetro ahora justificadas — pero estabilidad
   DUDOSA, concentración 50% y ~19 operaciones por año.

**La única decisión pendiente es de Felipe: qué hacer con la Fase 1.**

---

## 29 de agosto de 2026 (cierre 4) — El respaldo de cada elección. La respuesta de fondo

Se midió lo que quedaba pendiente: **cuánta evidencia había detrás de cada
elección de parámetro.** Salida cruda en
`docs/salida_walkforward_29ago2026_con_respaldo.txt`.

Cada ventana ahora registra cuántas operaciones tuvo **cada candidato** en el
tramo de entrenamiento, y el informe muestra por ventana el `respaldo`
(operaciones detrás del valor elegido) y el `margen` contra el segundo mejor.
El margen va contra el segundo y no contra el peor: contra el peor siempre
parece holgado y esconde un empate arriba.

### La comparación que contesta todo

| Par / TF | Respaldo por ventana | Márgenes | Qué dice |
|---|---|---|---|
| BTC 15m | **300–562 ops** | hasta +216 | evidencia sólida, y dice que NO funciona |
| **BTC 1h** | **30–77 ops** | **5 de 6 por debajo de +7** | decisiones al borde del ruido |
| ETH 15m | ~300–500 ops | amplios | evidencia sólida, y dice que NO funciona |
| ETH 1h | **9–33 ops** | mezclados | no había con qué elegir |

**La diferencia entre los tramos no es la estrategia: es cuánta evidencia
hay.** Donde sobra evidencia, dice que no. Donde parece decir que sí, la
evidencia es delgada. Ese es el resultado de fondo de toda la Fase 1.

### BTCUSDT 1h, ventana por ventana

```
Ventana   Elegido   Resultado            Respaldo
   1        4.0     +53.62  (9 ops)      31 ops,  +4.00 al 2do
   2        6.0      -6.61  (6 ops)      35 ops,  +1.02 al 2do
   3        5.0     +19.04 (22 ops)      30 ops,  +3.04 al 2do
   4        4.0     +41.01 (29 ops)      37 ops,  +6.92 al 2do
   5        5.0     +33.04 (27 ops)      56 ops, +25.56 al 2do
   6        5.0    +127.06 (24 ops)      77 ops,  +2.83 al 2do
```

Cinco de seis ventanas eligieron con menos de 7 USDT de margen; una con
**1.02**. Sobre tres años de entrenamiento y 500 USDT de cuenta, eso no es
una preferencia.

**Hay dos lecturas y este dato NO las distingue:**

- **Pesimista:** la elección del multiplicador fue un volado, y el +53%
  descansa en decisiones que el entrenamiento no respaldaba.
- **Benigna:** si 4x, 5x y 6x rinden casi igual, el margen chico entre ellos
  no importa — la decisión que sí importaba (no elegir 2x ni 3x) pudo
  tomarse con holgura, y el aporte de +256 contra FIJO 2x sigue en pie.

Lo que las separaría es **la distancia entre el grupo de arriba (4-6) y el de
abajo (2-3)**, que está guardada en `candidatos_evaluados` pero no se
imprime. **Pendiente, no resuelto.**

### ETHUSDT 1h: la causa raíz de su 100% de dispersión

Entre 9 y 33 operaciones de entrenamiento. **La ventana 3 eligió 2.0x — el
extremo opuesto del menú — sobre NUEVE operaciones.** No es que la estrategia
sea errática: es que no había con qué elegir. Confirma lo que la bandera de
estabilidad detectaba de rebote.

### La bandera `ARBITRARIA` no sirvió, y queda dicho

**Dio CERO en los cuatro tramos.** Se definió estricta a propósito (solo
dispara con 0 operaciones o empate exacto) para no inventar un umbral del
tipo «menos de N operaciones es poco» mirando estos mismos datos. El precio
fue que **el caso que había que detectar — elegir sobre nueve operaciones —
no la activa.**

Lo que funcionó fue la **columna cruda de respaldo**. Se deja la bandera
porque agarra el caso degenerado, pero hay una prueba
(`test_la_bandera_de_arbitraria_NO_agarra_una_muestra_diminuta`) que deja
constancia de la limitación en vez de disimularla. Si algún día se le agrega
un umbral, esa prueba obliga a discutirlo en vez de saltearlo.

### Un error de esta sesión, y su verificación

Se ejecutó un `git checkout -- .` innecesario encadenado en un comando que
solo debía copiar un archivo, y descartó la instrumentación y sus pruebas
antes de commitearlas. Se rehizo a mano.

**Para no commitear evidencia generada por código que ya no existía**, se
volvió a correr BTCUSDT 1h con el código rehecho y se comparó con `diff`
contra la tabla guardada: **idénticas, sin una sola diferencia.** La
evidencia de esta entrada está verificada, no supuesta.

### Estado

**Fase 1 sigue ABIERTA.** Los `null` de `config.yaml` siguen en `null`.
**180 pruebas.** Ya no queda nada por medir de lo que se sabía dudoso.

El único candidato vivo sigue siendo **BTCUSDT 1h**: +267.15 USDT (+53.43%),
PF 1.560, estabilidad **DUDOSA**, concentración **50%**, ~19 operaciones por
año y **elecciones respaldadas por 30-77 operaciones con márgenes de 1 a 7
USDT**.

Pendiente único: imprimir la distancia entre el grupo 4-6 y el 2-3 en
entrenamiento, que decide cuál de las dos lecturas de BTC 1h es la correcta.

---

## 29 de agosto de 2026 (cierre 3) — La bandera de estabilidad, rehecha

### Qué estaba mal

El criterio era «el mismo valor ganó en al menos la mitad de las ventanas».
Dos defectos:

1. **Con pocas ventanas, una mayoría mínima alcanza.** En ETHUSDT 1h los
   elegidos fueron `[5, 5, 2, 6, 6, 6]` — de punta a punta del menú — y decía
   «estable», porque 6.0 ganó exactamente 3 de 6. En la corrida anterior el
   MISMO tramo daba «inestable»; lo único que había cambiado era tener una
   ventana menos.
2. **Trataba los candidatos como etiquetas sueltas cuando son números
   ordenados.** Elegir 4 y después 5 es casi ponerse de acuerdo; elegir 2 y
   después 6 es no haber encontrado nada. Contar apariciones no los
   distingue.

### El criterio nuevo

Se mide **dispersión**: cuánto del menú de candidatos abarcan las elecciones.

| Dispersión | Veredicto |
|---|---|
| ≤ 25% | ESTABLE |
| ≤ 50% | DUDOSA |
| > 50% | INESTABLE |

El umbral tiene una razón que no depende de nuestros datos: **si las
elecciones abarcan más de la mitad del menú, el entrenamiento no está
localizando una región, está recorriendo la carta.**

Para candidatos no numéricos (un parámetro categórico, donde la distancia
entre dos valores no significa nada) se cae al criterio por conteo, ahora con
mayoría **estricta** — un empate no es una elección.

`dispersion_pct` **se reporta siempre en crudo** junto al veredicto. Si el
umbral está mal puesto, el número de al lado lo delata.

### Los cuatro tramos con el criterio nuevo

| Par / TF | Elegidos | Dispersión | Antes | Ahora |
|---|---|---|---|---|
| BTC 15m | 6,6,6,6,6,6 | 0% | SÍ | **ESTABLE** |
| **BTC 1h** | 4,6,5,4,5,5 | 50% | SÍ | **DUDOSA** |
| ETH 15m | 6,6,6,6,5,6 | 25% | SÍ | **ESTABLE** |
| ETH 1h | 5,5,2,6,6,6 | 100% | SÍ | **INESTABLE** |

**BTC 1h bajó de «SÍ» a DUDOSA.** Es el único candidato que quedaba vivo, así
que el criterio nuevo le pega justamente al resultado que nos convenía
sostener. Eso es evidencia de que no se acomodó la vara.

### La advertencia que corresponde dejar escrita

**Este criterio se escribió DESPUÉS de ver los cuatro resultados.** Se eligió
por el razonamiento de arriba y no por el veredicto que produce, y el hecho
de que degrade nuestro mejor tramo respalda eso — pero el riesgo existe y
queda registrado, acá y en el docstring de `estabilidad`.

No se pudo verificar que las pruebas nuevas fallen con el criterio viejo
(fallarían por `ImportError`, no por la aserción). En su lugar, la prueba del
caso límite lleva adentro `assert elegidos.count(6.0) == len(elegidos) / 2`,
que fija la condición exacta que hacía pasar al criterio anterior: si alguien
cambia el ejemplo, la prueba avisa que dejó de probar lo que dice.

### Lo que NO se hizo, y por qué importa

La verdadera razón para desconfiar de ETH 1h no es la dispersión: es que
**tuvo 59 operaciones en seis años, con ventanas de 0 y 2 operaciones**. Una
elección hecha sobre esa muestra no es una elección. La dispersión lo detecta
de rebote — el criterio no mide cantidad de evidencia, y no se le agregó esa
medición para no seguir tocando el juicio en la misma sesión en que se lo
reescribió. **Queda anotado como pendiente.**

### Estado

**Fase 1 sigue ABIERTA.** Los `null` de `config.yaml` siguen en `null`.
172 pruebas. Único candidato vivo: **BTCUSDT 1h**, ahora con estabilidad
**DUDOSA**, 50% de concentración y ~19 operaciones por año.

Pendiente anotado: medir el respaldo de cada elección (cuántas operaciones
tenía el tramo de entrenamiento), que es lo que de verdad invalida a ETH 1h.

---

## 29 de agosto de 2026 (cierre 2) — La brecha de 126 USDT, y un error mío de lectura

Felipe pidió medir de dónde salían los 126.01 USDT de brecha que quedaban en
BTCUSDT 1h contra el «mejor en retrospectiva». Salida cruda en
`docs/salida_cierres_de_ventana_29ago2026_corregida.txt`.

### La respuesta: no eran cierres forzados

| Par / TF | Cortadas por el borde |
|---|---|
| BTC 15m | **0** de 976 |
| **BTC 1h** | **0** de 117 |
| ETH 15m | **0** de 811 |
| ETH 1h | 1 de 59 (−1.59 USDT) |

Antes del arreglo del recorte, **los cuatro tramos** tenían una operación
cortada, todas el mismo día. Ahora prácticamente ninguno. El artefacto de las
costuras, que ayer parecía el problema central, **era en buena medida un
efecto del propio bug**: el mes ciego después de cada costura empujaba las
entradas a agolparse contra el borde siguiente. Arreglado el recorte, el
artefacto se disolvió solo.

### El error: se buscó la causa donde no estaba

La brecha de BTC 1h **sí es el precio de no conocer el futuro**, que es lo
que el rótulo original decía. Los elegidos son `[4.0, 6.0, 5.0, 4.0, 5.0,
5.0]` y el mejor en retrospectiva fue 5.0x: **el walk-forward eligió 5.0x en
solo 3 de las 6 ventanas.** En las otras tres eligió 4x y 6x, y esa
diferencia es exactamente lo que el método cobra.

Se había afirmado lo contrario — «es el mismo parámetro en ambos, así que la
brecha no es sobreajuste» — apoyándose en una nota del script que comparaba
contra el valor **dominante**, no contra todas las ventanas. La nota se había
escrito ese mismo día. Costó una corrida de 12 minutos persiguiendo cierres
forzados que resultaron ser cero.

**Es útil que haya quedado registrado**: el número crudo (126.01) siempre
estuvo bien; lo que falló fue la frase que lo interpretaba. Una nota
equivocada es peor que ninguna, porque ahorra el trabajo de pensar.

### Qué significa entonces el +267.15 de BTC 1h

Un barrido sobre los seis años habría mostrado **+393.16**; la realidad
captura **+267.15**. Son **32% de inflación**, medidos sobre nuestros propios
datos. Ese es el número concreto de cuánto engaña un barrido.

Y deja el resultado de BTC 1h **más creíble que antes de medirlo**, no menos:
+267.15 es lo que sobrevive después de descontar el autoengaño, y ya no queda
ninguna brecha sin explicar.

### Arreglado en el código

`nota_de_brecha()` en `main_walkforward.py`: cuenta ventana por ventana, dice
«TODAS» solo cuando de verdad fueron todas, y si no, informa en cuántas
coincidió y qué eligió en el resto. Se sacó de adentro de `main()` y tiene
**6 pruebas** (164 en total), la primera de ellas el caso exacto que engañó.

### Estado

**Fase 1 sigue ABIERTA. Los `null` de `config.yaml` siguen en `null`.**

Ya no quedan pendientes de medición: todo lo que se sabía dudoso está medido.
Los números de la entrada siguiente (cierre) son los vigentes y ahora están
completamente explicados.

Queda **una sola decisión pendiente, y es de Felipe**: qué hacer con la
Fase 1. El único candidato vivo es BTCUSDT 1h — +267.15 USDT (+53.43%) en
seis años, PF 1.560, pero **50% de concentración y ~19 operaciones por año**.

Y queda anotado, sin resolver, el defecto de la bandera de estabilidad
(declara «SÍ» con una mayoría mínima; ver la entrada siguiente).

---

## 29 de agosto de 2026 (cierre) — La re-corrida limpia. Estos son los números vigentes

> Las cifras de esta entrada siguen siendo las vigentes. La entrada de arriba
> (cierre 2) explica la única brecha que quedaba sin justificar.

Walk-forward re-corrido con el arreglo del recorte. Salida cruda en
`docs/salida_walkforward_29ago2026_corregida.txt`. **Estas cifras reemplazan
a las de la primera entrada de hoy**, que se midieron con tramos mutilados.

| Par / TF | Fuera de muestra | FIJO 2x | Aporte de la hipótesis | Elegidos | Concentr. |
|---|---|---|---|---|---|
| BTC 15m | **−351.20** (−70.24%), PF 0.854, 976 ops | −451.48 | +100 | 6.0 en las 6 | −26% |
| **BTC 1h** | **+267.15** (+53.43%), PF 1.560, 117 ops | +10.89 | **+256** | 4,6,5,4,5,5 | **50%** |
| ETH 15m | **−224.20** (−44.84%), PF 0.908, 811 ops | −421.07 | +197 | 6.0 en 5 de 6 | −33% |
| ETH 1h | **+10.00** (+2.00%), PF 1.051, 59 ops | +88.87 | **−79** | 5,5,2,6,6,6 | **920%** |

### Qué cambió respecto de la corrida con el bug

Todo se movió, y el movimiento tiene sentido en cada caso:

- **Los 15m empeoraron** (BTC −63% → −70%, ETH −35% → −45%). Al devolverles
  el 9% del período aparecieron más señales y todas restaron. Coherente con
  que el problema de 15m es el peaje: más velas = más operaciones = más
  comisión sobre una ventaja que no la cubre.
- **BTC 1h mejoró en las tres dimensiones a la vez**: PF 1.367 → 1.560,
  +33% → +53%, y **concentración 66% → 50%**. Que mejoren juntas es
  tranquilizador: si el retorno hubiera subido empeorando la concentración,
  sería otra operación afortunada y no una mejora.
- **ETH 1h dejó de perder** (−13.6% → +2.0%) pero destapó algo peor: ver
  abajo.

### Dos validaciones de que el arreglo hace lo que debe

1. **En BTC 15m la brecha contra el «mejor en retrospectiva» dio 0.00
   exacto.** Tiene que ser así: si el parámetro elegido es el mismo en todas
   las ventanas, coser los tramos debe dar idéntico a correr todo de una.
   Antes no coincidía porque cada costura tenía 30 días de agujero.
2. **Desapareció la ventana 7 fantasma.** La última ventana ahora llega a
   2026-08-29, el final real de los datos.

### El hallazgo más importante de la re-corrida: ETH 1h, concentración 920%

No es un error de impresión. El neto es +10 USDT y la mejor operación sola
aportó ~+92: **todo el resto junto perdió ~82**. No es una estrategia con un
pico afortunado, es una operación afortunada rodeada de 58 perdedoras. Es la
cifra más elocuente de todo lo que llevamos medido.

### Un defecto de la bandera de estabilidad, encontrado por accidente

En ETH 1h los elegidos son `[5, 5, 2, 6, 6, 6]` — van de 2 a 6, dispersión
visible a ojo. Pero la bandera dijo **«Estable: SÍ»**, porque el criterio es
«el mismo valor gana en al menos la mitad de las ventanas» y 6.0 ganó
exactamente 3 de 6.

En la corrida anterior este mismo tramo daba «NO» y acertaba. Lo único que
cambió fue tener 6 ventanas en vez de 7: **la aritmética se dio vuelta sin
que la estrategia cambiara.** Con pocas ventanas, una mayoría mínima alcanza
para declarar estabilidad donde no la hay.

**No se tocó el criterio.** Cambiar cómo se juzga la estabilidad justo
después de ver un resultado que no gusta es exactamente la forma de
engañarse que este proyecto trata de evitar. Queda anotado como decisión
pendiente de Felipe.

### Estado

**Fase 1 sigue ABIERTA. Los `null` de `config.yaml` siguen en `null`.**
Nada se decidió.

Lo que quedó establecido con evidencia:

1. **La hipótesis del trailing es un mecanismo real.** Aportó +100, +256 y
   +197 USDT en tres de los cuatro tramos, y el entrenamiento eligió entre 4x
   y 6x año tras año con datos distintos, sin tocar nunca 2 ni 3. Sobrevivió
   al arreglo de un bug que movió todos los números.
2. **Los 15m están descartados** en los dos pares.
3. **ETH 1h está descartado**: la hipótesis lo empeora y su resultado es una
   sola operación.
4. **Queda un único candidato: BTCUSDT 1h**, con 50% de concentración y 117
   operaciones en seis años (~19 por año).

Pendientes anotados, ninguno resuelto:

- Quedan 126.01 USDT de brecha en BTC 1h contra el «mejor en retrospectiva»,
  con el mismo parámetro elegido (5.0x), así que tampoco es sobreajuste.
  Probablemente sean cierres forzados en las costuras nuevas (los bordes se
  corrieron del 17-ago al 16-sep). Se mide re-corriendo
  `tools/medir_cierres_de_ventana.py`, que ahora usa el código arreglado.
- El criterio de la bandera de estabilidad.

---

## 29 de agosto de 2026 (más tarde) — Medir el artefacto encontró un bug peor

Felipe pidió medir cuánto cuestan los cierres forzados de ventana, antes de
creerle a los números de la corrida anterior. Se construyó
`tools/medir_cierres_de_ventana.py` (solo lectura, no toca el motor). Salida
cruda en `docs/salida_cierres_de_ventana_29ago2026.txt`.

La herramienta **replica cada operación cortada desde su entrada** y, al
llegar al borde, compara el stop reconstruido contra el que el motor
registró. Si no coinciden, lo dice y descarta el caso en vez de devolver un
número inventado. **Las cuatro réplicas validaron; cero descartes.**

### Lo que costaron los cierres forzados

| Par / TF | Cortadas | Dejado sobre la mesa | Resultado del WF |
|---|---|---|---|
| BTC 15m | 1 de 888 | +2.02 | −316.74 |
| **BTC 1h** | **1 de 109** | **+142.39** | **+165.24** |
| ETH 15m | 1 de 744 | −1.45 | −173.86 |
| ETH 1h | 1 de 55 | −2.61 | −67.81 |

En BTC 1h **una sola operación cortada valía el 86% del resultado del
tramo**. Entró el 17-ago-2026 y fue cortada el mismo día, en el borde de la
ventana 6; de haber seguido llegaba al 23-ago con +140.66. Explica 142 de los
227.92 USDT de brecha contra el «mejor en retrospectiva».

En 15m el artefacto es despreciable: las operaciones entran y salen rápido,
así que la costura casi nunca las agarra abiertas. **Solo pesa en 1h.**

**No leerlo como «BTC 1h en realidad da +307».** Es UNA operación, de la
semana pasada, y arreglar una medición que cuelga de una operación con una
estimación que cuelga de la misma operación no da terreno firme. Lo que sí
queda establecido es que el walk-forward con costuras anuales es una regla de
medición ruidosa para una estrategia de pocas operaciones largas.

### Y buscando el porqué apareció un bug de verdad

Los cuatro cierres forzados caían todos en la misma costura y ninguna ventana
anterior tenía posiciones abiertas. Eso no cerraba, y tirando de ahí:

**`backtest_engine.correr()` aplicaba `descartar_dias_iniciales: 30` a
CUALQUIER DataFrame que recibiera.** Correcto para el histórico completo (la
idea es saltear el libro vacío de un par recién listado). **Incorrecto para
los tramos que le pasa el walk-forward**, que son pedazos del medio de la
historia.

Medido sobre BTCUSDT 1h:

| Ventana | Velas de prueba | Tras el recorte | Perdidas |
|---|---|---|---|
| 1 a 6 | ~8.760 c/u | ~8.040 | **720 c/u** |
| 7 | 289 | **0** | 289 |

**4.609 velas de prueba que el motor nunca miró** — 192 días, medio año de
los seis evaluados, casi el 9% del período fuera de muestra. Tres
consecuencias:

1. **La ventana 7 se descartaba entera** por ser más corta que el recorte.
   Por eso siempre reportaba 0 operaciones: no era falta de señales.
2. **Un mes ciego después de cada costura.** Por eso la operación huérfana
   del 17-ago nunca se retomó en la ventana siguiente.
3. **Lo más serio: también mutilaba cada tramo de ENTRENAMIENTO.** Los 5
   candidatos × 7 ventanas se evaluaron sobre datos incompletos, así que **la
   elección del parámetro estaba contaminada**, no solo la medición.

### El arreglo

Decisión de Felipe: arreglar y re-correr. En tres capas:

- `backtest_engine.correr()` recibe `recortar_inicio: bool = True`. El
  comportamiento por defecto no cambia.
- `walk_forward.correr()` recorta **una vez**, sobre el histórico entero,
  antes de partirlo, y pasa `recortar_inicio=False` en cada tramo. El
  descarte por listado reciente se sigue aplicando igual.
- Las dos referencias de `main_walkforward.py` (FIJO 2x y mejor en
  retrospectiva) corren sobre un tramo, así que también lo apagan — si no, se
  comparaba contra un período distinto del que midió el walk-forward.

**Tres pruebas nuevas** (158 en total). Se verificó que las dos del
walk-forward **fallan sin el arreglo**: una prueba que pasa igual con y sin
el arreglo no prueba nada.

### Qué queda invalidado

**Los números de la entrada anterior de hoy.** Se midieron con tramos a los
que les faltaba el 9% del período y con la selección de parámetro
contaminada. Las conclusiones cualitativas probablemente aguanten (el
mecanismo del trailing funciona; los 15m no pagan sus costos; ETH 1h es
inestable), pero **ninguna cifra de esa entrada es citable** hasta que la
re-corrida diga otra cosa. Se dejan igual, sin borrar, para que se vea qué
cambió y por qué.

---

## 29 de agosto de 2026 — El walk-forward corrió. Qué dijo

Corrida completa de `main_walkforward.py` sobre los cuatro tramos
(BTCUSDT y ETHUSDT, en 15m y 1h). Salida cruda guardada en
`docs/salida_walkforward_29ago2026.txt`. Duró unos 12 minutos.

La hipótesis era una sola, con razón mecánica: **con 24-27% de acierto el
resultado depende de que las pocas ganadoras corran, y un trailing a 2xATR
las corta antes de tiempo.** Se probaron 2/3/4/5/6 xATR, reeligiendo cada
año con los tres anteriores, sin tocar nunca el stop inicial.

### Los cuatro resultados

| Par / TF | Fuera de muestra | FIJO 2x | Elegidos | Estable | Concentr. |
|---|---|---|---|---|---|
| BTC 15m | **−316.74** (−63.35%), PF 0.872, 888 ops | −451.48 | 6.0 en las 7 | SÍ | −31% |
| **BTC 1h** | **+165.24** (+33.05%), PF 1.367, 109 ops | +10.89 | 4,6,5,4,5,5,5 | SÍ | 66% |
| ETH 15m | **−173.86** (−34.77%), PF 0.934, 744 ops | −421.07 | 6.0 en 6 de 7 | SÍ | −48% |
| ETH 1h | **−67.81** (−13.56%), PF 0.631, 55 ops | +88.87 | 5,5,2,6,6,6,2 | **NO** | −35% |

### Lo que se aprendió (esto es lo que importa, no la tabla)

**1. El mecanismo es real y se comporta igual en tres de cuatro tramos.**
Dar aire al trailing mejoró el resultado fuera de muestra en BTC 15m
(+134.74), BTC 1h (+154.35) y ETH 15m (+247.21) contra no hacer nada. No es
casualidad de un par: la razón mecánica que motivó la hipótesis era correcta.

**2. Y aun así no salva a los 15m.** Los dos tramos de 15m siguen perdiendo
fuerte. Es coherente con el hallazgo de costos del 28-ago: la ventaja bruta
existe, pero con 744-888 operaciones el peaje se la come. Más aire en las
ganadoras no cambia cuántas veces se paga comisión.

**3. En los 15m eligió 6.0x, el borde del rango probado, casi siempre.**
Eso no es un óptimo: es una pendiente que se chocó con el límite. El
entrenamiento pedía "lo más ancho posible" y nunca encontró un punto dulce
interior. Si algún día se retoma, hay que saber que el rango 2-6 no bastó
para acorralar el máximo — no que 6 sea la respuesta.

**4. ETH 1h es la refutación, y es la parte más valiosa de la corrida.**
Es el único tramo donde la hipótesis **perdió plata**: −67.81 contra +88.87
de no tocar nada, o sea 156.68 USDT peor. Y no fue mala suerte:

- La bandera dijo **«Estable: NO»** *antes* de mirar el resultado. Los
  elegidos saltan 5 → 2 → 6 → 2. El único tramo con selección inestable es
  el único donde la selección destruyó valor. La bandera funciona.
- La causa está a la vista: **55 operaciones en seis años.** La ventana 1
  tuvo 0 operaciones y la ventana 2 tuvo 1. Con esa muestra el
  entrenamiento no mide nada, elige al azar, y el azar cobra.

**5. El backtest simple habría elegido justo el peor tramo.** ETH 1h era el
que mejor se veía el 28-ago (PF 1.675, +27.83%). Fuera de muestra pierde. Es
la demostración concreta, sobre nuestros propios datos, de para qué sirve
todo este aparato. Vale más que cualquier PF que hubiéramos conseguido.

**6. BTC 1h mejoró su concentración, pero sigue enferma.** Pasó de 161% a
**66%**. La diferencia no es cosmética: antes, sacando la mejor operación el
resultado se daba vuelta y quedaba negativo; ahora sacándola quedan ~56 USDT
en seis años. Positivo, pero flaco. Sigue siendo un sistema que depende
demasiado de un puñado de operaciones.

### Una duda abierta que hay que resolver ANTES de creerle a estos números

En BTC 1h el «mejor en retrospectiva» (+393.16) le saca 227.92 USDT al
walk-forward (+165.24). El script rotulaba eso como «cuánto nos habría
engañado el barrido tramposo», **y ese rótulo está mal**: el barrido eligió
**5.0x**, que es el mismo valor que el walk-forward eligió en 4 de 7
ventanas. Si fuera sobreajuste de parámetro, habría elegido otra cosa.

La explicación probable es otra: **el walk-forward cierra a la fuerza toda
posición abierta al final de cada ventana anual.** Son 6 cierres forzados en
una fecha arbitraria del calendario, en una estrategia donde una sola
operación aporta el 66% del resultado. Si es eso, los +165.24 están
**subestimando** la estrategia — sería un artefacto del método, no una
propiedad del sistema.

**No está medido.** Es verificable contando las operaciones con
`motivo_salida = "fin del periodo"` y cuánto dejaron sobre la mesa. **No se
hizo, a propósito**, para no encadenar análisis sin que Felipe decida.

Corregido en el código: `main_walkforward.py` ya no rotula la brecha como
sobreajuste sin más, distingue el signo, y avisa explícitamente cuando el
valor elegido en retrospectiva coincide con el del walk-forward.

### En qué estado queda la Fase 1

**Abierta.** Nada se decidió: los `null` de `config.yaml` siguen en `null`.
La hipótesis del trailing quedó contestada — funciona como mecanismo, no
alcanza como salvación — y hay un solo candidato con vida, **BTCUSDT 1h**,
con dos reparos serios (66% de concentración y 109 operaciones en seis
años, que son ~18 por año).

Lo que sigue lo decide Felipe. Las opciones sobre la mesa, sin recomendar
ninguna todavía:

1. **Medir el artefacto de los cierres forzados de ventana.** No es una
   hipótesis nueva sobre los datos, es corregir la regla de medición. Barato
   y aclara si +165 o +393 es el número honesto.
2. **Cerrar la Fase 1 con el hallazgo**, como se hizo con EURUSD en TITAN el
   25-ago: dejar escrito que la estrategia de rupturas no paga sus costos en
   cripto salvo marginalmente en BTC 1h, y no seguir.
3. **Una segunda hipótesis.** Ojo: dos hipótesis seguidas sobre los mismos
   datos son un barrido con otro nombre. Si se hace, tiene que tener razón
   mecánica propia y saberse de antemano que el riesgo de engañarse sube.

---

## 28 de agosto de 2026 — CIERRE DE SESIÓN. Módulo 5 y qué falta

> **Histórico. NO empieces por acá** — el walk-forward que esta entrada dejó
> pendiente ya se corrió el 29-ago, encontró un bug de medición por el
> camino, y se volvió a correr arreglado. Empezá por la entrada del 29 de
> agosto (cierre).

### Dónde quedó todo

Fase 0 **cerrada**. Fase 1 **abierta y avanzada**: están los cinco módulos
(datos, indicadores, señal, riesgo, backtest, walk-forward). **155 pruebas
pasan.** Nada puede operar todavía: los tres cerrojos del día 1 siguen
puestos y vigilados por pruebas.

### La decisión que tomó Felipe, y que gobierna lo que sigue

Ante la evidencia de que la estrategia no da un resultado neto defendible,
eligió **atacar el problema de costos con UNA hipótesis validada con
walk-forward** — explícitamente **no** barrer parámetros hasta encontrar algo
lindo.

**La hipótesis:** con 24-27% de acierto, el resultado depende de que las
pocas ganadoras corran mucho. Un trailing a 2×ATR se mueve muy pegado al
precio, y un retroceso de 2×ATR es ruido normal dentro de una tendencia — así
que probablemente esté cortando ganadoras que aún tenían recorrido.

**Lo que la sostiene:** `config.yaml` ya declaraba `atr_multiplicador_sl` y
`trailing_atr_multiplicador` como dos números distintos, pero
`stop_manager.py` usaba el mismo para ambos. Son trabajos diferentes: el
inicial define cuánto se arriesga (y por lo tanto cuánto se compra), el
trailing define cuánto aire tiene una ganadora. **Tocar el trailing no cambia
el riesgo.** O sea que esto es implementar lo que el config ya pedía, no
inventar un parámetro para tener algo que barrer. Ya está implementado y
probado.

### PENDIENTE — lo primero que hay que hacer mañana

**El walk-forward quedó corriendo y no alcanzó a dar resultados.** Hay que
volver a lanzarlo:

```
venv\Scripts\python.exe main_walkforward.py
```

Tarda varios minutos (BTCUSDT 15m son 36 corridas del motor sobre tramos de
tres años). Ya se le arregló el búfer de salida, así que ahora muestra el
avance en vivo en vez de quedarse mudo hasta el final.

**Qué mirar cuando termine, en este orden:**

1. **¿El elegido es ESTABLE entre ventanas?** Si cada año gana un valor
   distinto, no hay óptimo: hay ruido, y el proceso está eligiendo al azar.
   Eso ya sería una respuesta, y es un "no".
2. **¿Cuánta CONCENTRACIÓN hay fuera de muestra?** Si el resultado vuelve a
   depender de una sola operación, no aprendimos nada.
3. **La distancia contra "el mejor en retrospectiva".** Ese número es,
   literalmente, cuánto nos habríamos engañado barriendo sin esta disciplina.
   Vale la pena anotarlo aunque la hipótesis falle.
4. Recién al final, el resultado neto.

**Si el walk-forward no mejora nada**, la conclusión honesta es que la
estrategia de la sección 7 no tiene ventaja explotable en BTC ni ETH, y
corresponde plantearle a Felipe cerrar la Fase 1 con ese hallazgo — como hizo
con EURUSD en TITAN el 25-ago. **No encadenar una segunda hipótesis sin
preguntarle:** dos hipótesis seguidas sobre los mismos datos ya son un
barrido con otro nombre.

### Lo que se agregó en esta sesión (módulo 5)

- `backtesting/walk_forward.py` — entrenar 3 años, probar 1, avanzar 1. El
  capital se arrastra entre ventanas.
- **La prueba que sostiene todo:** espía el proceso interceptando cada
  llamada al motor y verifica que, en las corridas de selección, el último
  dato visto sea anterior al primer dato del tramo de prueba de esa ventana.
  Sin eso, un "fuera de muestra" contaminado se ve **exactamente igual** que
  uno limpio.
- `signal_engine.mascara_de_senales()` — camino vectorizado, 1,8× más rápido,
  necesario porque el walk-forward corre el motor decenas de veces. **El
  camino lento sigue siendo el de referencia**: una prueba compara los dos
  vela por vela con cuatro juegos de umbrales, otra compara las operaciones
  que produce el motor por cada camino, y sobre datos reales dan idéntico
  (157 ops, 549,63 finales).
- Se sacó del repo la configuración de Obsidian (`.obsidian/`), que se había
  colado por un `git add -A`. Los archivos siguen en el disco.

### Un detalle de método que conviene no perder

La prueba de equivalencia de las máscaras **se protegió sola** en el primer
intento: el escenario sintético no generaba ninguna señal, así que habría
pasado comparando dos series vacías. Ahora exige que haya señales antes de
dar la comparación por válida. Vale como recordatorio: **una prueba que pasa
sin haber ejercitado nada es peor que no tenerla**, porque da confianza
falsa.

---

## 28 de agosto de 2026 — Módulo 4: el backtest, y las primeras cifras reales

### Decisiones de modelado, todas medidas antes de tomarlas

**La entrada va a la apertura de la vela siguiente, no al cierre de la vela
de señal.** Comprar al cierre es imposible: recién sabés cuál fue el cierre
cuando la vela ya cerró. Se midió cuánto cuesta hacerlo bien, sobre las 659
velas de señal de BTC y ETH en 1h: el salto cierre→apertura siguiente tiene
**mediana 0,0000%** y media ±0,001%. En cripto no hay huecos de fin de
semana. O sea que hacerlo bien no cuesta casi nada — pero se hace igual,
porque lo correcto no depende de que sea barato.

**Slippage: 0,05% por lado.** El spread de BTCUSDT ronda 0,01% y nuestras
compras de 100-250 USDT no mueven un libro de millones. 0,05% es 5× el
spread típico; el margen extra cubre que las rupturas ocurren en momentos
rápidos. Justificación completa en `config/config.yaml`.

**Se descartan los primeros 30 días de cotización de cada par.** Salió de
mirar el peor hueco a la baja de ETHUSDT: **−48,50%**. No es un desplome. Es
el 22-ago-2017, cinco días después del listado: la vela abre en 144,21 —que
es también su mínimo— tras cerrar en 280 la anterior, y cierra en 287. Una
operación suelta en un libro casi vacío. Backtestear sobre eso genera
operaciones falsas a precios falsos.

**El stop no siempre se ejecuta en su precio.** Si la vela abre por debajo
del stop, la orden sale a la apertura, que es peor. Precio de salida =
`min(stop, apertura)`.

### Resultados — ADX ≥ 20, consolidación ≤ 0,75%, guardia macro apagada

Netos de comisión (0,1% por lado) y slippage (0,05% por lado), capital 500
USDT, riesgo 1% por operación, 2017-2026.

| Par | TF | Ops | PF | Acierto | Retorno | Max DD |
|---|---|---|---|---|---|---|
| BTCUSDT | 15m | 1.496 | **0,756** | 24,5% | **−92,22%** | 93,31% |
| BTCUSDT | 1h | 157 | 1,130 | 31,8% | +9,93% | 14,91% |
| BTCUSDT | 4h | 3 | 2,821 | 33,3% | +2,36% | 1,25% |
| ETHUSDT | 15m | 1.197 | **0,735** | 27,0% | **−85,63%** | 87,12% |
| ETHUSDT | 1h | 75 | 1,675 | 34,7% | +27,83% | 8,92% |
| ETHUSDT | 4h | 0 | — | — | — | — |

### Lo que de verdad importa: la concentración

Los dos únicos resultados positivos con muestra son un espejismo.

**BTCUSDT 1h** — neto +49,63 USDT en nueve años. La **mejor operación sola
aporta +80,14**, o sea el **161%** del resultado. Sin ella el sistema
**pierde −30,51**. Resultado por año: negativo en 4 de 9 años (2018, 2021,
2023, 2025), y 2024 solo aporta +81,3.

**ETHUSDT 1h** — neto +139,16. La mejor aporta **+113,63, el 82%**. Sin ella
quedan +25,53 en nueve años, que es ~0,5% anual. Y 2026 solo aporta +97,1 de
los +139.

Es **exactamente** el hallazgo de GOLD en TITAN: una ventana aporta el 100%
del resultado. Un sistema cuyo rendimiento depende de una sola operación no
tiene ventaja estadística demostrada — tiene suerte documentada.

### El desastre de 15m son los costos, no la estrategia

Se corrió BTCUSDT 15m dos veces, idéntico salvo los costos:

| | PF | Ops | Retorno | Costos pagados |
|---|---|---|---|---|
| Con costos reales | **0,756** | 1.496 | **−92,22%** | 718,63 USDT |
| Sin ningún costo | **1,292** | 1.475 | **+498,68%** | 0 |

Esto **cambia el diagnóstico**. En bruto la lógica de ruptura **sí tiene una
ventaja real** en 15 minutos: PF 1,292 sobre 1.475 operaciones es una
muestra grande y no depende de ninguna operación en particular. El problema
es que **la ventaja por operación es más chica que el peaje**.

Los 718,63 USDT de costos en nueve años son **el 144% del capital inicial**.
Se pagó de comisiones y slippage una vez y media la cuenta entera. A 0,48
USDT de costo promedio por operación, con 1.496 operaciones, no hay
estrategia que sobreviva si su ventaja bruta por operación no supera eso.

(El conteo de operaciones cambia levemente —1.496 contra 1.475— porque sin
costos la cuenta crece distinto y el tope diario del 3% se dispara en
momentos distintos. Es esperable, no un error.)

**El replanteo correcto del problema no es "la estrategia no sirve", es "la
ventaja por operación no paga el peaje".** Y eso apunta a una dirección
concreta: menos operaciones y más grandes, no más filtros sobre las mismas.
Pero 1h ya tiene solo 157 operaciones y depende de una sola, y 4h tiene 3.

### Estado

- Pruebas: **141 pasan**.
- La estrategia de la sección 7 del MEGAPROMPT, tal como está especificada,
  **no da un resultado neto defendible** en BTC ni en ETH: en 15m tiene
  ventaja bruta pero la comen los costos, y en 1h el neto positivo descansa
  en una sola operación.
- Decisión de qué hacer con eso: **pendiente de Felipe.** No se barre
  parámetros hasta que él lo decida — barrer sobre esto es la forma más
  rápida de fabricar un falso positivo.

---

## 28 de agosto de 2026 — Fase 1 ABIERTA: datos, indicadores, señal y riesgo

Felipe aprobó abrir la Fase 1. Decisiones tomadas por él antes de empezar:
**BTCUSDT y ETHUSDT**, **todo el historial desde 2017**, en 15m, 1h y 4h.

### Histórico descargado

**829.930 velas** en disco, de Binance Mainnet por el endpoint público —
sin llaves. 836 segundos en total, y de acá en más solo se pide lo que
falta.

| Par | 15m | 1h | 4h |
|---|---|---|---|
| BTCUSDT | 316.139 | 79.048 | 19.778 |
| ETHUSDT | 316.139 | 79.048 | 19.778 |

Todo desde el 17-ago-2017. Cero duplicados, cero desorden. Huecos: 33 en
15m (565 velas), 28 en 1h, 8 en 4h. Los dos pares dan **exactamente** los
mismos conteos y los mismos huecos, y eso es correcto, no un error de
copia: se listaron el mismo día y las paradas de mantenimiento de Binance
afectan a todos los pares a la vez.

### Módulos entregados

**1 — Capa de datos** (`core/data_feed.py`). Descarga incremental, guardado
en CSV y auditoría. Vigila las tres cosas que arruinan un backtest en
silencio: la vela en curso (se descarta siempre, comparando `close_time`
contra la hora actual), los huecos (se reportan, nunca se rellenan —
inventar una vela es fabricar precio) y los duplicados/desorden (se
reauditan al leer del disco).

**2 — Indicadores** (`strategy/indicators.py`). EMA, SMA, ATR, ADX,
Bollinger, desviación porcentual, rango de consolidación, volumen promedio.
A mano, sin `pandas_ta`. Con la prueba anti-*lookahead* que recalcula los 13
indicadores cortando la serie en cuatro puntos: si un valor cambia según
cuántas velas *posteriores* existan, estaba mirando al futuro.

Dos lugares donde el lookahead se colaba, los dos resueltos con `shift(1)`:
el rango de consolidación incluía la vela que lo estaba rompiendo, y el
promedio de volumen incluía la vela de ruptura (que trae volumen enorme, así
que el filtro se ablandaba justo cuando debía ser exigente).

ATR y ADX usan suavizado de Wilder (α = 1/p), no EMA común (α = 2/(p+1)).
Hay una prueba que compara contra las dos fórmulas y exige que coincida con
Wilder y **no** con la otra.

**3 — Señal y riesgo** (`strategy/`, `risk/`). Separados en archivos
distintos, como manda la Regla 3. El motor de señal no sabe cuánto capital
hay ni si hoy se perdió el límite; solo dice si hay ruptura. El portero
decide si eso se ejecuta.

Del lado del riesgo hay cuatro cosas que vale la pena tener anotadas:

- **Las comisiones entran en el dimensionamiento.** Se despeja la cantidad
  con el 0,1% de ida y el 0,1% de vuelta dentro de la fórmula. Sin eso, la
  pérdida real al tocar el stop siempre supera un poco el 1% que creíamos
  arriesgar — poco, pero siempre en contra.
- **En Spot no se puede comprar por más del capital.** Con un stop muy
  pegado al precio, la fórmula pide una compra mayor a lo que hay. Se
  recorta y se avisa: el riesgo real queda *por debajo* del configurado.
- **Una compra por debajo del mínimo de Binance se rechaza, no se agranda.**
  Agrandarla para llegar a los 5 USDT sería romper el límite de riesgo para
  poder operar.
- **El trailing nunca baja, y se cuelga del mayor CIERRE, no del mayor
  máximo.** Una mecha larga de un minuto raro subiría el stop a un nivel que
  el precio nunca sostuvo. Hay una prueba que derrumba el precio con la
  volatilidad explotando y exige que el stop no retroceda ni una vez.
- **El break-even NO está implementado, a propósito.** TITAN tuvo un bug de
  break-even que nunca se activaba y que ninguna prueba automatizada
  atrapó — solo lo encontró la observación en vivo (`docs/BITACORA.md`,
  14-ago-2026). Si se quiere, se agrega como regla explícita con su propia
  prueba, no escondido dentro del trailing.

**El bug F de TITAN está tapado desde el primer día.** `portfolio_guard.py`
impide abrir dos pares del mismo grupo de correlación. En TITAN eso se
descubrió operando: el 19-ago-2026 un SELL en EURUSD y un SELL en GOLD eran
una sola apuesta al dólar tomada dos veces, y pegaron en su stop con 118
segundos de diferencia. En cripto el problema es peor porque casi todo sigue
a Bitcoin: comprar BTC y ETH a la vez no es diversificar.

### Hallazgo: la tensión entre el filtro de régimen y la consolidación

Al escribir `regime_filter.py` noté que la sección 7 del MEGAPROMPT pide dos
cosas que se pelean: **tendencia** (ADX alto) y **consolidación previa**
(precio quieto en las últimas 50 velas). Una consolidación *es* un tramo sin
tendencia, así que mientras el precio está quieto el ADX baja.

En vez de dejarlo como sospecha, se midió sobre BTCUSDT 1h, 78.998 velas
analizables (2017-2026):

| Qué tan quieto estuvo el precio | ADX medio |
|---|---|
| Muy quieto (cuartil 1) | 20,7 |
| Quieto | 24,4 |
| Movido | 29,1 |
| Muy movido (cuartil 4) | 36,1 |

**La tensión es real pero no es fatal.** El ADX sí cae cuando el mercado se
aquieta, pero **el 47% de las velas consolidadas igual pasan ADX ≥ 20**
(9.311 de 19.750). El motivo: el ADX empieza a subir en la vela de ruptura
misma, así que funciona más como confirmación que como filtro previo.

Entradas que sobrevivirían a las cuatro condiciones, en nueve años de
BTCUSDT 1h, con la consolidación fijada en el cuartil más quieto (≤ 0,74%):

| Filtro de régimen | Entradas en 9 años |
|---|---|
| Sin filtro | 332 |
| ADX ≥ 20 | 214 |
| ADX ≥ 25 | 120 |

**Conclusión provisoria:** el filtro no mata la estrategia, pero es caro. A
ADX ≥ 25 quedan ~13 entradas por año, que es poca muestra para afirmar nada.
Si esas 332 operaciones sin filtro no rinden, no hay filtro que las salve.
No se decide nada acá: se decide con el backtest completo, y por eso
`config.yaml` sigue con `adx_minimo: null`.

### Estado

- Pruebas: **123 pasan**, 0 fallan. Ninguna toca la red.
- Falta para cerrar la Fase 1: el motor de backtest (comisiones + slippage),
  el barrido de parámetros y la validación walk-forward.

---

## 28 de agosto de 2026 — FASE 0 CERRADA

Felipe creó sus llaves de Testnet y corrió `tools/verificar_conexion.py`.
**Terminó en verde.** Los seis chequeos pasaron: `.env` presente, config
válido, ping correcto, reloj a −174 ms de Binance (tolerancia: 1000 ms),
lectura de cuenta correcta y datos de mercado disponibles.

Con eso se cumple lo único que faltaba, y la **Fase 0 queda cerrada**.

### Tres cosas que dejó la verificación

**1. El precio de Testnet SÍ sigue al mercado real.** Al ver BTC a 77.584
en Testnet sospeché que fuera un precio inventado del servidor de pruebas,
lo cual habría descalificado a Testnet como fuente de datos. Lo comparé
contra Mainnet y la sospecha era infundada:

| Par | Mainnet | Testnet | Diferencia |
|---|---|---|---|
| BTCUSDT | 77.580,00 | 77.579,99 | −0,00 % |
| ETHUSDT | 2.436,22 | 2.436,70 | +0,02 % |

Igual, esto no cambia la decisión de dónde sacar los datos (ver punto 2):
el Testnet replica el precio, pero su libro de órdenes y su liquidez son
ficticios, así que sigue sin servir para medir rendimiento — solo mecánica.

**2. El histórico de Mainnet se baja SIN NINGUNA LLAVE.** Los endpoints de
velas (`get_klines`) son públicos: 1000 velas por pedido, encadenables
hacia atrás. Esto define la fuente de datos de la Fase 1 y es la opción más
segura posible — el backtest se alimenta de datos reales de mercado sin que
haya credenciales involucradas en ningún momento.

**3. Queda confirmado que el mínimo de compra no nos afecta.** Binance
reporta para BTCUSDT: cantidad mínima 0,00001 BTC, paso 0,00001, y compra
mínima **5,00 USDT**. Con nuestra compra típica de ~100-250 USDT estamos
entre 20 y 50 veces por encima del mínimo. El hallazgo P de TITAN (el lote
mínimo de GOLD forzando 2,34 % de riesgo con 1 % configurado) no tiene
equivalente acá.

### Un detalle a tener presente en Fase 3

La cuenta de Testnet reporta `canWithdraw: True`. En Testnet da igual —es
dinero de mentira y ese campo describe la cuenta, no la API key—, pero en
Mainnet ese mismo campo en `True` sería una alarma. El chequeo que sí
importa es el de permisos de la API key (`enableWithdrawals`), que solo
existe en Mainnet y que el script ya vigila: si aparece encendido, corta
con código de error y no sigue.

### Arreglo aplicado

La verificación imprimió ~500 líneas de saldos, porque la cuenta de Testnet
viene con cientos de monedas de regalo. Salida inservible. Ahora muestra el
conteo total y solo USDT, BTC, ETH, BNB y USDC; el resto se ve con
`--todos-los-saldos`.

### Estado

- Fase 0: **CERRADA** el 28-ago-2026.
- Pruebas: 14 pasan, 0 fallan.
- Fase 1: **NO iniciada.** Necesita aprobación explícita de Felipe, y antes
  hay dos decisiones que tomar con él: qué pares entran al barrido y cuánto
  historial se descarga.

---

## 28 de agosto de 2026 — Fase 0: entorno montado (construcción)

**Qué se hizo.** Se creó el proyecto desde cero en
`C:\Proyectos\Proyecto-KINETIC`, repositorio git propio, separado de TITAN.
Entorno virtual con Python 3.12.9, dependencias fijadas, configuración
central, cliente de Binance de solo lectura, script de verificación de
conexión y una batería de 14 pruebas que vigilan que nada pueda operar
todavía.

**Decisiones tomadas (confirmadas por Felipe, no asumidas):**

| Parámetro | Valor | Razón |
|---|---|---|
| Ubicación | `C:\Proyectos\Proyecto-KINETIC`, repo git propio | Separación total de TITAN: protocolos distintos, historiales distintos, nada de KINETIC puede romper TITAN por accidente |
| Capital del bot | 500 USDT | Elegido por Felipe |
| Riesgo por operación | 1,0 % (= 5 USDT) | Punto de partida conservador del MEGAPROMPT. Aguanta ~20 pérdidas seguidas |
| Pérdida diaria máxima | 3,0 % (= 15 USDT) | Recomendación del MEGAPROMPT: corta el día tras 3 pérdidas seguidas |
| Modo | `TESTNET` | Fase 0. `MAINNET` solo lo cambia Felipe a mano, en Fase 3 |

**Hallazgo — el mínimo de Binance NO es un problema con 500 USDT.**
Durante la definición de capital surgió la duda de si $5 de riesgo por
operación chocaba con el mínimo de compra de Binance (~$5-10 por orden).
No choca, y vale dejar escrito el porqué para no volver a discutirlo:
*lo que se arriesga no es lo que se compra*. El tamaño de la compra es
`riesgo ÷ distancia del stop`. Con un stop a 2×ATR, que en cripto suele
caer entre el 2 % y el 5 % del precio, la compra queda entre ~$100 y ~$250.
Muy por encima del mínimo. El problema del lote mínimo que sí tiene GOLD
en TITAN (hallazgo P) no se replica acá con este capital.

**Cerrojos de seguridad puestos desde el día 1.** Son tres, redundantes a
propósito:

1. `core/exchange_client.py` no tiene **ningún** método capaz de enviar una
   orden. No es un olvido: la clase tiene una lista blanca de endpoints y
   cualquier otro lanza `PermissionError`.
2. Construir un cliente contra Mainnet exige pasar `permitir_mainnet=True`
   de forma explícita. Ningún script del repo lo hace solo.
3. `tests/test_solo_lectura.py` **lee el código fuente** de `core/`,
   `strategy/`, `risk/`, `backtesting/` y `tools/` y falla si aparece una
   llamada del tipo `create_order`, `withdraw`, `universal_transfer`, etc.
   También falla si `config.yaml` queda apuntando a `MAINNET`.

La idea del punto 3 está copiada de TITAN, donde las pruebas sobre código
fuente vigilan que la Torre de Control no toque MT5.

**Nota sobre el entorno de esta sesión.** En la sesión de Claude Code hay
conectado un servidor MCP de Binance con herramientas de trading real
(crear órdenes, transferir fondos). No se usó ni se va a usar: KINETIC
habla con Binance por su propio código (`python-binance`), no por ese MCP.
Queda anotado porque es exactamente el tipo de atajo que la Regla 4 del
MEGAPROMPT prohíbe.

**Nota técnica.** No se usa `pandas_ta` (bug de compatibilidad con numpy
reciente al importar `NaN`, como advierte el MEGAPROMPT). Los indicadores
se van a calcular a mano en `strategy/indicators.py` en la Fase 1. El
entorno quedó con `pandas 3.0.5` y `numpy 2.5.2`; pandas 3.x es una versión
mayor reciente, así que si algún ejemplo de internet no compila, sospechar
de eso antes que del código propio.

**Qué falta para cerrar la Fase 0.** Una sola cosa, y depende de Felipe:
*(hecho el mismo día — ver la entrada de arriba)*

- [x] Crear las llaves de **Binance Testnet** en https://testnet.binance.vision/
      (se entra con una cuenta de GitHub, es gratis y es dinero de mentira),
      copiarlas al archivo `.env`, y correr
      `venv\Scripts\python.exe tools\verificar_conexion.py`.
      Hasta que ese script termine en verde, la Fase 0 **no** está cerrada.

Las llaves las pega Felipe a mano en su propio `.env`. Nadie —Claude
incluido— debe pedírselas por chat.

**Parámetros deliberadamente en blanco.** `config/config.yaml` tiene 8
valores en `null`. No es un descuido: son las decisiones que el MEGAPROMPT
(sección 7) prohíbe asumir y que se resuelven con evidencia en la Fase 1:
par, temporalidad, umbral de consolidación, ADX mínimo, distancia máxima
bajo la SMA200, máximo de posiciones simultáneas, supuesto de slippage y
años de historial.

**Estado de las pruebas:** 14 pasan, 0 fallan.

**Próximo paso, cuando Felipe lo apruebe:** Fase 1 — motor de backtest con
Signal Engine y Risk Manager integrados desde el inicio, neto de comisiones
(0,1 % por lado) y slippage, validado con walk-forward.
