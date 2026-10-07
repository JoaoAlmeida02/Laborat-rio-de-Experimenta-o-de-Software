"""Cálculo do tempo de recuperação (Time to Restore Service) a partir de workflow runs."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import statistics
from typing import Any, NamedTuple

from metricas.falhas import classificar_conclusion


from dataclasses import dataclass


@dataclass
class ResultadoRecuperacao:
    """Estrutura com o resultado da análise de tempo de recuperação."""

    episodios: list[dict[str, Any]]
    mediana: timedelta | None
    proporcao_censurados: float

    def __iter__(self):
        """Permite desempacotamento como tupla: episodios, mediana, prop = resultado."""
        return iter((self.episodios, self.mediana, self.proporcao_censurados))

    def __getitem__(self, item: Any) -> Any:
        """Permite acesso tanto por índice numérico quanto por chave de string."""
        if isinstance(item, int):
            return (self.episodios, self.mediana, self.proporcao_censurados)[item]
        if isinstance(item, str):
            return getattr(self, item)
        raise TypeError(f"Índice inválido: {item}")

    def get(self, key: str, default: Any = None) -> Any:
        """Acesso seguro a campos no estilo dicionário."""
        return getattr(self, key, default)


def para_datetime_utc(valor: str | datetime) -> datetime:
    """Converte strings ISO 8601 (incluindo 'Z') ou datetime em datetime timezone-aware em UTC."""
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor).replace("Z", "+00:00")
    dt = datetime.fromisoformat(texto)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def tempo_recuperacao(runs: list[dict[str, Any]]) -> ResultadoRecuperacao:
    """Calcula os episódios de tempo de recuperação por workflow.

    Agrupa por workflow_id e ordena cronologicamente por run_started_at.
    - Episódio inicia na primeira falha de uma sequência e encerra no próximo sucesso.
    - Runs 'ignorar' (ex.: cancelled) não abrem nem fecham episódios.
    - Falhas nunca recuperadas tornam-se episódios censurados.

    Retorna:
        ResultadoRecuperacao contendo:
        - lista de episódios
        - mediana das durações dos episódios não censurados (ou None se não houver)
        - proporção de episódios censurados (0.0 a 1.0)
    """
    por_workflow: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        wf_id = run.get("workflow_id")
        por_workflow[wf_id].append(run)

    episodios: list[dict[str, Any]] = []

    for wf_id, wf_runs in por_workflow.items():
        # Ordena cronologicamente por run_started_at (fallback para created_at)
        runs_ordenados = sorted(
            wf_runs,
            key=lambda r: para_datetime_utc(r.get("run_started_at") or r.get("created_at")),
        )

        falha_inicial: dict[str, Any] | None = None

        for r in runs_ordenados:
            classe = classificar_conclusion(r.get("conclusion"))

            if classe == "ignorar":
                # Runs ignorados não abrem nem fecham episódio
                continue

            if classe == "falha":
                # Marca apenas a primeira falha da sequência
                if falha_inicial is None:
                    falha_inicial = r

            elif classe == "sucesso":
                if falha_inicial is not None:
                    dt_inicio = para_datetime_utc(falha_inicial["run_started_at"])
                    dt_fim = para_datetime_utc(r["updated_at"])
                    duracao = dt_fim - dt_inicio

                    episodios.append({
                        "workflow_id": wf_id,
                        "inicio": dt_inicio,
                        "fim": dt_fim,
                        "duracao": duracao,
                        "duracao_segundos": duracao.total_seconds(),
                        "censurado": False,
                    })
                    falha_inicial = None

        # Falha que permaneceu sem recuperação até o fim do histórico = episódio censurado
        if falha_inicial is not None:
            dt_inicio = para_datetime_utc(falha_inicial["run_started_at"])
            episodios.append({
                "workflow_id": wf_id,
                "inicio": dt_inicio,
                "fim": None,
                "duracao": None,
                "duracao_segundos": None,
                "censurado": True,
            })

    total_episodios = len(episodios)
    episodios_nao_censurados = [ep for ep in episodios if not ep["censurado"]]
    episodios_censurados = [ep for ep in episodios if ep["censurado"]]

    proporcao_censurados = (
        len(episodios_censurados) / total_episodios if total_episodios > 0 else 0.0
    )

    duracoes = [ep["duracao"] for ep in episodios_nao_censurados]
    mediana_duracao = statistics.median(duracoes) if duracoes else None

    return ResultadoRecuperacao(
        episodios=episodios,
        mediana=mediana_duracao,
        proporcao_censurados=proporcao_censurados,
    )
