r"""
Verifica el supuesto del que cuelga toda la correccion del sesgo de supervivencia.

QUE SE VERIFICA, Y POR QUE ANTES QUE NADA
------------------------------------------
La especificacion de la Fase 2 (seccion 2.4) afirma que el archivo historico
`data.binance.vision` contiene tambien los pares que Binance ya deslisto, a
diferencia del endpoint `/api/v3/klines` que solo sirve los que hoy existen.

Sobre esa afirmacion se apoya la etapa 0 entera: la reconstruccion del
universo mes a mes sin sesgo de supervivencia. Si el archivo no tiene lo que
se supone, se cae la mitad del trabajo planificado.

**Es verificable en minutos y cuesta una descarga.** El MEGAPROMPT v2.0
seccion 10 lo dice con todas las letras: antes de construir sobre un
supuesto, verificarlo si es barato.

QUE HACE, EN TRES PASOS
-----------------------
1. Enumera los simbolos que existen en el ARCHIVO, leyendo el listado del
   bucket. No usa `exchangeInfo`: usarlo seria volver a meter el sesgo por la
   ventana, que es exactamente el error que se quiere corregir.
2. Enumera los simbolos de `exchangeInfo` SEPARANDO POR ESTADO. Esto es lo
   que la primera version de este script hizo mal: comparo contra *todos* los
   simbolos y dio 25 deslistados, cuando son cientos. Binance no borra un par
   deslistado de `exchangeInfo` -- lo deja con estado `BREAK`, a veces por
   años. Filtrar por `status == "TRADING"` es exactamente como entro el sesgo
   de supervivencia en la Fase 1 (ver `tools/elegir_universo.py`).
3. Baja varios deslistados de verdad, verifica su SHA256 contra el
   `.CHECKSUM` que los acompaña, y muestra las primeras filas.

Si el paso 3 funciona, el supuesto es cierto y la etapa 0 puede construirse.

Se corre asi:

    venv\Scripts\python.exe tools\verificar_archivo_binance.py
"""

from __future__ import annotations

import hashlib
import io
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from core import data_feed  # noqa: E402

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BASE = "https://data.binance.vision"
ESPACIO = "{http://s3.amazonaws.com/doc/2006-03-01/}"

# Cuantos deslistados se bajan de verdad. Con seis alcanza para
# confirmar el supuesto sin castigar el bucket ni la paciencia.
MUESTRA = 6


