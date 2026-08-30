# KINETIC — Fase 2: especificación de estrategias para backtesting

**Destinatario:** ingeniería de desarrollo
**Origen:** cierre de Fase 1 (30-ago-2026, hallazgo negativo sobre 500 operaciones fuera de muestra)
**Autor del diseño:** análisis cuantitativo externo, encargado por Felipe Muñoz
**Fecha:** 30 de agosto de 2026
**Estado del bot:** sigue sin poder operar. Los tres cerrojos en código se mantienen. Este documento no habilita ejecución.

---

## 0. Cómo leer este documento

El informe de cierre de Fase 1 dejó seis restricciones medidas y una infraestructura de 194 pruebas que no se toca. Este documento hace tres cosas:

1. **Corrige cuatro cosas del método de Fase 1** que hay que arreglar antes de volver a medir nada (sección 2).
2. **Fija la función objetivo y los criterios de aceptación numéricos**, comprometidos antes de bajar datos (sección 3).
3. **Especifica cuatro estrategias candidatas con parámetros cerrados**, en orden de ejecución y con criterio de corte en cada etapa (secciones 6 a 9).

**La regla que gobierna todo el documento:** en Fase 2 **no se barre ningún parámetro**. Todos los valores están fijados de antemano a partir de literatura publicada. Si una estrategia funciona con los valores por defecto, es real. Si solo funciona después de calibrarla, no lo es. Fase 1 midió que un barrido en retrospectiva infla el resultado entre 20% y 200%; la forma de eliminar esa inflación no es medirla mejor, es no barrer.

Nada de lo que sigue afirma que alguna de estas estrategias vaya a ser rentable. Son hipótesis con criterios de falsación escritos por adelantado.

---

## 1. Decisiones tomadas y sus consecuencias

Felipe cerró tres decisiones el 30-ago-2026. Cada una tiene consecuencias no obvias que hay que hacer explícitas.

### 1.1 Se evalúan futuros perpetuos USDT-M desde ya

**Qué desbloquea:**

- **La pata corta.** La mitad del ciclo deja de ser inoperable. Es la pregunta abierta #2 del informe de cierre.
- **Comisiones sustancialmente menores.** Spot está en 0,10% maker y taker para cuenta regular, que baja a 0,075% pagando comisiones en BNB. Futuros arranca en 0,02% maker y 0,05% taker. En viaje de ida y vuelta maker-maker, la diferencia es de 0,15% a 0,04%.
- **Estrategias no direccionales.** El carry de financiación (long spot + short perpetuo) no depende de acertar la dirección. Es la pregunta abierta #6.

**Qué introduce, y hay que modelarlo o no vale nada:**

- **Financiación (funding).** Se cobra o se paga cada 8 horas sobre el nocional. En una posición mantenida un mes son ~90 cobros. Puede superar largamente el ahorro en comisiones. **Es un costo obligatorio del modelo, no un detalle.**
- **Riesgo de liquidación.** No existe en Spot. Obliga a un tope de apalancamiento explícito en la capa de riesgo.
- **Historia más corta.** Los perpetuos USDT-M arrancan alrededor de septiembre de 2019, no en agosto de 2017. Toda estrategia que use la pata corta tiene menos muestra, y hay que reportarlo.

**Decisión de arquitectura que se recomienda y hay que respetar:**

> La pata larga se ejecuta en **Spot** (no paga financiación). La pata corta se ejecuta en **perpetuos USDT-M** (no hay otra forma). No se usan perpetuos para la pata larga salvo que la medición de financiación de la sección 5.1 demuestre que sale más barato, cosa que hay que probar con datos, no suponer.

### 1.2 La unidad de la apuesta pasa a ser híbrida: cartera con rebalanceo + stop de catástrofe

Esto obliga a **reescribir `risk/`**. Es el único módulo fuera de `strategy/` que cambia.

| | Fase 1 | Fase 2 |
|---|---|---|
| Qué determina el tamaño | Distancia al stop (riesgo 1% del capital) | Volatilidad del activo y volatilidad objetivo de la cartera |
| Rol del stop | Define el tamaño y cierra la operación | Solo protege contra colapso de un activo. **No define el tamaño** |
| Unidad contable | Operación abierta y cerrada | Peso objetivo por activo y fecha de rebalanceo |
| Pérdida diaria máxima | Sobre operaciones cerradas | Sobre patrimonio a precio de mercado |

El stop de catástrofe existe para un caso concreto: que un activo del portafolio colapse por causa idiosincrática (hackeo, colapso de proyecto, deslistado sorpresivo). No existe para gestionar el riesgo direccional ordinario, que ahora lo gestionan los pesos y la compuerta de régimen.

### 1.3 La vara de éxito: igualar al mercado con la mitad de la caída

Esto define la función objetivo y hace obligatorio un benchmark, que es la ausencia más grave de Fase 1.

**Advertencia importante sobre cómo formalizar esto, y por qué hay que tener cuidado.**

La lectura literal sería exigir dos condiciones a la vez: retorno ≥ 100% del benchmark **y** caída máxima ≤ 50% del benchmark. Esa formulación es casi con seguridad inalcanzable, y rechazaría un sistema que funciona.

La razón es conocida: los sistemas de seguimiento de tendencia mejoran el retorno ajustado por riesgo pero típicamente **entregan parte del retorno bruto** a cambio de recortar la caída, porque están fuera del mercado en parte de la subida. Exigir las dos cosas simultáneamente repite exactamente el error del criterio 3 de Fase 1: un criterio bien intencionado pero mal especificado para la familia de estrategia que se está evaluando, que habría rechazado un sistema válido.

