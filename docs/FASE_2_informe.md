# Fase 2 — Investigación de estrategias. Informe de cierre

**Proyecto:** KINETIC — bot de trading algorítmico sobre Binance
**Fecha:** 31 de agosto de 2026
**Capital de referencia:** 500 USDT
**Ventana de diseño:** 2019-01-01 a 2024-12-31
**Holdout:** 2025 en adelante — **no se miró**, y sigue cerrado por código

> Este informe está escrito para leerse **fuera del repositorio**, por alguien
> que no vio una línea del código. Todos los números salen de corridas
> guardadas, listadas al final.
>
> Es la continuación del informe de cierre de la Fase 1, que había concluido
> que la estrategia de rupturas no tenía ventaja explotable. Ese informe se
> llevó a una consulta externa con perfil de analista de cripto, y de ahí
> salió la especificación que esta fase ejecutó.

---

## 1. El veredicto, en una frase

**Se probaron cuatro estrategias con parámetros cerrados de antemano, y
ninguna superó a comprar Bitcoin y no hacer nada — cada capa de complejidad
que se le agregó al activo empeoró el resultado de forma monótona.**

---

## 2. Lo que esta fase hizo distinto de la Fase 1

La consulta externa señaló cuatro problemas del cierre anterior. Los cuatro se
corrigieron, y esa corrección es la mitad del valor de esta fase.

| Problema de la Fase 1 | Qué se hizo |
|---|---|
| **Nunca se midió contra comprar y mantener.** El "+2,6% en seis años" se comparaba contra no operar, no contra el activo. | Todo se mide contra **B1 = comprar BTC y no tocar**, que en esta ventana hizo +1.199%. Es un rival durísimo y ese es el punto. |
| **Sesgo de supervivencia.** El universo se armaba con los pares que existen hoy. | Universo reconstruido mes a mes desde el archivo histórico, **con los muertos adentro**. Medido: la Fase 1 veía el **66%** del mercado que existió. |
| **Costos de un solo número.** | Modelo por venue, tipo de orden, rango de liquidez y financiación cada pocas horas. |
| **Sin criterios formales.** | Seis criterios PASA/NO PASA **commiteados antes de bajar un solo dato**. |

**El compromiso previo es lo que le da validez a un resultado negativo.** Los
criterios están en `docs/FASE_2_criterios.md`, con fecha de commit anterior a
la primera descarga. Ninguno se movió después.

---

## 3. Las cinco mediciones previas

La especificación pedía cinco mediciones baratas capaces de **matar una
estrategia antes de programarla**. Se hicieron las cinco. Dos cambiaron el
plan y una cerró una estrategia sin escribirla.

### 3.1 El sesgo de supervivencia tiene número

De 650 símbolos descargados del archivo, **190 estaban deslistados (29%)**.
Por el universo pasaron 116 símbolos, de los cuales **22 desaparecieron**.

**Cinco de esos 22 no murieron: se cambiaron de nombre** (MATIC→POL,
RNDR→RENDER, FTM→S, BTT→BTTC, BCHABC→BCH). Aplicarles la penalización por
deslistado del −20% habría sido un error disfrazado de conservadurismo.

Quedan **17 muertes reales**, y son severas: LUNA −100%, LINA −99,8%,
REN −97,6%, UNFI −96,8%.

**La prueba visible de que la reconstrucción funciona: LUNA está en el
universo de enero de 2022**, cuatro meses antes de irse a cero. Con el
universo de la Fase 1 no habría aparecido nunca.

### 3.2 Rotación del universo — 41% anual

Punta a punta, contra el **37%** que reporta la literatura sobre las 30
mayores por capitalización. Buen encaje, y valida usar volumen cotizado como
sustituto de capitalización (desviación consciente, ver §7).

**Costo forzado: ~0,49% anual** antes de que la señal haga nada. Si un símbolo
sale del top 20, hay que venderlo.

### 3.3 Dispersión transversal — y una conjetura que salió al revés

