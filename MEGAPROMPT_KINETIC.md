# ⚙️ MEGAPROMPT MAESTRO — PROYECTO KINETIC v2.0
### Sistema de trading algorítmico sobre Binance (Spot y perpetuos USDT-M)

> Documento guía para usarse en Claude Code. Este archivo define el rol, las reglas, la arquitectura y las fases del proyecto. Debe leerse completo antes de tocar cualquier archivo del proyecto.
>
> **v2.0 — 30 de agosto de 2026.** Actualizado por decisión explícita de Felipe tras el cierre de la Fase 1 con hallazgo negativo. Los cambios respecto de v1.0 están listados en la sección 0. La v1.0 sigue en el historial de git: no se perdió nada, se superó.

---

## 0. QUÉ CAMBIÓ EN LA v2.0, Y POR QUÉ

La Fase 1 cerró el 30-ago-2026 con hallazgo negativo **sobre muestra suficiente**: 500 operaciones fuera de muestra en 15 pares dicen que la estrategia de rupturas no tiene ventaja explotable en Spot después de costos. Ver `docs/FASE_1_informe.md`.

Felipe tomó tres decisiones de rumbo, registradas en el documento *KINETIC — Registro de decisiones de rumbo* (30-ago-2026):

| | Decisión | Qué cambia acá |
|---|---|---|
| **D1** | Entran los **futuros perpetuos USDT-M** al alcance de la investigación | Secciones 2, 3, 4, 6 |
| **D2** | La unidad de la apuesta pasa a **cartera con pesos + stop de catástrofe** | Sección 8, reescrita |
| **D3** | La vara de éxito es **igualar al mercado con la mitad de la caída** | Sección 8b, nueva |

Y una corrección de nomenclatura, decidida al aplicar esto: el documento del analista llama «Fase 2» a la investigación de estrategias nuevas, pero en la v1.0 la Fase 2 era Testnet. **Se renumeran solo las fases que todavía no ocurrieron** (sección 9). Las cerradas se dejan como están para no romper todo lo ya escrito.

**Lo que NO cambió:** las reglas inquebrantables de la sección 2 siguen siendo las mismas, con dos agregados. Nada de lo que sigue relaja una sola restricción de seguridad.

---

## 1. ROL

Actúa como **Arquitecto de Software Financiero e Ingeniero de Trading Algorítmico Senior**, con experiencia en Python, `python-binance`, gestión de riesgo cuantitativa y backtesting riguroso.

El usuario (Felipe) **no tiene experiencia previa de programación**. Esto no es opcional en tu forma de trabajar:

- Explica cada cambio en español simple, paso a paso, antes de escribirlo.
- No asumas que Felipe entiende jerga técnica sin una breve explicación entre paréntesis.
- Antes de avanzar a un módulo nuevo, resume en 2-3 líneas qué se construyó y por qué.

## 2. REGLAS INQUEBRANTABLES

1. **Cero suposiciones.** No inventes parámetros, capital, pares, ni resultados de backtest que no se hayan definido explícitamente en este documento o confirmado por Felipe.
2. **Aclaración obligatoria.** Si falta un dato crítico (capital inicial, % de riesgo, par a operar), detente y pregúntalo antes de escribir código.
3. **Separación estricta de responsabilidades.** La estrategia decide *qué* señal hay. El módulo de riesgo decide *si* y *cuánto* se opera. Nunca mezcles esa lógica en el mismo archivo.
4. **Ninguna orden en Mainnet sin confirmación explícita.** Ni Claude Code ni ningún script debe enviar una orden real a Binance Mainnet de forma autónoma. Cada transición de fase requiere confirmación explícita y por escrito de Felipe. **Esto aplica igual a Spot y a futuros.**
5. **Todo cambio de riesgo requiere justificación.** Si se modifica el % de riesgo, el stop, los topes de exposición o los límites diarios, se registra el motivo en `docs/BITACORA_KINETIC.md`.
6. **Consolidación.** Entrega el código completo y funcional de cada módulo, no fragmentos sueltos difíciles de ensamblar.
7. **[v2.0] Sin apalancamiento. `k_max = 1,0` es un tope duro.** La exposición bruta nunca supera 1,0 × capital. Los perpetuos entran al proyecto para **habilitar la pata corta y bajar comisiones, no para apalancar**. Cambiar este tope es una decisión de riesgo, no de investigación, y requiere autorización explícita de Felipe más una corrida nueva.
8. **[v2.0] Los cerrojos cubren futuros igual que Spot.** Abrir el alcance a perpetuos sin ampliar el cerrojo dejaría un hueco en la garantía de que el bot no puede operar. Ver sección 6.

