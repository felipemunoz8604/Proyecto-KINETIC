# KINETIC — Registro de decisiones de rumbo

**Fecha:** 30 de agosto de 2026
**Decide:** Felipe Muñoz
**Destinatario:** ingeniería de desarrollo
**Contexto:** cierre de Fase 1 con hallazgo negativo. La estrategia de rupturas de rango con confirmación de volumen queda descartada.
**Documento de detalle:** *KINETIC — Fase 2: especificación de estrategias para backtesting*. Este registro es el resumen de qué cambia en el código y por qué. Las especificaciones completas están allá.

---

## Resumen

| # | Decisión | Impacto principal en código |
|---|---|---|
| **D1** | Se evalúan **futuros perpetuos USDT-M** desde ya. KINETIC deja de estar restringido a Spot solo-largos | `data/`, modelo de costos, `security/` |
| **D2** | La unidad de la apuesta pasa a **cartera con pesos rebalanceados + stop de catástrofe**. Deja de ser "operación con stop" | **`risk/` se reescribe**, `backtest/` cambia su contabilidad |
| **D3** | La vara de éxito es **igualar al mercado con la mitad de la caída máxima** | Nuevo módulo de benchmarks y métricas, obligatorio en todo reporte |

**Nada de esto habilita operar.** No se escribe módulo de ejecución. Los tres cerrojos en código se mantienen y se amplían (ver D1).

---

## D1 — Entran los futuros perpetuos USDT-M

### Qué se decidió

KINETIC deja de estar limitado a Binance Spot solo-largos. Los perpetuos USDT-M entran al alcance de la investigación desde la Fase 2.

### Por qué

Tres razones concretas. Habilita la pata corta, que hace operable la mitad del ciclo que hoy no lo es. Baja las comisiones de forma sustancial (Spot arranca en 0,10% por lado, o 0,075% pagando en BNB; futuros arranca en 0,02% maker y 0,05% taker). Y habilita estrategias no direccionales, en concreto el carry de financiación, que no depende de acertar la dirección del precio.

### Qué hay que construir

**En `data/`:**

- Descargador de velas diarias de perpetuos desde el archivo: `data/futures/um/monthly/klines/<SÍMBOLO>/1d/`, con verificación de `.CHECKSUM`.
- **Histórico de tasas de financiación por símbolo.** Es una serie aparte de las velas, con periodicidad de 8 horas. Sin esta serie, cualquier backtest que use perpetuos es inválido y no debe correrse.
- Registro explícito de la **fecha de inicio real de cada perpetuo**. Arrancan alrededor de septiembre de 2019, no en agosto de 2017. Todo reporte que use perpetuos debe imprimir su ventana efectiva junto al resultado.

**En el modelo de costos:**

- Esquema de comisiones **por venue**: Spot y USDT-M como tablas separadas y configurables, con maker y taker distintos, y descuento por BNB como parámetro.
- **Aplicación de financiación cada 8 horas** sobre el nocional de las posiciones en perpetuos, con el signo correcto: tasa positiva significa que los largos pagan a los cortos.

**En `risk/`:**

- **Tope de apalancamiento explícito y duro: exposición bruta ≤ 1,0 × capital.** Los futuros entran para habilitar cortos y bajar comisiones, no para apalancar. Cambiar este tope requiere autorización explícita de Felipe y una corrida nueva.
- Modelado de margen y liquidación para la pata corta. Es un riesgo que no existe en Spot.

**En `security/`:**

- Extender la lista blanca de endpoints de solo lectura a los endpoints de futuros que se necesiten (klines y tasas de financiación).
- **Ampliar la prueba que lee el código fuente y falla si aparece una orden**, para que cubra también los endpoints de orden de futuros. Hoy solo cubre Spot. Este punto es importante: abrir el alcance a futuros sin ampliar el cerrojo deja un hueco en la garantía de que el bot no puede operar.

### Qué NO cambia

No se escribe módulo de ejecución, ni para Spot ni para futuros. El cliente sigue siendo de solo lectura.

### Definición de terminado

Se puede reconstruir la serie de precios y de financiación de cualquier perpetuo del universo, el modelo de costos aplica financiación con signo correcto, y la prueba de cerrojo falla si alguien introduce una llamada de orden de futuros.

---

## D2 — La unidad de la apuesta pasa a cartera con stop de catástrofe

### Qué se decidió

El sistema deja de razonar por operación individual con stop. Pasa a razonar por **pesos objetivo de cartera con rebalanceo periódico**, con un **stop de catástrofe** por posición encima.

