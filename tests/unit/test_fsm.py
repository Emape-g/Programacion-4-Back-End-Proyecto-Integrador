"""
tests/unit/test_fsm.py
======================

Tests unitarios del mapa de transiciones de la máquina de estados
del Pedido (spec 3.4, v7: 5 estados, sin EN_CAMINO).
"""

import pytest

from app.modules.pedido.service import TRANSITIONS

pytestmark = pytest.mark.unit


class TestTransiciones:
    """Mapa TRANSITIONS — fuente de verdad de la FSM."""

    def test_cinco_estados_definidos(self):
        assert set(TRANSITIONS.keys()) == {
            "PENDIENTE", "CONFIRMADO", "EN_PREP", "ENTREGADO", "CANCELADO",
        }

    @pytest.mark.parametrize("desde,hacia", [
        ("PENDIENTE", "CONFIRMADO"),
        ("PENDIENTE", "CANCELADO"),
        ("CONFIRMADO", "EN_PREP"),
        ("CONFIRMADO", "CANCELADO"),
        ("EN_PREP", "ENTREGADO"),
        ("EN_PREP", "CANCELADO"),
    ])
    def test_transiciones_validas(self, desde, hacia):
        assert hacia in TRANSITIONS[desde]

    @pytest.mark.parametrize("terminal", ["ENTREGADO", "CANCELADO"])
    def test_estados_terminales_sin_salidas(self, terminal):
        """RN-01: un estado terminal no admite transiciones salientes."""
        assert TRANSITIONS[terminal] == []

    def test_no_existe_en_camino(self):
        """v7 elimina EN_CAMINO de la FSM."""
        assert "EN_CAMINO" not in TRANSITIONS
        assert all("EN_CAMINO" not in destinos for destinos in TRANSITIONS.values())