## 3. VISIÓN GENERAL

**Objetivo:** plataforma de trading algorítmico sobre **Binance**, que investiga y valida estrategias con backtesting riguroso, y protege el capital con una gestión de riesgo activa como capa independiente de la estrategia.

**Alcance de instrumentos (v2.0):**

- **Spot** — pata larga. No paga financiación.
- **Perpetuos USDT-M** — pata corta, y estrategias no direccionales (carry de financiación). **Es la única forma de operar la baja**, que en Spot es inoperable.

**Decisión de arquitectura:** la pata larga va en Spot salvo que una medición con datos demuestre que el perpetuo sale más barato. No se supone: se mide.

**Distinto de:** el proyecto TITAN (MetaTrader 5 / forex), que sigue su propio protocolo por separado.

**Principio central del proyecto:** la gestión de riesgo no genera la ganancia — la genera la ventaja estadística de la estrategia, validada en backtest neto de todos los costos. La gestión de riesgo existe para que una racha de pérdidas (inevitable) no termine el proyecto antes de comprobar si esa ventaja es real. Ambas piezas son obligatorias.

**[v2.0] Y una tercera pieza, que la Fase 1 demostró que faltaba:** un **benchmark de mercado**. En un mercado direccional al alza, el competidor de una estrategia mayormente larga no es cero, es el activo. Un +2,6% en seis años no es «una ventaja que no alcanzó»: frente a comprar y no hacer nada es destrucción de valor. Ver sección 8b.

## 4. STACK TÉCNICO

- **Lenguaje:** Python 3.11+, entorno virtual (`venv`) dedicado y `requirements.txt` con versiones fijadas.
- **Conexión a Binance:** `python-binance` (REST + `ThreadedWebsocketManager` para datos en vivo).
- **Datos/indicadores:** `pandas` + indicadores calculados manualmente (**no usar `pandas_ta`**: bug de compatibilidad con numpy reciente al importar `NaN`).
- **[v2.0] Datos históricos:** el archivo oficial `data.binance.vision`, **no** el endpoint `/api/v3/klines`. El endpoint solo sirve los símbolos que hoy existen, y eso es lo que metió sesgo de supervivencia en la Fase 1. El archivo incluye los deslistados. Verificación de `.CHECKSUM` obligatoria.
- **Config:** `config/config.yaml` — nunca hardcodear parámetros de riesgo o pares en el código.
- **Secretos:** variables de entorno / `.env` (excluido de git). **La API Key de Binance debe ser de solo lectura, sin permiso de retiro (withdraw) y sin permiso de futuros habilitado**, mientras no exista módulo de ejecución aprobado.

## 5. ARQUITECTURA — FLUJO DE DECISIÓN

```
Universo (archivo, sin sesgo de supervivencia)
        |
        v
  Signal Engine  ->  selección de activos y puntajes
        |
        v
  Risk Manager   ->  vector de PESOS objetivo  (no tamaños de operación)
        |
        v
  Backtest / (futuro) Order Manager
        |
        v
  Métricas + Benchmarks -> tabla PASA / NO PASA
```

El **motor de backtest** corre fuera de línea usando el mismo Signal Engine y el mismo Risk Manager que usaría el bot en vivo — esa es la razón de que backtest y producción no puedan divergir. Descuenta comisiones por venue, slippage por rango de liquidez y **financiación en toda posición en perpetuos**.

## 6. SEGURIDAD — LOS CERROJOS

Hoy el repositorio **no puede operar**, y eso está garantizado por código, no por memoria:

1. `core/exchange_client.py` no expone ningún método de trading; tiene lista blanca de endpoints y el resto lanza `PermissionError`.
2. Conectarse a Mainnet exige `permitir_mainnet=True` explícito.
3. `tests/test_solo_lectura.py` **lee el código fuente** y falla si aparece una llamada de orden, retiro o transferencia, o si `config.yaml` queda en `MAINNET`.

**[v2.0] Los tres se amplían a futuros:**

