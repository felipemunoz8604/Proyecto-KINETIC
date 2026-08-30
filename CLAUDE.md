# KINETIC — contexto para Claude Code

Este archivo lo lee Claude Code solo al abrir esta carpeta. Está escrito para
que una sesión nueva entienda en dos minutos cómo se trabaja acá, sin que
Felipe tenga que explicar todo de nuevo.

## Quién es Felipe

Felipe Muñoz es el único desarrollador y **no es programador**. Explicá todo
en español simple, sin jerga sin traducir. Si necesitás que corra un comando,
dáselo completo y listo para copiar y pegar — y **en sintaxis de PowerShell**,
que es la terminal que usa. PowerShell 5.1 **no acepta `&&`**: los comandos
van de a uno.

## Qué es KINETIC

Bot de trading algorítmico para **Binance Spot** (cripto, sin
apalancamiento). Estrategia: rupturas de rango con confirmación de volumen,
filtradas por régimen de mercado, con la gestión de riesgo como capa
independiente.

**Proyecto separado de TITAN** (MetaTrader 5 / forex, en
`C:\Proyectos\Proyecto-TITAN`). Otro repo, otro entorno, otro protocolo.
Nada de acá toca aquello. Si Felipe habla de "el proyecto" sin más, fijate
en qué carpeta estás.

## Antes de escribir código: leé estos dos, en este orden

1. **`docs/BITACORA_KINETIC.md`** — cronológico, más reciente arriba. Es la
   verdad del proyecto: qué se hizo, qué se decidió y **por qué**. La entrada
   más reciente siempre dice qué es lo próximo.
2. **`MEGAPROMPT_KINETIC.md`** — las reglas. Manda sobre todo lo demás.

## Las reglas que no se negocian

1. **Cero suposiciones.** No inventes parámetros, capital, pares ni
   resultados. Si falta un dato crítico, **pará y preguntá**.
2. **Los `null` de `config.yaml` están en blanco a propósito, y ahora
   además son un resultado.** La Fase 1 cerró sin promover ninguno porque
   ninguna configuración pasó su propio criterio. **No los completes.**
3. **La estrategia y el riesgo nunca viven en el mismo archivo.** La
   estrategia dice qué señal hay; `risk/` decide si se ejecuta y con cuánto.
4. **Ninguna orden a Mainnet, nunca, por ningún motivo.** El paso a dinero
   real lo activa Felipe a mano. Ni siquiera "para probar".
5. **Ninguna fase avanza sin aprobación explícita de Felipe.**
6. Todo cambio de riesgo se justifica en la bitácora.

## Los tres cerrojos (no los aflojes)

Hoy el repo **no puede operar**, y eso está garantizado por código, no por
memoria:

1. `core/exchange_client.py` no expone ningún método de trading; tiene lista
   blanca de endpoints y el resto lanza `PermissionError`.
2. Conectarse a Mainnet exige `permitir_mainnet=True` explícito.
3. `tests/test_solo_lectura.py` **lee el código fuente** y falla si aparece
   un `create_order`/`withdraw`/`transfer`, o si `config.yaml` queda en
   `MAINNET`.

## Cómo se evita que el backtest mienta

Esto es lo más importante del proyecto y lo más fácil de romper sin darse
cuenta. Está todo probado, no lo desarmes:

- **Nada mira al futuro.** Hay una prueba que recalcula los 13 indicadores
  cortando la serie en varios puntos: si un valor cambia según cuántas velas
  *posteriores* existan, estaba espiando.
- **La entrada va a la apertura de la vela siguiente**, no al cierre de la
  vela de señal.
- **El stop no siempre se ejecuta en su precio**: si la vela abre por debajo,
  sale ahí, peor.
- **Los costos se cobran de los dos lados**: 0,1% comisión + 0,05% slippage.
- **Se descartan los primeros 30 días de cada par** (libro vacío tras el
  listado).
- **El walk-forward elige mirando solo el pasado de cada ventana.** Hay una
  prueba que espía el proceso para verificarlo. Un "fuera de muestra"
  contaminado se ve *exactamente igual* que uno limpio.
- **`mascara_de_senales()` es un atajo por velocidad**; el camino lento
  (`evaluar_vela`) es el de referencia. Dos pruebas exigen que coincidan. Si
  cambiás una condición, cambiala en los dos lados.

## Convenciones técnicas

- **Pruebas:** `venv\Scripts\python.exe -m pytest tests/ -q`
- **Datos:** salen de Binance Mainnet por el endpoint **público** de velas
  (`get_klines`), sin llaves. Testnet **no** se usa como fuente: sigue el
  precio real de cerca pero su libro de órdenes es ficticio.
- **`.env`** tiene las llaves reales y está en `.gitignore`. **Nunca lo leas
  para incluirlo en un commit, mensaje ni salida de ningún tipo.** Y nunca le
  pidas las llaves a Felipe por chat.
- **No se versiona** lo que se regenera solo: `data/`, `venv/`, `logs/`,
  `.obsidian/`, los CSV de reportes. Si generás una herramienta nueva que
  escribe un archivo derivado, agregalo al `.gitignore`.
- **No usar `pandas_ta`** (bug con numpy reciente al importar `NaN`). Los
  indicadores se calculan a mano en `strategy/indicators.py`.
- **Git:** commits nuevos siempre (nunca `--amend` salvo pedido explícito),
  mensajes que expliquen el **porqué**. Ojo con `git add -A`: ya se coló una
  vez la configuración de Obsidian.

## Dónde está parado el proyecto (29-ago-2026)

**Fases 0 y 1 CERRADAS. Ninguna fase abierta.** La Fase 1 cerró con hallazgo
negativo: la estrategia de rupturas no paga sus costos en cripto. El informe
formal es **`docs/FASE_1_informe.md`** — leelo antes de proponer nada.

Cerrar la Fase 1 **no abre la Fase 2.** No hay estrategia validada que llevar
a Testnet, y avanzar de fase necesita decisión explícita de Felipe.

Lo construido queda sano y sirve para cualquier estrategia futura: datos,
indicadores, señal, riesgo, backtest y walk-forward, con 185 pruebas.

## El error que este proyecto tiene que evitar

**Barrer parámetros hasta que algo dé lindo.** Con suficientes intentos
siempre aparece un PF 1,8 por puro azar, y no hay forma de distinguirlo de
una ventaja real.

Ya pasó una vez que las cifras engañaron: en 1 hora el sistema "ganaba", pero
**una sola operación aportaba el 161% del resultado en BTC y el 82% en ETH**.
Es el mismo hallazgo que GOLD en TITAN: una ventana aporta todo.

Por eso: **una hipótesis por vez, con razón mecánica, validada con
walk-forward.** Si una hipótesis falla, **preguntale a Felipe antes de
encadenar la siguiente** — dos hipótesis seguidas sobre los mismos datos son
un barrido con otro nombre.
