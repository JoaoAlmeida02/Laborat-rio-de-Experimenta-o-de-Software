"""Testes unitários para classificação das métricas DORA (metricas/classificacao.py)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from metricas.classificacao import (
    LIMIARES_CFR,
    LIMIARES_RECUPERACAO_SEGUNDOS,
    MAPEAMENTO_CATEGORIAS,
    MAPEAMENTO_INVERSO,
    categoria_geral,
    classificar_cfr,
    classificar_dora,
    classificar_recuperacao,
)


def test_exemplo_obrigatorio_enunciado_4_3_3_1():
    """Verifica o exemplo obrigatório: categorias (4, 3, 3, 1) -> mediana 3 -> High."""
    assert categoria_geral([4, 3, 3, 1]) == "High"
    assert categoria_geral(["Elite", "High", "High", "Low"]) == "High"


def test_constantes_e_mapeamentos():
    """Valida o mapeamento numérico e inverso dos 4 níveis DORA."""
    assert MAPEAMENTO_CATEGORIAS == {"Elite": 4, "High": 3, "Medium": 2, "Low": 1}
    assert MAPEAMENTO_INVERSO == {4: "Elite", 3: "High", 2: "Medium", 1: "Low"}
    assert LIMIARES_CFR["Elite"] == 0.15
    assert LIMIARES_RECUPERACAO_SEGUNDOS["Elite"] == 3600.0


def test_classificar_cfr_faixas():
    """Testa a classificação de CFR nas faixas Elite (0-15%), High (16-30%), Medium (31-45%) e Low (>45%)."""
    assert classificar_cfr(0.0) == "Elite"
    assert classificar_cfr(0.15) == "Elite"
    assert classificar_cfr(0.16) == "High"
    assert classificar_cfr(0.30) == "High"
    assert classificar_cfr(0.31) == "Medium"
    assert classificar_cfr(0.45) == "Medium"
    assert classificar_cfr(0.46) == "Low"
    assert classificar_cfr(1.0) == "Low"
    assert classificar_cfr(None) is None


def test_classificar_recuperacao_faixas():
    """Testa faixas de recuperação: Elite (<1h), High (<1d), Medium (<1sem), Low (>=1sem)."""
    # Menos de 1 hora
    assert classificar_recuperacao(timedelta(minutes=59)) == "Elite"
    assert classificar_recuperacao(3599) == "Elite"

    # Entre 1 hora e menos de 1 dia
    assert classificar_recuperacao(timedelta(hours=1)) == "High"
    assert classificar_recuperacao(timedelta(hours=23, minutes=59)) == "High"
    assert classificar_recuperacao(86399) == "High"

    # Entre 1 dia e menos de 1 semana
    assert classificar_recuperacao(timedelta(days=1)) == "Medium"
    assert classificar_recuperacao(timedelta(days=6, hours=23)) == "Medium"
    assert classificar_recuperacao(7 * 86400 - 1) == "Medium"

    # 1 semana ou mais
    assert classificar_recuperacao(timedelta(days=7)) == "Low"
    assert classificar_recuperacao(timedelta(days=14)) == "Low"
    assert classificar_recuperacao(7 * 86400) == "Low"

    # None
    assert classificar_recuperacao(None) is None


def test_categoria_geral_arredondamento_para_baixo():
    """Verifica cenários diversos de mediana arredondada para baixo."""
    # (4, 4, 3, 2) -> ordenada [2, 3, 4, 4], mediana 3.5 -> floor(3.5) = 3 -> High
    assert categoria_geral([4, 4, 3, 2]) == "High"

    # (4, 3, 2, 1) -> ordenada [1, 2, 3, 4], mediana 2.5 -> floor(2.5) = 2 -> Medium
    assert categoria_geral([4, 3, 2, 1]) == "Medium"

    # Todos iguais
    assert categoria_geral([4, 4, 4, 4]) == "Elite"
    assert categoria_geral([1, 1, 1, 1]) == "Low"

    # Duas métricas (ex: CFR=Elite(4) e Recuperação=High(3)) -> mediana 3.5 -> floor 3 -> High
    assert categoria_geral(["Elite", "High"]) == "High"

    # Duas métricas (High(3) e Medium(2)) -> mediana 2.5 -> floor 2 -> Medium
    assert categoria_geral(["High", "Medium"]) == "Medium"


def test_categoria_geral_validacoes():
    """Verifica erros ao passar lista vazia ou valores inválidos."""
    with pytest.raises(ValueError, match="vazia"):
        categoria_geral([])

    with pytest.raises(ValueError, match="desconhecido"):
        categoria_geral(["Invalida"])

    with pytest.raises(ValueError, match="inválido"):
        categoria_geral([5])

    with pytest.raises(TypeError):
        categoria_geral([None])


def test_classificar_dora_integrado():
    """Testa função consolidada de classificação de múltiplas métricas."""
    resultado = classificar_dora(cfr=0.10, tempo_recuperacao_val=timedelta(hours=2))
    assert resultado["cfr"] == "Elite"
    assert resultado["recuperacao"] == "High"
    # Mediana de 4 e 3 é 3.5 -> floor 3 -> High
    assert resultado["geral"] == "High"

    # Apenas uma métrica disponível
    res_unica = classificar_dora(cfr=0.50, tempo_recuperacao_val=None)
    assert res_unica["cfr"] == "Low"
    assert res_unica["recuperacao"] is None
    assert res_unica["geral"] == "Low"