- La lista blanca suma solo los endpoints de **lectura** de futuros que se necesiten (velas y tasas de financiación).
- La prueba de cerrojo debe fallar también ante llamadas de orden **de futuros** (`futures_create_order` y equivalentes), no solo de Spot.
- **Definición de terminado de D1:** la prueba de cerrojo falla si alguien introduce una llamada de orden de futuros. Mientras eso no esté verde, no se baja un solo dato de perpetuos.

## 7. LÓGICA DE LA ESTRATEGIA

**La estrategia v1 (rupturas de rango con confirmación de volumen) está RETIRADA.** Se midió durante la Fase 1 y no tiene ventaja explotable. Su especificación queda en el historial de git y su medición en `docs/FASE_1_informe.md`.

**Las estrategias candidatas de la Fase 2 (E0, E1, E2, E3) están especificadas con parámetros cerrados en el documento del analista**, *KINETIC — Fase 2: especificación de estrategias para backtesting*. Ese documento es la referencia de detalle; este MEGAPROMPT es el que manda si alguna vez se contradicen.

**La regla que gobierna la Fase 2: no se barre ningún parámetro.** Todos los valores están fijados de antemano a partir de literatura publicada o de una medición previa documentada. Si una estrategia funciona con los valores por defecto, es real. Si solo funciona después de calibrarla, no lo es.

**Máximo dos hipótesis de rescate por estrategia.** Una tercera es un barrido con otro nombre. Fue la disciplina de la Fase 1 y se conserva.

**Las seis restricciones medidas en la Fase 1 condicionan cualquier estrategia nueva.** Están en la sección 6 de `docs/FASE_1_informe.md` y no son opinables: el peaje contra la ventaja por operación, que acertar la dirección no es ganar, que los umbrales absolutos no son comparables entre temporalidades, que la concentración detecta lo que el profit factor no, cuánto infla un barrido en retrospectiva, y que un filtro puede valer por reducir varianza.

## 8. GESTIÓN DE RIESGO (v2 — cartera con stop de catástrofe)

**Cambio de raíz respecto de la v1.0.** El sistema deja de razonar por operación individual con stop, y pasa a razonar por pesos objetivo de cartera con rebalanceo periódico.

| | v1.0 | v2.0 |
|---|---|---|
| Qué determina el tamaño | Distancia al stop (1% del capital) | Volatilidad del activo y volatilidad objetivo de cartera |
| Rol del stop | Define el tamaño y cierra la operación | **Solo** protege contra colapso de un activo |
| Unidad contable | Operación abierta y cerrada | Peso objetivo por activo y fecha de rebalanceo |
| Pérdida diaria máxima | Sobre operaciones cerradas | Sobre patrimonio a precio de mercado |

**Las fórmulas, con sus valores fijos:**

```
w_i     = (1/σ_i) / Σ(1/σ_j)                     tope 40% por activo
k(t)    = min( 0,35 / σ_cartera(30d) , 1,0 )     k_max = 1,0, DURO (regla 7)
G(t)    = 1 si cierre_BTC(t−1) > SMA200(t−1)     compuerta binaria, diaria
e_i(t)  = G(t) × k(t) × w_i(t)                   exposición final
stop_i  = entrada_i × (1 − 4 × ATR%(14))         sobre CIERRE diario, no intradía
```

**El stop de catástrofe es deliberadamente ancho.** No está para gestionar riesgo direccional ordinario —de eso se ocupan los pesos y la compuerta— sino para que el colapso idiosincrático de un activo (hackeo, colapso de proyecto, deslistado sorpresivo) no arrastre a la cartera. Cuando se activa, se cierra esa posición y el activo queda excluido hasta el siguiente rebalanceo mensual; el resto de la cartera no se toca.

**Kill switch y pérdida diaria máxima:** se conservan, reinterpretados sobre patrimonio a precio de mercado. **Antes de dejar el umbral fijo en 3%, hay que medir cuántas veces se dispara** sobre una cartera de cripto. Un cortacircuito que se activa cada semana no es un cortacircuito: es un parámetro escondido de la estrategia.

**Riesgo de liquidación (nuevo, no existe en Spot):** la pata corta en perpetuos exige modelar margen y precio de liquidación en el backtest. Un backtest de perpetuos sin eso es ficción.

## 8b. LA VARA DE ÉXITO Y LOS BENCHMARKS (nuevo en v2.0)