| | |
|---|---|
| Correlación media por pares (90 días) | **mediana 0,593** |
| Fechas por encima de 0,80 | **5 de 72 (7%)** |
| Dispersión de retornos a 28 días | mediana 17,3% |

La especificación fijaba el corte en ~0,80: si se superaba, la selección
transversal perdía prioridad. **No se superó.** La creencia de que "todo
cripto se mueve junto" venía de mirar quince pares grandes y parecidos.

El techo de una selección perfecta solo-larga: **+22,1% cada 28 días**, contra
un peaje de ida y vuelta de 0,33%. **El costo no es la restricción que manda
para la selección.**

**Pero un techo alto es condición necesaria, no suficiente.** Se anotó así
antes de correr E1, y E1 confirmó la advertencia: el espacio existe y el
momentum a 28 días no lo encuentra.

### 3.4 Frecuencia de la compuerta de régimen

BTC contra su media de 200 días, seis años:

| | |
|---|---|
| Cambios de estado | **43** (7,2/año) |
| Tramo DENTRO | mediana **6 días**, máximo 385 |
| **2022** | **cero cambios** — 365 días afuera |

**30 de los 44 tramos duran menos de un mes.** No es "adentro un año, afuera
un año": son dos regímenes largos más una nube de latigazos. Costo: **1,18%
anual** solo por la compuerta.

### 3.5 Financiación de perpetuos — y la falsación de E3

**624.755 cobros de 107 perpetuos.**

| | |
|---|---|
| Mediana anualizada | **10,95%** sobre nocional |
| Cobros con tasa positiva | 83,5% |
| p90 / p99 | 39,7% / 190,5% |

La mediana daba **exactamente 10,95% en todas las cortes**, lo que parecía un
error. Verificado: **el 54% de los cobros vale exactamente 0,01%**, la tasa
base de Binance. Es el piso del mercado asomando por la mediana.

**El carry sí es no direccional:** paga en tramos alcistas y bajistas por
igual. Eso juega a favor de E3.

**La falsación previa a codificar de E3, con sus dos lecturas:**

- *Literalmente sobrevive*: 10,95% es treinta veces el 0,36% que cuesta montar
  y desmontar la estructura.
- *Pero el capital se ocupa en las dos patas*, así que sobre capital son
  **5,47%**, y **5,12% neto**. Sobre 500 USDT: **25,57 dólares al año.**

La especificación había anticipado este caso y pedía nombrarlo en vez de
esconderlo detrás de un buen ratio. Nombrado.

Un detalle técnico que importa: **el intervalo de cobro no es 8 horas para
todos.** De 106 perpetuos, 21 cobran cada 4 horas y 5 cada 2. Anualizar con la
constante les borra la mitad del carry.

---

## 4. Las cuatro estrategias

Todas con parámetros cerrados de antemano, tomados de literatura publicada o
de una medición previa. **No se barrió ningún parámetro.**

| | Qué es |
|---|---|
| **E0** | BTC solo. Dentro si el cierre supera la media de 200 días; tamaño por volatilidad objetivo del 35% |
| **E1** | Top 5 por momentum a 28 días sobre volatilidad, del universo de 20; pesos por inversa de volatilidad; misma compuerta |
| **E2** | E1 más una pata corta de 5 nombres en perpetuos; sin compuerta; financiación modelada |
| **E3** | Largo Spot + corto perpetuo sobre el mismo activo, para cobrar financiación |

---

## 5. El cuadro, sobre la misma ventana

Cada estrategia se corrió con la ventana que le tocaba, pero compararlas así
sería comparar períodos distintos. Acá van todas sobre **2020-01-01 a
2024-12-31** — la manda E2, porque antes de 2020 no había perpetuos.

