# KINETIC

Bot de trading algorítmico para **Binance Spot** (criptomonedas, sin
apalancamiento). Detecta rupturas de rango con confirmación de volumen,
filtra por régimen de mercado, y protege el capital con una capa de riesgo
independiente de la estrategia.

Proyecto **separado de TITAN** (MetaTrader 5 / forex). Cada uno tiene su
propio repositorio, su propio entorno y su propio protocolo.

> ⚠️ **Estado: Fases 0 y 1 CERRADAS (29-ago-2026). Ninguna fase abierta.**
> Hoy este repositorio **no puede operar**. No existe código capaz de enviar
> una orden a Binance, y hay pruebas automáticas que fallan si alguien lo
> agrega.

---

## Cómo se lee este repositorio

| Documento | Qué contiene |
|---|---|
| [`MEGAPROMPT_KINETIC.md`](MEGAPROMPT_KINETIC.md) | Las reglas del proyecto: rol, arquitectura, fases. Manda sobre todo lo demás |
| [`docs/BITACORA_KINETIC.md`](docs/BITACORA_KINETIC.md) | **Léelo primero.** Cronológico: qué se hizo, qué se decidió y por qué |
| [`config/config.yaml`](config/config.yaml) | Todos los parámetros. Si un número no está acá, el código no debería conocerlo |

---

## Puesta en marcha

El entorno ya está creado. Si hay que rehacerlo desde cero:

```bash
py -3.12 -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para reproducir el entorno **exacto** (con las dependencias de las
dependencias), usar `requirements-lock.txt` en vez de `requirements.txt`.

### Configurar las llaves de Binance Testnet

1. Entrar a https://testnet.binance.vision/ con una cuenta de GitHub.
   Es gratis y el dinero es de mentira.
2. Generar una API Key y su Secret.
3. Copiar `.env.example` como `.env` y pegar ahí las dos.

```bash
copy .env.example .env
```

El archivo `.env` está en `.gitignore` y nunca se sube a git. **Nadie debe
pedirte esas llaves por chat, Claude incluido.**

### Verificar que todo funciona

```bash
venv\Scripts\python.exe tools\verificar_conexion.py
```

Comprueba conexión, sincronización de reloj, validez de las llaves, lectura
de la cuenta y descarga de velas. **No opera ni mueve un centavo.**

### Correr las pruebas

```bash
venv\Scripts\python.exe -m pytest tests/ -q
```

---

## Cómo está armado

```
Binance (datos)
      ↓
DATA FEED  →  SIGNAL ENGINE  →  RISK MANAGER  →  EXECUTION  →  Binance
                (qué señal)      (si va y         (la manda)
                                  cuánto)
```

La regla estructural es que **la estrategia y el riesgo nunca viven en el
mismo archivo**. La estrategia dice qué señal hay; el módulo de riesgo es el
portero y decide si esa señal se ejecuta y con qué tamaño. Nada llega a
Binance sin pasar por el portero.

| Carpeta | Rol | Fase |
|---|---|---|
| `core/` | Conexión a Binance y lectura de configuración | 0 ✅ |
| `strategy/` | Indicadores, filtro de régimen, motor de señal | 1 ✅ |
| `risk/` | Tamaño de posición, stops, límites, guardia de cartera | 1 ✅ |
| `backtesting/` | Motor de backtest y walk-forward | 1 ✅ |
| `execution/` | Envío y seguimiento de órdenes reales | 2 |
| `journal/` | Diario de operaciones | 2 |
| `tools/` | Utilidades de diagnóstico (solo lectura) | 0 ✅ |

---

## Parámetros vigentes

Confirmados por Felipe el 28 de agosto de 2026:

- **Capital del bot:** 500 USDT
- **Riesgo por operación:** 1 % → 5 USDT de pérdida máxima si el stop pega
- **Pérdida diaria máxima:** 3 % → 15 USDT; al llegar, el bot no abre nada
  nuevo hasta el día siguiente
- **Stop inicial:** entrada − 2 × ATR(14), con trailing tipo Chandelier
- **Modo:** `TESTNET`

Hay 8 parámetros más en `null` dentro de `config.yaml` (par, temporalidad,
umbrales). **Siguen en blanco porque la Fase 1 cerró sin promover ninguno:**
ninguna configuración pasó su propio criterio. Eso es el resultado, no un
pendiente.

---

## Seguridad

Tres cerrojos, redundantes a propósito:

1. **`core/exchange_client.py` no tiene ningún método capaz de operar.**
   Tiene una lista blanca de endpoints de solo lectura; cualquier otro
   lanza `PermissionError`.
2. **Conectarse a Mainnet exige `permitir_mainnet=True` explícito.** Ningún
   script del repositorio lo hace por su cuenta.
3. **`tests/test_solo_lectura.py` lee el código fuente** y falla si aparece
   una llamada capaz de mover dinero, o si `config.yaml` queda apuntando a
   `MAINNET`.

Cuando llegue la Fase 3 (dinero real, 5 USD), la API Key de Mainnet debe
crearse con **lectura + spot trading, y el permiso de retiro APAGADO**.

**El paso a dinero real lo activa Felipe, a mano, y nadie más.**

---

## Las cuatro fases

- **Fase 0 — Entorno.** venv, dependencias, llaves de Testnet, verificación
  de conexión de solo lectura. ✅ **CERRADA el 28-ago-2026**
- **Fase 1 — Backtest local.** Señal y riesgo integrados desde el inicio,
  walk-forward, neto de comisiones (0,1 % por lado) y slippage.
  ✅ **CERRADA el 29-ago-2026 con hallazgo negativo:** la estrategia no paga
  sus costos en cripto. Ver [`docs/FASE_1_informe.md`](docs/FASE_1_informe.md)
- **Fase 2 — Binance Testnet.** Se prueba la mecánica de ejecución, no el
  rendimiento (el Testnet tiene liquidez y datos limitados).
- **Fase 3 — Micro-testing en Mainnet (5 USD).** Solo tras validar 1 y 2, y
  con confirmación explícita y por escrito de Felipe.

Ninguna fase avanza sin que Felipe la apruebe explícitamente.