def _leer(url: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def simbolos_del_archivo(prefijo: str = "data/spot/monthly/klines/") -> list[str]:
    """
    Los simbolos que existen en el archivo historico.

    El bucket se lista de a 1000 con paginacion por `marker`. Cada carpeta de
    primer nivel bajo el prefijo es un simbolo.
    """
    simbolos: list[str] = []
    marcador = ""
    while True:
        url = f"{BUCKET}?delimiter=/&prefix={prefijo}"
        if marcador:
            url += f"&marker={urllib.parse.quote(marcador, safe='')}"
        raiz = ET.fromstring(_leer(url))
        lote = [
            p.find(f"{ESPACIO}Prefix").text[len(prefijo):].strip("/")
            for p in raiz.findall(f"{ESPACIO}CommonPrefixes")
        ]
        if not lote:
            break
        simbolos.extend(lote)
        truncado = raiz.find(f"{ESPACIO}IsTruncated")
        if truncado is None or truncado.text != "true":
            break
        marcador = prefijo + lote[-1] + "/"
        print(f"    {len(simbolos):,} simbolos leidos...", flush=True)
    return simbolos


def meses_disponibles(simbolo: str, tf: str = "1d") -> list[str]:
    """Los archivos mensuales que tiene un simbolo, del mas viejo al mas nuevo."""
    prefijo = f"data/spot/monthly/klines/{simbolo}/{tf}/"
    url = f"{BUCKET}?prefix={prefijo}"
    raiz = ET.fromstring(_leer(url))
    nombres = [
        c.find(f"{ESPACIO}Key").text.rsplit("/", 1)[-1]
        for c in raiz.findall(f"{ESPACIO}Contents")
    ]
    return sorted(n for n in nombres if n.endswith(".zip"))


def bajar_y_verificar(simbolo: str, archivo: str, tf: str = "1d"):
    """
    Baja un mensual y comprueba su SHA256 contra el .CHECKSUM que lo acompaña.

    Devuelve `(velas, sha_ok)`. Verificar el checksum no es ceremonia: un zip
    truncado se lee igual y mete datos falsos sin avisar.
    """
    base = f"{BASE}/data/spot/monthly/klines/{simbolo}/{tf}/{archivo}"
    crudo = _leer(base)
    esperado = _leer(base + ".CHECKSUM").decode().split()[0]
    sha_ok = hashlib.sha256(crudo).hexdigest() == esperado

    with zipfile.ZipFile(io.BytesIO(crudo)) as z:
        nombre = z.namelist()[0]
        with z.open(nombre) as f:
            lineas = f.read().decode().strip().splitlines()
    return lineas, sha_ok


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    print("=" * 76)
    print(" KINETIC - verificacion del archivo historico de Binance")
    print("=" * 76)
    print("  De este supuesto cuelga la correccion del sesgo de supervivencia,")
    print("  y con ella la mitad de la etapa 0. Se verifica antes de construir.")
    print()

    print("  [1/3] Enumerando simbolos del ARCHIVO...", flush=True)
    try:
        archivo = simbolos_del_archivo()
    except Exception as e:  # noqa: BLE001
        print(f"  [X] No se pudo leer el listado del bucket: {e}")
        print("      Sin esto no se puede reconstruir el universo. Es bloqueante.")
        return 1
    print(f"        {len(archivo):,} simbolos en el archivo.")

    print("  [2/3] Enumerando simbolos de exchangeInfo por ESTADO...", flush=True)
    cliente = data_feed._cliente_publico()
    simbolos = cliente.get_exchange_info()["symbols"]
    operando = {s["symbol"] for s in simbolos if s["status"] == "TRADING"}
    detenidos = {s["symbol"] for s in simbolos if s["status"] != "TRADING"}
    print(f"        {len(operando):,} TRADING, {len(detenidos):,} detenidos.")

    # Un par deslistado puede estar en cualquiera de los dos lugares: seguir
    # en exchangeInfo con estado BREAK, o haber desaparecido del todo. Los dos
    # cuentan, y los dos tienen historico en el archivo.
    muertos = (detenidos | (set(archivo) - operando - detenidos))
    usdt_vivos = sorted(s for s in operando if s.endswith("USDT"))
    usdt_muertos = sorted(s for s in muertos if s.endswith("USDT"))

    print()
    print("  EL TAMAÑO DEL SESGO, POR FIN MEDIBLE")
    print(f"    Pares USDT operando hoy:        {len(usdt_vivos):>6,}")
    print(f"    Pares USDT deslistados:         {len(usdt_muertos):>6,}")
    total = len(usdt_vivos) + len(usdt_muertos)
    if total:
        print(f"    La Fase 1 vio solo el           {len(usdt_vivos) / total * 100:>5.0f}% "
              f"del mercado que existio")

    if not usdt_muertos:
        print()
        print("  [X] No se detectaron pares deslistados contra USDT.")
        print("      El supuesto de la seccion 2.4 de la especificacion seria")
        print("      falso y habria que rediseñar la correccion. BLOQUEANTE.")
        return 1

    print(f"    Ejemplos: {', '.join(usdt_muertos[:8])}")

    print()
    print("  [3/3] Bajando deslistados de verdad para confirmar que sirven...")
    print(f"        {'Simbolo':<14} {'Meses':>6}  {'Periodo':<20} Checksum")
    revisados = 0
    fallos = 0
    for simbolo in usdt_muertos:
        if revisados >= MUESTRA:
            break
        try:
            meses = meses_disponibles(simbolo)
        except Exception:  # noqa: BLE001
            continue
        if not meses:
            continue
        lineas, sha_ok = bajar_y_verificar(simbolo, meses[-1])
        revisados += 1
        if not (sha_ok and lineas):
            fallos += 1
        periodo = f"{meses[0][-11:-4]} a {meses[-1][-11:-4]}"
        print(f"        {simbolo:<14} {len(meses):>6}  {periodo:<20} "
              f"{'OK' if sha_ok else 'NO COINCIDE'}  ({len(lineas)} velas)")

    print()
    print("=" * 76)
    if revisados and not fallos:
        print(" SUPUESTO CONFIRMADO")
        print("=" * 76)
        print(f"  {revisados} de {revisados} deslistados bajaron con checksum valido.")
        print("  El archivo sirve velas de pares que ya no se operan. La etapa 0")
        print("  puede construirse encima.")
        print()
        print("  MATIZ SOBRE COMO LO DESCRIBE LA ESPECIFICACION: no es que el")
        print("  archivo tenga simbolos que exchangeInfo no tiene -- casi todos")
        print("  los deslistados SIGUEN en exchangeInfo, con estado BREAK. El")
        print("  sesgo de la Fase 1 no entro por usar el endpoint equivocado,")
        print("  entro por filtrar status == TRADING. El arreglo funciona igual,")
        print("  pero conviene saber donde estaba realmente el agujero.")
        return 0
    print(" SUPUESTO NO CONFIRMADO")
    print("=" * 76)
    print(f"  {fallos} de {revisados} fallaron. Es bloqueante para la etapa 0.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