| | CAGR | Caída máx. | **Calmar** | Sobre 500 USDT | Costo/año |
|---|---|---|---|---|---|
| **B1** comprar y mantener BTC | +66,97% | −76,6% | **0,874** | **+5.989** | — |
| Nulo: 42% de BTC, comprado una vez | +42,96% | −66,6% | 0,645 | +2.487 | — |
| **E0** | +32,80% | −40,2% | **0,816** | +1.567 | 0,93% |
| **E1** | +15,38% | −44,7% | **0,344** | +523 | 1,66% |
| **E2** | −6,41% | −60,9% | **−0,105** | −138 | 3,54% |
| **E3** (de la medición 5.1) | +5,12% | — | — | +128 | 0,36% |

### La matriz de criterios

| | 1 Calmar | 2 Caída | 3 vs base | 4 IC | 5 cola | 6 costo | |
|---|---|---|---|---|---|---|---|
| **E0** | NO | sí | NO | NO | NO | sí | **2/6** |
| **E1** | NO | sí | NO | NO | NO | sí | **2/6** |
| **E2** | NO | NO | NO | NO | NO | NO | **0/6** |

El criterio 1 exige Calmar ≥ 1,8 × el de B1, o sea **1,573**. El mejor de los
cuatro llegó a **0,816**.

**No falta un ajuste: falta un factor de 1,9.**

---

## 6. Las cinco cosas que quedaron medidas

Son las que condicionan cualquier estrategia que venga después.

### 6.1 Cada capa de complejidad restó, y de forma monótona

```
  comprar y mantener BTC            0,874
  + compuerta y volatilidad (E0)    0,816
  + selección por momentum (E1)     0,344
  + pata corta (E2)                -0,105
```

No hay una capa que aporte y otra que reste: **todas restan, y cada una más
que la anterior.** El costo sube en el mismo orden: 0,93% → 1,66% → 3,54%
anual, con 8,8 → 12,5 → 25,5 vueltas de cartera.

### 6.2 La compuerta de régimen funciona — pero solo empata

Contra el control nulo correcto (tener la misma fracción de BTC comprada una
vez y no tocarla), la compuerta **compra un 26% de Calmar**. Es real.

El problema es otro: **mezclar BTC con efectivo baja el Calmar** (0,645 contra
0,874). La compuerta recupera eso y un poco más, y con eso te deja donde
estabas comprando BTC.

Dónde se gana y dónde se paga, en dos años:

| Año | E0 | B1 |
|---|---|---|
| **2021** | **−15,2%** | **+57,6%** |
| **2022** | **−0,0%** | **−65,3%** |

**2022 es la compuerta haciendo su trabajo perfecto.** **2021 es la factura**,
y es exactamente el año de los 19 latigazos que había marcado la medición 3.4.
El seguro contra 2022 se paga con 2021.

### 6.3 Elegir por momentum salió peor que no elegir

E1 y la canasta B2 (los 10 más líquidos, equiponderada, mismo rebalanceo)
operan el mismo universo. La única diferencia es que E1 **elige cinco por
momentum**:

| | Calmar |
|---|---|
| B2, sin ninguna señal | **0,405** |
| E1, eligiendo por momentum | **0,268** |

*(sobre la ventana 2019-2024)*

Y el criterio 4 de E1 es el más duro de todos: **el intervalo de confianza del
CAGR cruza cero.** No es que E1 rinda poco — no hay evidencia de que gane
nada.

### 6.4 La pata corta es la peor de las capas

E2 pierde plata. Dos números explican por qué:

- **67 de los 93 stops de catástrofe cayeron en la pata corta**, unos 13 por
  año sobre 5 posiciones, con un stop de 4×ATR que debería ser rarísimo. Es el
  desplome de momentum visto del otro lado: **las monedas de peor momentum son
  las que rebotan más violentamente.**
- **2022: E2 perdió 25,4% mientras el mercado caía 65,3%.** Si la neutralidad
  funcionara, ese tendría que haber sido su mejor año. Que pierda ahí dice que
  el problema no es la exposición al mercado, es la selección.

**Lo que sí funcionó fue la financiación:** la pata corta cobró **+109,81
USDT**, el 22% del capital inicial en cinco años. El único mecanismo nuevo que
E2 traía hizo lo que la medición prometía, y la estrategia igual pierde.

