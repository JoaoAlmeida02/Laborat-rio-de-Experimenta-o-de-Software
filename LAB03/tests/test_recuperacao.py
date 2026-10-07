"""Testes unitários para cálculo do tempo de recuperação (metricas/recuperacao.py)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from metricas.recuperacao import (
    ResultadoRecuperacao,
    para_datetime_utc,
    tempo_recuperacao,
)


def test_para_datetime_utc():
    """Valida conversão de datetime nativo com e sem timezone."""
    dt_sem_tz = datetime(2024, 1, 1, 10, 0)
    assert para_datetime_utc(dt_sem_tz) == datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    dt_com_tz = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert para_datetime_utc(dt_com_tz) == dt_com_tz


def test_exemplo_enunciado_1h20():
    """Testa o exemplo exato do enunciado: falha às 10:00 e sucesso às 11:20 -> 1h20 (80 min)."""
    runs = [
        {
            "workflow_id": 1,
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:00:00Z",
            "updated_at": "2024-05-10T10:05:00Z",
        },
        {
            "workflow_id": 1,
            "conclusion": "success",
            "run_started_at": "2024-05-10T11:15:00Z",
            "updated_at": "2024-05-10T11:20:00Z",
        },
    ]

    resultado = tempo_recuperacao(runs)

    assert isinstance(resultado, ResultadoRecuperacao)
    assert len(resultado.episodios) == 1

    ep = resultado.episodios[0]
    assert ep["censurado"] is False
    assert ep["duracao"] == timedelta(hours=1, minutes=20)
    assert ep["duracao_segundos"] == 4800.0

    assert resultado.mediana == timedelta(hours=1, minutes=20)
    assert resultado.proporcao_censurados == pytest.approx(0.0)

    # Verifica desempacotamento e acessos
    episodios, med, prop = resultado
    assert med == timedelta(minutes=80)
    assert prop == 0.0
    assert resultado[0] == episodios
    assert resultado[1] == med
    assert resultado[2] == prop
    assert resultado["mediana"] == timedelta(minutes=80)
    assert resultado.get("proporcao_censurados") == 0.0

    with pytest.raises(TypeError, match="Índice inválido"):
        _ = resultado[3.14]


def test_falha_nunca_recuperada_episodio_censurado():
    """Verifica que uma falha sem sucesso subsequente gera um episódio censurado e não entra na mediana."""
    runs = [
        {
            "workflow_id": 1,
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:00:00Z",
            "updated_at": "2024-05-10T10:10:00Z",
        }
    ]

    resultado = tempo_recuperacao(runs)

    assert len(resultado.episodios) == 1
    ep = resultado.episodios[0]
    assert ep["censurado"] is True
    assert ep["fim"] is None
    assert ep["duracao"] is None

    assert resultado.mediana is None
    assert resultado.proporcao_censurados == pytest.approx(1.0)


def test_runs_cancelled_e_skipped_sao_ignorados():
    """Garante que runs ignorados (cancelled, etc.) não abrem, não fecham e não quebram episódios."""
    runs = [
        # Início da falha
        {
            "workflow_id": 42,
            "conclusion": "failure",
            "run_started_at": "2024-05-10T10:00:00Z",
            "updated_at": "2024-05-10T10:05:00Z",
        },
        # Run cancelado no meio: deve ser ignorado
        {
            "workflow_id": 42,
            "conclusion": "cancelled",
            "run_started_at": "2024-05-10T10:30:00Z",
            "updated_at": "2024-05-10T10:35:00Z",
        },
        # Segunda falha da mesma sequência: mantém a primeira como início
        {
            "workflow_id": 42,
            "conclusion": "timed_out",
            "run_started_at": "2024-05-10T10:45:00Z",
            "updated_at": "2024-05-10T10:50:00Z",
        },
        # Run skipped: ignorado
        {
            "workflow_id": 42,
            "conclusion": "skipped",
            "run_started_at": "2024-05-10T11:00:00Z",
            "updated_at": "2024-05-10T11:05:00Z",
        },
        # Sucesso que encerra o episódio
        {
            "workflow_id": 42,
            "conclusion": "success",
            "run_started_at": "2024-05-10T11:10:00Z",
            "updated_at": "2024-05-10T11:20:00Z",
        },
    ]

    resultado = tempo_recuperacao(runs)

    assert len(resultado.episodios) == 1
    ep = resultado.episodios[0]
    assert ep["censurado"] is False
    assert ep["duracao"] == timedelta(hours=1, minutes=20)


def test_multiplos_workflows_agrupados_separadamente():
    """Verifica que o cálculo é feito isoladamente por workflow_id e calcula a mediana correta."""
    runs = [
        # Workflow 1: 1 hora de recuperação
        {
            "workflow_id": 1,
            "conclusion": "failure",
            "run_started_at": "2024-05-01T08:00:00Z",
            "updated_at": "2024-05-01T08:05:00Z",
        },
        {
            "workflow_id": 1,
            "conclusion": "success",
            "run_started_at": "2024-05-01T08:50:00Z",
            "updated_at": "2024-05-01T09:00:00Z",
        },
        # Workflow 2: 3 horas de recuperação
        {
            "workflow_id": 2,
            "conclusion": "failure",
            "run_started_at": "2024-05-01T10:00:00Z",
            "updated_at": "2024-05-01T10:10:00Z",
        },
        {
            "workflow_id": 2,
            "conclusion": "success",
            "run_started_at": "2024-05-01T12:50:00Z",
            "updated_at": "2024-05-01T13:00:00Z",
        },
    ]

    resultado = tempo_recuperacao(runs)

    assert len(resultado.episodios) == 2
    # Mediana entre 1h e 3h = 2h
    assert resultado.mediana == timedelta(hours=2)
    assert resultado.proporcao_censurados == pytest.approx(0.0)


def test_cenario_misto_com_episodios_censurados_e_resolvidos():
    """Testa proporção de censura quando há episódios recuperados e episódios não recuperados."""
    runs = [
        # Workflow 1: recuperado em 2 horas
        {
            "workflow_id": 10,
            "conclusion": "failure",
            "run_started_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:10:00Z",
        },
        {
            "workflow_id": 10,
            "conclusion": "success",
            "run_started_at": "2024-01-01T11:50:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
        },
        # Workflow 10: nova falha que nunca recupera
        {
            "workflow_id": 10,
            "conclusion": "failure",
            "run_started_at": "2024-01-02T10:00:00Z",
            "updated_at": "2024-01-02T10:05:00Z",
        },
    ]

    resultado = tempo_recuperacao(runs)

    assert len(resultado.episodios) == 2
    # 1 resolvido (2h) e 1 censurado -> mediana deve ser 2h
    assert resultado.mediana == timedelta(hours=2)
    # 1 censurado em 2 = 50%
    assert resultado.proporcao_censurados == pytest.approx(0.5)


def test_sem_falhas_retorna_vazio():
    """Verifica que quando não há falhas, nenhum episódio é gerado."""
    runs = [
        {
            "workflow_id": 1,
            "conclusion": "success",
            "run_started_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:10:00Z",
        }
    ]

    resultado = tempo_recuperacao(runs)
    assert len(resultado.episodios) == 0
    assert resultado.mediana is None
    assert resultado.proporcao_censurados == pytest.approx(0.0)
