# KINETIC — Seguimiento de la segunda consulta

**Fecha:** 1 de septiembre de 2026
**Para:** análisis cuantitativo externo
**De:** Felipe Muñoz
**Sobre:** su respuesta del 1-sep-2026, tras ejecutar el paso 1 de su §8

---

## 0. Qué se hizo

Se ejecutó el **paso 1**: re-puntuar las corridas existentes contra C-A y C-B.
Costó cero pruebas de DSR, como usted anticipó.

Y se agregó una medición no pedida, para verificar una sospecha propia sobre
la regla de régimen. **La sospecha resultó equivocada**, pero la medición
destapó otra cosa que sí bloquea el criterio.

**Antes que nada: su §2 es correcto.** Se verificó la aritmética completa —la
descomposición, el factor 1,93, el contrafactual de 2021 (nos da 1,24 contra
su 1,27, diferencia de redondeo anual)— y no hay ningún error. La
reformulación de "¿por qué nada funciona?" a "¿por qué bajar la caída cuesta
casi lo mismo en retorno?" es un aporte real y quedó incorporada.

Este documento trae **dos problemas de definición** que hay que cerrar antes
de que C-A y C-B puedan usarse como vara, y **una corrección nuestra**.

---

## 1. C-A, tal como está escrito, no mide una captura

C-A dice: *"en meses alcistas, retorno acumulado sobre el de B1"*. Aplicado
literalmente sobre 43 meses compuestos, eso es el cociente de dos números que
crecieron exponencialmente a tasas distintas — **no una fracción capturada**.

Para E0, la misma palabra da cuatro valores muy distintos:

| Lectura | E0 |
|---|---|
| Retornos acumulados en meses alcistas — **C-A textual** | **0,108** |
| Retornos mensuales medios geométricos | 0,333 |
| Retornos anualizados | 0,260 |
| **La "captura" de su propio §2.2** (CAGR sobre la ventana entera) | **0,490** |

Datos: E0 acumuló +150,1% en los 43 meses alcistas; B1, +1.383,9%.

**Creemos que el 70% fue elegido pensando en la cuarta lectura.** Contra el
0,490 de E0, exigir 0,70 es una vara exigente pero razonable. Contra el 0,108,
es inalcanzable para cualquier cosa que no esté comprada al 100%: **el control
nulo del 42% de BTC comprado una vez da 0,437**, y ese ni siquiera es una
estrategia.

No creemos que sea un error de razonamiento sino de redacción, y por eso lo
traemos en vez de elegir nosotros: **¿cuál de las cuatro es C-A, y el 70%
corresponde a esa?**

---

## 2. La ventana de régimen SÍ es un parámetro libre, y mueve el veredicto

Usted la presentó como *"regla de régimen, sin parámetros libres nuevos"*, con
los 12 meses tomados de la literatura de tendencia. Medimos qué pasa al
variarla, **sin tocar E0 en ninguna corrida** — solo cambia la vara:

| Ventana | Meses bajistas | C-A | **C-B** | Caída E0 | Caída B1 |
|---|---|---|---|---|---|
| 3 meses | 23 | 0,549 | 0,203 | −12,9% | −63,7% |
| 6 meses | 21 | 0,431 | 0,228 | −12,8% | −56,0% |
| 9 meses | 17 | 0,145 | **0,032** | −1,9% | −60,3% |
| **12 meses** (propuesta) | 17 | **0,108** | **0,089** | −5,6% | −63,7% |
| 18 meses | 18 | 0,551 | **0,474** | −13,7% | −29,0% |
| 24 meses | 19 | 0,733 | 0,437 | −13,7% | −31,5% |

**C-B va de 0,032 a 0,474 — un factor de 15. C-A va de 0,108 a 0,733 — un
factor de 7.**

Y el cruce con su umbral del 40% para C-B: **E0 pasa cómodo con 3, 6, 9 y 12
meses, y falla con 18 y 24.** La ventana decide el veredicto.

El mecanismo se ve en la última columna: con 18 y 24 meses el conjunto
"bajista" ya no contiene lo peor de 2022, y la caída de B1 pasa de −63,7% a
−29,0%. **Cambia el denominador, no la estrategia.**

Esto no invalida la idea de condicionar al régimen, que nos parece correcta.
Pero significa que **la ventana necesita justificación previa igual que los
umbrales**, y elegirla ahora que tenemos la tabla sería exactamente el barrido
que los dos queremos evitar.

---

## 3. Una sospecha nuestra que resultó equivocada

La traemos porque el resultado negativo es informativo.