**La formalización correcta de "igualar al mercado con la mitad de la caída" es duplicar el ratio Calmar.** Ese es el criterio que se usa para pasar o no pasar. El ratio de retorno se reporta como información, no como filtro. Ver sección 3.

---

## 2. Cuatro correcciones al método de Fase 1

Estas se implementan **antes** de escribir una sola línea de estrategia nueva.

### 2.1 Falta el benchmark de mercado. Es obligatorio desde ahora

Las tres corridas de Fase 1 se midieron contra dos referencias internas: no elegir parámetro, y el mejor parámetro en retrospectiva. Ninguna se midió contra **comprar el activo y no hacer nada**.

En un mercado direccional al alza y con estrategia solo-largos, el competidor real no es cero. Es el activo. Un +2,6% en seis años no es "una ventaja que no alcanzó": frente a comprar y mantener es destrucción de valor de dos órdenes de magnitud.

**Requisito:** todo backtest a partir de ahora reporta como mínimo tres curvas de patrimonio y sus métricas completas, definidas en la sección 3.2.

### 2.2 La métrica de concentración se rompe cerca de cero, y hay que reemplazarla

El 920% de ETH 1h en la corrida 1 no fue una señal extrema. Fue una división por casi-cero: la contribución de una operación medida como porcentaje del **neto** tiene denominador inestable, y tiende a infinito cuando el neto tiende a cero.

Además, el criterio "ninguna operación aporta más del 20%" está mal especificado para seguimiento de tendencia, que se define por asimetría positiva: la mayoría de las operaciones pierde poco y unas pocas pagan todo el año. Ese criterio rechazaría a un trend follower funcional.

**Reemplazos obligatorios:**

| En vez de | Usar |
|---|---|
| % del **neto** que aporta la mejor operación | % del **beneficio bruto** (denominador siempre positivo) |
| Bandera binaria de concentración | **Curva de retiro top-k:** recalcular el CAGR quitando las k mejores operaciones o los k mejores meses, para k = 1, 3, 5, 10. Se grafica y se reporta |
| Juicio informal sobre si el resultado es suerte | **Bootstrap por bloques** sobre retornos diarios (bloques de 30 días, 10.000 remuestreos) → intervalo de confianza del 95% del CAGR. Si el IC cruza cero, no hay ventaja aunque la estimación puntual sea positiva |
| Estimación informal de inflación por barrido | **Deflated Sharpe Ratio** (Bailey y López de Prado), que penaliza explícitamente el número de configuraciones probadas, y **PBO/CSCV** si en algún momento se vuelve a barrer |

La intuición de Fase 1 de medir empíricamente la inflación del barrido (+18 a +58 USDT) fue correcta. El DSR le pone número formal al mismo fenómeno.

### 2.3 El peaje de 0,30% no es fijo

Verificado contra la estructura de comisiones vigente:

| Escenario | Comisión ida y vuelta | Slippage estimado | **Peaje total** |
|---|---|---|---|
| Supuesto de Fase 1 (Spot, taker, sin descuento) | 0,20% | 0,10% | **0,30%** |
| Spot, taker, comisiones en BNB | 0,15% | 0,10% | **0,25%** |
| Spot, maker, comisiones en BNB | 0,15% | ~0,02% | **~0,17%** |
| Perpetuo USDT-M, taker | 0,10% | 0,10% | **0,20%** + financiación |
| Perpetuo USDT-M, maker | 0,04% | ~0,02% | **~0,06%** + financiación |

Notas para implementación:

- En Spot a nivel VIP 0, maker y taker cuestan lo mismo (0,10%, o 0,075% con BNB). La ventaja de las órdenes maker **no está en la comisión, está en no cruzar el spread**, que es la parte de slippage.
- Las órdenes maker traen **riesgo de no ejecución**, que introduce su propio sesgo si no se modela. Solo son aplicables a estrategias sin urgencia de ejecución, es decir rebalanceo programado. **No** aplican a rupturas ni a stops.
- El descuento por BNB es del 25% en Spot y del 10% en futuros. Hay que verificar el esquema vigente contra la cuenta real antes de fijar los números en el modelo de costos.

**Consecuencia de diseño más importante:** con estos números, la frecuencia de rebalanceo se vuelve una decisión económica calculable de antemano.

| Frecuencia | Rotación supuesta | Vueltas completas/año | Costo anual @0,25% | Costo anual @0,06% |
|---|---|---|---|---|
| Semanal | 50% | 26 | **6,5%** | 1,6% |
| Quincenal | 50% | 13 | **3,3%** | 0,8% |
| Mensual | 50% | 6 | **1,5%** | 0,4% |

En Spot, el rebalanceo semanal se come entre 5 y 7 puntos de retorno anual antes de empezar. **Por eso la sección 6 especifica rebalanceo mensual para la pata larga.**

### 2.4 El sesgo de supervivencia SÍ se puede corregir

El informe de cierre dice que no hay forma de traer los pares deslistados. Eso es cierto del endpoint `/api/v3/klines`, que es lo que usa el descargador actual. **No es cierto del archivo histórico oficial.**

La documentación oficial de `binance/binance-public-data` indica que todos los símbolos están soportados en `data.binance.vision`, y el ejemplo que da la propia documentación descarga velas de `ADABKRW`, un par cuyo activo de cotización ya no se opera. El script `fetch-all-trading-pairs.sh` se describe como la forma de obtener los símbolos **actualmente activos**, lo que confirma que el archivo contiene más que eso.

**Por qué importa cuantitativamente.** Ammann, Burdorf, Liebi y Stöckl midieron el sesgo sobre 3.904 criptomonedas entre 2014 y 2021: **0,93% anualizado para carteras ponderadas por capitalización, 62,19% para carteras equiponderadas**. El agregado de 15 pares equiponderados de la corrida 3 es exactamente el peor caso.

