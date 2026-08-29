"""
Corre el backtest sobre el historico ya descargado - Fase 1.

Los parametros que en config.yaml estan en `null` (porque el MEGAPROMPT
prohibe asumirlos) se pasan por linea de comandos. Asi se puede explorar sin
tocar el archivo de configuracion, y lo que se explora queda escrito en el
comando en vez de perderse.

Ejemplos:

    venv\\Scripts\\python.exe main_backtest.py --par BTCUSDT --tf 1h --adx 20 --cons 0.75
    venv\\Scripts\\python.exe main_backtest.py --todos --adx 20 --cons 0.75
    venv\\Scripts\\python.exe main_backtest.py --todos --adx 0 --cons 0.75 --slippage 0.10
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))

from backtesting import backtest_engine as motor  # noqa: E402
from core import config_loader as cfgmod  # noqa: E402
from core import data_feed  # noqa: E402
from risk import position_sizing  # noqa: E402
from strategy import indicators as ind  # noqa: E402

# Reglas reales de BTCUSDT/ETHUSDT en Binance, verificadas el 28-ago-2026.
REGLAS = position_sizing.ReglasSimbolo(
    paso_cantidad=0.00001, cantidad_minima=0.00001, compra_minima=5.0
)


def preparar_config(base: dict, args) -> dict:
    """Copia la config y completa los pendientes con lo que vino por CLI."""
    cfg = copy.deepcopy(base)
    est = cfg["estrategia"]

    est["regimen"]["adx_minimo"] = args.adx
    est["consolidacion"]["umbral_desviacion_pct"] = args.cons
    est["portfolio_guard"]["distancia_maxima_bajo_sma_pct"] = args.macro
    if args.slippage is not None:
        cfg["costos"]["slippage_pct_por_lado"] = args.slippage
    if args.riesgo is not None:
        cfg["riesgo"]["por_operacion_pct"] = args.riesgo
    if args.sin_limite_diario:
        cfg["riesgo"]["perdida_diaria_max_pct"] = 100.0
    return cfg


def correr_uno(par: str, tf: str, cfg: dict, guardar_diario: bool) -> motor.Resultado:
    df = data_feed.cargar(par, tf, carpeta=RAIZ / cfg["datos"]["carpeta_historico"])
    con_indicadores = ind.agregar_indicadores(df, cfg)
    resultado = motor.correr(con_indicadores, cfg, par=par, temporalidad=tf,
                             reglas_simbolo=REGLAS)

    if guardar_diario and resultado.operaciones:
        salida = RAIZ / "backtesting" / "reports" / f"operaciones_{par}_{tf}.csv"
        motor.operaciones_a_dataframe(resultado.operaciones).to_csv(salida, index=False)
        print(f"  Diario de operaciones -> {salida.relative_to(RAIZ)}")
    return resultado


def main() -> int:
    p = argparse.ArgumentParser(description="Backtest de KINETIC.")
    p.add_argument("--par", help="un solo par, ej. BTCUSDT")
    p.add_argument("--tf", help="una sola temporalidad, ej. 1h")
    p.add_argument("--todos", action="store_true", help="todo el universo del config")
    p.add_argument("--adx", type=float, default=20.0, help="ADX minimo (0 = sin filtro)")
    p.add_argument("--cons", type=float, default=0.75,
                   help="umbral de consolidacion, en %% de desviacion")
    p.add_argument("--macro", type=float, default=None,
                   help="%% maximo por debajo de la SMA200 (omitir = guardia apagada)")
    p.add_argument("--slippage", type=float, default=None, help="%% por lado")
    p.add_argument("--riesgo", type=float, default=None, help="%% por operacion")
    p.add_argument("--sin-limite-diario", action="store_true",
                   help="apaga el tope diario, para aislar el efecto de la estrategia")
    p.add_argument("--diario", action="store_true", help="guarda el CSV de operaciones")
    args = p.parse_args()

    base = cfgmod.cargar()
    cfg = preparar_config(base, args)

    if args.todos or not args.par:
        pares = list(base["backtest"]["universo"])
        temporalidades = [args.tf] if args.tf else list(base["backtest"]["temporalidades"])
    else:
        pares = [args.par]
        temporalidades = [args.tf] if args.tf else list(base["backtest"]["temporalidades"])

    print("=" * 72)
    print(" KINETIC - BACKTEST (neto de comisiones y slippage)")
    print("=" * 72)
    print(f"  Capital:      {cfg['capital']['monto']:,.0f} USDT")
    print(f"  Riesgo/op:    {cfg['riesgo']['por_operacion_pct']}%")
    print(f"  Tope diario:  {cfg['riesgo']['perdida_diaria_max_pct']}%")
    print(f"  Comision:     {cfg['costos']['comision_por_lado_pct']}% por lado")
    print(f"  Slippage:     {cfg['costos']['slippage_pct_por_lado']}% por lado")
    print(f"  ADX minimo:   {args.adx}    Consolidacion: <= {args.cons}%")
    print(f"  Guardia SMA:  {'apagada' if args.macro is None else f'-{args.macro}%'}")

    filas = []
    for par in pares:
        for tf in temporalidades:
            print("\n" + "-" * 72)
            print(f"{par} {tf}")
            print("-" * 72)
            try:
                r = correr_uno(par, tf, cfg, args.diario)
            except FileNotFoundError as e:
                print(f"  [X] {e}")
                continue
            print(r.metricas.informe())
            m = r.metricas
            if m.operaciones:
                filas.append((par, tf, m.operaciones, m.profit_factor,
                              m.tasa_acierto_pct, m.retorno_total_pct,
                              m.max_drawdown_pct, m.capital_final))

    if filas:
        print("\n" + "=" * 72)
        print(" RESUMEN")
        print("=" * 72)
        print(f"  {'Par':<9} {'TF':<4} {'Ops':>5} {'PF':>7} {'Acierto':>8} "
              f"{'Retorno':>9} {'MaxDD':>8} {'Final':>10}")
        for par, tf, ops, pf, acierto, ret, dd, final in filas:
            pf_txt = "inf" if pf == float("inf") else f"{pf:.3f}"
            print(f"  {par:<9} {tf:<4} {ops:>5} {pf_txt:>7} {acierto:>7.1f}% "
                  f"{ret:>8.2f}% {dd:>7.2f}% {final:>10,.2f}")
        print()
        print("  Recordatorio: un Profit Factor por debajo de 1,00 significa que la")
        print("  estrategia PIERDE dinero. No hay ajuste de riesgo que arregle eso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
