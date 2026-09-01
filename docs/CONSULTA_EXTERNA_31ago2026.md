# KINETIC — Consulta externa

**Fecha:** 31 de agosto de 2026
**Para:** analista de mercados de criptomonedas
**De:** Felipe Muñoz, desarrollador único del proyecto

---

## 0. Cómo leer este documento

Es la segunda consulta. La primera se hizo con el informe de cierre de la
Fase 1, y de ahí volvió una especificación de cuatro estrategias que **se
ejecutó completa**. Ninguna pasó.

Este documento no pide "otra estrategia". Pide algo más incómodo y más útil:
**decidir si hay razón para esperar que algo supere a comprar Bitcoin y no
tocarlo en este mercado, y si no la hay, qué debería hacer el proyecto.**

Se adjuntan los dos informes completos —`FASE_1_informe.md` y
`FASE_2_informe.md`— con todos los números y sus corridas. Este documento es
el resumen ejecutable: lo que está medido, lo que ya se probó, y las preguntas.

**Una advertencia de método.** Si la respuesta a esta consulta es una quinta,
sexta y séptima estrategia sobre los mismos datos, el proyecto va a encontrar
alguna que "funcione" por puro azar. Ya se probaron seis configuraciones. El
Deflated Sharpe las descuenta y ninguna llega. **Una recomendación que valga
tiene que decir por qué esperaríamos que la próxima sea distinta, no solo cuál
sería.**

---

## 1. El contexto operativo

No es negociable y limita todo lo demás.

| | |
|---|---|
| Capital | **500 USDT** |
| Venue | Binance Spot; perpetuos USDT-M disponibles pero **sin apalancamiento** (`k_max = 1,0`) |
| Costos | Spot 0,075-0,10% por lado + slippage 0,03-0,10% según liquidez. Perpetuos 0,02-0,05% + financiación |
| Mínimo de orden | 5 USDT (algunos símbolos 1, los deslistados viejos 10) |
| Operación | Automatizada, sin intervención discrecional |
| Estado | **No opera.** No existe módulo de ejecución y hay cerrojos por código que lo impiden |

**El capital manda más de lo que parece.** Con 500 USDT, una estructura que
ocupe las dos patas deja 250 por lado; una estrategia que rinda 5% anual da 25
dólares al año. Cualquier propuesta tiene que pasar por esa cuenta antes de
cualquier ratio.

---

## 2. Lo que ya se probó, y con qué resultado

**Fase 1** — rupturas de rango con confirmación de volumen, en 15m, 1h y 4h,
sobre hasta 15 pares. 500 operaciones fuera de muestra. **+2,6% en seis años**,
mediana de los pares negativa, una sola operación aportando el 36% del neto.

**Fase 2** — cuatro estrategias especificadas por la consulta anterior, más
las dos hipótesis de rescate permitidas. Ventana 2020-2024 para que sean
comparables:

| | Qué es | Calmar | Criterios |
|---|---|---|---|
| **B1** | Comprar BTC y no tocar | **0,874** | *(es la vara)* |
| Nulo | 42% de BTC comprado una vez | 0,645 | — |
| **E0** | BTC + media de 200 días + volatilidad objetivo | 0,816 | 2/6 |
| **E1** | Top 5 por momentum 28d entre los 20 más líquidos | 0,268 | 2/6 |
| **R1** | E1 con ventana de 90 días | 0,350 | 2/6 |
| **R2** | E1 con 8 posiciones | 0,306 | 1/6 |
| **E2** | E1 más pata corta en perpetuos | −0,105 | 0/6 |
| **E3** | Carry de financiación (largo Spot + corto perpetuo) | — | 25 USDT/año |

El criterio principal pedía **Calmar ≥ 1,8 × el de comprar y mantener**, o sea
1,573. El mejor llegó a 0,816.

**No falta un ajuste: falta un factor de 1,9.**

---

## 3. El hallazgo central

**Cada capa de complejidad agregada sobre "comprar Bitcoin" empeoró el
resultado ajustado por riesgo, de forma monótona:**

```
  comprar y mantener BTC            0,874
  + compuerta y volatilidad (E0)    0,816
  + selección por momentum (E1)     0,344
  + pata corta (E2)                -0,105
```

Y el costo sube en el mismo orden: **0,93% → 1,66% → 3,54% anual**.

