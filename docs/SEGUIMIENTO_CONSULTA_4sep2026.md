# KINETIC — Seguimiento de la respuesta del 4-sep-2026

**Fecha:** 4 de septiembre de 2026
**Para:** análisis cuantitativo externo
**De:** Felipe Muñoz
**Sobre:** su respuesta del 4-sep-2026 — M3a, M3b y la regla de decisión

---

## 0. El resultado

**Se ejecutaron M3a y M3b. La regla que usted escribió dice CERRAR, por la
condición de caída.** Ningún N la cumple, y el N declarado (10) tampoco.

Los criterios se escribieron y commitearon **antes** de correr, en
`docs/CRITERIOS_M3_4sep2026.md`, commit `4a4158b`. La corrida es posterior.

**Su predicción se cumplió: M3b la mata.** Pero el argumento con que usted la
cierra —"queda cerrado por imposibilidad"— **no se sostiene**, y eso es lo
primero que traemos. Va en la §2.

Y hay un hallazgo que no estaba en su plan y que es el resultado técnico de
esta etapa: **des-parpadear la compuerta de forma implementable la empeora, no
la mejora.** Va en la §3.

---

## 1. Lo que dio

**M3a — la condición de retorno.** Log-retorno de BTC en los días que cada
compuerta deja afuera. Pasa si es negativo, por más que el costo.

| | Días fuera | Trans. | Log afuera | Costo | |
|---|---|---|---|---|---|
| E0 sin des-parpadear | 699 | 39 | +0,4919 | 0,0488 | **NO** |
| consolidada N=5 *(techo)* | 703 | 15 | +0,0132 | 0,0187 | **NO** |
| consolidada N=10 *(techo)* | 694 | 13 | −0,0239 | 0,0163 | **PASA** |
| consolidada N=20 *(techo)* | 670 | 11 | −0,1615 | 0,0138 | **PASA** |
| consolidada N=30 *(techo)* | 641 | 9 | −0,2175 | 0,0112 | **PASA** |
| **confirmada N=5** *(real)* | 707 | 15 | **+0,9724** | 0,0187 | **NO** |
| **confirmada N=10** *(real)* | 703 | 13 | **+1,2666** | 0,0163 | **NO** |
| **confirmada N=20** *(real)* | 689 | 11 | **+0,7847** | 0,0138 | **NO** |
| **confirmada N=30** *(real)* | 670 | 9 | **+0,7753** | 0,0112 | **NO** |

**M3b — la condición de caída.** Umbral 38,3% sobre la caída máxima; 30,6%
sobre la media de los 3 peores episodios.

| | Caída máx. | | 3 episodios | |
|---|---|---|---|---|
| E0 sin des-parpadear | −64,2% | NO | −38,9% | NO |
| consolidada N=5 | −48,6% | NO | −32,7% | NO |
| consolidada N=10 | −48,6% | NO | −32,7% | NO |
| consolidada N=20 | −49,1% | NO | −32,9% | NO |
| consolidada N=30 | −44,0% | NO | −31,8% | NO |
| confirmada N=5 | −55,4% | NO | −48,3% | NO |
| confirmada N=10 | −66,9% | NO | −49,1% | NO |
| confirmada N=20 | −54,3% | NO | −44,4% | NO |
| confirmada N=30 | −69,5% | NO | −47,4% | NO |

**Ninguna, con ninguna de las dos medidas de caída.** El veredicto no depende
de esa elección, que era su preocupación en la §4.

---

## 2. Su conclusión de "imposibilidad" no se sostiene

Usted escribe: *"ni siquiera la compuerta oráculo que evita 2022 entero pasa
C-B′, y el asunto queda cerrado por imposibilidad, no por búsqueda agotada."*

**Su oráculo resuelve al nivel ANUAL, y la resolución es justamente lo que
decide.** Corrimos los tres:

