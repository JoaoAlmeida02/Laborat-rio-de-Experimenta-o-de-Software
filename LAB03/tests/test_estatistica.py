# Testes unitarios para metricas/estatistica.py
import numpy as np
import pytest

from metricas.estatistica import (
    bootstrap_spearman_ci,
    cliffs_delta,
    corrigir_pvalores_holm,
    epsilon_squared_kruskal,
    interpretar_cliffs_delta,
    interpretar_epsilon_squared,
)


def test_cliffs_delta_casos_extremos():
    # Separacao perfeita onde x > y
    x = [10, 11, 12]
    y = [1, 2, 3]
    d = cliffs_delta(x, y)
    assert d == 1.0
    assert interpretar_cliffs_delta(d) == "grande"

    # Separacao perfeita onde x < y
    d_inv = cliffs_delta(y, x)
    assert d_inv == -1.0
    assert interpretar_cliffs_delta(d_inv) == "grande"

    # Amostras identicas
    d_zero = cliffs_delta([5, 5, 5], [5, 5, 5])
    assert d_zero == 0.0
    assert interpretar_cliffs_delta(d_zero) == "desprezível"


def test_cliffs_delta_valores_intermediarios():
    x = [1, 2, 3, 4]
    y = [2, 3, 4, 5]
    d = cliffs_delta(x, y)
    assert -1.0 <= d <= 1.0
    # Interpretacoes de magnitude conforme Romano
    assert interpretar_cliffs_delta(0.10) == "desprezível"
    assert interpretar_cliffs_delta(0.20) == "pequeno"
    assert interpretar_cliffs_delta(0.40) == "médio"
    assert interpretar_cliffs_delta(0.60) == "grande"
    assert interpretar_cliffs_delta(-0.40) == "médio"
    assert interpretar_cliffs_delta(None) is None


def test_cliffs_delta_amostra_vazia_ou_invalida():
    assert cliffs_delta([], [1, 2]) is None
    assert cliffs_delta([1, 2], []) is None
    assert cliffs_delta([None, np.nan], [1, 2]) is None


def test_epsilon_squared_kruskal():
    # H = 7.2, n = 9 -> eps2 = 7.2 / 8 = 0.9
    eps2 = epsilon_squared_kruskal(7.2, 9)
    assert pytest.approx(eps2, 0.001) == 0.9
    assert interpretar_epsilon_squared(eps2) == "grande"

    # Interpretacoes
    assert interpretar_epsilon_squared(0.005) == "desprezível"
    assert interpretar_epsilon_squared(0.03) == "pequeno"
    assert interpretar_epsilon_squared(0.10) == "médio"
    assert interpretar_epsilon_squared(0.25) == "grande"
    assert interpretar_epsilon_squared(None) is None

    # Casos de borda
    assert epsilon_squared_kruskal(None, 10) is None
    assert epsilon_squared_kruskal(5.0, 1) is None
    assert epsilon_squared_kruskal(5.0, 0) is None


def test_bootstrap_spearman_ci():
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    y = [2, 1, 4, 3, 6, 5, 8, 7, 10, 9]
    res = bootstrap_spearman_ci(x, y, n_resamples=200, conf_level=0.95, random_state=42)
    assert res["n"] == 10
    assert res["rho"] > 0.8
    assert res["p_valor"] < 0.01
    assert res["ci_inferior"] <= res["rho"] <= res["ci_superior"]


def test_bootstrap_spearman_ci_amostra_pequena_ou_degenerada():
    # Amostra com menos de 3 pares validos
    res = bootstrap_spearman_ci([1, 2], [1, 2])
    assert res["rho"] is None
    assert res["ci_inferior"] is None

    # Tratamento de NaNs
    x = [1, 2, 3, np.nan, 5]
    y = [1, 2, np.nan, 4, 5]
    res_nan = bootstrap_spearman_ci(x, y, n_resamples=50, random_state=42)
    assert res_nan["n"] == 3

    # Caso onde todas as reamostragens dao constantes (sem variancia)
    res_const = bootstrap_spearman_ci([1, 1, 1, 1], [2, 2, 2, 2], n_resamples=10, random_state=42)
    assert res_const["ci_inferior"] is None


def test_corrigir_pvalores_holm():
    p_orig = [0.001, 0.02, 0.03, 0.04, 0.50]
    corr = corrigir_pvalores_holm(p_orig, alfa=0.05)
    assert len(corr["p_corrigidos"]) == len(p_orig)
    assert len(corr["rejeicoes"]) == len(p_orig)
    assert corr["rejeicoes"][0] is True
    assert corr["rejeicoes"][-1] is False

    # Lista vazia
    vazio = corrigir_pvalores_holm([])
    assert vazio["rejeicoes"] == []
    assert vazio["p_corrigidos"] == []

    # Tratamento de None ou NaN
    com_nan = corrigir_pvalores_holm([0.01, None, np.nan])
    assert len(com_nan["p_corrigidos"]) == 3
