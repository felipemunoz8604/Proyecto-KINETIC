# Bitácora KINETIC

Cronológico, más reciente arriba. Este es el documento que hay que leer
primero en cualquier sesión nueva, antes de tocar código.

---

## 29 de agosto de 2026 (cierre) — La re-corrida limpia. Estos son los números vigentes

> **Si estás retomando el proyecto, empezá por acá.** Las dos entradas de
> más abajo del 29-ago cuentan cómo se llegó hasta este punto; las cifras que
> valen son las de esta.

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