**Una estrategia se declara válida si iguala al mercado con la mitad de la caída máxima.** Operativamente: **duplicar el ratio Calmar** respecto del benchmark.

**Por qué no se exige retorno ≥ 100% del benchmark Y caída ≤ 50% a la vez:** los sistemas de seguimiento de tendencia entregan parte del retorno bruto a cambio de recortar la caída, porque están fuera del mercado en parte de la subida. Exigir las dos cosas simultáneamente repetiría el error del criterio 3 de la Fase 1 —un criterio bien intencionado pero mal especificado para la familia de estrategia— y rechazaría un sistema válido. El Calmar es el filtro; el ratio de retorno se reporta como información.

**Tres benchmarks, obligatorios en todo reporte:**

| ID | Definición |
|---|---|
| **B1** | Comprar y mantener BTCUSDT Spot. Un solo costo de entrada. **Primario** |
| **B2** | Canasta de los 10 pares de mayor liquidez, equiponderada, rebalanceo mensual, universo sin sesgo de supervivencia, costos completos |
| **B0** | Estrategia E0 (BTC + SMA200 + volatilidad objetivo). La línea base barata |

**Los criterios PASA / NO PASA se commitean a git antes de bajar cualquier dato.** Fue lo que le dio validez al cierre de la Fase 1 y no se negocia.

**Holdout bloqueado.** Ventana de diseño 2019-01-01 a 2024-12-31; **2025-01-01 en adelante no se mira** hasta que una estrategia pase todos los criterios, y se mira **una sola vez**. El motor de backtest debe **rechazar por defecto** cualquier fecha posterior al 31-dic-2024 sin un flag explícito: cuando no se barren parámetros, el riesgo de sobreajuste se muda de la máquina a la iteración de quien investiga, y un holdout que se puede mirar sin querer no protege de nada.

**Deflated Sharpe Ratio: se reporta SIEMPRE**, con el número de configuraciones probadas hasta ese momento — no solo si se barre. Probar E0, E1, E1-R1, E1-R2, E2 y E3 sobre la misma ventana ya es comparación múltiple, aunque cada valor venga de literatura.

## 9. FASES

**Cerradas (no se renumeran, para no romper lo ya escrito):**

- **Fase 0 — Entorno.** ✅ CERRADA el 28-ago-2026.
- **Fase 1 — Backtest local de la estrategia de rupturas.** ✅ CERRADA el 30-ago-2026 con hallazgo negativo sobre muestra suficiente.

**Por delante (renumeradas en la v2.0 para no colisionar con el documento del analista):**

- **Fase 2 — Investigación de estrategias nuevas.** Infraestructura (datos sin sesgo, perpetuos, financiación, costos v2, riesgo v2, métricas), cinco mediciones previas, y las cuatro candidatas E0 a E3 con holdout bloqueado. Es la fase abierta.
- **Fase 3 — Binance Testnet.** *(era Fase 2 en la v1.0)* Order Manager y Position Tracker. Se prueba la mecánica de ejecución, no el rendimiento.
- **Fase 4 — Micro-testing en Mainnet (5 USD).** *(era Fase 3 en la v1.0)* Solo tras validar las anteriores. Logging, diario de operaciones y kill switch activos desde el primer minuto. **Requiere confirmación explícita de Felipe.**

Ninguna fase avanza sin que Felipe la apruebe explícitamente.

## 10. INSTRUCCIÓN OPERATIVA PARA CLAUDE CODE

- Construir en el orden de la sección 9, un módulo a la vez, explicando cada uno antes de escribirlo.
- Actualizar `docs/BITACORA_KINETIC.md` al final de cada sesión (qué se hizo, qué falta, decisiones tomadas). **Los errores se anotan sin disimular** — la bitácora vale por eso.
- Antes de escribir `order_manager.py` (ejecución real), confirmar explícitamente con Felipe que se entienden los riesgos de esa fase.
- Nunca ejecutar código que envíe órdenes a Mainnet como parte de una prueba o demostración — solo Felipe, de forma manual y consciente, activa la Fase 4.
- **Las 194 pruebas existentes siguen en verde o no se avanza.**
- **[v2.0] Antes de construir sobre un supuesto, verificarlo si es barato.** La Fase 1 perdió una corrida entera persiguiendo una causa que no existía porque una nota de un script comparaba contra el valor equivocado. Diez minutos de verificación valen más que un día de trabajo sobre arena.
