# Testes para o ponto de entrada do pipeline (pipeline/__main__.py) e flag --repos
from pathlib import Path
from unittest.mock import patch
import pytest

from pipeline.__main__ import estimar_chamadas_api, main

RAIZ = Path(__file__).resolve().parents[1]
REPOS_FIXTURE = RAIZ / "tests" / "fixtures" / "repos_smoke.csv"
SUBAMOSTRA_30 = RAIZ / "replicacao" / "subamostra_30.csv"


def test_estimar_chamadas_api_sem_repos_fixo():
    cfg = {"limite_repos": 100, "inicio": "2025-01-01", "fim": "2025-12-31", "faixas_estrelas": ["100..200"]}
    est = estimar_chamadas_api(cfg)
    assert est["limite_repos"] == 100
    assert est["is_repos_fixo"] is False
    assert est["detalhes"]["1_selecao"]["subtotal"] > 0
    assert est["total_estimado"] > 0


def test_estimar_chamadas_api_com_repos_fixo():
    cfg = {"limite_repos": 100, "inicio": "2025-01-01", "fim": "2025-12-31"}
    est = estimar_chamadas_api(cfg, caminho_repos_fixos=REPOS_FIXTURE)
    assert est["limite_repos"] == 2
    assert est["is_repos_fixo"] is True
    assert est["detalhes"]["1_selecao"]["subtotal"] == 0
    assert est["candidatos_estimados"] == 0
    # 2 repos * 10 releases/commits + 2 repos * 12 meses runs
    assert est["total_estimado"] == (2 + 2 * 9) + (2 * 12)


def test_pipeline_dry_run_com_repos(capsys):
    main(["--repos", str(SUBAMOSTRA_30), "--dry-run"])
    captured = capsys.readouterr().out
    assert "Modo replicação: 30 repositórios fixos informados via --repos" in captured or "Modo replicacao" in captured
    assert "Etapa 1 (Seleção e Funil): 0 requisições (pulada)" in captured or "Pulada" in captured


def test_pipeline_repos_inexistente():
    with pytest.raises(SystemExit) as exc_info:
        main(["--repos", "caminho_totalmente_inexistente_12345.csv"])
    assert "nao encontrado" in str(exc_info.value).lower() or "não encontrado" in str(exc_info.value).lower()


def test_pipeline_etapa_todas_com_repos_pula_etapa1(monkeypatch):
    chamou_selecao = []
    chamou_releases = []
    chamou_runs = []
    chamou_consolidar = []

    monkeypatch.setattr("pipeline.__main__.selecionar_repositorios", lambda api, cfg: chamou_selecao.append(True))
    monkeypatch.setattr("pipeline.__main__.rodar_coleta_releases", lambda argv: chamou_releases.append(argv))
    monkeypatch.setattr("pipeline.__main__.rodar_coleta_runs_pipeline", lambda **kwargs: chamou_runs.append(kwargs))
    monkeypatch.setattr("pipeline.__main__.consolidar_dataset", lambda **kwargs: chamou_consolidar.append(kwargs))

    main(["--repos", str(REPOS_FIXTURE), "--etapa", "todas"])

    assert len(chamou_selecao) == 0, "Etapa 1 (seleção) NÃO deve ser executada quando --repos for informado"
    assert len(chamou_releases) == 1, "Etapa 2 (releases) deve ser executada"
    assert str(REPOS_FIXTURE.resolve()) in chamou_releases[0]
    assert len(chamou_runs) == 1, "Etapa 3 (runs) deve ser executada"
    assert chamou_runs[0]["caminho_repos_csv"] == REPOS_FIXTURE.resolve()
    assert len(chamou_consolidar) == 1, "Etapa 4 (consolidar) deve ser executada"
    assert chamou_consolidar[0]["arquivo_repos"] == str(REPOS_FIXTURE.resolve())


def test_coleta_runs_com_coluna_repo_apenas(tmp_path):
    csv_teste = tmp_path / "repos_minimo.csv"
    csv_teste.write_text("repo\nowner_teste/repo_teste\n", encoding="utf-8")

    with patch("pipeline.coleta_runs.coletar_runs", return_value=[]):
        from pipeline.coleta_runs import rodar_coleta_runs_pipeline
        metricas = rodar_coleta_runs_pipeline(
            caminho_repos_csv=csv_teste,
            inicio="2025-01-01",
            fim="2025-12-31",
            pasta_saida=tmp_path,
        )
        assert len(metricas) == 1
        assert metricas[0]["repo"] == "owner_teste/repo_teste"


def test_consolidar_com_coluna_repo_apenas(tmp_path):
    from pipeline.consolidar import consolidar_dataset
    csv_repos = tmp_path / "repos.csv"
    csv_repos.write_text("repo,stars\nowner_teste/repo_teste,100\n", encoding="utf-8")
    csv_lt = tmp_path / "lead_time.csv"
    csv_lt.write_text("repo,deploy_frequency_semana,n_entregas\nowner_teste/repo_teste,1.5,10\n", encoding="utf-8")
    csv_runs = tmp_path / "runs.csv"
    csv_runs.write_text("repo,cfr_ci,tempo_recuperacao_h,total_runs\nowner_teste/repo_teste,0.1,5.0,60\n", encoding="utf-8")

    ds = consolidar_dataset(
        pasta_dados=tmp_path,
        arquivo_repos=str(csv_repos),
        arquivo_lead_time="lead_time.csv",
        arquivo_metricas_runs="runs.csv",
        caminho_saida=tmp_path / "dataset.csv",
        caminho_manifest=tmp_path / "MANIFEST.json",
        inicio_janela="2025-01-01",
        fim_janela="2025-12-31",
    )
    assert len(ds) == 1
    assert ds[0]["repo"] == "owner_teste/repo_teste"
    assert ds[0]["owner"] == "owner_teste"
    assert ds[0]["repo_nome"] == "repo_teste"

