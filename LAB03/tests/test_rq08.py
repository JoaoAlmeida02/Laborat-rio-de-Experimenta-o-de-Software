"""Testes unitários para as funções puras de RQ 08 (Rework Rate e correlação com CFR b)."""

from __future__ import annotations

import pandas as pd
import pytest

from analises.rq08 import (
    calcular_correlacao_rework_cfr,
    calcular_rework_rate_puro,
    tabela_por_categoria_dora,
)


def test_calcular_rework_rate_puro_casos_borda() -> None:
    """Testa o cálculo matemático de Rework Rate e prevenção de divisão por zero."""
    assert calcular_rework_rate_puro(corretivas=5, total_avaliadas=10) == 0.5
    assert calcular_rework_rate_puro(corretivas=0, total_avaliadas=15) == 0.0
    assert calcular_rework_rate_puro(corretivas=12, total_avaliadas=12) == 1.0
    assert calcular_rework_rate_puro(corretivas=0, total_avaliadas=0) is None
    assert calcular_rework_rate_puro(corretivas=3, total_avaliadas=-1) is None


def test_calcular_correlacao_rework_cfr_sintetico() -> None:
    """Verifica o cálculo de correlação de Spearman e intervalo de confiança bootstrap."""
    df_sintetico = pd.DataFrame({
        "rework_rate": [0.10, 0.25, 0.40, 0.60, 0.75, 0.90],
        "cfr_entrega": [0.05, 0.20, 0.35, 0.55, 0.70, 0.85],
    })

    res = calcular_correlacao_rework_cfr(
        df_sintetico,
        col_rework="rework_rate",
        col_cfr="cfr_entrega",
        n_resamples=500,
        random_state=42,
    )

    assert res["n"] == 6
    assert res["rho"] is not None
    assert res["rho"] > 0.95  # Relação monotônica estritamente crescente
    assert res["p_valor"] < 0.05
    assert res["significativo_5pct"] is True
    assert res["ci_inferior_95"] is not None
    assert res["ci_superior_95"] is not None
    assert res["ci_inferior_95"] <= res["ci_superior_95"]


def test_calcular_correlacao_rework_cfr_amostra_insuficiente() -> None:
    """Verifica comportamento gracioso com menos de 3 pares válidos."""
    df_pequeno = pd.DataFrame({
        "rework_rate": [0.1, 0.2],
        "cfr_entrega": [0.3, 0.4],
    })
    res = calcular_correlacao_rework_cfr(df_pequeno)
    assert res["n"] == 2
    assert res["rho"] is None
    assert res["significativo_5pct"] is False


def test_tabela_por_categoria_dora_estrutura() -> None:
    """Testa a geração da tabela descritiva estratificada por categoria DORA."""
    df_teste = pd.DataFrame([
        {"categoria_dora_geral": "Elite", "rework_rate": 0.20, "cfr_entrega": 0.10},
        {"categoria_dora_geral": "Elite", "rework_rate": 0.30, "cfr_entrega": 0.15},
        {"categoria_dora_geral": "High", "rework_rate": 0.40, "cfr_entrega": 0.25},
        {"categoria_dora_geral": "Medium", "rework_rate": 0.50, "cfr_entrega": 0.35},
        {"categoria_dora_geral": "Low", "rework_rate": 0.80, "cfr_entrega": 0.70},
    ])

    tab = tabela_por_categoria_dora(
        df_teste,
        col_categoria="categoria_dora_geral",
        col_rework="rework_rate",
        col_cfr="cfr_entrega",
    )

    # 4 categorias + 1 linha consolidada (Total Geral) = 5 linhas
    assert len(tab) == 5
    assert list(tab["categoria_dora"]) == ["Low", "Medium", "High", "Elite", "Total Geral"]

    linha_elite = tab[tab["categoria_dora"] == "Elite"].iloc[0]
    assert linha_elite["total_repos"] == 2
    assert linha_elite["rework_mediana"] == 0.25
    assert linha_elite["cfr_b_mediana"] == 0.125

    linha_total = tab[tab["categoria_dora"] == "Total Geral"].iloc[0]
    assert linha_total["total_repos"] == 5
