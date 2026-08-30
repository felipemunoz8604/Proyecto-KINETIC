# Fase 2 — Criterios de aceptación. COMPROMISO PREVIO

**Fecha:** 30 de agosto de 2026
**Estado:** commiteado **antes** de descargar los datos de la Fase 2

> **Este documento se commitea antes de bajar un solo dato nuevo.** Es la
> práctica que le dio validez al cierre de la Fase 1: allá se falló un
> criterio por un solo par y no se tocó, precisamente porque estaba escrito de
> antemano y había un commit con fecha anterior que lo probaba.
>
> Un criterio escrito después de ver el resultado no es un criterio, es una
> justificación.

---

## 1. Qué se está evaluando

Cuatro estrategias candidatas —**E0, E1, E2, E3**— especificadas con
parámetros cerrados en `docs/FASE_2_especificacion.md`.

**No se barre ningún parámetro.** Todos los valores salen de literatura
publicada o de una medición previa documentada. Si una estrategia funciona con
los valores por defecto, es real. Si solo funciona después de calibrarla, no
lo es.

**Máximo dos hipótesis de rescate por estrategia.** Una tercera es un barrido
con otro nombre.

---

## 2. La ventana

| | |
|---|---|
| **Diseño** | 2019-01-01 a 2024-12-31 |
| **Holdout** | 2025-01-01 en adelante |

El holdout **no se mira** hasta que una estrategia pase todos los criterios en
la ventana de diseño. Se mira **una sola vez**. Si falla ahí, la estrategia se
descarta y no se reajusta.

Está implementado como candado en `metrics/ventana.py`, no como acuerdo:
cualquier función que reciba datos posteriores al 31-dic-2024 levanta
`HoldoutBloqueado` salvo `permitir_holdout=True` explícito.

---

## 3. Los seis criterios

Se evalúan sobre la ventana de diseño. **Para pasar hay que cumplir los seis.**

| # | Criterio | Umbral |
|---|---|---|
| **1** | Calmar contra B1, **comparado por pares** | mediana del cociente ≥ **1,8** |
| **2** | Caída máxima contra B1 | ≤ **0,60 ×** MaxDD(B1) |
| **3** | Supera a la línea base barata | Calmar ≥ **1,15 ×** Calmar(B0) |
| **4** | La ventaja no es una observación afortunada | IC 95% del CAGR por bootstrap por bloques **excluye cero** |
| **5** | Robustez a la cola derecha | quitando los 3 mejores meses, CAGR ≥ **0,50 ×** CAGR(B1) |
| **6** | El costo no se come el resultado | costo total anual ≤ **25%** del CAGR bruto |

Se reporta además, **como información y no como filtro**, el cociente
CAGR(estrategia) / CAGR(B1).

### 3.1 Por qué el criterio 1 cambió respecto de la especificación

La especificación pedía `Calmar ≥ 1,8 × Calmar(B1)` con B1 medido desde el
1-ene-2019. **Medido el 30-ago-2026, Calmar(B1) va de 0,439 a 0,973 según el
mes en que arranque la ventana**, así que ese criterio exigiría entre 0,79 y
1,75 dependiendo de una fecha que nadie eligió por una razón de fondo. Mediría
en parte la estrategia y en parte el calendario.

**Forma corregida, decidida por Felipe el 30-ago-2026:** para cada una de las
20 fechas de arranque que la especificación ya pedía en su sección 7.2, se
compara el Calmar de la estrategia contra el de B1 **sobre esa misma
ventana**, y se exige que **la mediana de los cocientes** supere 1,8.

Así la fecha se cancela sola, y no agrega trabajo: esas corridas ya estaban
planificadas para la prueba de robustez. Implementado en
`metrics.robustez.comparar_por_pares`, con una prueba que fija el invariante —
si la estrategia *es* el benchmark, el cociente da 1,000 exacto en todos los
arranques.

### 3.2 Cómo interactúan los criterios 1 y 2

No son independientes: el Calmar lleva la caída en el denominador, así que
cortar más la caída afloja el retorno exigido.

| Su caída | = × B1 | CAGR que necesita | = % del de B1 |
|---|---|---|---|
| 46,0% | 0,60 | 76,2% | **108%** |
| 30,6% | 0,40 | 50,8% | 72% |
| 23,0% | 0,30 | 38,1% | 54% |
| 15,3% | 0,20 | 25,4% | 36% |