Los mismos autores documentan que las monedas que desaparecen tienen menor capitalización, menor volumen y menor antigüedad que las supervivientes, y que **tras controlar por el sesgo desaparece la relación positiva entre retornos y momentum a una semana**, además de encontrar momentum en las grandes y reversión en las pequeñas.

**Tres consecuencias directas para el diseño:**

1. El universo se reconstruye mes a mes desde el archivo, incluyendo los pares que después desaparecieron. Especificación en 4.1.
2. Se pondera por liquidez, no equiponderado. Reduce el sesgo residual de ~62% a ~1% anual.
3. **Toda estrategia de momentum se restringe a alta capitalización/liquidez.** En el segmento pequeño el efecto documentado es de reversión, no de momentum. Un ranking sobre el universo completo estaría midiendo ruido.

---

## 3. Función objetivo y criterios de aceptación

**Se commitea a git antes de bajar cualquier dato.** Se mantiene la práctica de Fase 1, que fue lo que le dio validez al cierre.

### 3.1 Benchmarks

| ID | Definición |
|---|---|
| **B1** | Comprar y mantener BTCUSDT Spot desde el inicio de la ventana. Un solo costo de entrada (0,075% + 0,05%). Es el benchmark primario |
| **B2** | Canasta de los 10 pares de mayor liquidez, equiponderada, rebalanceo mensual, con el universo reconstruido sin sesgo de supervivencia y con costos completos |
| **B0** | Estrategia E0 de la sección 6.1. Es la línea base barata: si nada la supera, se implementa E0 y se cierra el proyecto de investigación |

### 3.2 Métricas obligatorias en todo reporte

Para la estrategia y para cada benchmark, sobre la misma ventana:

- CAGR
- Volatilidad anualizada
- **Máxima caída (MaxDD)** y duración de la caída máxima en días
- **Calmar** (CAGR / |MaxDD|) — es la métrica primaria
- Sortino
- Porcentaje de tiempo en mercado
- Rotación anualizada
- **Costo total pagado** (comisiones + slippage + financiación) expresado como % del capital medio, por año
- Contribución de la mejor operación al **beneficio bruto**
- **Curva de retiro top-k** para k = 1, 3, 5, 10
- **IC 95% del CAGR** por bootstrap por bloques
- **Deflated Sharpe Ratio**
- Número de deslistados atravesados y su impacto

### 3.3 Criterios PASA / NO PASA

Evaluados sobre la ventana de diseño **2019-01-01 a 2024-12-31**. La ventana 2025-01-01 en adelante es holdout bloqueado (sección 7.3).

| # | Criterio | Umbral |
|---|---|---|
| **1** | **Calmar de la estrategia vs B1** | ≥ **1,8 ×** Calmar(B1) |
| **2** | **Máxima caída vs B1** | ≤ **0,60 ×** MaxDD(B1) |
| **3** | **Supera a la línea base barata** | Calmar(estrategia) ≥ **1,15 ×** Calmar(B0) |
| **4** | **La ventaja no es una observación afortunada** | IC 95% del CAGR por bootstrap por bloques **excluye cero** |
| **5** | **Robustez a la cola derecha** | Quitando los 3 mejores meses, CAGR ≥ **0,50 ×** CAGR(B1) |
| **6** | **El costo no se come el resultado** | Costo total anual ≤ **25%** del CAGR bruto de la estrategia |

Se reporta además, **como información y no como filtro**, el ratio CAGR(estrategia) / CAGR(B1).

**Criterios 1 y 2 juntos son la traducción de "igualar al mercado con la mitad de la caída".** El criterio 3 es el más duro y el más importante: E0 cuesta unas pocas horas de código; cualquier cosa más compleja tiene que justificar su complejidad, o se descarta y se implementa E0.

Si una estrategia falla un criterio, **no se ajusta y se vuelve a correr**. Se anota el fallo y se pasa a la siguiente. Se permite un máximo de **dos hipótesis de rescate** por estrategia, que fue exactamente la disciplina de Fase 1 y hay que conservarla. Una tercera es un barrido con otro nombre.

---

## 4. Cambios de infraestructura previos

Se ejecutan en orden. Ninguna estrategia se codifica hasta que esto esté con pruebas en verde.

### 4.1 Capa de datos: universo sin sesgo de supervivencia

**Fuente:** `https://data.binance.vision/data/spot/monthly/klines/<SÍMBOLO>/1d/<SÍMBOLO>-1d-<AAAA>-<MM>.zip`, con verificación del `.CHECKSUM` que acompaña a cada archivo.

**Procedimiento:**

1. Enumerar los símbolos disponibles en el archivo, **no** los símbolos activos del endpoint de `exchangeInfo`. Ésta es la corrección central. Si se toman los activos de hoy, el sesgo vuelve.
2. Construir una **matriz de disponibilidad símbolo × mes**: para cada mes, qué símbolos tienen datos.
3. Descargar velas diarias (`1d`) de todos ellos. Fase 2 no necesita 15m, 1h ni 4h. El volumen de datos baja drásticamente.
4. Auditoría de huecos y duplicados por serie, reusando la herramienta existente.

**Filtros de universo, aplicados en cada fecha de rebalanceo t:**

- Par cotizado contra USDT
- Base que no sea stablecoin (`USDC`, `BUSD`, `TUSD`, `FDUSD`, `DAI`, `USDP`, `PAX`, `EUR`, `GBP`, `TRY`, `BRL`, y la lista que corresponda)
- Sin tokens apalancados (sufijos `UP`, `DOWN`, `BULL`, `BEAR`, `3L`, `3S`)
- Al menos **180 días** de historia disponible a fecha t
- Ranking por **mediana del volumen cotizado diario (quote volume) de los últimos 30 días**
- **Universo = los 20 primeros**

