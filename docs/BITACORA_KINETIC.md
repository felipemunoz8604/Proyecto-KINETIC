# Bitácora KINETIC

Cronológico, más reciente arriba. Este es el documento que hay que leer
primero en cualquier sesión nueva, antes de tocar código.

---

## 28 de agosto de 2026 — CIERRE DE SESIÓN. Módulo 5 y qué falta

> **Si estás retomando el proyecto, empezá por acá.**

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
