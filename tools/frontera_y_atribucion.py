r"""
Pasos 1 a 4 de la respuesta del analista del 2-sep-2026. Cuestan CERO pruebas.

QUE HACE, EN EL ORDEN QUE EL LOS PIDIO
----------------------------------------
1. **Mide U, D y R sobre B1.** Fija la frontera. No depende de ninguna
   estrategia y se mide una sola vez.
2. **Recalcula c_up y c_down de las seis configuraciones** con la particion
   por el signo del propio mes, y las contrasta contra la frontera.
3. **Implementa C-B' con CDaR al 95%** en vez de la caida maxima, que tenia
   una sola observacion.
4. **Corre B3 y B4** y atribuye: cuanto de E0 es dimensionamiento y cuanto es
   temporizacion.

POR QUE NINGUNO CUESTA PRUEBAS DE DEFLATED SHARPE
---------------------------------------------------
Ninguno elige. Los cuatro miden lo ya corrido con otra vara, o resuelven una
ecuacion con una incognita:

- **La frontera** sale de una identidad algebraica sobre B1.
- **c_up y c_down** son las mismas seis curvas particionadas de otra forma.
- **La CDaR** es otro estadistico sobre las mismas curvas.
- **B3** no se busca hasta que de lindo: se resuelve para igualar un CAGR que
  ya estaba fijado. **B4** es E0 con la compuerta apagada, sin grados de
  libertad.

El contador de configuraciones probadas sigue en **seis**. Los pasos 5 y 6 --
A1 y A2 -- si cuestan una prueba cada uno, y no se corren aca.

LO QUE HAY QUE MIRAR EN LA SALIDA
-----------------------------------
**La columna `exigido` no es un umbral elegido.** Es el c_up minimo para
igualar el retorno total de B1, dado el c_down que la estrategia realmente
tuvo. Hay una prueba (`test_la_frontera_es_exactamente_ganarle_a_b1`) que
verifica que pasar la frontera y ganarle a B1 son el mismo evento.

Se corre asi:

    venv\Scripts\python.exe tools\frontera_y_atribucion.py
"""

from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import numpy as np  # noqa: E402

from backtesting import corridas  # noqa: E402
from metrics import benchmarks, frontera, metricas, regimen  # noqa: E402
from risk import compuerta as cp  # noqa: E402

CARPETA = RAIZ / "data" / "archivo"
CARPETA_PERP = RAIZ / "data" / "perpetuo"
CARPETA_FIN = RAIZ / "data" / "financiacion"
FILTROS = RAIZ / "data" / "filtros_spot.json"