**Sospechábamos** que el rezago de 12 meses inflaba la protección de E0: la
regla marca como bajistas a 2022-03 … 2023-06, quince meses corridos, pero BTC
subió 154,5% en 2023. Si E0 hubiera estado afuera durante esos meses
mal etiquetados, su protección sería un artefacto del rezago.

**El etiquetado sí falla:** de 17 meses marcados bajistas, **9 subieron**
(53%). Pero eso no infla nada, y la razón está en la exposición:

| | Exposición media de E0 |
|---|---|
| En los 9 meses mal etiquetados (subieron) | **0,48** |
| En los 8 que sí bajaron | **0,11** |

**E0 estaba invertido durante los meses mal etiquetados.** Contribuyeron
retorno positivo, no ceros artificiales. La protección viene de 2022, donde la
compuerta estuvo cerrada del todo y el etiquetado es correcto.

Sacando de la cuenta los 9 meses mal etiquetados —cosa que **mira al futuro y
por eso no sirve como criterio, solo como diagnóstico**— C-B pasa de **0,089 a
0,085**. Prácticamente idéntico.

**La protección de E0 es real y no es un artefacto del rezago.** La sospecha
era razonable y estaba equivocada.

---

## 4. Lo que sí quedó firme del paso 1

Con la ventana de 12 meses, sobre 2020-2024:

| | C-A | **C-B** | Retorno en alcistas | Caída en bajistas |
|---|---|---|---|---|
| **E0** | 0,108 | **0,089** | +150,1% | **−5,6%** |
| E1 | 0,080 | 0,264 | +111,4% | −16,8% |
| R1 | 0,053 | 0,158 | +73,7% | −10,1% |
| R2 | 0,105 | 0,268 | +145,6% | −17,1% |
| E2 | 0,009 | 0,670 | +12,5% | −42,7% |
| Nulo 42% | 0,437 | 0,818 | +604,2% | −52,0% |
| B1 | 1,000 | 1,000 | +1.383,9% | −63,7% |

**Su tesis principal se confirma, y con más margen del que usted suponía:** la
caída de E0 en meses bajistas es el **9%** de la de comprar y mantener —
−5,6% contra −63,7%. Usted esperaba que E0 pasara C-B con holgura. Pasa con
muchísima.

Y se confirma también su predicción de que E0 falla C-A bajo cualquier lectura
de las cuatro.

La versión de C-B sobre el **peor tramo bajista contiguo** —una curva real, no
encadenada— da exactamente lo mismo que la encadenada en las seis
configuraciones. Esa elección no está manejando el resultado.

**C-C** (IC 95% del cociente de captura, bloques de 3 meses): excluye 1,0 en
E0, E1, R1, E2 y el nulo; lo contiene en R2. Interpretamos "excluye la
indiferencia" como "no contiene 1,0"; si su intención era otra, corríjanos.

---

## 5. Las tres preguntas

1. **¿Cuál de las cuatro lecturas es C-A**, y el 70% corresponde a esa? Si es
   la del §2.2 —CAGR sobre la ventana entera— entonces C-A y C-B dejan de ser
   condicionales al régimen en el numerador, y conviene que lo diga explícito.

2. **¿Cómo se fija la ventana de régimen sin mirar la tabla de §2?** Nos
   parece que hay tres salidas honestas y no sabemos cuál prefiere: fijar 12
   por la literatura y **declarar la sensibilidad como limitación**; usar un
   criterio que no dependa de una ventana; o exigir que se cumpla en **todas**
   las ventanas de 3 a 24 meses, que es lo más duro y lo más portátil.

3. **¿De dónde salen el 70% y el 40%?** Sigue sin haber derivación. Con la
   sensibilidad de §2 encima, dos umbrales sin justificar sobre una vara que
   se mueve un factor de 15 no se pueden usar como criterio de decisión.

---

## 6. Lo que no se hizo, y por qué

**No se corrió M1.** Su §8 lo pone después del paso 1, y el paso 1 devolvió
dos problemas de definición. Correr M1 ahora significaría medir contra una
vara que todavía no está cerrada.

**No se eligió ninguna ventana ni ningún umbral.** Tenemos la tabla completa;
elegir ahora sería elegir mirando el resultado.

**No se tocó el holdout.** Sigue cerrado por código.

---

### Evidencia

| Archivo | Qué contiene |
|---|---|
| `salida_repuntaje_1sep2026.txt` | Paso 1 completo: C-A, C-B, C-C de las seis |
| `salida_sensibilidad_regimen_1sep2026.txt` | Ventanas de 3 a 24 meses y el diagnóstico de etiquetado |

**464 pruebas automáticas en verde**, incluidas diez nuevas sobre C-A y C-B —
entre ellas que el benchmark contra sí mismo da 1,000 exacto, y que la
clasificación de un mes no usa su propio resultado.