| Oráculo | Log afuera | % de B1 | Caída | C-A′ | C-B′ |
|---|---|---|---|---|---|
| **mensual** | −3,3528 | 229,3% | **−25,2%** | **sí** | **sí** |
| **trimestral** | −1,9097 | 174,0% | **−31,7%** | **sí** | **sí** |
| anual (sin 2022) | −1,0274 | 140,0% | −53,6% | sí | **NO** |

**El oráculo mensual cumple las dos condiciones con holgura, y el trimestral
también.** Solo el anual falla, y falla exactamente por lo que usted describe:
deja adentro marzo de 2020 y mediados de 2021 enteros.

Entonces la conclusión correcta no es que sea imposible. Es que **hace falta
resolver al nivel del trimestre o más fino**, y el oráculo lo consigue porque
conoce el resultado del período antes de que empiece.

Traemos esto porque un lector que verifique va a encontrarlo, y porque la
diferencia importa: *"no existe"* y *"existe pero ningún estimador llega"* son
dos cierres distintos, y el segundo es el que la evidencia sostiene. **El
cierre no queda más débil por decirlo bien; queda más difícil de tumbar.**

---

## 3. El hallazgo que no estaba en el plan: des-parpadear empeora

Su M3a, tal como está escrito, **mira al futuro.** Para saber que un tramo
duró menos de N días hay que esperar a que termine; el día que empieza no se
sabe si va a ser corto. **No se puede operar con eso.**

Eso no lo invalida: lo vuelve un **techo**. Como falsador es válido y de una
sola cara —si ni el techo pasa, ninguna versión implementable pasa—. Como
validador no sirve. Está probado en
`test_consolidar_mira_al_futuro_y_confirmar_no`, que corta la serie antes de
que un tramo termine y verifica que la consolidada **cambia hacia atrás**
cuando llegan datos nuevos.

Por eso medimos también la versión implementable: **confirmación de N días**,
la señal tiene que sostenerse antes de actuar. Solo usa el pasado.

**Y acá está el resultado:**

| N | Log afuera, techo | Log afuera, real | Diferencia |
|---|---|---|---|
| 5 | +0,0132 | +0,9724 | +0,9593 |
| 10 | −0,0239 | +1,2666 | +1,2905 |
| 20 | −0,1615 | +0,7847 | +0,9463 |
| 30 | −0,2175 | +0,7753 | +0,9928 |

**Las cuatro versiones implementables dejan afuera entre +0,78 y +1,27 de
log-retorno. La compuerta cruda de E0, sin des-parpadear, dejaba afuera
+0,49.** Des-parpadear de forma honesta la hace **entre 1,6 y 2,6 veces peor**
en la condición de retorno.

Y en la de caída también: la confirmada a N=10 cae **−66,9%**, contra −64,2%
de la cruda.

**Esto importa para su §7.3.** Usted diagnosticó bien —el problema es que la
compuerta suelta la posición en un mercado que sube— pero **el des-parpadeo es
la cura equivocada.** La confirmación retrasa la reentrada después de cada
hueco, y en este mercado los huecos se recuperan rápido: la demora cuesta más
que el latigazo que evita.

Si hubiéramos medido solo su versión, el techo pasa C-A′ en N=10, 20 y 30, y
habríamos concluido que del lado del retorno A2 tenía margen. **La versión
implementable dice lo contrario.** Separar las dos es lo que evitó ese error.

---

## 4. La regla, aplicada

Copiada de su §5.3 y ejecutada sin interpretarla:

1. ¿Ningún N deja afuera log-retorno negativo? → **no** (el techo lo logra
   con N = 10, 20, 30).
2. ¿Ningún N deja adentro una caída menor a 38,3%? → **SÍ, ninguno.**
3. N declarado = 10: techo **C-A′ pasa, C-B′ no**; real **C-A′ no, C-B′ no**.

> **La regla dice CERRAR. A2 no se corre.**

Y por la regla adicional que escribimos antes de medir: aunque el techo
hubiera cumplido las dos, la versión implementable no lo hace, y A2 tendría
que ser implementable.

---

## 5. Verificado: los números de detectabilidad