No es que una capa haya fallado y las otras anden. Todas restan, y cada una
más que la anterior.

---

## 4. Las once restricciones medidas

Son límites del entorno, no opiniones sobre estrategias. **Cualquier propuesta
tiene que ser compatible con las once.**

### De la Fase 1

1. **El peaje es fijo y hay que superarlo por operación.** En 15m la ventaja
   típica capturada es **doce veces más chica que el costo**. Una estrategia
   intradía de alta frecuencia en Spot está muerta antes de empezar.
2. **Entre el 24% y el 29% de las operaciones que aciertan la dirección igual
   pierden plata**, por costos y por ejecución.
3. **Los umbrales absolutos no son comparables entre temporalidades.** Un
   filtro calibrado en 1h puede estar apagado en 15m y bloquear el 99,3% en 4h.
   Todo umbral debe expresarse en unidades relativas (ATR, desviaciones).
4. **La concentración detecta el problema antes que el profit factor**, en las
   tres corridas. El resultado agregado puede ser positivo con la mediana de
   los pares negativa.
5. **Barrer parámetros en retrospectiva infla entre 20% y 200%.** Ese es el
   tamaño real del autoengaño de un backtest optimizado.
6. **Un componente puede ganarse el lugar limitando daño, no generando
   señal.** El filtro de consolidación no aportaba información pero convertía
   −69 en +193 al acotar pérdidas en los pares malos.

### De la Fase 2

7. **La compuerta de régimen funciona, pero solo compensa el costo de tener
   efectivo.** Contra el control nulo correcto aporta **+26% de Calmar**; el
   problema es que mezclar BTC con efectivo *baja* el Calmar, y la compuerta
   apenas recupera eso. Su beneficio (2022: 0% contra −65% del mercado) se paga
   con sus latigazos (2021: −15% contra +58%).
8. **El universo NO se mueve todo junto.** Correlación media por pares
   **0,593**; solo 5 de 72 fechas superan 0,80. El techo de una selección
   perfecta solo-larga es **+22% cada 28 días** contra un peaje de 0,33%.
   **Hay espacio; el momentum a 28 y a 90 días no lo encuentra.**
9. **Elegir por momentum salió peor que no elegir.** Sobre el mismo universo y
   el mismo rebalanceo, la canasta equiponderada de los 10 más líquidos da
   Calmar 0,405 y E1 da 0,268.
10. **Las monedas de peor momentum rebotan violentamente.** En E2, **67 de 93
    stops de catástrofe cayeron en la pata corta**, con un stop de 4×ATR que
    debería ser rarísimo. Shortear el peor momentum es pararse delante de eso.
11. **La financiación de perpetuos es real, cobrable y no direccional** —paga
    igual en tramos alcistas y bajistas— **pero chica**: mediana 10,95% anual
    sobre nocional, que con las dos patas ocupadas son 5,12% sobre capital.

---

## 5. Lo que el proyecto ya tiene construido

Cualquier propuesta puede darlo por hecho. Nada de esto depende de la
estrategia. **454 pruebas automáticas en verde.**

- **Datos sin sesgo de supervivencia:** 650 símbolos de Spot con los
  deslistados adentro, 112 perpetuos, 624.755 cobros de financiación, todo con
  verificación de checksum.
- **Universo reconstruido mes a mes** por regla mecánica, con prueba de
  no-anticipación.
- **Modelo de costos por venue** con financiación real del archivo y filtros de
  intercambio.
- **Capa de riesgo**: pesos por inversa de volatilidad, escalar de volatilidad
  objetivo, compuerta de régimen, stop de catástrofe.
- **Motor de cartera por exposición objetivo**, con posiciones cortas,
  financiación y liquidación de deslistados con penalización.
- **Métricas y robustez**: Calmar, comparación por pares sobre 20 arranques,
  bootstrap por bloques, curva de retiro top-k, Deflated Sharpe.
- **Holdout 2025+ intacto**, cerrado por código y nunca mirado.

Escribir una estrategia nueva es escribir un módulo de `strategy/`. Todo lo
demás se reusa.

---

## 6. Los sesgos que el trabajo NO corrige

Van pegados a cualquier lectura.