**Nota metodológica que hay que documentar:** la literatura ordena por capitalización de mercado. El archivo de Binance no la tiene, así que se usa volumen cotizado como sustituto de liquidez. Es una desviación consciente respecto de la literatura y hay que anotarla en la bitácora. Si más adelante se quiere cerrar esa brecha, hay que traer capitalización histórica de una fuente externa, con su propio sesgo de supervivencia a controlar.

**Manejo de deslistados:** si un símbolo desaparece del archivo después del mes m, cualquier posición en él se liquida al último cierre disponible aplicando una penalización que modela el colapso de liquidez. **Se corre sensibilidad con penalización 0%, −20% y −50%** y se reportan las tres. No se elige una: se reportan las tres.

### 4.2 Capa de datos: perpetuos y financiación

- Velas diarias de perpetuos USDT-M desde el archivo (`data/futures/um/monthly/klines/`).
- **Histórico de tasas de financiación** por símbolo. Es un dato aparte de las velas y hay que traerlo. Sin esto, cualquier backtest que use perpetuos es inválido.
- Documentar la fecha de inicio real de cada perpetuo. La muestra es más corta que en Spot y eso cambia la interpretación de todo resultado de E2 y E3.

### 4.3 Modelo de costos v2

Reemplaza al modelo de Fase 1. Debe distinguir:

- **Venue:** Spot o perpetuo USDT-M, con esquemas de comisión separados y configurables
- **Tipo de orden:** maker o taker, con parámetro explícito por estrategia
- **Financiación:** aplicada cada 8 horas al nocional de las posiciones en perpetuos, con el signo correcto (tasa positiva = los largos pagan a los cortos)
- **Slippage por liquidez:** no un valor único. Se propone una función escalonada por rango de liquidez, con los valores fijados de antemano:

| Rango de liquidez en el universo | Slippage por lado |
|---|---|
| Puestos 1 a 5 | 0,03% |
| Puestos 6 a 12 | 0,05% |
| Puestos 13 a 20 | 0,10% |

Estos valores son pesimistas a propósito, en la misma línea que el 0,05% de Fase 1, que se eligió como cinco veces el spread típico de BTCUSDT. Se puede refinar midiendo spreads reales por rango, y si se hace, hay que medirlo antes de correr, no después.

- **Filtros de intercambio:** `LOT_SIZE.stepSize`, `NOTIONAL.minNotional` (típicamente 5 USDT en Spot) y precisión de precio. Con 500 USDT y 5 posiciones, cada posición ronda 100 USDT, muy por encima del mínimo, pero el redondeo por `stepSize` debe estar en el backtest o los pesos no cerrarán.

### 4.4 Capa de riesgo v2

Reescritura de `risk/`. Interfaz nueva:

```
pesos_finales = compuerta(t) × escalar_volatilidad(t) × pesos_inversa_volatilidad(t)
```

**Pesos por inversa de la volatilidad.** Para los N activos seleccionados:

```
w_i = (1 / σ_i) / Σ_j (1 / σ_j)
σ_i = desviación estándar de retornos logarítmicos diarios de los últimos 30 días × √365
```

Tope: ningún activo supera el **40%** de la exposición bruta.

**Escalar de volatilidad de cartera.**

```
k_t = min( σ_objetivo / σ_cartera(t) , k_max )
σ_objetivo = 35% anualizado          [FIJO]
k_max = 1,0                          [FIJO — sin apalancamiento en v1]
```

`σ_cartera(t)` se calcula sobre los retornos de la cartera con pesos ex-ante de los últimos 30 días. El tope `k_max = 1,0` es innegociable en v1: los futuros entran para habilitar cortos, **no** para apalancar. Cambiar `k_max` requiere decisión explícita de Felipe y una corrida nueva.

**Compuerta de régimen.** Binaria, definida en 6.2.

**Stop de catástrofe.**

```
stop_i = precio_entrada_i × (1 − 4 × ATR%(14d)_i)     [multiplicador 4 = FIJO]
```

Evaluado **sobre el cierre diario**, no intradía. Si se activa, se cierra esa posición y el activo queda excluido hasta el siguiente rebalanceo mensual. El resto de la cartera no se toca.

Es deliberadamente ancho. No está para gestionar riesgo direccional ordinario. Está para que el colapso de un activo no arrastre a la cartera.

**Kill switch y pérdida diaria máxima.** Se conservan, reinterpretados sobre patrimonio a precio de mercado, no sobre operaciones cerradas. El 3% diario sobre una cartera de cripto va a dispararse con mucha más frecuencia que sobre operaciones individuales; **hay que medir cuántas veces se dispara antes de dejarlo fijo en 3%**, porque un cortacircuito que se activa cada semana no es un cortacircuito, es un parámetro escondido de la estrategia.

### 4.5 Métricas y benchmarks

Implementar todo lo listado en 3.1 y 3.2 como módulo reusable. Es lo que va a decidir las cuatro estrategias, así que va con pruebas propias.

### 4.6 Lo que se conserva sin cambios

`data/` (descarga incremental y auditoría), `indicators/` (13 indicadores con prueba de no-anticipación), el motor de señal con su prueba de equivalencia vela a vela, el walk-forward genérico, y la capa de seguridad con cliente de solo lectura y lista blanca de endpoints. Las 194 pruebas siguen en verde o no se avanza.

---

## 5. Mediciones previas a codificar cualquier estrategia

Cinco mediciones baratas que pueden matar una estrategia antes de escribirla. Es exactamente lo que pide la pregunta abierta #1 del informe de cierre: hacer el cálculo antes de programar.

