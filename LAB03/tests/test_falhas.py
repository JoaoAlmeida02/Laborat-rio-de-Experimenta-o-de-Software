"""Testes unitários para cálculo de Change Failure Rate (metricas/falhas.py)."""

from __future__ import annotations

import pytest

from metricas.falhas import TABELA_CLASSIFICACAO, cfr_ci, classificar_conclusion


def test_tabela_classificacao_padrao():
    """Verifica que a constante TABELA_CLASSIFICACAO contém os mapeamentos esperados."""
    assert TABELA_CLASSIFICACAO["success"] == "sucesso"
    assert TABELA_CLASSIFICACAO["failure"] == "falha"
    assert TABELA_CLASSIFICACAO["timed_out"] == "falha"
    assert TABELA_CLASSIFICACAO["startup_failure"] == "falha"
    assert TABELA_CLASSIFICACAO["cancelled"] == "ignorar"
    assert TABELA_CLASSIFICACAO["skipped"] == "ignorar"
    assert TABELA_CLASSIFICACAO["neutral"] == "ignorar"
    assert TABELA_CLASSIFICACAO["action_required"] == "ignorar"
    assert TABELA_CLASSIFICACAO["stale"] == "ignorar"
    assert TABELA_CLASSIFICACAO[None] == "ignorar"
    assert TABELA_CLASSIFICACAO["null"] == "ignorar"


def test_classificar_conclusion():
    """Testa a classificação de conclusions individuais, incluindo case-insensitivity."""
    assert classificar_conclusion("success") == "sucesso"
    assert classificar_conclusion("SUCCESS") == "sucesso"
    assert classificar_conclusion("failure") == "falha"
    assert classificar_conclusion("FAILURE") == "falha"
    assert classificar_conclusion("timed_out") == "falha"
    assert classificar_conclusion("startup_failure") == "falha"
    assert classificar_conclusion("cancelled") == "ignorar"
    assert classificar_conclusion("skipped") == "ignorar"
    assert classificar_conclusion("neutral") == "ignorar"
    assert classificar_conclusion("action_required") == "ignorar"
    assert classificar_conclusion("stale") == "ignorar"
    assert classificar_conclusion(None) == "ignorar"
    assert classificar_conclusion("null") == "ignorar"
    assert classificar_conclusion("qualquer_outro") == "ignorar"


def test_cfr_ci_calculo_correto():
    """Testa o cálculo do CFR com proporção exata de falhas e sucessos."""
    runs = [
        {"conclusion": "success"},
        {"conclusion": "failure"},
        {"conclusion": "success"},
        {"conclusion": "success"},
        {"conclusion": "timed_out"},
        {"conclusion": "success"},
        {"conclusion": "success"},
        {"conclusion": "success"},
    ]
    # 2 falhas, 6 sucessos = 2 / 8 = 0.25
    resultado = cfr_ci(runs)
    assert resultado == pytest.approx(0.25)


def test_cfr_ci_ignora_runs_marcados_como_ignorar():
    """Verifica que status como cancelled e skipped não entram no denominador do CFR."""
    runs = [
        {"conclusion": "failure"},
        {"conclusion": "success"},
        {"conclusion": "cancelled"},
        {"conclusion": "skipped"},
        {"conclusion": "neutral"},
        {"conclusion": "action_required"},
        {"conclusion": None},
    ]
    # 1 falha, 1 sucesso, 5 ignorados = 1 / 2 = 0.5
    resultado = cfr_ci(runs)
    assert resultado == pytest.approx(0.5)


def test_cfr_ci_divisao_por_zero_retorna_none():
    """Verifica tratamento de divisão por zero retornando None documentado."""
    assert cfr_ci([]) is None
    assert cfr_ci([{"conclusion": "cancelled"}, {"conclusion": "skipped"}]) is None
    assert cfr_ci([{"conclusion": None}]) is None


def test_cfr_ci_apenas_sucessos_ou_apenas_falhas():
    """Testa limites de 0% (todos sucesso) e 100% (todas falhas)."""
    sucessos = [{"conclusion": "success"}, {"conclusion": "success"}]
    assert cfr_ci(sucessos) == pytest.approx(0.0)

    falhas = [{"conclusion": "failure"}, {"conclusion": "timed_out"}]
    assert cfr_ci(falhas) == pytest.approx(1.0)