### Por qué

El peaje de costos es fijo por ida y vuelta, así que la salida no es capturar más por operación sino operar menos veces. El informe de Fase 1 midió que ese peaje es la restricción vinculante en temporalidades bajas. Con rebalanceo mensual, la fricción anual cae al orden del 1,5% y deja de ser el problema.

### Qué hay que construir

**`risk/` se reescribe.** Es el cambio más grande de la Fase 2. La interfaz cambia de raíz:

| | Antes | Ahora |
|---|---|---|
| Entrada | precio de entrada, precio de stop | activos seleccionados, matriz de retornos |
| Salida | tamaño de la posición | **vector de pesos objetivo** |
| Qué determina el tamaño | distancia al stop | volatilidad del activo y volatilidad objetivo de cartera |
| Rol del stop | define el tamaño y cierra | solo protege contra colapso de un activo |

Componentes nuevos, con los valores fijos de la especificación:

```
w_i     = (1/σ_i) / Σ(1/σ_j)                     tope 40% por activo
k(t)    = min( 0,35 / σ_cartera(30d) , 1,0 )     k_max = 1,0, duro
G(t)    = 1 si cierre_BTC(t−1) > SMA200(t−1)     compuerta binaria, evaluada a diario
e_i(t)  = G(t) × k(t) × w_i(t)                   exposición final
stop_i  = entrada_i × (1 − 4 × ATR%(14))         sobre cierre diario, no intradía
```

Cuando el stop de catástrofe se activa, se cierra **esa** posición y el activo queda excluido hasta el siguiente rebalanceo mensual. El resto de la cartera no se toca.

**`backtest/` cambia su contabilidad.** Deja de contar operaciones abiertas y cerradas y pasa a contar posiciones con peso objetivo y eventos de rebalanceo. Tres puntos que suelen implementarse mal y hay que cuidar:

1. **En un rebalanceo se paga costo sobre el delta de peso, no sobre la posición completa.** Si un activo pasa de 20% a 25%, se paga sobre el 5%. Cobrar la posición entera infla el costo de forma masiva e invalida la comparación entre frecuencias de rebalanceo.
2. **Deriva de precios entre rebalanceos.** El peso real se separa del peso objetivo por el movimiento del mercado. Hay que decidir y documentar si se corrige solo en la fecha de rebalanceo (recomendado) o de forma continua (mucho más caro).
3. **Conversión de pesos a cantidades con los filtros del intercambio.** `LOT_SIZE.stepSize` y `NOTIONAL.minNotional` (típicamente 5 USDT en Spot) se aplican al redondear, y el residuo se reporta. Con 500 USDT y 5 posiciones, cada una ronda 100 USDT y no hay problema de mínimos, pero sin el redondeo los pesos no cierran.

**Pérdida diaria máxima y kill switch:** se conservan, reinterpretados sobre patrimonio a precio de mercado y no sobre operaciones cerradas. **Antes de dejar el umbral fijo en 3%, hay que medir cuántas veces se dispara** sobre una cartera de cripto. Un cortacircuito que se activa cada semana no es un cortacircuito: es un parámetro escondido de la estrategia.

### Definición de terminado

`risk/` devuelve un vector de pesos a partir de una selección de activos, con pruebas de que respeta el tope del 40% por activo y el tope de exposición bruta de 1,0. El backtest cobra costos sobre deltas de peso, y hay una prueba que lo verifica comparando dos rebalanceos consecutivos con y sin cambio de composición.

---

## D3 — La vara de éxito: igualar al mercado con la mitad de la caída

### Qué se decidió

Una estrategia se declara válida si iguala al mercado con la mitad de la caída máxima. Operativamente, esto se traduce a **duplicar el ratio Calmar** respecto del benchmark.

### Por qué

Fase 1 midió contra dos referencias internas: no elegir parámetro, y el mejor parámetro en retrospectiva. Nunca midió contra comprar el activo y no hacer nada. En un mercado direccional al alza y con estrategia mayormente larga, el competidor real no es cero: es el activo.

**Nota sobre la formalización.** La lectura literal exigiría dos condiciones a la vez, retorno ≥ 100% del benchmark **y** caída ≤ 50%. Esa formulación es casi con seguridad inalcanzable y rechazaría un sistema que funciona, porque los sistemas de tendencia entregan parte del retorno bruto a cambio de recortar la caída. Sería el mismo error que el criterio 3 de Fase 1: bien intencionado pero mal especificado para la familia de estrategia. Por eso el criterio operativo es el Calmar, y el ratio de retorno se reporta como información y no como filtro.