### 5.1 Distribución de tasas de financiación

Sobre los 20 perpetuos más líquidos, 2019-2026: mediana, media, percentiles 10 y 90 de la tasa anualizada; fracción del tiempo con signo positivo; comportamiento en tramos alcistas contra bajistas.

**Decide:** si E3 (carry) tiene sentido, y si la pata larga conviene en Spot o en perpetuo.

### 5.2 Dispersión transversal del universo

Mediana de la desviación estándar transversal de los retornos a 28 días dentro del universo de 20, y correlación media por pares.

**Decide:** si la selección transversal puede aportar algo. El informe de cierre ya lo anticipó al observar que quince criptos contra el dólar suben y bajan casi todas juntas. **Si la correlación media por pares supera ~0,80 y la dispersión es baja, E1 y E2 tienen poco margen y hay que decirlo antes de invertir semanas.**

### 5.3 Rotación del universo

Porcentaje de símbolos del top-20 que salen del top-20 cada mes y cada año. Grobys y coautores documentan una rotación anual del 37% en el conjunto de las 30 mayores capitalizaciones.

**Decide:** cuánta rotación forzada por composición del universo va a pagar la estrategia, independientemente de la señal.

### 5.4 Frecuencia de cambio de la compuerta

Cuántas veces cruza BTC su media de 200 días en la ventana, y qué costo tendría cada cruce en vueltas completas de la cartera.

**Decide:** si hace falta un amortiguador contra el latigazo. **Si hace falta, es un parámetro nuevo y se cuenta como tal.**

### 5.5 Frecuencia de deslistado en el universo

De los símbolos que estuvieron en el top-20 en cada fecha, cuántos desaparecieron después del archivo, y cuándo.

**Decide:** la magnitud real del sesgo que Fase 1 no pudo medir, ahora sí medible.

---

## 6. Estrategias candidatas

Cada una con hipótesis, especificación cerrada y condición de falsación. **Ningún parámetro marcado `[FIJO]` se barre en Fase 2.**

### 6.1 E0 — Línea base: BTC con filtro de tendencia y volatilidad objetivo

**Es obligatoria y se implementa primero.** No es un descarte: es la vara. Si nada la supera, se implementa E0 y se cierra la investigación.

**Hipótesis:** la mayor parte del beneficio de "igualar al mercado con la mitad de la caída" viene de estar fuera del mercado en los tramos bajistas, no de seleccionar activos. Liu y Tsyvinski documentan momentum temporal en cripto, con el retorno actual prediciendo el retorno futuro hasta ocho semanas adelante.

**Especificación:**

| Elemento | Valor |
|---|---|
| Universo | BTCUSDT Spot, un solo activo |
| Señal | `cierre(t−1) > SMA(cierre, 200 días)(t−1)` `[FIJO]` |
| Ejecución | Apertura de la vela diaria siguiente a la señal |
| Exposición cuando la señal es cierta | `min(35% / σ_BTC(30d), 1,0)` `[FIJO]` |
| Exposición cuando es falsa | 0 (todo en USDT) |
| Venue | Spot, órdenes taker |
| Costos | 0,075% comisión + 0,03% slippage por lado |

**Falsación:** si E0 no alcanza Calmar ≥ 1,3 × Calmar(B1), el mecanismo de compuerta de régimen no funciona en este mercado, y las estrategias E1 y E2 —que dependen de la misma compuerta— quedan muy debilitadas antes de probarse. Sería un hallazgo mayor y hay que anotarlo.

---

### 6.2 E1 — Momentum transversal, solo largos, con volatilidad objetivo y compuerta

**La candidata principal.**

**Hipótesis:** el retorno ajustado por riesgo mejora combinando tres mecanismos independientes, cada uno con respaldo empírico separado: selección transversal por momentum, ponderación por inversa de volatilidad, y compuerta de régimen agregado.

**Base empírica.** Liu, Tsyvinski y Wu identifican tres factores —mercado, tamaño y momentum— que capturan el corte transversal de retornos esperados en cripto. La evidencia también indica que el efecto de momentum se concentra en la pata larga, que es justamente la que una cuenta Spot puede operar. La advertencia es igual de firme: el momentum en cripto sufre desplomes severos, una sola moneda puede anular el retorno de la cartera, y el fenómeno se asocia a las de alta capitalización — de ahí la restricción al top-20 por liquidez. La misma literatura señala que la gestión de volatilidad es útil para mitigar esos desplomes, que es exactamente el rol del escalar `k_t`.

**Especificación:**

| Elemento | Valor |
|---|---|
| Universo | Top 20 por liquidez, reconstruido mensualmente sin sesgo de supervivencia (sección 4.1) |
| Fecha de rebalanceo | Primer día de cada mes, 00:00 UTC `[FIJO]` |
| Ventana de momentum | 28 días `[FIJO]` |
| Salto (skip) | 1 día, para evitar la reversión de muy corto plazo `[FIJO]` |
| Puntaje | `s_i = r_i(28d) / σ_i(30d)` — **adimensional por construcción**, respeta la restricción 6.3 de Fase 1 |
| Selección | Los 5 de mayor `s_i`, con `s_i > 0` `[FIJO]` |
| Pesos | Inversa de la volatilidad entre los seleccionados, tope 40% por activo |
| Escalar de cartera | `k_t = min(35% / σ_cartera(30d), 1,0)` `[FIJO]` |
| Compuerta | `G_t = 1` si `BTC cierre(t−1) > SMA200(t−1)`, si no `G_t = 0`. Evaluada **diariamente** `[FIJO]` |
| Stop de catástrofe | `entrada × (1 − 4 × ATR%(14d))`, sobre cierre diario |
| Venue | Spot, **órdenes maker** en el rebalanceo (sin urgencia de ejecución), con modelado de no ejecución |
| Reintento por no ejecución | Si la orden maker no se completa en la sesión, se cierra a taker al día siguiente |

