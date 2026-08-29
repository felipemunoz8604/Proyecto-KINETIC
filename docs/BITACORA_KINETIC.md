# Bitácora KINETIC

Cronológico, más reciente arriba. Este es el documento que hay que leer
primero en cualquier sesión nueva, antes de tocar código.

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