### 6.5 La concentración sigue siendo el indicador que más avisa

CAGR que queda sacando los **3 mejores meses de 60**:

| | Completo | Sin 3 meses |
|---|---|---|
| E0 | +32,80% | **+12,44%** |
| E1 | +15,38% | +2,56% |
| E2 | −6,41% | −13,51% |

Ninguna pasa el criterio 5. Es el mismo hallazgo que hundió la Fase 1, medido
con una herramienta mejor: la curva de retiro top-k no pregunta "¿hay un mes
grande?" sino **"¿cuánto sobrevive sin él?"**.

---

## 7. Lo que este trabajo NO corrige

Van pegados a cualquier lectura de estos resultados.

**Supervivencia residual.** El archivo corrige los pares deslistados de
Binance, pero no las monedas que nunca llegaron a listarse ahí. El universo
sigue siendo "lo que Binance consideró listable".

**Sustituto de liquidez en vez de capitalización.** Se ordena por volumen
cotizado porque el archivo no trae capitalización. La rotación del 41% contra
el 37% de la literatura sugiere que el sustituto es razonable, pero es una
desviación consciente.

**Un solo intercambio.** Riesgo de exchange, regulatorio y de suspensión de
retiros no están modelados.

**Régimen histórico.** La ventana contiene un mercado alcista extraordinario:
BTC hizo +1.199% en cinco años. **B1 es un rival durísimo acá y lo sería mucho
menos en otra década.** Esto no rescata a ninguna candidata —los criterios
estaban escritos de antemano— pero es parte honesta de la lectura.

**Filtros de intercambio de época mixta.** Binance no versiona `exchangeInfo`.
Los símbolos vivos traen el mínimo de hoy (5 USDT) y los muertos quedaron
congelados en el viejo (10 USDT). Sesgo optimista, chico, **declarado en vez
de corregido porque el dato para corregirlo no existe**.

**Escala de capital.** Todo asume que 500 USDT no mueven el precio. Cierto en
el top-20; deja de serlo uno o dos órdenes de magnitud más arriba.

---

## 8. Qué quedó construido

Nada de esto depende de la estrategia y todo se reusa.

- **Capa de datos sin sesgo de supervivencia.** 650 símbolos de Spot, 112
  perpetuos, 624.755 cobros de financiación, con verificación de checksum.
- **Universo reconstruido mes a mes** con una sola función que corta el
  futuro, y una prueba que verifica que agregar datos posteriores no cambia
  ninguna decisión pasada.
- **Modelo de costos por venue**, con financiación que cobra los cobros reales
  del archivo (no una grilla teórica) y filtros de intercambio con cobertura
  del 100% sobre el universo.
- **Capa de riesgo** con `k_max = 1,0` cerrado por código: pedir
  apalancamiento levanta una excepción.
- **Motor de cartera por exposición objetivo**, con posiciones cortas,
  financiación y liquidación de deslistados con penalización.
- **Métricas y robustez**: Calmar, comparación por pares sobre 20 arranques,
  bootstrap por bloques, curva de retiro top-k y Deflated Sharpe.
- **451 pruebas automáticas**, todas en verde.

### Cuatro errores que las pruebas encontraron y que habrían mentido a favor

1. **Unidades de tiempo mezcladas dentro de un mismo archivo mensual.** Elegir
   la unidad por el máximo del archivo tiraba 30 filas a 1970 sin ningún error
   visible. Se encontró auditando los 650 archivos, no leyendo el código.
2. **Un deslistado se recompraba y reliquidaba todos los días**, pagando la
   penalización una vez por jornada hasta el final de la serie.
3. **Al saltar el stop de catástrofe, el peso liberado se repartía entre los
   que quedaban** — o sea, subir la exposición justo después de un derrumbe.
   La especificación lo prohíbe explícitamente.