Nota sobre `s_i > 0`: si menos de 5 activos tienen puntaje positivo, se toman los que haya y el resto queda en USDT. La cartera puede quedar parcialmente en efectivo por señal, además de por compuerta.

**Falsación:** falla cualquiera de los criterios 1 a 6 de la sección 3.3. En particular, si no supera a E0 por al menos 15% en Calmar, **la selección transversal no está aportando nada sobre la compuerta de régimen**, y hay que decirlo claramente en la bitácora.

**Las dos únicas hipótesis de rescate permitidas, si E1 falla:**

- **R1:** ventana de momentum de 90 días en lugar de 28. Está dentro del rango que la literatura considera, y no es un barrido: es una segunda medición documentada.
- **R2:** 8 posiciones en lugar de 5, para diluir el riesgo idiosincrático.

Una tercera no se hace. Se cierra E1 y se pasa a E2.

---

### 6.3 E2 — Momentum transversal largo-corto con perpetuos

**Solo se codifica si E1 pasa, o si la medición 5.2 muestra dispersión transversal alta.**

**Hipótesis:** neutralizar la exposición al mercado con una pata corta en perpetuos reduce la caída máxima más de lo que reduce el retorno.

**Especificación:** idéntica a E1, con estas diferencias:

| Elemento | Valor |
|---|---|
| Pata larga | Los 5 de mayor `s_i`, en Spot |
| Pata corta | Los 5 de menor `s_i`, en perpetuos USDT-M `[FIJO]` |
| Neutralidad | Nocional bruto igual en ambas patas |
| Compuerta | **No se aplica.** La cartera es aproximadamente neutral al mercado por construcción |
| Exposición bruta total | ≤ 1,0 × capital `[FIJO — sin apalancamiento]` |
| Financiación | Modelada cada 8 h sobre la pata corta, con su signo real |
| Ventana | Desde el inicio de los perpetuos, más corta que E1. **Reportar la ventana efectiva junto a todo resultado** |

**Advertencia que hay que tener presente al leer el resultado:** el informe de cierre de Fase 1 ya observó que las criptos contra el dólar se mueven casi todas juntas. Si eso se confirma en la medición 5.2, la pata corta va a cancelar la mayor parte del retorno junto con la mayor parte del riesgo. El Calmar puede quedar bien y el **retorno absoluto puede quedar demasiado bajo para tener sentido con 500 USDT de capital**. Ese caso hay que identificarlo y reportarlo explícitamente, no esconderlo detrás de un buen ratio.

Además, la literatura corregida por sesgo de supervivencia encuentra que la relación positiva entre retornos y momentum a una semana desaparece tras el control. E2 usa 28 días, no una semana, pero **la fragilidad de la evidencia de momentum en cripto es real y E2 debe leerse con esa cautela**.

**Falsación:** falla los criterios de 3.3, o no supera a E1 en Calmar. Si no supera a E1, la pata corta no justifica el riesgo operativo adicional (liquidación, financiación, venue extra) y se descarta.

---

### 6.4 E3 — Carry de financiación (largo Spot + corto perpetuo)

**No se codifica hasta que la medición 5.1 esté hecha.** Es la única candidata verdaderamente no direccional, y responde la pregunta abierta #6 del informe de cierre.

**Hipótesis:** la tasa de financiación de los perpetuos es positiva la mayor parte del tiempo, y una posición neutral que la cobre genera retorno sin depender de acertar la dirección.

**Estructura:** comprar el activo en Spot y vender el mismo nocional en el perpetuo. La posición es aproximadamente neutral al precio y cobra financiación cuando la tasa es positiva.

**Compuerta de entrada, a decidir con los datos de 5.1:** entrar solo cuando la financiación anualizada de los últimos N días supere un umbral que cubra el costo de montar y desmontar la estructura, que son cuatro comisiones (dos legs, entrada y salida).

**Riesgos que hay que modelar o el backtest es ficción:**

- **Riesgo de base.** Spot y perpetuo pueden divergir. La posición no es perfectamente neutral.
- **Liquidación de la pata corta.** Si el colateral no cubre un movimiento fuerte al alza, la pata corta se liquida y queda una posición larga desnuda. Hay que modelar el margen explícitamente.
- **Eficiencia de capital.** La estructura ocupa capital en las dos patas. Con 500 USDT esto **reduce a la mitad el capital efectivo**, y probablemente hace la estrategia irrelevante a esta escala. Hay que calcularlo antes de codificar.
- **Compresión del rendimiento.** Es un trade conocido y ampliamente ocupado. La medición 5.1 tiene que mirar la evolución del carry en el tiempo, no solo su promedio histórico.

**Falsación previa a codificar:** si la mediana de la financiación anualizada neta de comisiones, medida en 5.1, no supera con margen el costo de montar la estructura, **E3 no se codifica**. Se anota el número y se cierra.

---

## 7. Protocolo de validación

### 7.1 Higiene que se conserva de Fase 1

Todo esto ya está construido y probado. Se aplica igual:

- Ninguna serie mira al futuro. Prueba de no-anticipación sobre los 13 indicadores, cortando la serie en varios puntos.
- Las señales se calculan sobre vela cerrada y se ejecutan a la apertura de la siguiente.
- Los costos se cobran de los dos lados, siempre.
- Se descartan los primeros 30 días de cada par tras su listado.
- El motor vectorizado se compara vela a vela contra la implementación de referencia.
- Los criterios se commitean antes de bajar los datos.

