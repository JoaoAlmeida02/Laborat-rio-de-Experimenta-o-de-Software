"""Testes unitários para as funções puras de RQ 07 (sensibilidade das classificações DORA)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from analises.rq07 import (
    CATEGORIAS,
    avaliar_c4_filtrada,
    calcular_matriz_transicao,
    classificar_configuracao,
    comparar_pares,
)


@pytest.fixture
def df_sintetico_dora() -> pd.DataFrame:
    """Cria DataFrame com dados sintéticos conhecidos para testar classificações DORA."""
    return pd.DataFrame([
        # Repo 1: Alta frequência, lead time curto, baixo CFR, rápida recuperação -> Elite
        {
            "repo": "org/elite_repo",
            "deploy_frequency_semana": 10.0,
            "lead_time_release_h": 12.0,
            "lead_time_commit_h": 6.0,
            "cfr_ci": 0.05,
            "cfr_entrega": 0.04,
            "tempo_recuperacao_h": 0.5,
        },
        # Repo 2: Frequência moderada, lead time médio, CFR moderado -> Medium / High
        {
            "repo": "org/medium_repo",
            "deploy_frequency_semana": 0.5,
            "lead_time_release_h": 200.0,
            "lead_time_commit_h": 100.0,
            "cfr_ci": 0.25,
            "cfr_entrega": 0.35,
            "tempo_recuperacao_h": 12.0,
        },
        # Repo 3: Baixa frequência, lead time longo, alto CFR -> Low
        {
            "repo": "org/low_repo",
            "deploy_frequency_semana": 0.05,
            "lead_time_release_h": 1200.0,
            "lead_time_commit_h": 800.0,
            "cfr_ci": 0.55,
            "cfr_entrega": 0.60,
            "tempo_recuperacao_h": 200.0,
        },
        # Repo 4: Repo com métricas ausentes (NaN)
        {
            "repo": "org/parcial_repo",
            "deploy_frequency_semana": 2.0,
            "lead_time_release_h": 30.0,
            "lead_time_commit_h": None,
            "cfr_ci": None,
            "cfr_entrega": None,
            "tempo_recuperacao_h": None,
        },
    ])


def test_classificar_configuracao_atribui_categorias_corretas(df_sintetico_dora: pd.DataFrame) -> None:
    """Verifica se classificar_configuracao calcula as categorias individuais e gerais esperadas."""
    res = classificar_configuracao(
        df_sintetico_dora,
        col_frequencia="deploy_frequency_semana",
        col_lead_time="lead_time_release_h",
        col_cfr="cfr_ci",
        col_recuperacao="tempo_recuperacao_h",
    )

    assert len(res) == 4
    assert res.loc[0, "categoria_geral"] == "Elite"
    assert res.loc[0, "n_metricas"] == 4

    assert res.loc[1, "categoria_geral"] in ("Medium", "High")
    assert res.loc[2, "categoria_geral"] == "Low"

    # Repo com valores nulos ainda computa categoria com as métricas disponíveis
    assert res.loc[3, "n_metricas"] == 2
    assert res.loc[3, "categoria_geral"] is not None


def test_comparar_pares_concordancia_perfeita() -> None:
    """Testa comparar_pares quando duas séries são 100% idênticas."""
    s1 = pd.Series(["Elite", "High", "Medium", "Low", "Medium"])
    s2 = pd.Series(["Elite", "High", "Medium", "Low", "Medium"])

    comp = comparar_pares(s1, s2, nome_a="C1", nome_b="C2")
    assert comp["n"] == 5
    assert comp["mudaram"] == 0
    assert comp["pct_mudanca"] == 0.0
    assert comp["pct_concordancia"] == 100.0
    assert comp["kappa_linear"] == 1.0
    assert "quase perfeita" in comp["interpretacao_kappa"].lower()


def test_comparar_pares_com_mudancas_e_valores_nulos() -> None:
    """Testa comparar_pares com divergências controladas e exclusão correta de NaN."""
    s1 = pd.Series(["Elite", "High", "Medium", "Low", None])
    s2 = pd.Series(["High", "High", "Low", "Low", "Elite"])

    comp = comparar_pares(s1, s2, nome_a="A", nome_b="B")
    # Apenas os 4 primeiros são comparáveis em ambos
    assert comp["n"] == 4
    # Mudaram: idx 0 (Elite->High) e idx 2 (Medium->Low) => 2
    assert comp["mudaram"] == 2
    assert comp["pct_mudanca"] == 50.0
    assert comp["pct_concordancia"] == 50.0
    assert comp["kappa_linear"] is not None
    assert 0.0 <= comp["kappa_linear"] <= 1.0


def test_matriz_transicao_estrutura_e_contagens() -> None:
    """Verifica que matriz de transição possui formato 4x4 ordenado por Low < Medium < High < Elite."""
    s_origem = pd.Series(["Elite", "Elite", "High", "Medium", "Low"])
    s_destino = pd.Series(["Elite", "High", "Medium", "Medium", "Low"])

    matriz = calcular_matriz_transicao(s_origem, s_destino, labels=CATEGORIAS)

    assert list(matriz.index) == CATEGORIAS
    assert list(matriz.columns) == CATEGORIAS
    assert matriz.shape == (4, 4)

    # 1 permaneceu Elite, 1 Elite virou High
    assert matriz.loc["Elite", "Elite"] == 1
    assert matriz.loc["Elite", "High"] == 1
    assert matriz.loc["Elite", "Low"] == 0

    # Total de transições soma o n
    assert matriz.values.sum() == 5


def test_avaliar_c4_filtrada_consenso_inexistente(tmp_path: Path) -> None:
    """Verifica comportamento gracioso quando arquivo de consenso não existe."""
    df_fake = pd.DataFrame([{"repo": "a/b"}])
    c1_fake = pd.Series(["High"])
    res, df_detalhe = avaliar_c4_filtrada(df_fake, tmp_path / "inexistente.csv", c1_fake)
    assert res["n_amostra_rotulada"] == 0
    assert df_detalhe.empty