4. **La financiación se cobraba contra una grilla teórica de 00, 08 y 16 en
   punto.** El dato real trae sellos como `12:00:00.001` y símbolos de 2 y 4
   horas: ningún cobro habría coincidido.

---

## 9. Qué NO habilita este cierre

- **No habilita operar.** No existe módulo de ejecución y no debe escribirse
  ninguno. El repositorio no puede mandar una orden: el cliente tiene lista
  blanca de endpoints de solo lectura, y hay una prueba que lee el código
  fuente y falla si aparece un `create_order`.
- **No habilita apalancamiento.** `k_max = 1,0` es tope duro.
- **No abre la Fase 3.** Avanzar de fase necesita decisión explícita.
- **No consumió el holdout.** 2025 en adelante sigue cerrado por código y se
  mira una sola vez, sobre una estrategia que haya pasado todo lo demás.
  Ninguna llegó.

---

## 10. Preguntas abiertas, para quien diseñe lo que venga

1. **¿Existe algo que le gane a comprar BTC en Calmar, en un mercado con esta
   asimetría?** La ventana tiene un alcista extraordinario. La pregunta
   honesta puede no ser "qué estrategia gana" sino "en qué régimen tendría
   sentido esperar que alguna gane".

2. **La compuerta compra 26% de Calmar sobre no hacer nada, y se lo come el
   costo de tener efectivo.** ¿Hay una forma de estar fuera del riesgo sin
   estar en efectivo? Es la pregunta que E3 rozaba y que su escala no dejó
   contestar.

3. **Los latigazos de la compuerta cuestan 1,18% anual y 2021 entero.** Un
   amortiguador es un parámetro nuevo, y hay que medir qué le hace a la salida
   de enero de 2022 antes de agregarlo. Ahorrar 1,18% no sirve si el precio es
   entrar tarde al único año en que la compuerta funcionó.

4. **El momentum a 28 días no encuentra la dispersión que existe.** El techo
   de la selección perfecta es +22% cada 28 días y la correlación media es
   0,59: el espacio está. ¿Qué señal transversal lo encontraría? Esta fase
   solo puede decir cuál no.

5. **El carry de financiación funciona y es no direccional, pero rinde 25
   dólares al año a esta escala.** ¿A qué capital deja de ser irrelevante, y
   qué riesgos nuevos aparecen ahí?

---

## 11. Cierre

Cuatro estrategias, cinco mediciones previas, seis criterios escritos antes de
ver un dato. **Ninguna candidata pasó, y el mejor resultado del conjunto
quedó a un factor de 1,9 de la vara.**

El hallazgo no es que una estrategia en particular haya fallado. Es que
**sobre este universo, esta ventana y este nivel de costos, cada capa de
complejidad agregada sobre "comprar Bitcoin" empeoró el resultado ajustado por
riesgo, de forma monótona y con el costo creciendo en el mismo orden.**

Eso es un resultado, no un fracaso — y vale precisamente porque los criterios
estaban escritos de antemano y no se movió ninguno.

---

### Evidencia

Todas las corridas están guardadas en `docs/`:

| Archivo | Qué contiene |
|---|---|
| `salida_universo_30ago2026.txt` | Universo reconstruido, mediciones 5.3 y 5.5 |
| `salida_filtros_30ago2026.txt` | Filtros de intercambio y su cobertura |
| `salida_mediciones_previas_30ago2026.txt` | Mediciones 5.2 y 5.4 |
| `salida_riesgo_v2_30ago2026.txt` | Perfil de la capa de riesgo |
| `salida_e0_30ago2026.txt` | E0 y su control nulo |
| `salida_e1_30ago2026.txt` | E1 y los seis criterios |
| `salida_medicion_51_31ago2026.txt` | Financiación y la falsación de E3 |
| `salida_e2_31ago2026.txt` | E2 y los seis criterios |
| `salida_comparacion_31ago2026.txt` | Los cuatro sobre la misma ventana |

El compromiso previo con los criterios está en `docs/FASE_2_criterios.md`, con
fecha de commit anterior a la primera descarga de datos de esta fase.
