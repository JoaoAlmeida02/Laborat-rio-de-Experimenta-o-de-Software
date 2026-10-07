"""Cálculo do Change Failure Rate (CFR) para execuções de CI (workflow runs)."""

from __future__ import annotations

from typing import Any

# Tabela padrão de mapeamento de conclusions da API do GitHub Actions
TABELA_CLASSIFICACAO: dict[str | None, str] = {
    "success": "sucesso",
    "failure": "falha",
    "timed_out": "falha",
    "startup_failure": "falha",
    "cancelled": "ignorar",
    "skipped": "ignorar",
    "neutral": "ignorar",
    "action_required": "ignorar",
    "stale": "ignorar",
    "null": "ignorar",
    None: "ignorar",
}


def classificar_conclusion(conclusion: str | None) -> str:
    """Classifica o resultado de um run em 'sucesso', 'falha' ou 'ignorar'.

    Parâmetros:
        conclusion: String retornada pela API do GitHub (ou None para em andamento/sem conclusão).

    Retorno:
        'sucesso' se o run passou, 'falha' se quebrou ou deu timeout, ou 'ignorar' caso cancelado/pulado.
    """
    normalizado = conclusion.lower().strip() if isinstance(conclusion, str) else conclusion
    return TABELA_CLASSIFICACAO.get(normalizado, "ignorar")


def cfr_ci(runs: list[dict[str, Any]]) -> float | None:
    """Calcula a taxa de falha de mudanças (Change Failure Rate) para CI (variante a).

    CFR = falhas / (sucessos + falhas), desconsiderando runs com status 'ignorar'.

    Parâmetros:
        runs: Lista de dicionários representando workflow runs.

    Retorno:
        Float entre 0.0 e 1.0 com a proporção de falhas, ou None se não houver runs válidos (divisão por zero).
    """
    total_falhas = 0
    total_sucessos = 0

    for run in runs:
        classe = classificar_conclusion(run.get("conclusion"))
        if classe == "falha":
            total_falhas += 1
        elif classe == "sucesso":
            total_sucessos += 1

    total_validos = total_falhas + total_sucessos
    if total_validos == 0:
        return None

    return total_falhas / total_validos
