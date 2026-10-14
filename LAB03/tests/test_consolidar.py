"""Testes unitários para o módulo de consolidação (pipeline/consolidar.py)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from pipeline.consolidar import calcular_sha256, consolidar_dataset, obter_info_git


def test_calcular_sha256(tmp_path: Path):
    arquivo = tmp_path / "teste.txt"
    arquivo.write_text("conteudo para hash", encoding="utf-8")
    sha = calcular_sha256(arquivo)
    assert len(sha) == 64
    assert isinstance(sha, str)

    # Arquivo inexistente retorna string vazia
    assert calcular_sha256(tmp_path / "inexistente.txt") == ""


def test_obter_info_git():
    info = obter_info_git()
    assert "commit" in info
    assert "branch" in info
    # No repositório de desenvolvimento, deve encontrar commit e branch
    if info["commit"]:
        assert len(info["commit"]) == 40


def test_consolidar_dataset_completo(tmp_path: Path):
    # 1. Cria repos.csv
    repos_csv = tmp_path / "repos.csv"
    with open(repos_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f,
            fieldnames=[
                "full_name", "owner", "repo", "stars", "forks", "open_issues",
                "language", "default_branch", "created_at", "idade_anos",
                "idade_dias", "contribuidores"
            ],
        )
        escritor.writeheader()
        escritor.writerow({
            "full_name": "psf/requests",
            "owner": "psf",
            "repo": "requests",
            "stars": "50000",
            "forks": "9000",
            "open_issues": "150",
            "language": "Python",
            "default_branch": "main",
            "created_at": "2011-02-13T18:00:00Z",
            "idade_anos": "14.0",
            "idade_dias": "5113.0",
            "contribuidores": "350",
        })

    # 2. Cria lead_time_release.csv
    lt_csv = tmp_path / "lead_time_release.csv"
    with open(lt_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f,
            fieldnames=[
                "repo", "unidade", "n_entregas", "deploy_frequency_semana",
                "lead_time_release_h", "lead_time_commit_h", "n_commits",
                "cfr_entrega", "cfr_entrega_avaliadas", "cfr_entrega_censuradas",
                "rework_rate", "ignoradas_sem_anterior", "ignoradas_compare_404",
                "ignoradas_sem_commits"
            ],
        )
        escritor.writeheader()
        escritor.writerow({
            "repo": "psf/requests",
            "unidade": "release",
            "n_entregas": "8",
            "deploy_frequency_semana": "0.1538",
            "lead_time_release_h": "1100.5",
            "lead_time_commit_h": "450.2",
            "n_commits": "85",
            "cfr_entrega": "0.125",
            "cfr_entrega_avaliadas": "8",
            "cfr_entrega_censuradas": "0",
            "rework_rate": "0.1428",
            "ignoradas_sem_anterior": "1",
            "ignoradas_compare_404": "0",
            "ignoradas_sem_commits": "0",
        })

    # 3. Cria metricas_runs.csv
    runs_csv = tmp_path / "metricas_runs.csv"
    with open(runs_csv, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(
            f,
            fieldnames=[
                "repo", "total_runs", "cfr_ci", "tempo_recuperacao_s",
                "tempo_recuperacao_h", "recuperacao_proporcao_censurados",
                "total_episodios"
            ],
        )
        escritor.writeheader()
        escritor.writerow({
            "repo": "psf/requests",
            "total_runs": "150",
            "cfr_ci": "0.08",
            "tempo_recuperacao_s": "1800.0",
            "tempo_recuperacao_h": "0.5",
            "recuperacao_proporcao_censurados": "0.05",
            "total_episodios": "6",
        })

    saida_dataset = tmp_path / "dataset.csv"
    saida_manifest = tmp_path / "MANIFEST.json"

    linhas = consolidar_dataset(
        pasta_dados=tmp_path,
        arquivo_repos=repos_csv.name,
        arquivo_lead_time=lt_csv.name,
        arquivo_metricas_runs=runs_csv.name,
        caminho_saida=saida_dataset,
        caminho_manifest=saida_manifest,
        inicio_janela="2025-01-01",
        fim_janela="2025-12-31",
    )

    assert len(linhas) == 1
    r = linhas[0]
    assert r["repo"] == "psf/requests"
    assert r["stars"] == 50000
    assert r["language"] == "Python"
    assert r["contribuidores"] == 350
    assert r["deploy_frequency_semana"] == 0.1538
    assert r["lead_time_commit_h"] == 450.2
    assert r["lead_time_release_h"] == 1100.5
    assert r["cfr_ci"] == 0.08
    assert r["cfr_entrega"] == 0.125
    assert r["tempo_recuperacao_s"] == 1800.0
    assert r["recuperacao_proporcao_censurados"] == 0.05
    assert r["ignoradas_sem_anterior"] == 1
    assert r["categoria_dora_cfr"] == "Elite"  # 12.5% <= 15%
    assert r["categoria_dora_recuperacao"] == "Elite"  # 1800s < 3600s
    assert r["categoria_dora_geral"] == "Elite"

    # Validações do MANIFEST.json
    assert saida_manifest.exists()
    with open(saida_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert "data_coleta" in manifest_data
    assert manifest_data["janela"]["inicio"] == "2025-01-01"
    assert manifest_data["dataset"]["total_repositorios"] == 1
    assert len(manifest_data["dataset"]["sha256"]) == 64
    assert len(manifest_data["fontes_dados"]["repos_csv"]["sha256"]) == 64