Su §3 es aritmética correcta sobre los intervalos que medimos. Reproduce
exacto:

| | Semiancho/mes | Exceso anual necesario |
|---|---|---|
| B4 sin compuerta | 0,0218 | **29,8%** |
| B3 constante | 0,0287 | **41,2%** |
| E0 | 0,0334 | **49,3%** |
| E1 | 0,0426 | **66,6%** |

Está implementado en `metrics/frontera.exceso_detectable` y no calculado a
mano, porque es el número que usted propone como hallazgo central y un
hallazgo central se calcula donde se pueda probar.

Coincidimos en que es lo más importante que sale de los cuatro intercambios:
**es un resultado sobre la muestra, no sobre las estrategias.**

---

## 6. Dónde queda el cierre, dicho con precisión

Hay **dos** cierres en pie y conviene no confundirlos, porque uno es más
fuerte que el otro:

**El cierre de diseño.** Dentro del espacio "compuerta de encendido y apagado
sobre BTC a exposición plena", ninguna versión estimable cumple las dos
condiciones sobre 2020-2024, y las implementables van en la dirección
contraria. **Esto es sobre este espacio de diseño, no sobre todos.** Un
oráculo trimestral pasa; ningún estimador probado se le acerca.

**El cierre de muestra.** Aunque algo funcionara, esta ventana no podría
certificarlo: harían falta entre 30% y 49% anuales de exceso sobre BTC para
que el intervalo dejara de contener cero. **Este es el fuerte, y no depende
del espacio de diseño.**

El segundo es el que hace que "buscar mejor" no sea una salida, y por eso
coincidimos en no correr M1 ni M2.

---

## 7. Lo que se hizo y lo que no

**Se hizo:** M3a y M3b con los cuatro N, en las dos versiones; los tres
oráculos; las dos medidas de caída; la verificación de la detectabilidad.
Cuesta **cero pruebas de DSR** — son particiones de la serie de BTC, no
corridas de estrategia. **El contador sigue en seis.**

**No se hizo:** A2, M1, M2. No se eligió ningún N. No se tocó el holdout.

**Un error nuestro, encontrado por una prueba propia:** la primera versión de
`consolidar` fusionaba también el **primer** tramo, que está cortado por el
arranque de los datos y no por el mercado —el mismo criterio que `latigazos`
ya aplicaba al último—. Cambió los números de N=30 y ninguna conclusión. Está
corregido y con prueba.

**512 pruebas automáticas en verde**, 21 nuevas en esta etapa.

---

## 8. La única pregunta que queda

Es para Felipe y no es técnica, y usted ya la formuló bien: **la elección entre
B1 y E0 es una apuesta de régimen.**

Lo que agregamos, ahora medido: **E0 no es "B1 con menos riesgo".** Es una
apuesta distinta. Su `c_down` de 0,356 dice que gana donde el mercado pierde,
y su `c_up` de 0,441 dice que se queda con menos de la mitad de la subida. En
una ventana como 2020-2024 pierde; en una como 2022 sola, gana con claridad.

**Queda escrita como apuesta, no escondida dentro de un umbral.** Que era el
punto.

---

### Evidencia

| Archivo | Qué contiene |
|---|---|
| `CRITERIOS_M3_4sep2026.md` | La regla, commiteada en `4a4158b`, **antes** de la corrida |
| `salida_m3_4sep2026.txt` | M3a, M3b, los tres oráculos, el precio de no mirar adelante, y la verificación de detectabilidad |
| `salida_frontera_3sep2026.txt` | La etapa anterior, para contrastar |

Las pruebas que sostienen lo que se afirma acá:

- `test_consolidar_mira_al_futuro_y_confirmar_no` — la distinción entre techo
  y estrategia, verificada cortando la serie.
- `test_los_episodios_no_se_superponen` — que la media de los 3 peores sean
  tres caídas y no una partida en tres.
- `test_las_dos_condiciones_tiran_de_los_mismos_dias` — su §5.2, sobre una
  serie construida a mano donde el mecanismo se ve aislado.
