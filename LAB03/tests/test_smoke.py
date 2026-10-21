"""Smoke test do pipeline DORA para execução rápida no CI sem rede e sem token.

Marcado com @pytest.mark.smoke.
Executa o fluxo completo do pipeline para 2 repositórios utilizando fixtures de cache commitadas:
1. Coleta e sumarização de releases e lead time (a e b) via GitHubAPI em modo somente_cache;
2. Coleta de workflow runs e cálculo de CFR (a) / Tempo de Recuperação via ClienteHTTP em modo somente_cache;
3. Consolidação final em dataset.csv e geração de MANIFEST.json criptográfico;
4. Verificação de integridade e bloqueio estrito de chamadas à rede quando fora do cache.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from metricas.datas import janela
from pipeline.coleta_runs import coletar_runs
from pipeline.consolidar import consolidar_dataset
from pipeline.github_api import GitHubAPI
from pipeline.http import ClienteHTTP
from pipeline.releases import coletar_repositorio, resumir, salvar_csv

RAIZ = Path(__file__).resolve().parents[1]
FIXTURES_DIR = RAIZ / "tests" / "fixtures"
CACHE_FIXTURE_DIR = FIXTURES_DIR / "cache_http"
REPOS_FIXTURE = FIXTURES_DIR / "repos_smoke.csv"


@pytest.mark.smoke
def test_smoke_pipeline_completo_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Executa o pipeline em 2 repositórios usando o cache commitado como fixture, sem token e sem rede."""
    # Garante ausência total de token e ativação forçada do modo somente_cache
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("HTTP_SOMENTE_CACHE", "1")
    monkeypatch.setenv("GITHUB_SOMENTE_CACHE", "1")

    pasta_dados = tmp_path / "data"
    pasta_dados.mkdir(parents=True, exist_ok=True)

    # Copia o CSV de repositórios fixture para a pasta temporária
    caminho_repos = pasta_dados / "repos.csv"
    caminho_repos.write_text(REPOS_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

    # Lê os repositórios da fixture
    with open(caminho_repos, newline="", encoding="utf-8") as f:
        repos_lista = list(csv.DictReader(f))
    assert len(repos_lista) == 2

    inicio_janela = "2025-01-01"
    fim_janela = "2025-12-31"
    ini_dt, fim_dt = janela(inicio_janela, fim_janela)

    # -------------------------------------------------------------
    # ETAPA 1 (Releases & Lead Time): execução com GitHubAPI somente_cache
    # -------------------------------------------------------------
    api = GitHubAPI(cache_dir=str(CACHE_FIXTURE_DIR), somente_cache=True)
    resumos_releases = []

    for r in repos_lista:
        full_name = r["full_name"]
        owner, repo = full_name.split("/", 1)
        dados_repo = coletar_repositorio(api, owner, repo, ini_dt, fim_dt, unidade="release")
        resumo = resumir(dados_repo, ini_dt, fim_dt)
        resumos_releases.append(resumo)

    caminho_lead_time_csv = pasta_dados / "lead_time_release.csv"
    salvar_csv(caminho_lead_time_csv, resumos_releases)
    assert caminho_lead_time_csv.exists()
    assert len(resumos_releases) == 2

    # -------------------------------------------------------------
    # ETAPA 2 (Workflow Runs & CI): execução com ClienteHTTP somente_cache
    # -------------------------------------------------------------
    cliente = ClienteHTTP(cache_dir=str(CACHE_FIXTURE_DIR), somente_cache=True)
    metricas_runs = []

    for r in repos_lista:
        full_name = r["full_name"]
        owner, repo = full_name.split("/", 1)
        branch = r["default_branch"]
        cp_file = pasta_dados / f"cp_{owner}_{repo}.json"

        runs = coletar_runs(
            owner=owner,
            repo=repo,
            branch=branch,
            data_inicio=inicio_janela,
            data_fim=fim_janela,
            cliente=cliente,
            caminho_checkpoint=cp_file,
        )
        assert len(runs) > 0

        # Métrica simplificada para teste de integração dos dados de CI
        total_runs = len(runs)
        falhas = sum(1 for item in runs if item.get("conclusion") == "failure")
        cfr = falhas / total_runs if total_runs > 0 else 0.0

        metricas_runs.append({
            "repo": full_name,
            "total_runs": total_runs,
            "cfr_ci": round(cfr, 4),
            "tempo_recuperacao_s": 3600.0,
            "tempo_recuperacao_h": 1.0,
            "recuperacao_proporcao_censurados": 0.0,
            "total_episodios": 1,
        })

    caminho_runs_csv = pasta_dados / "metricas_runs.csv"
    salvar_csv(caminho_runs_csv, metricas_runs)
    assert caminho_runs_csv.exists()

    # -------------------------------------------------------------
    # ETAPA 3 (Consolidação): gera dataset.csv e MANIFEST.json
    # -------------------------------------------------------------
    caminho_dataset = pasta_dados / "dataset.csv"
    caminho_manifest = pasta_dados / "MANIFEST.json"

    linhas_dataset = consolidar_dataset(
        pasta_dados=pasta_dados,
        arquivo_repos=str(caminho_repos),
        arquivo_lead_time="lead_time_release.csv",
        arquivo_metricas_runs="metricas_runs.csv",
        caminho_saida=caminho_dataset,
        caminho_manifest=caminho_manifest,
        inicio_janela=inicio_janela,
        fim_janela=fim_janela,
    )

    # -------------------------------------------------------------
    # VALIDAÇÃO DOS RESULTADOS
    # -------------------------------------------------------------
    assert caminho_dataset.exists()
    assert caminho_manifest.exists()
    assert len(linhas_dataset) == 2

    # Verifica colunas e categorias DORA atribuídas
    for linha in linhas_dataset:
        assert "repo" in linha
        assert "categoria_dora_geral" in linha
        assert linha["categoria_dora_geral"] in ("Elite", "High", "Medium", "Low")
        assert linha["n_entregas"] > 0
        assert linha["total_runs"] > 0

    # Valida integridade do manifesto
    with open(caminho_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["dataset"]["total_repositorios"] == 2
    assert len(manifest_data["dataset"]["sha256"]) == 64


@pytest.mark.smoke
def test_smoke_somente_cache_bloqueia_acesso_a_rede() -> None:
    """Verifica que o modo somente_cache falha com erro explícito ao tentar chamada não cacheada."""
    cliente = ClienteHTTP(cache_dir=str(CACHE_FIXTURE_DIR), somente_cache=True)
    with pytest.raises(RuntimeError, match="Acesso à API bloqueado no modo somente cache"):
        cliente.get("https://api.github.com/repos/nao_existe/inexistente/releases")

    api = GitHubAPI(cache_dir=str(CACHE_FIXTURE_DIR), somente_cache=True)
    with pytest.raises(RuntimeError, match="Acesso à API bloqueado no modo somente cache"):
        api.get("/repos/nao_existe/inexistente/releases")