def _titulo(texto: str) -> None:
    print()
    print("=" * 78)
    print(f" {texto}")
    print("=" * 78)


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True, errors="replace")
    # pandas 3.x avisa que `to_period` descarta la zona horaria. Es cierto y no
    # importa: los periodos son etiquetas, no instantes. Se calla para que el
    # archivo de evidencia quede legible.
    warnings.filterwarnings("ignore", message="Converting to PeriodArray")
    t0 = time.time()
    print("=" * 78)
    print(" KINETIC - la frontera derivada y la atribucion de E0")
    print("=" * 78)
    print("  Pasos 1 a 4 de la respuesta del analista del 2-sep-2026.")
    print("  CERO pruebas de Deflated Sharpe: ninguno elige nada. El contador")
    print("  de configuraciones probadas sigue en seis.")
    print()

    c = corridas.construir(CARPETA, CARPETA_PERP, CARPETA_FIN, FILTROS,
                           avisar=lambda t: print(f"  {t}", flush=True))
    b1 = c.b1
    print(f"  Ventana {c.dias[0].date()} a {c.dias[-1].date()}"
          f"   ({time.time() - t0:.0f} s)")

    # --- Paso 4 (se corre antes porque B3 necesita el CAGR de E0) ----------
    print("  Calibrando B3 al CAGR de E0...", flush=True)
    cagr_e0 = metricas.cagr(c.curvas["E0"])
    k_b3, curva_b3 = benchmarks.calibrar_exposicion_constante(
        lambda k: corridas.curva_a_exposicion_constante(c, k), cagr_e0)
    print("  Armando B4 (E0 sin compuerta)...", flush=True)
    curva_b4 = corridas.curva_sin_compuerta(c)

    curvas = {"B1 comprar y mantener": b1,
              f"B3 constante k={k_b3:.3f}": curva_b3,
              "B4 sin compuerta": curva_b4}
    curvas.update(c.curvas)

    # --- Paso 1 ------------------------------------------------------------
    _titulo("PASO 1 - U, D Y R SOBRE B1. LA FRONTERA QUEDA FIJADA")
    f = frontera.frontera(b1)
    print("  En log-retornos mensuales, sobre la ventana entera:")
    print()
    print(f"    U  meses en que B1 subio (n={f.periodos_arriba:>2})"
          f"          {f.u:>+9.4f}")
    print(f"    D  meses en que B1 bajo  (n={f.periodos_abajo:>2})"
          f"          {f.d:>+9.4f}")
    print(f"    R = |D| / U                          {f.r:>9.4f}")
    print()
    print("  La frontera, tal como la escribio el analista:")
    print()
    print("      c_up  >=  1 - (1 - c_down) * R")
    print()
    print(f"  {'c_down':>10}{'c_up exigido':>16}")
    for cd in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
        print(f"  {cd:>10.1f}{f.exige(cd):>16.4f}")
    print()
    print("  Se lee asi: una estrategia que no perdiera NADA en ningun mes")
    print(f"  bajista (c_down = 0) todavia necesitaria capturar el "
          f"{f.exige(0.0):.1%} de la")
    print("  subida solo para empatar con comprar y no tocar.")
    print()
    print("  Y no hay ningun numero elegido en esa linea: R se mide sobre B1")
    print("  y el resto es despejar. Ganar la frontera y ganarle a B1 en")
    print("  retorno total son EL MISMO EVENTO -- hay una prueba que lo exige.")

    # --- Paso 2 ------------------------------------------------------------
    _titulo("PASO 2 - c_up Y c_down POR EL SIGNO DEL PROPIO MES")
    print(f"  {'':<24}{'c_up':>8}{'c_down':>9}{'exigido':>10}"
          f"{'margen':>9}{'':>6}")
    puntos = {}
    for nombre, curva in curvas.items():
        p = frontera.capturas(curva, b1, nombre)
        puntos[nombre] = p
        print(f"  {nombre:<24}{p.c_up:>8.3f}{p.c_down:>9.3f}"
              f"{p.exigido:>10.3f}{p.margen:>+9.3f}"
              f"{'  PASA' if p.pasa else '    NO':>6}")
    print()
    print("  c_down NEGATIVO significa que la estrategia GANA en los meses en")
    print("  que el mercado pierde. Es lo que hace E0, y por eso la palabra")
    print("  'proteccion' se le quedaba corta.")

    print()
    print("  Control de robustez -- el mismo cuadro en semanal y trimestral.")
    print("  El criterio se fija en mensual, que es la convencion. Si el")
    print("  veredicto cambiara con el periodo, hay que decirlo.")
    print()
    print(f"  {'':<24}{'c_up sem':>10}{'pasa':>7}{'c_up trim':>12}{'pasa':>7}")
    for nombre, curva in curvas.items():
        s = frontera.capturas(curva, b1, nombre, frontera.SEMANAL)
        q = frontera.capturas(curva, b1, nombre, frontera.TRIMESTRAL)
        print(f"  {nombre:<24}{s.c_up:>10.3f}{'si' if s.pasa else 'NO':>7}"
              f"{q.c_up:>12.3f}{'si' if q.pasa else 'NO':>7}")

    # --- La correccion sobre la 5.1 del analista ---------------------------
    _titulo("LA MEZCLA DE PARTICIONES EN LA 5.1 DEL ANALISTA")
    alcistas = regimen.clasificar_meses(c.velas_btc["close"])
    viejo = regimen.puntuar(c.curvas["E0"], b1, alcistas, "E0")
    # La particion vieja, pero en log-retornos como manda su 3.
    e_log = frontera.log_por_periodo(c.curvas["E0"])
    b_log = frontera.log_por_periodo(b1)
    com = e_log.index.intersection(b_log.index).intersection(alcistas.index)
    marca = alcistas.loc[com]
    ca_vieja = float(e_log.loc[com][marca].sum() / b_log.loc[com][marca].sum())
    nuevo = puntos["E0"]
    print("  El analista evalua contra la frontera un c_up de 0,34. Ese numero")
    print("  sale de la particion VIEJA -- regimen de 12 meses -- y la")
    print("  frontera esta definida sobre la particion NUEVA, la de su 4.3.")
    print()
    print(f"  C-A vieja (regimen 12m), en log-retornos      {ca_vieja:>8.4f}")
    print(f"  c_up nuevo (signo del propio mes)             {nuevo.c_up:>8.4f}")
    print(f"  Frontera exigida a E0                         "
          f"{nuevo.exigido:>8.4f}")
    print()
    print(f"  Con la particion correcta E0 falla igual, pero por "
          f"{abs(nuevo.margen):.3f} y no")
    print(f"  por {nuevo.exigido - ca_vieja:.3f}. El veredicto no cambia; "
          "el margen si.")
    print()
    print(f"  (Y la C-A vieja en retorno simple, la del 1-sep, era "
          f"{viejo.captura:.3f}:")
    print("   el cociente de acumulados que el propio analista retiro.)")

    # --- Paso 3 ------------------------------------------------------------
    _titulo("PASO 3 - C-B' CON CDaR AL 95% EN VEZ DE LA CAIDA MAXIMA")
    print("  La caida maxima tiene UNA observacion. La CDaR al 95% promedia el")
    print("  peor 5% de la distribucion diaria de caida: cientos.")
    print()
    print(f"  {'':<24}{'caida max':>11}{'frac.':>8}{'CDaR 95%':>11}"
          f"{'frac.':>8}{'C-B?':>7}")
    for nombre, curva in curvas.items():
        peor, _, _, _ = metricas.caida_maxima(curva)
        peor_b1, _, _, _ = metricas.caida_maxima(b1)
        frac_max = abs(peor) / abs(peor_b1)
        frac_cdar = frontera.fraccion_de_cdar(curva, b1)
        print(f"  {nombre:<24}{peor * 100:>10.1f}%{frac_max:>8.3f}"
              f"{frontera.cdar(curva) * 100:>10.1f}%{frac_cdar:>8.3f}"
              f"{'  si' if frac_cdar <= frontera.CAIDA_OBJETIVO else '  NO':>7}")
    print()
    print(f"  C-B' pide la fraccion <= {frontera.CAIDA_OBJETIVO:.2f}, que es "
          "literal 'la mitad de la")
    print("  caida' del objetivo declarado por Felipe. Ese 0,50 no es")
    print("  inventado por nadie: es el objetivo, escrito como cociente.")

    print()
    print("  PERO LA CDaR NO ENTREGA LAS OBSERVACIONES QUE PROMETE")
    print("  ------------------------------------------------------")
    print("  El motivo del cambio era pasar de UNA observacion a cientos. Se")
    print("  conto cuantos valores DISTINTOS hay en la cola del peor 5%:")
    print()
    print(f"  {'':<24}{'dias en la cola':>17}{'valores distintos':>19}")
    for nombre, curva in curvas.items():
        caidas = frontera.caida_diaria(curva).to_numpy()
        k = max(1, int(round(len(caidas) * (1.0 - frontera.NIVEL_CDAR))))
        cola = np.sort(caidas)[:k]
        print(f"  {nombre:<24}{k:>17}"
              f"{len(np.unique(np.round(cola, 10))):>19}")
    print()
    print("  Mientras una estrategia esta AFUERA del mercado su patrimonio no")
    print("  se mueve, asi que su caida contra el maximo previo es la MISMA")
    print("  todos esos dias. La cola de E0 son 91 copias de un solo numero.")
    print()
    print("  O sea que para una estrategia con compuerta a efectivo la CDaR")
    print("  degenera en la caida maxima, y el argumento de 'cientos de")
    print("  observaciones' no vale justo para el tipo de estrategia que se")
    print("  esta evaluando. El veredicto no cambia -- E0 falla C-B' con las")
    print("  dos medidas -- pero la razon para cambiar de medida si.")

    # --- C-C' ---------------------------------------------------------------
    _titulo("C-C' - IC 95% DEL EXCESO MENSUAL DE LOG-RETORNO CONTRA B1")
    print("  Antes se remuestreaba el cociente de captura y se preguntaba si")
    print("  excluia 1,0. Con la frontera la indiferencia ya no esta en 1,0,")
    print("  asi que se mide el exceso directo y se pide que excluya CERO.")
    print()
    for nombre, curva in curvas.items():
        bajo, alto = frontera.intervalo_de_exceso(curva, b1)
        veredicto = "excluye cero" if (alto < 0 or bajo > 0) else "CONTIENE cero"
        print(f"  {nombre:<24}[{bajo:>+8.4f}, {alto:>+8.4f}]   {veredicto}")

    # --- Paso 4 ------------------------------------------------------------
    _titulo("PASO 4 - ATRIBUCION: DIMENSIONAMIENTO CONTRA TEMPORIZACION")
    print("  B3 es exposicion constante calibrada al MISMO CAGR que E0: aisla")
    print("  cuanto de E0 se consigue simplemente tomando menos posicion.")
    print("  B4 es E0 sin la compuerta: aisla lo que aporta la compuerta.")
    print()
    print(f"  {'':<24}{'CAGR':>10}{'caida max':>11}{'Calmar':>9}{'vs B1':>8}")
    calmar_b1 = metricas.calcular(b1, "B1").calmar
    for nombre in ("B1 comprar y mantener", f"B3 constante k={k_b3:.3f}",
                   "B4 sin compuerta", "E0"):
        m = metricas.calcular(curvas[nombre], nombre)
        print(f"  {nombre:<24}{m.cagr * 100:>+9.2f}%"
              f"{m.caida_maxima * 100:>10.1f}%{m.calmar:>9.3f}"
              f"{m.calmar / calmar_b1:>8.3f}")

    m_b3 = metricas.calcular(curva_b3, "B3")
    m_b4 = metricas.calcular(curva_b4, "B4")
    m_e0 = metricas.calcular(c.curvas["E0"], "E0")
    print()
    print(f"  La exposicion constante que iguala el CAGR de E0 es "
          f"k = {k_b3:.3f}")
    print(f"  (CAGR B3 {m_b3.cagr * 100:+.2f}% contra "
          f"E0 {m_e0.cagr * 100:+.2f}%).")
    print()
    print(f"  APORTE DE LA COMPUERTA sobre exposicion constante del mismo")
    print(f"  CAGR:  {m_e0.calmar / m_b3.calmar - 1.0:+.1%} de Calmar")
    print(f"  APORTE DE LA COMPUERTA sobre solo volatilidad objetivo (B4):"
          f"  {m_e0.calmar / m_b4.calmar - 1.0:+.1%}")
    print()
    print("  El analista estimo este aporte en +37% en su 2.3, con un B3 a")
    print("  k~0,55 y Calmar 0,594. Corrido con el motor y los mismos costos,")
    print(f"  la exposicion que iguala el CAGR es k={k_b3:.3f} y su Calmar es")
    print(f"  {m_b3.calmar:.3f}. El aporte medido es "
          f"{m_e0.calmar / m_b3.calmar - 1.0:+.1%}, no +37%.")

    # --- Lo que la identidad ya contesta sobre A1 ---------------------------
    _titulo("A1 NO HACE FALTA CORRERLA: LA IDENTIDAD YA LA CONTESTA")
    print("  A1 es 'E0 con k_max y sin objetivo de volatilidad': exposicion")
    print("  1,0 cuando la compuerta esta abierta, 0 cuando esta cerrada.")
    print()
    print("  A exposicion 1,0 el rebalanceo diario es no hacer nada, asi que")
    print("  el log-retorno de A1 es EXACTAMENTE el de BTC en los dias con la")
    print("  compuerta abierta, menos el costo de las transiciones. Y la")
    print("  frontera es EXACTAMENTE igualar el retorno total de B1.")
    print()
    print("  O sea que la pregunta 'pasa A1' es la misma pregunta que 'los")
    print("  dias que la compuerta dejo afuera sumaron negativo'.")
    print()
    velas = c.velas_btc
    g = cp.compuerta_de_regimen(velas["close"]).reindex(
        c.dias).fillna(0).astype(int)
    cierres = velas["close"].reindex(c.dias)
    log = np.log(cierres / cierres.shift(1)).fillna(0.0)
    abierta = g == 1
    dentro, afuera = float(log[abierta].sum()), float(log[~abierta].sum())
    print(f"  Dias con compuerta abierta   {int(abierta.sum()):>6}"
          f"  de {len(c.dias)}  ({abierta.mean():.1%})")
    print(f"  Transiciones de la compuerta {int((g.diff().abs() > 0).sum()):>6}")
    print()
    print(f"  log-retorno de BTC con la compuerta ABIERTA   {dentro:>+9.4f}")
    print(f"  log-retorno de BTC con la compuerta CERRADA   {afuera:>+9.4f}")
    print(f"  log-retorno total de B1                       "
          f"{dentro + afuera:>+9.4f}")
    print()
    if afuera > 0:
        print(f"  **Los dias que la compuerta dejo afuera sumaron "
              f"{afuera:+.4f}.**")
        print("  BTC SUBIO mientras E0 estaba afuera. Quedarse afuera costo")
        print(f"  {afuera:.4f} de log-retorno, antes de cualquier costo de")
        print("  operacion.")
        print()
        print(f"  A1 termina con el {dentro / (dentro + afuera):.1%} del "
              "log-retorno total de B1")
        print("  y la frontera pide el 100%. **A1 falla, y no por poco.**")
    else:
        print("  Los dias afuera sumaron negativo: A1 podria pasar y hay que")
        print("  correrla. Cuesta una prueba de Deflated Sharpe.")
    print()
    print("  ESTO NO CUESTA PRUEBAS DE DSR y hay que decir por que: no se")
    print("  corrio ninguna configuracion nueva. Es la compuerta de E0 --que")
    print("  ya esta entre las seis-- descompuesta segun su propio estado.")
    print()
    print("  PERO HAY QUE SER HONESTO CON LA ASIMETRIA: si esto hubiera dado")
    print("  que A1 pasa, correrla despues seria confirmar algo ya sabido, no")
    print("  explorar. Dio que no pasa, asi que ahorra la prueba en vez de")
    print("  gastarla -- pero la asimetria existe y queda anotada.")
    print()
    print("  Y sale de ahi una condicion general, que vale para CUALQUIER")
    print("  compuerta de encendido y apagado a exposicion plena:")
    print()
    print("      pasa la frontera  <=>  los dias que deja afuera suman")
    print("                             negativo, por mas que el costo")
    print()
    print("  Es necesaria y suficiente, y sale de la identidad. En una ventana")
    print("  donde BTC multiplico por 13, es una condicion muy dura.")

    _titulo("LO QUE CONTESTAN LOS CUATRO PASOS JUNTOS")
    fallan = [n for n, p in puntos.items() if not p.pasa and n != "B1 comprar y mantener"]
    print(f"  Configuraciones evaluadas contra la frontera: {len(puntos) - 1}")
    print(f"  Las que la pasan: {len(puntos) - 1 - len(fallan)}")
    print()
    e = puntos["E0"]
    print(f"  E0, la mejor de todas, capturo {e.c_up:.1%} de la subida y")
    print(f"  necesitaba {e.exigido:.1%}. Le faltan "
          f"{abs(e.margen):.3f} de captura.")
    print()
    print("  Y ninguna capa la acerca: la compuerta aporta lo que aporta, el")
    print("  objetivo de volatilidad mueve por la linea de exposicion")
    print("  constante, y la seleccion por momentum resta.")

    print(f"\n  ({time.time() - t0:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
