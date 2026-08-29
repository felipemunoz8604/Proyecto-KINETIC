# Bitácora KINETIC

Cronológico, más reciente arriba. Este es el documento que hay que leer
primero en cualquier sesión nueva, antes de tocar código.

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