### 7.2 Qué cambia

Como en Fase 2 **no se seleccionan parámetros**, el walk-forward deja de ser un mecanismo de selección y pasa a cumplir dos funciones distintas:

1. **Estabilidad temporal:** reportar las métricas de 3.2 año por año, para ver si el resultado depende de un tramo concreto.
2. **Prueba de robustez a la fecha de arranque:** correr la estrategia con 20 fechas de inicio distintas separadas por una semana, y reportar la dispersión del resultado. Una estrategia cuyo resultado depende del día en que se empezó no es una estrategia.

### 7.3 Holdout bloqueado

**Ventana de diseño: 2019-01-01 a 2024-12-31.**
**Holdout: 2025-01-01 en adelante.**

El holdout **no se mira** hasta que una estrategia pasa todos los criterios de 3.3 en la ventana de diseño. Se mira **una sola vez**. Si falla en el holdout, la estrategia se descarta y no se reajusta.

Esto es lo que reemplaza al walk-forward como defensa contra el sobreajuste. Cuando no se barren parámetros, el riesgo de sobreajuste ya no está en la máquina: está en la iteración del investigador. Un holdout bloqueado es la única defensa contra eso.

---

## 8. Presupuesto de parámetros

| Estrategia | Parámetros libres | Valores, todos fijados de antemano |
|---|---|---|
| E0 | 2 | SMA 200 días; σ objetivo 35% |
| E1 | 5 | Ventana 28 d; N=5; universo top 20; σ objetivo 35%; SMA 200 d |
| E2 | 5 | Los mismos de E1 |
| E3 | 2 | Umbral de financiación (de 5.1); ventana de medición |

Reglas:

1. **Ningún parámetro se barre.** Todos salen de literatura publicada o de una medición previa documentada.
2. Agregar un parámetro (por ejemplo un amortiguador para la compuerta) requiere anotarlo en la bitácora **antes** de correr, con su justificación.
3. Máximo **dos hipótesis de rescate** por estrategia. Una tercera es un barrido con otro nombre.
4. Si en algún momento se decide barrer, se reporta obligatoriamente **DSR y PBO**, y se descuenta el resultado en el orden de magnitud que Fase 1 ya midió (20% a 200%).

---

## 9. Orden de trabajo y criterios de corte

| Etapa | Trabajo | Corte |
|---|---|---|
| **0** | Infraestructura: datos de archivo sin sesgo (4.1), perpetuos y financiación (4.2), costos v2 (4.3), riesgo v2 (4.4), métricas y benchmarks (4.5) | Todas las pruebas en verde, incluidas las 194 existentes |
| **1** | Las cinco mediciones previas (sección 5) | Si 5.2 muestra correlación media > 0,80 y dispersión baja, se reordena: E1 y E2 pierden prioridad frente a E0 |
| **2** | **E0** (línea base) | Si Calmar(E0) < 1,3 × Calmar(B1), anotar el hallazgo: la compuerta de régimen no funciona aquí |
| **3** | **E1** (momentum transversal solo largos) | Criterios 1 a 6 de 3.3. Máximo dos rescates |
| **4** | Decisión sobre **E3** con los datos de 5.1 | Si el carry neto no cubre el costo de la estructura, no se codifica |
| **5** | **E2** (largo-corto), solo si E1 pasó o 5.2 lo justifica | Debe superar a E1 en Calmar |
| **6** | **Holdout 2025-2026**, una sola vez, sobre la ganadora | Si falla, se descarta y no se reajusta |
| **7** | Documento de cierre de Fase 2, con el mismo estándar que el de Fase 1 | — |

**Estimación de esfuerzo:** la etapa 0 es la más pesada porque incluye reescribir `risk/` y rehacer la capa de datos. Las etapas 2 y 3 son baratas: reescriben `strategy/` y reusan todo lo demás. Ese fue exactamente el diseño arquitectónico de Fase 1 y ahora rinde.

---

## 10. Errores de Fase 1 que no se repiten

Lista de verificación para el revisor de cada corrida:

- [ ] ¿Hay benchmark de mercado en el reporte? (B1 y B2 obligatorios)
- [ ] ¿Los umbrales están en unidades de volatilidad o en rangos, nunca en porcentaje absoluto del precio? La restricción 6.3 de Fase 1 casi cierra el proyecto con una conclusión falsa por este error
- [ ] ¿La concentración se mide sobre beneficio **bruto** y no sobre neto?
- [ ] ¿Está la curva de retiro top-k?
- [ ] ¿Está el IC por bootstrap por bloques?
- [ ] ¿El universo se reconstruyó desde el archivo, incluyendo deslistados?
- [ ] ¿Se reportaron las tres sensibilidades de penalización por deslistado?
- [ ] ¿La financiación está modelada en toda posición en perpetuos?
- [ ] ¿La conclusión se sostiene sobre más de cuatro mediciones? La restricción 6.6 de Fase 1 documenta una conclusión falsa que sobrevivió con dos pares y se dio vuelta con quince
- [ ] ¿Se commitearon los criterios antes de bajar los datos?
- [ ] ¿Se respetó el límite de dos hipótesis de rescate?

---

## 11. Sesgos y riesgos que este diseño NO corrige

Van pegados a cualquier resultado de Fase 2, igual que la sección 7 del informe de Fase 1.

**Sesgo de supervivencia residual.** El archivo de Binance corrige el sesgo de los pares **deslistados de Binance**. No corrige el de las monedas que nunca llegaron a listarse ahí. El universo sigue siendo "lo que Binance consideró listable", que es un filtro de calidad no aleatorio. La magnitud residual es desconocida, pero mucho menor que la que había en Fase 1.