### Qué hay que construir

**Módulo de benchmarks, obligatorio en todo reporte:**

| ID | Definición |
|---|---|
| **B1** | Comprar y mantener BTCUSDT Spot. Un solo costo de entrada. Benchmark primario |
| **B2** | Canasta de los 10 pares de mayor liquidez, equiponderada, rebalanceo mensual, universo sin sesgo de supervivencia, con costos completos |
| **B0** | BTC con media de 200 días y volatilidad objetivo (estrategia E0 de la especificación). Es la línea base barata |

**Módulo de métricas.** Para la estrategia y para cada benchmark, sobre la misma ventana: CAGR, volatilidad anualizada, máxima caída y su duración, **Calmar**, Sortino, tiempo en mercado, rotación anualizada, costo total pagado como porcentaje del capital medio, contribución de la mejor operación al **beneficio bruto**, curva de retiro top-k para k = 1/3/5/10, intervalo de confianza del 95% del CAGR por bootstrap por bloques, y Deflated Sharpe Ratio.

**Reemplazo de la métrica de concentración de Fase 1.** La versión actual mide la contribución de la mejor operación como porcentaje del **neto**, y ese denominador se vuelve inestable cerca de cero: el 920% de ETH 1h fue una división por casi-cero, no una señal extrema. La versión nueva usa el **beneficio bruto** como denominador, que siempre es positivo, y se acompaña de la curva de retiro top-k.

**Emisión automática de la tabla PASA / NO PASA.** Toda corrida debe imprimir los seis criterios de aceptación de la especificación con su resultado, sin que nadie los calcule a mano.

**Barrera dura del holdout.** La ventana de diseño es 2019-01-01 a 2024-12-31. **2025-01-01 en adelante es holdout bloqueado.** Hay que implementar una barrera en el motor de backtest que impida correr sobre esa ventana sin un flag explícito, para que no se mire por accidente durante el desarrollo. Cuando no se barren parámetros, el riesgo de sobreajuste ya no está en la máquina, está en la iteración de quien investiga; un holdout que se puede mirar sin querer no protege de nada.

### Definición de terminado

Cualquier corrida emite las tres curvas de patrimonio, la tabla completa de métricas y la tabla de criterios PASA/NO PASA, y el motor rechaza por defecto cualquier fecha posterior al 31-dic-2024.

---

## Impacto por módulo

| Módulo | Impacto |
|---|---|
| `data/` | **Amplía.** Archivo histórico completo incluyendo deslistados, perpetuos, tasas de financiación |
| `indicators/` | Sin cambios. Los 13 indicadores y la prueba de no-anticipación se conservan |
| `strategy/` | **Se reescribe.** Es el diseño previsto desde Fase 1 y ahora rinde |
| `risk/` | **Se reescribe.** Cambio de interfaz completo (D2) |
| `backtest/` | **Cambia la contabilidad.** De operaciones a pesos y rebalanceos (D2) |
| `walkforward/` | Se conserva, con función nueva: estabilidad temporal y robustez a la fecha de arranque, no selección de parámetros |
| Métricas y reportes | **Módulo nuevo** (D3) |
| `security/` | **Amplía.** Cerrojos extendidos a futuros (D1) |

Las 194 pruebas existentes siguen en verde o no se avanza.

---

## Lo que sigue prohibido

- No se escribe módulo de ejecución.
- No se conecta a fondos reales.
- No se completa la configuración de producción. Los valores de la especificación son parámetros de investigación.
- No se activa apalancamiento. `k_max = 1,0` es duro.

---

## Pendientes a confirmar por ingeniería

Tres verificaciones que hay que cerrar antes de construir encima:

1. **Esquema de comisiones vigente** en la cuenta real, para Spot y USDT-M, con y sin descuento por BNB. Los números de la especificación salen de fuentes públicas y hay que confirmarlos contra la cuenta.
2. **Que el archivo de `data.binance.vision` devuelve efectivamente los pares deslistados.** La documentación oficial indica que todos los símbolos están soportados y su propio ejemplo usa un par que ya no se opera, pero conviene comprobarlo con una descarga real antes de construir la capa de universo encima. De esto depende toda la corrección del sesgo de supervivencia.
3. **Modelo de margen** para la pata corta en perpetuos: qué esquema se asume y cómo se calcula el precio de liquidación en el backtest.
