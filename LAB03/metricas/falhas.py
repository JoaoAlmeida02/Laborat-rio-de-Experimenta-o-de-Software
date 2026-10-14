"""Cálculo do Change Failure Rate (CFR) para execuções de CI (workflow runs)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from metricas.corretiva import HEURISTICA_PADRAO, eh_corretiva, mensagens_da_entrega
from metricas.datas import para_datetime

PRAZO_CORRECAO = timedelta(days=7)

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


def avaliar_entregas(
    entregas: list[dict[str, Any]], fim, versao: str = HEURISTICA_PADRAO
) -> dict[str, int]:
    """Classifica as entregas para o CFR (b).

    Uma entrega falhou se a próxima entrega sai em até 7 dias e é corretiva.
    Entregas dos últimos 7 dias da janela (fim exclusivo, vindo de janela())
    são censuradas: ainda não se sabe se haverá correção.

    Parâmetros:
        entregas: entregas da janela em ordem cronológica, no formato de pipeline.releases.
        fim: fim exclusivo da janela.
        versao: chave de metricas.corretiva.HEURISTICAS.

    Retorno:
        Dicionário com 'falhas', 'avaliadas' e 'censuradas'.
    """
    ordenadas = sorted(entregas, key=lambda e: para_datetime(e["data"]))
    contagem = {"falhas": 0, "avaliadas": 0, "censuradas": 0}

    for i, entrega in enumerate(ordenadas):
        data = para_datetime(entrega["data"])
        if data + PRAZO_CORRECAO > fim:
            contagem["censuradas"] += 1
            continue

        contagem["avaliadas"] += 1
        if i + 1 < len(ordenadas):
            proxima = ordenadas[i + 1]
            dentro_prazo = para_datetime(proxima["data"]) - data <= PRAZO_CORRECAO
            if dentro_prazo and eh_corretiva(
                entrega["tag"], proxima["tag"], mensagens_da_entrega(proxima), versao
            ):
                contagem["falhas"] += 1

    return contagem


def cfr_entrega(
    entregas: list[dict[str, Any]], fim, versao: str = HEURISTICA_PADRAO
) -> float | None:
    """Change Failure Rate pelo proxy de entrega (variante b).

    CFR = entregas que falharam / entregas avaliadas (censuradas fora do denominador).

    Retorno:
        Float entre 0.0 e 1.0, ou None se nenhuma entrega puder ser avaliada.
    """
    contagem = avaliar_entregas(entregas, fim, versao)
    if contagem["avaliadas"] == 0:
        return None
    return contagem["falhas"] / contagem["avaliadas"]


def rework_rate(entregas: list[dict[str, Any]], versao: str = HEURISTICA_PADRAO) -> float | None:
    """Proporção de entregas corretivas sobre o total (RQ 08, métrica DORA de 2024).

    A primeira entrega não tem anterior para comparar e fica fora do cálculo.
    """
    ordenadas = sorted(entregas, key=lambda e: para_datetime(e["data"]))
    pares = list(zip(ordenadas, ordenadas[1:]))
    if not pares:
        return None
    corretivas = sum(
        eh_corretiva(anterior["tag"], atual["tag"], mensagens_da_entrega(atual), versao)
        for anterior, atual in pares
    )
    return corretivas / len(pares)
