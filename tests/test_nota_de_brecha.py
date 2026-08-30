"""
La nota que explica la brecha contra el "mejor en retrospectiva".

Existe esta prueba porque la nota YA ENGANO UNA VEZ. El 29-ago-2026 comparaba
contra el valor DOMINANTE de las ventanas en vez de contra todas, y afirmo
"mismo valor que eligio el walk-forward: 5.0x" cuando 5.0x habia ganado 3 de
6 ventanas. Como esa frase decia que la brecha NO era sobreajuste, se salio a
buscar la causa a otro lado -- cierres forzados de ventana -- y se gasto una
corrida entera para descubrir que eran cero.

Una nota que interpreta mal un numero es peor que no tenerla: el numero
crudo obliga a pensar, la nota equivocada te ahorra el trabajo de pensar mal.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from main_walkforward import nota_de_brecha  # noqa: E402


def texto(*args) -> str:
    return "\n".join(nota_de_brecha(*args))


# ===========================================================================
# El caso que motivo la prueba
# ===========================================================================

def test_no_dice_mismo_valor_cuando_solo_gano_la_mitad_de_las_ventanas():
    """
    BTCUSDT 1h, corrida corregida del 29-ago-2026: elegidos [4,6,5,4,5,5] y
    el mejor en retrospectiva fue 5.0x. Es el caso exacto que la version
    anterior interpretaba al reves.
    """
    t = texto([4.0, 6.0, 5.0, 4.0, 5.0, 5.0], 5.0, 126.01)

    assert "TODAS" not in t, "5.0x gano 3 de 6 ventanas, no todas"
    assert "solo 3 de 6" in t
    assert "[4.0, 6.0]" in t, "tiene que decir que eligio en las otras"
    assert "SI es el precio de no conocer el futuro" in t


def test_dice_TODAS_solo_cuando_de_verdad_gano_en_todas():
    """BTCUSDT 15m: 6.0x en las seis ventanas, y su brecha dio 0.00."""
    t = texto([6.0] * 6, 6.0, 0.0)

    assert "TODAS" in t
    assert "NO es sobreajuste" in t
    assert "buscar la causa en otro lado" in t


def test_una_sola_ventana_distinta_ya_alcanza_para_no_decir_TODAS():
    """El borde del criterio: 5 de 6 no es 6 de 6."""
    t = texto([6.0, 6.0, 6.0, 6.0, 5.0, 6.0], 6.0, 17.66)

    assert "TODAS" not in t
    assert "solo 5 de 6" in t
    assert "[5.0]" in t


def test_el_caso_mas_disperso_se_reporta_como_tal():
    """ETHUSDT 1h: elegidos [5,5,2,6,6,6] y el mejor fue 2.0x, que gano una."""
    t = texto([5.0, 5.0, 2.0, 6.0, 6.0, 6.0], 2.0, 78.87)

    assert "solo 1 de 6" in t
    assert "[5.0, 6.0]" in t


# ===========================================================================
# El signo
# ===========================================================================

def test_brecha_positiva_dice_MEJOR():
    t = texto([5.0] * 3, 5.0, 126.01)
    assert "126.01 USDT MEJOR" in t


def test_brecha_negativa_dice_PEOR_y_no_inventa_un_signo():
    """
    Con resultados negativos el barrido puede salir PEOR que el walk-forward.
    La version original imprimia el numero con signo dentro de una frase que
    decia "mejor", y quedaba ilegible.
    """
    t = texto([6.0] * 6, 6.0, -34.46)

    assert "34.46 USDT PEOR" in t
    assert "no hubo premio por mirar el futuro" in t
    assert "-34.46" not in t, "el signo ya esta en la palabra PEOR"