**Sustituto de liquidez en lugar de capitalización.** Se ordena por volumen cotizado, no por capitalización de mercado. Es una desviación consciente respecto de la literatura de referencia y puede cambiar la composición del universo en formas no medidas.

**Un solo intercambio.** Todo se mide sobre Binance. Riesgo de intercambio, riesgo regulatorio y riesgo de suspensión de retiros no están modelados en ningún backtest de este documento.

**Régimen histórico.** La ventana 2019-2026 contiene un mercado alcista extraordinario. Una estrategia solo-largos o mayormente-larga calibrada ahí tiene un sesgo de régimen que ningún walk-forward corrige.

**Escala de capital.** Todo está medido asumiendo que 500 USDT no mueven el precio, cosa que es cierta en el top-20 pero deja de serlo si el capital crece uno o dos órdenes de magnitud. El modelo de slippage por rango habría que rehacerlo.

**El apalancamiento está apagado a propósito.** `k_max = 1,0`. Los futuros entran a este proyecto para habilitar la pata corta y bajar comisiones, no para apalancar. Cambiar esto es una decisión de riesgo, no de investigación, y requiere aprobación explícita.

---

## 12. Lo que este documento NO habilita

Igual que el cierre de Fase 1:

- **No habilita operar.** No existe módulo de ejecución y no debe escribirse ninguno hasta que una estrategia pase el holdout de 7.3.
- **No habilita conectarse a fondos reales.** Los tres cerrojos en código y la prueba que lee el fuente y falla si aparece una orden se mantienen.
- **No fija ninguna configuración de producción.** Los valores de este documento son parámetros de investigación, no de operación.

---

## Anexo A — Fórmulas

```
# Momentum ajustado por volatilidad (adimensional)
r_i(t)  = cierre_i(t−1) / cierre_i(t−1−28) − 1
σ_i(t)  = std( log-retornos diarios de i, últimos 30 días ) × sqrt(365)
s_i(t)  = r_i(t) / σ_i(t)

# Pesos por inversa de volatilidad, entre los N seleccionados
w_i(t)  = (1/σ_i(t)) / Σ_j (1/σ_j(t)),   con tope w_i ≤ 0,40

# Escalar de volatilidad de cartera
σ_p(t)  = std( retornos de la cartera con pesos ex-ante, últimos 30 días ) × sqrt(365)
k(t)    = min( 0,35 / σ_p(t) , 1,0 )

# Compuerta de régimen
G(t)    = 1 si cierre_BTC(t−1) > SMA(cierre_BTC, 200)(t−1), si no 0

# Exposición final por activo
e_i(t)  = G(t) × k(t) × w_i(t)

# Stop de catástrofe
stop_i  = precio_entrada_i × (1 − 4 × ATR%(14)_i)     [evaluado sobre cierre diario]

# Financiación (solo perpetuos), cada 8 horas
flujo   = − posición_nocional × tasa_financiación
          (tasa positiva ⇒ los largos pagan a los cortos)

# Métricas
CAGR    = (patrimonio_final / patrimonio_inicial)^(365/días) − 1
MaxDD   = min_t ( patrimonio(t) / max_{s≤t} patrimonio(s) − 1 )
Calmar  = CAGR / |MaxDD|
```

---

## Anexo B — Referencias

**Factores y momentum en cripto**

- Liu, Y., Tsyvinski, A. y Wu, X. (2022). *Common Risk Factors in Cryptocurrency.* Journal of Finance 77(3), 1133-1177. Tres factores —mercado, tamaño y momentum— capturan el corte transversal de retornos esperados.
- Liu, Y. y Tsyvinski, A. (2021). *Risks and Returns of Cryptocurrency.* Review of Financial Studies 34(6), 2689-2727. Momentum temporal: el retorno actual predice el retorno futuro hasta ocho semanas adelante.

**Sesgo de supervivencia — base de la sección 2.4**

- Ammann, M., Burdorf, T., Liebi, L. y Stöckl, S. (2022). *Survivorship and Delisting Bias in Cryptocurrency Markets.* SSRN 4287573. Sesgo anualizado de 0,93% (ponderado por capitalización) frente a 62,19% (equiponderado) sobre 3.904 criptomonedas, 2014-2021. Momentum en las grandes, reversión en las pequeñas.
- Grobys, K., Sandretto, D. y Äijö, J. (2026). *On survivor cryptocurrency momentum.* Finance Research Letters 92, 109602. Rotación anual del 37% en el conjunto de las 30 mayores capitalizaciones.

**Desplomes de momentum y gestión de volatilidad**

- *Cryptocurrency momentum has (not) its moments.* Financial Markets and Portfolio Management (2025). Los desplomes de momentum en cripto son severos, una sola moneda puede anular el retorno de cartera, y la gestión de volatilidad los mitiga.

**Sobreajuste de backtests**

- Bailey, D. y López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.* Journal of Portfolio Management.
- Bailey, D., Borwein, J., López de Prado, M. y Zhu, Q. (2017). *The Probability of Backtest Overfitting.* Journal of Computational Finance.

**Datos e infraestructura**

- `binance/binance-public-data` — documentación oficial del archivo `data.binance.vision`. Todos los símbolos soportados, incluidos los que ya no se operan.
- Documentación oficial de filtros de Spot: `LOT_SIZE`, `NOTIONAL` / `MIN_NOTIONAL`, `PRICE_FILTER`.

**Verificación pendiente a cargo de ingeniería:** el esquema de comisiones vigente en la cuenta real (Spot y USDT-M, con y sin descuento por BNB) debe confirmarse contra la cuenta antes de fijar los números del modelo de costos de la sección 4.3.