**En el tope de caída permitido hay que superar a comprar y esperar.** La vara
solo se vuelve razonable cortando la caída bastante más abajo del tope.

**La restricción que manda es la caída, no el retorno.** Queda anotado acá
antes de correr para que después nadie lo lea como una sorpresa.

### 3.3 El criterio 3 cuando E0 sale mal

Hueco detectado en la especificación y cerrado acá: el criterio 3 pide superar
a E0 por 15% en Calmar, pero **si E0 sale malo, superarlo es trivial** y el
criterio se queda sin dientes justo cuando más falta hace.

**Regla:** el criterio 3 se evalúa contra `max(Calmar(B0), Calmar(B1))`. Si la
línea base barata resulta peor que comprar y esperar, entonces comprar y
esperar pasa a ser la línea base, que es lo honesto.

---

## 4. Lo que se reporta siempre, pase o no pase

Para la estrategia y para cada benchmark, sobre la misma ventana:

CAGR · volatilidad anualizada · caída máxima y su duración · **Calmar** ·
Sortino · tiempo en mercado · rotación anualizada · costo total pagado como %
del capital medio por año · contribución de la mejor operación al **beneficio
bruto** · **curva de retiro top-k** para k = 1/3/5/10 · **IC 95% del CAGR** por
bootstrap por bloques · **Deflated Sharpe Ratio** · número de deslistados
atravesados y su impacto.

### 4.1 El DSR se reporta SIEMPRE

Agregado respecto de la especificación, que lo pedía solo «si en algún momento
se vuelve a barrer».

Probar **E0, E1, E1-R1, E1-R2, E2 y E3** sobre la misma ventana ya es
comparación múltiple, aunque cada valor venga de literatura publicada. Al no
barrer, el riesgo de sobreajuste no desaparece: **se muda de la máquina a la
persona que investiga.** El holdout lo cubre en parte; el DSR le pone número.

Se reporta con el **número de configuraciones probadas hasta ese momento**, que
crece a lo largo de la fase.

---

## 5. Qué pasa si una estrategia falla

**No se ajusta y se vuelve a correr.** Se anota el fallo y se pasa a la
siguiente. Máximo dos hipótesis de rescate por estrategia, las que ya están
nombradas en la especificación.

Si una falla un criterio por poco, **el criterio no se mueve.** Ya pasó en la
Fase 1 —7 de 15 pares cuando hacían falta 8— y no moverlo fue lo que hizo que
el cierre valiera algo.

---

## 6. Los sesgos que este diseño NO corrige

Van pegados a cualquier resultado de la Fase 2.

**Supervivencia residual.** El archivo corrige el sesgo de los pares
deslistados de Binance —**medido: 485 operando hoy contra 250 deslistados, la
Fase 1 vio el 66% del mercado que existió**— pero no corrige el de las monedas
que nunca llegaron a listarse ahí. El universo sigue siendo «lo que Binance
consideró listable», que es un filtro de calidad no aleatorio.

**Sustituto de liquidez en lugar de capitalización.** Se ordena por volumen
cotizado porque el archivo no trae capitalización. Es una desviación
consciente respecto de la literatura de referencia.

**Un solo intercambio.** Riesgo de intercambio, regulatorio y de suspensión de
retiros no están modelados en ningún backtest.

**Régimen histórico.** La ventana 2019-2026 contiene un mercado alcista
extraordinario. Una estrategia mayormente larga calibrada ahí tiene un sesgo
de régimen que ningún walk-forward corrige.

**Escala de capital.** Todo asume que 500 USDT no mueven el precio. Cierto en
el top-20; deja de serlo si el capital crece uno o dos órdenes de magnitud.

---

## 7. Lo que este documento no habilita

- **No habilita operar.** No existe módulo de ejecución y no debe escribirse
  ninguno hasta que una estrategia pase el holdout.
- **No habilita apalancamiento.** `k_max = 1,0` es tope duro (MEGAPROMPT v2.0,
  regla 7).
- **No fija configuración de producción.** Todos los valores de la Fase 2 son
  parámetros de investigación.
