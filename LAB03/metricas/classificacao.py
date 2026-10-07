"""Classificação DORA das métricas coletadas (Elite, High, Medium, Low).

Define as faixas de desempenho por métrica e o cálculo da categoria geral consolidada.
"""

from __future__ import annotations

from datetime import timedelta
import math
import statistics
from typing import Any, Sequence

MAPEAMENTO_CATEGORIAS: dict[str, int] = {
    "Elite": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
}

MAPEAMENTO_INVERSO: dict[int, str] = {
    4: "Elite",
    3: "High",
    2: "Medium",
    1: "Low",
}

# Limiares configuráveis para Change Failure Rate (CFR)
# Elite: 0-15%, High: 16-30%, Medium: 31-45%, Low: >45%
LIMIARES_CFR: dict[str, float] = {
    "Elite": 0.15,
    "High": 0.30,
    "Medium": 0.45,
}

# Limiares configuráveis para tempo de recuperação em segundos
# Elite: < 1h (3600s), High: < 1 dia (86400s), Medium: < 1 semana (604800s), Low: >= 1 semana
LIMIARES_RECUPERACAO_SEGUNDOS: dict[str, float] = {
    "Elite": 3600.0,
    "High": 86400.0,
    "Medium": 7 * 86400.0,
}


def classificar_cfr(cfr: float | None) -> str | None:
    """Classifica a métrica Change Failure Rate em uma categoria DORA.

    Retorna 'Elite', 'High', 'Medium', 'Low', ou None se valor for ausente.
    """
    if cfr is None:
        return None
    if cfr <= LIMIARES_CFR["Elite"]:
        return "Elite"
    if cfr <= LIMIARES_CFR["High"]:
        return "High"
    if cfr <= LIMIARES_CFR["Medium"]:
        return "Medium"
    return "Low"


def classificar_recuperacao(tempo: timedelta | float | int | None) -> str | None:
    """Classifica o tempo de recuperação em uma categoria DORA.

    Parâmetros:
        tempo: Objeto timedelta ou número representando segundos (ou None se não mensurável).

    Retorno:
        'Elite', 'High', 'Medium', 'Low', ou None se tempo for ausente.
    """
    if tempo is None:
        return None

    if isinstance(tempo, timedelta):
        segundos = tempo.total_seconds()
    else:
        segundos = float(tempo)

    if segundos < LIMIARES_RECUPERACAO_SEGUNDOS["Elite"]:
        return "Elite"
    if segundos < LIMIARES_RECUPERACAO_SEGUNDOS["High"]:
        return "High"
    if segundos < LIMIARES_RECUPERACAO_SEGUNDOS["Medium"]:
        return "Medium"
    return "Low"


def categoria_geral(categorias: Sequence[str | int]) -> str:
    """Calcula a categoria DORA geral a partir da mediana das categorias arredondada para baixo.

    Mapeamento: Elite=4, High=3, Medium=2, Low=1.
    Exemplo: (4, 3, 3, 1) -> mediana 3 -> High.
    """
    if not categorias:
        raise ValueError("A sequência de categorias não pode ser vazia.")

    valores: list[int] = []
    for cat in categorias:
        if isinstance(cat, int):
            if cat not in MAPEAMENTO_INVERSO:
                raise ValueError(f"Valor numérico de categoria inválido: {cat}")
            valores.append(cat)
        elif isinstance(cat, str):
            nome_normalizado = cat.strip().capitalize()
            if nome_normalizado not in MAPEAMENTO_CATEGORIAS:
                raise ValueError(f"Nome de categoria desconhecido: '{cat}'")
            valores.append(MAPEAMENTO_CATEGORIAS[nome_normalizado])
        else:
            raise TypeError(f"Tipo inválido para categoria: {type(cat)}")

    mediana_num = statistics.median(valores)
    valor_arredondado = math.floor(mediana_num)
    # Garante limites válidos [1, 4]
    valor_final = max(1, min(4, valor_arredondado))

    return MAPEAMENTO_INVERSO[valor_final]


def classificar_dora(
    cfr: float | None = None,
    tempo_recuperacao_val: timedelta | float | int | None = None,
) -> dict[str, Any]:
    """Classifica individualmente e consolidada as métricas DORA fornecidas."""
    cat_cfr = classificar_cfr(cfr)
    cat_recuperacao = classificar_recuperacao(tempo_recuperacao_val)

    categorias_validas = [c for c in [cat_cfr, cat_recuperacao] if c is not None]
    cat_geral = categoria_geral(categorias_validas) if categorias_validas else None

    return {
        "cfr": cat_cfr,
        "recuperacao": cat_recuperacao,
        "geral": cat_geral,
    }