- **Régimen histórico.** La ventana contiene un alcista extraordinario: BTC
  hizo +1.199% en cinco años. **B1 es un rival durísimo acá y lo sería mucho
  menos en otra década.** Esto no rescata a ninguna candidata, pero es central
  para interpretar el hallazgo.
- **Supervivencia residual.** El archivo trae los deslistados de Binance, no
  las monedas que nunca llegaron a listarse.
- **Liquidez como sustituto de capitalización**, porque el archivo no trae
  capitalización.
- **Un solo intercambio.** Riesgo de exchange y regulatorio no modelados.
- **Escala.** Todo asume que 500 USDT no mueven el precio.

---

## 7. Las preguntas

### 7.1 La pregunta de fondo

**¿Hay razón teórica o empírica para esperar que alguna estrategia
automatizable, solo-larga o casi, con 500 USDT y sin apalancamiento, supere a
comprar Bitcoin y no tocarlo en términos de Calmar?**

Si la respuesta es no —o "no en este régimen"— **eso es una respuesta válida y
la queremos escrita.** La especificación anterior ya contemplaba el caso: *"si
nada la supera, se implementa E0 y se cierra la investigación."*

### 7.2 Si la respuesta es que sí

1. **¿Qué señal transversal encontraría la dispersión que el momentum no
   encuentra?** Está medido que el espacio existe (correlación 0,59, techo de
   +22% cada 28 días) y que el momentum a 28 y a 90 días no lo captura. ¿Qué
   otra cosa lo haría, y **con qué mecanismo económico**, no con qué
   backtest?
2. **¿Hay forma de estar fuera del riesgo sin estar en efectivo?** Es la
   pregunta que más rinde según lo medido: la compuerta compra 26% de Calmar y
   se lo come el costo de tener plata quieta. E3 la rozaba y su escala no dejó
   contestarla.
3. **¿A qué capital deja de ser irrelevante el carry de financiación**, y qué
   riesgos nuevos aparecen ahí (liquidación, base, compresión)?
4. **¿Qué le hace un amortiguador a la compuerta?** Los latigazos cuestan
   1,18% anual y el año 2021 entero. Pero retrasar las salidas puede costar la
   de enero de 2022, que es la única que valió. Es un parámetro nuevo y hay
   que medir las dos cosas antes de agregarlo.

### 7.3 Sobre el método

5. **¿Los criterios están bien puestos?** Pedir Calmar ≥ 1,8 × el de comprar y
   mantener, en una ventana donde comprar y mantener hizo +1.199%, puede ser
   una vara imposible por construcción y no una vara exigente. **Si el
   criterio está mal, decilo** — pero decilo con un criterio alternativo y con
   la razón, no con un número más cómodo.
6. **¿Cuánto pesa el sesgo de régimen?** Toda la evidencia sale de 2019-2024.
   ¿Qué de lo medido acá esperarías que se sostenga en un mercado lateral o
   bajista prolongado, y qué no?

---

## 8. Qué haría útil la respuesta

Lo que volvió de la consulta anterior funcionó muy bien y conviene repetir el
formato:

- **Hipótesis con mecanismo económico**, no con resultado de backtest.
- **Parámetros cerrados de antemano**, con la fuente de cada valor.
- **Condición de falsación explícita** para cada propuesta — idealmente una que
  se pueda evaluar con una medición barata **antes** de programar, como la que
  cerró E3.
- **Cuántas propuestas**, sabiendo que cada configuración adicional descuenta
  el Deflated Sharpe de todas las demás.
- **Y la opción de decir que no hay nada que proponer**, si esa es la lectura
  honesta de lo medido.

---

## 9. Lo que esta consulta no habilita

- No habilita operar. No hay módulo de ejecución y no se va a escribir hasta
  que algo pase el holdout.
- No habilita apalancamiento. `k_max = 1,0` es tope duro.
- No abre ninguna fase nueva. Eso lo decide Felipe.

---

### Adjuntos

| Documento | Qué es |
|---|---|
| `FASE_1_informe.md` | Cierre de la Fase 1 — rupturas de rango |
| `FASE_2_informe.md` | Cierre de la Fase 2 — las cuatro candidatas y los dos rescates |
| `FASE_2_criterios.md` | Los seis criterios, commiteados antes de bajar datos |

Las nueve corridas completas están en `docs/salida_*.txt`, listadas al final
del informe de la Fase 2.
