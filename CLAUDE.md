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

## Dónde está parado el proyecto (4-sep-2026)

**Fases 0, 1 y 2 CERRADAS. Ninguna fase abierta.**

La **Fase 2** cerró con hallazgo negativo sobre las cuatro candidatas que la
consulta externa había especificado. El informe formal es
**`docs/FASE_2_informe.md`** — leelo antes de proponer nada, junto con
`docs/FASE_1_informe.md`. Los dos están escritos para sostenerse fuera del
repo.

El resultado, sobre 2020-2024 y contra comprar BTC y no tocar (Calmar 0,874):

| | Calmar | Veredicto |
|---|---|---|
| **E0** BTC + compuerta + volatilidad objetivo | 0,816 | NO PASA — 2/6 criterios |
| **E1** momentum transversal largo | 0,344 | NO PASA — 2/6 |
| **E2** momentum largo/corto con perpetuos | −0,105 | NO PASA — 0/6 |
| **E3** carry de financiación | — | rinde 25 USDT al año sobre 500 |

**El hallazgo central: cada capa de complejidad agregada sobre "comprar
Bitcoin" empeoró el resultado ajustado por riesgo, de forma monótona**, con el
costo creciendo en el mismo orden (0,93% → 1,66% → 3,54% anual). El criterio 1
exigía Calmar 1,573 y el mejor llegó a 0,816: **falta un factor de 1,9, no un
ajuste.**

**Las dos hipótesis de rescate de E1 se corrieron el 31-ago-2026 por decisión
de Felipe, y las dos fallaron:** R1 (ventana de 90 días) 2/6 criterios con
Calmar 0,350, R2 (ocho posiciones) 1/6 con Calmar 0,306. La especificación
permitía dos y dice textual *"una tercera no se hace"*: **el cupo está
agotado.**

**No propongas una estrategia nueva ni una variante nueva de las que hay.**
Inventar una después de ver fallar seis configuraciones, y conociendo ya los
datos, es el barrido que este proyecto existe para evitar.

### La vara nueva (3-sep-2026): la frontera derivada

Dos consultas externas cambiaron el criterio. **Los umbrales inventados del 70%
y el 40% se retiraron y los reemplaza una identidad**, en
`metrics/frontera.py`:

    c_up  >=  1 - (1 - c_down) * R        con R = |D| / U

donde U y D son los log-retornos agregados de B1 en los meses que subió y bajó.
**No hay ningún número elegido ahí.** Pasar esa frontera y superar el retorno
total de B1 son el mismo evento, y hay una prueba que lo exige
(`test_la_frontera_es_exactamente_ganarle_a_b1`).

Sobre 2020-2024: **R = 0,5666**, y **ninguna de las siete configuraciones la
pasa** en mensual, semanal ni trimestral. E0, la mejor, capturó 0,441 y
necesitaba 0,635.

**`metrics/regimen.py` es la vara VIEJA y se conserva a propósito** — su
ventana de 12 meses resultó ser un parámetro libre que movía el resultado un
factor de 15. No la uses para decidir nada; sirve para contrastar.

**A1 y A2 están las dos contestadas y NO se corren.** A exposición plena una
compuerta solo elige días, así que pasa si y solo si los días que deja afuera
suman negativo. BTC subió +0,4919 mientras E0 estaba afuera (A1), y M3
falsó A2 el 4-sep-2026: ningún N cumple la condición de caída.

### Las dos cosas del 4-sep que hay que tener presentes

**Des-parpadear la compuerta de forma implementable la EMPEORA.** La versión
con confirmación de N días deja afuera entre +0,78 y +1,27 de log-retorno,
contra +0,49 de la compuerta cruda. La consolidación de tramos cortos que da
mejor **mira al futuro** y por eso es un techo, no una estrategia
(`test_consolidar_mira_al_futuro_y_confirmar_no`). Si proponés des-parpadear,
esto ya está medido y da peor.

**El cierre fuerte es de MUESTRA, no de diseño.** Harían falta entre 29,8% y
49,3% anuales de exceso sobre BTC para que esta ventana pudiera certificar
algo — 60 meses y un solo ciclo no alcanzan. Por eso "buscar una estrategia
mejor" no es una salida: el problema no es la estrategia, es que la muestra no
puede decidir. Un oráculo trimestral SÍ pasa las dos condiciones; ningún
estimador probado se le acerca.

**El holdout (2025 en adelante) NO se miró** y sigue cerrado por código en
`metrics/ventana.py`. Ninguna candidata llegó a merecerlo.

Lo construido se reusa entero y no depende de la estrategia: datos sin sesgo
de supervivencia, universo reconstruido mes a mes, costos por venue con
financiación, riesgo v2, motor de cartera por exposición (con cortos), y
métricas de robustez. **512 pruebas en verde.**

**Las curvas de las seis corridas se arman en un solo lugar:
`backtesting/corridas.py`.** Si necesitás las candidatas para comparar algo, usá
ese módulo — no rearmes la construcción, que ya se copió dos veces.

Cerrar la Fase 2 **no abre la Fase 3.** No hay estrategia validada que llevar
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
