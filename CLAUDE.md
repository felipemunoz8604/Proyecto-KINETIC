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
- **Nunca encadenes comandos destructivos de git** (`checkout --`, `reset`,
  `clean`) en una línea que hace otra cosa. El 29-ago-2026 un
  `git checkout -- .` colado en un comando que solo debía copiar un archivo
  descartó trabajo sin commitear. Si algo no está commiteado, se commitea
  **antes** de tocar el índice.
- **Decisión de gobernanza (29 de agosto de 2026):** Felipe aprueba **cada**
  operación de git a mano, una por una — igual que en TITAN. **No marques
  `git commit` ni `git push` como «no preguntar de nuevo»**, ni le sugieras
  agregar reglas de permiso para ellos. Quiere seguir viendo cada operación,
  no solo la primera vez que aparece el diálogo.
- **El remoto es privado:** `origin` apunta a
  `github.com/felipemunoz8604/Proyecto-KINETIC`, privado a propósito — el
  repo tiene la lógica de la estrategia y los resultados completos.

## Dónde está parado el proyecto (30-ago-2026)

**Fases 0 y 1 CERRADAS. Ninguna fase abierta.** La Fase 1 cerró con hallazgo
negativo **sobre muestra suficiente**: la estrategia de rupturas no tiene
ventaja explotable en Spot después de costos. El informe formal es
**`docs/FASE_1_informe.md`** — leelo antes de proponer nada. Está escrito para
sostenerse fuera del repo, y su **sección 6 tiene las seis restricciones
medidas** que condicionan cualquier estrategia nueva.

La evidencia final: 500 operaciones fuera de muestra en 15 pares en 4h, seis
años, +193 USDT sobre 7.500 de capital (2,6% total), mediana de los pares
negativa, y **una sola operación aportando el 36% del neto agregado**.

**Decisión de Felipe del 30-ago-2026: la estrategia de rupturas se descarta y
se busca otra.** Va a llevar el informe a una consulta externa con perfil de
analista de cripto. **No propongas una estrategia nueva por tu cuenta ni
empieces a escribir `strategy/` hasta que Felipe traiga esa definición.**

Cambiar de estrategia significa reescribir `strategy/`. Todo lo demás —datos,
indicadores, riesgo, backtest, walk-forward, cerrojos— se reusa tal cual, con
194 pruebas.

Cerrar la Fase 1 **no abre la Fase 2.** No hay estrategia validada que llevar
a Testnet, y avanzar de fase necesita decisión explícita de Felipe.

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

**Lo que funcionó para no engañarnos, y conviene repetir:**

1. **Escribir los criterios y commitearlos ANTES de bajar los datos.** Se hizo
   en la corrida de 15 pares (commit `d52a127`, anterior a la ejecución). Se
   falló un criterio por un solo par y no se tocó. Un criterio escrito después
   de ver el resultado no es un criterio, es una justificación.
2. **Elegir el universo con una regla mecánica** (`tools/elegir_universo.py`),
   no con una lista escrita a mano — una lista a mano viene teñida por lo que
   uno sabe de cada moneda.
3. **Mirar concentración, estabilidad y respaldo antes que el resultado.** La
   concentración detectó el problema en las tres corridas; el profit factor no.
4. **Desconfiar de una conclusión sacada de cuatro mediciones.** Con dos pares
   concluimos que el filtro de consolidación no aportaba información; con
   quince se dio vuelta. Está corregido en el informe a propósito, no borrado.
