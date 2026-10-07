"""Testes unitários para o coletor de workflow runs (pipeline/coleta_runs.py)."""

from __future__ import annotations

from datetime import date
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.coleta_runs import (
    carregar_checkpoint,
    coletar_periodo,
    coletar_runs,
    converter_data,
    gerar_meses,
    salvar_checkpoint_atomico,
    subdividir_dias,
    subdividir_semanas,
)
from pipeline.http import ClienteHTTP


def test_converter_data():
    """Testa conversão de strings para objetos date."""
    assert converter_data("2024-02-29") == date(2024, 2, 29)
    assert converter_data(date(2024, 1, 1)) == date(2024, 1, 1)


def test_gerar_meses():
    """Verifica divisão correta de período em meses do calendário."""
    meses = gerar_meses(date(2024, 1, 15), date(2024, 3, 10))
    assert meses == [
        (date(2024, 1, 15), date(2024, 1, 31)),
        (date(2024, 2, 1), date(2024, 2, 29)),  # Ano bissexto
        (date(2024, 3, 1), date(2024, 3, 10)),
    ]


def test_subdividir_semanas_e_dias():
    """Testa divisão em blocos de até 7 dias e dia a dia."""
    semanas = subdividir_semanas(date(2024, 1, 1), date(2024, 1, 10))
    assert semanas == [
        (date(2024, 1, 1), date(2024, 1, 7)),
        (date(2024, 1, 8), date(2024, 1, 10)),
    ]

    dias = subdividir_dias(date(2024, 1, 1), date(2024, 1, 3))
    assert dias == [
        (date(2024, 1, 1), date(2024, 1, 1)),
        (date(2024, 1, 2), date(2024, 1, 2)),
        (date(2024, 1, 3), date(2024, 1, 3)),
    ]


def test_subdivisao_automatica_quando_atinge_1000_runs(caplog):
    """Verifica subdivisão de mês em semanas e semana em dias ao atingir teto de 1000 runs."""
    cliente_mock = MagicMock(spec=ClienteHTTP)

    def mock_get(url, params=None):
        created = params.get("created", "")
        # Mês inteiro atinge o teto de 1.000
        if created == "2024-01-01..2024-01-31":
            return {"total_count": 1000, "workflow_runs": []}
        # Semana 1 atinge teto de 1.000
        if created == "2024-01-01..2024-01-07":
            return {"total_count": 1000, "workflow_runs": []}
        # Outras semanas ou dias retornam contagem normal
        return {"total_count": 2, "workflow_runs": [{"id": 1, "created": created}]}

    cliente_mock.get.side_effect = mock_get
    cliente_mock.get_paginado.return_value = [{"id": 999}]

    with caplog.at_level(logging.WARNING):
        runs = coletar_periodo(
            cliente=cliente_mock,
            owner="org",
            repo="repo",
            branch="main",
            inicio=date(2024, 1, 1),
            fim=date(2024, 1, 31),
            nivel="mes",
        )

    assert len(runs) > 0
    # Verifica que houve logging da subdivisão do mês e da semana
    assert any("Período mensal 2024-01-01..2024-01-31 atingiu o teto" in r.message for r in caplog.records)
    assert any("Período semanal 2024-01-01..2024-01-07 atingiu o teto" in r.message for r in caplog.records)


def test_salvar_e_carregar_checkpoint_atomico(tmp_path: Path):
    """Testa escrita atômica do checkpoint e recuperação dos dados."""
    caminho = tmp_path / "checkpoint.json"
    dados = {
        "periodos_concluidos": ["2024-01-01..2024-01-31"],
        "runs": {"10": {"id": 10, "conclusion": "success"}},
    }

    salvar_checkpoint_atomico(caminho, dados)
    assert caminho.exists()

    recuperado = carregar_checkpoint(caminho)
    assert recuperado["periodos_concluidos"] == ["2024-01-01..2024-01-31"]
    assert recuperado["runs"]["10"]["id"] == 10


def test_retomada_apos_interrupcao_ctrl_c(tmp_path: Path):
    """Garante que execução interrompida pode ser retomada sem repetir períodos já salvos."""
    checkpoint_file = tmp_path / "runs_checkpoint.json"
    cliente_mock = MagicMock(spec=ClienteHTTP)
    cliente_mock.cota_restante = 4500

    chamadas_periodo = []

    def mock_get(url, params=None):
        created = params.get("created", "")
        chamadas_periodo.append(created)
        if created == "2024-01-01..2024-01-31":
            return {"total_count": 1, "workflow_runs": [{"id": 101, "conclusion": "success"}]}
        if created == "2024-02-01..2024-02-29":
            # Simula Ctrl+C durante a coleta do 2º mês
            raise KeyboardInterrupt()
        return {"total_count": 1, "workflow_runs": [{"id": 102, "conclusion": "failure"}]}

    cliente_mock.get.side_effect = mock_get

    # 1ª Execução: interrompida no 2º mês
    with pytest.raises(KeyboardInterrupt):
        coletar_runs(
            owner="org",
            repo="repo",
            branch="main",
            data_inicio="2024-01-01",
            data_fim="2024-02-29",
            cliente=cliente_mock,
            caminho_checkpoint=checkpoint_file,
        )

    # Verifica que o mês 1 foi salvo com sucesso no checkpoint
    cp1 = carregar_checkpoint(checkpoint_file)
    assert "2024-01-01..2024-01-31" in cp1["periodos_concluidos"]
    assert "101" in cp1["runs"]
    assert "2024-02-01..2024-02-29" not in cp1["periodos_concluidos"]

    # 2ª Execução: agora o 2º mês responde com sucesso
    def mock_get2(url, params=None):
        created = params.get("created", "")
        chamadas_periodo.append(created)
        return {"total_count": 1, "workflow_runs": [{"id": 102, "conclusion": "success"}]}

    cliente_mock.get.side_effect = mock_get2
    chamadas_periodo.clear()

    runs_totais = coletar_runs(
        owner="org",
        repo="repo",
        branch="main",
        data_inicio="2024-01-01",
        data_fim="2024-02-29",
        cliente=cliente_mock,
        caminho_checkpoint=checkpoint_file,
    )

    # Verifica que o mês 1 NÃO foi requisitado novamente
    assert "2024-01-01..2024-01-31" not in chamadas_periodo
    assert "2024-02-01..2024-02-29" in chamadas_periodo

    # Total de runs combinados dos 2 períodos
    ids_coletados = {r["id"] for r in runs_totais}
    assert ids_coletados == {101, 102}


def test_barra_progresso_exibe_cota_restante(tmp_path: Path):
    """Verifica que a cota restante da API é repassada para o set_postfix da barra de progresso."""
    checkpoint_file = tmp_path / "cp.json"
    cliente_mock = MagicMock(spec=ClienteHTTP)
    cliente_mock.cota_restante = 4850
    cliente_mock.get.return_value = {"total_count": 1, "workflow_runs": [{"id": 1}]}

    with patch("pipeline.coleta_runs.tqdm") as mock_tqdm:
        pbar_mock = MagicMock()
        mock_tqdm.return_value.__enter__.return_value = pbar_mock

        coletar_runs(
            owner="org",
            repo="repo",
            data_inicio="2024-01-01",
            data_fim="2024-01-31",
            cliente=cliente_mock,
            caminho_checkpoint=checkpoint_file,
        )

        assert pbar_mock.set_postfix.called
        # Verifica se alguma chamada continha cota=4850
        chamadas_postfix = [c.kwargs for c in pbar_mock.set_postfix.call_args_list]
        assert any(kwargs.get("cota") == 4850 for kwargs in chamadas_postfix)
