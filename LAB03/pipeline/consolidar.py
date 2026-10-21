"""Consolidação das métricas DORA em um dataset final (data/dataset.csv) e geração de MANIFEST.json.

Combina metadados dos repositórios, métricas de releases/entregas (Lead Time a e b, CFR b, Rework Rate)
e métricas de CI/CD (CFR a, Tempo de Recuperação e episódios censurados).
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from metricas.classificacao import classificar_dora

RAIZ = Path(__file__).resolve().parents[1]


def calcular_sha256(caminho: Path | str) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        return ""
    hasher = hashlib.sha256()
    with open(caminho_p, "rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            hasher.update(bloco)
    return hasher.hexdigest()


def obter_info_git() -> dict[str, str | None]:
    """Obtém o hash do commit atual e o nome da branch do repositório Git."""
    info = {"commit": None, "branch": None}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True, cwd=str(RAIZ)
        ).strip()
        info["commit"] = commit
    except Exception:
        pass

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=str(RAIZ),
        ).strip()
        info["branch"] = branch
    except Exception:
        pass

    return info


def carregar_csv_como_dict(caminho: Path | str, chave_pk: str = "repo") -> dict[str, dict[str, Any]]:
    """Carrega arquivo CSV indexando pelo campo especificado."""
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        return {}

    resultado = {}
    with open(caminho_p, "r", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            chave = linha.get(chave_pk) or linha.get("full_name") or linha.get("repo")
            if chave:
                resultado[chave.strip()] = linha
    return resultado


def converter_numero(valor: Any, tipo=float):
    """Converte valores textuais de CSV para int, float ou None."""
    if valor is None or valor == "" or str(valor).lower() in ("none", "null", "nan"):
        return None
    try:
        return tipo(valor)
    except (ValueError, TypeError):
        return None


def consolidar_dataset(
    pasta_dados: Path | str = "data",
    arquivo_repos: str = "repos.csv",
    arquivo_lead_time: str = "lead_time_release.csv",
    arquivo_metricas_runs: str = "metricas_runs.csv",
    caminho_saida: Path | str = "data/dataset.csv",
    caminho_manifest: Path | str = "data/MANIFEST.json",
    inicio_janela: str = "2025-01-01",
    fim_janela: str = "2025-12-31",
) -> list[dict[str, Any]]:
    """Gera o dataset consolidado final com 1 linha por repositório e exporta CSV e MANIFEST.json."""
    pasta = Path(pasta_dados)
    caminho_csv = pasta / arquivo_repos if not Path(arquivo_repos).is_absolute() else Path(arquivo_repos)
    caminho_lt = pasta / arquivo_lead_time if not Path(arquivo_lead_time).is_absolute() else Path(arquivo_lead_time)
    caminho_runs = pasta / arquivo_metricas_runs if not Path(arquivo_metricas_runs).is_absolute() else Path(arquivo_metricas_runs)
    saida = Path(caminho_saida)
    manifest_p = Path(caminho_manifest)

    if not caminho_csv.exists():
        raise FileNotFoundError(f"Arquivo base de repositórios '{caminho_csv}' não encontrado.")

    dict_repos = carregar_csv_como_dict(caminho_csv, chave_pk="full_name")
    dict_lt = carregar_csv_como_dict(caminho_lt, chave_pk="repo")
    dict_runs = carregar_csv_como_dict(caminho_runs, chave_pk="repo")

    linhas_dataset = []

    for nome_repo, dados_repo in dict_repos.items():
        dados_lt = dict_lt.get(nome_repo, {})
        dados_runs = dict_runs.get(nome_repo, {})

        # Metadados
        owner = dados_repo.get("owner") or (nome_repo.split("/")[0] if "/" in nome_repo else "")
        raw_repo = dados_repo.get("repo") or ""
        if "/" in str(raw_repo):
            repo_curto = str(raw_repo).split("/")[1]
        else:
            repo_curto = raw_repo or (nome_repo.split("/")[1] if "/" in nome_repo else nome_repo)
        stars = converter_numero(dados_repo.get("stars"), int) or 0
        forks = converter_numero(dados_repo.get("forks"), int) or 0
        open_issues = converter_numero(dados_repo.get("open_issues"), int) or 0
        language = dados_repo.get("language") or "Outra"
        contribuidores = converter_numero(dados_repo.get("contribuidores"), int) or 1
        idade_anos = converter_numero(dados_repo.get("idade_anos"), float) or 0.0
        idade_dias = converter_numero(dados_repo.get("idade_dias"), float) or 0.0
        created_at = dados_repo.get("created_at") or ""
        default_branch = dados_repo.get("default_branch") or "main"

        # Frequência de Deploy e Entregas
        deploy_freq = converter_numero(dados_lt.get("deploy_frequency_semana"), float) or 0.0
        n_entregas = converter_numero(dados_lt.get("n_entregas"), int) or 0
        n_commits = converter_numero(dados_lt.get("n_commits"), int) or 0

        # Lead Time
        lead_time_commit_h = converter_numero(dados_lt.get("lead_time_commit_h"), float)
        lead_time_release_h = converter_numero(dados_lt.get("lead_time_release_h"), float)

        # CFR e Rework Rate
        cfr_ci_val = converter_numero(dados_runs.get("cfr_ci"), float)
        cfr_entrega_val = converter_numero(dados_lt.get("cfr_entrega"), float)
        rework_rate_val = converter_numero(dados_lt.get("rework_rate"), float)
        cfr_avaliadas = converter_numero(dados_lt.get("cfr_entrega_avaliadas"), int) or 0
        cfr_censuradas = converter_numero(dados_lt.get("cfr_entrega_censuradas"), int) or 0

        # Tempo de Recuperação
        tempo_recup_s = converter_numero(dados_runs.get("tempo_recuperacao_s"), float)
        tempo_recup_h = converter_numero(dados_runs.get("tempo_recuperacao_h"), float)
        recup_censurados = converter_numero(dados_runs.get("recuperacao_proporcao_censurados"), float) or 0.0
        total_runs = converter_numero(dados_runs.get("total_runs"), int) or 0
        total_episodios = converter_numero(dados_runs.get("total_episodios"), int) or 0

        # Releases Ignoradas
        ign_sem_ant = converter_numero(dados_lt.get("ignoradas_sem_anterior"), int) or 0
        ign_404 = converter_numero(dados_lt.get("ignoradas_compare_404"), int) or 0
        ign_sem_commits = converter_numero(dados_lt.get("ignoradas_sem_commits"), int) or 0

        # Classificação DORA de referência (C1 do enunciado): release, lead time (a) e CFR (a)
        classif = classificar_dora(
            cfr=cfr_ci_val,
            tempo_recuperacao_val=tempo_recup_s,
            frequencia=deploy_freq if dados_lt else None,
            lead_time_h=lead_time_release_h,
        )

        linha = {
            "repo": nome_repo,
            "owner": owner,
            "repo_nome": repo_curto,
            "stars": stars,
            "forks": forks,
            "open_issues": open_issues,
            "language": language,
            "contribuidores": contribuidores,
            "idade_anos": idade_anos,
            "idade_dias": idade_dias,
            "created_at": created_at,
            "default_branch": default_branch,
            "deploy_frequency_semana": round(deploy_freq, 4),
            "n_entregas": n_entregas,
            "n_commits": n_commits,
            "lead_time_commit_h": round(lead_time_commit_h, 2) if lead_time_commit_h is not None else None,
            "lead_time_release_h": round(lead_time_release_h, 2) if lead_time_release_h is not None else None,
            "cfr_ci": round(cfr_ci_val, 4) if cfr_ci_val is not None else None,
            "cfr_entrega": round(cfr_entrega_val, 4) if cfr_entrega_val is not None else None,
            "cfr_entrega_avaliadas": cfr_avaliadas,
            "cfr_entrega_censuradas": cfr_censuradas,
            "rework_rate": round(rework_rate_val, 4) if rework_rate_val is not None else None,
            "tempo_recuperacao_s": tempo_recup_s,
            "tempo_recuperacao_h": tempo_recup_h,
            "recuperacao_proporcao_censurados": round(recup_censurados, 4),
            "total_runs": total_runs,
            "total_episodios_recuperacao": total_episodios,
            "ignoradas_sem_anterior": ign_sem_ant,
            "ignoradas_compare_404": ign_404,
            "ignoradas_sem_commits": ign_sem_commits,
            "categoria_dora_frequencia": classif["frequencia"],
            "categoria_dora_lead_time": classif["lead_time"],
            "categoria_dora_cfr": classif["cfr"],
            "categoria_dora_recuperacao": classif["recuperacao"],
            "categoria_dora_geral": classif["geral"],
            "categoria_dora_n_metricas": classif["n_metricas"],
        }
        linhas_dataset.append(linha)

    # Gravação do dataset.csv
    saida.parent.mkdir(parents=True, exist_ok=True)
    if linhas_dataset:
        with open(saida, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(linhas_dataset[0].keys()))
            escritor.writeheader()
            escritor.writerows(linhas_dataset)

    # Geração do MANIFEST.json (Inovação da Issue)
    git_info = obter_info_git()
    sha_dataset = calcular_sha256(saida)

    manifesto = {
        "data_coleta": datetime.now(timezone.utc).isoformat(),
        "janela": {
            "inicio": inicio_janela,
            "fim": fim_janela,
        },
        "git": {
            "commit": git_info["commit"],
            "branch": git_info["branch"],
        },
        "dataset": {
            "caminho": str(saida.as_posix()),
            "sha256": sha_dataset,
            "total_repositorios": len(linhas_dataset),
            "tamanho_bytes": saida.stat().st_size if saida.exists() else 0,
            "colunas_qtd": len(linhas_dataset[0]) if linhas_dataset else 0,
        },
        "fontes_dados": {
            "repos_csv": {
                "caminho": str(caminho_csv.as_posix()),
                "sha256": calcular_sha256(caminho_csv),
            },
            "lead_time_csv": {
                "caminho": str(caminho_lt.as_posix()),
                "sha256": calcular_sha256(caminho_lt),
            },
            "metricas_runs_csv": {
                "caminho": str(caminho_runs.as_posix()),
                "sha256": calcular_sha256(caminho_runs),
            },
        },
        "ambiente": {
            "python_versao": sys.version.split()[0],
            "sistema_operacional": sys.platform,
        },
    }

    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_p, "w", encoding="utf-8") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)

    print(f"Dataset consolidado com {len(linhas_dataset)} repositórios salvo em: {saida}")
    print(f"Manifesto de proveniência e integridade salvo em: {manifest_p}")

    return linhas_dataset


def main():
    parser = argparse.ArgumentParser(description="Consolida métricas DORA no dataset.csv e gera MANIFEST.json.")
    parser.add_argument("--dados", default="data", help="Diretório onde estão os arquivos parciais (default: data)")
    parser.add_argument("--saida", default="data/dataset.csv", help="Caminho do CSV consolidado (default: data/dataset.csv)")
    parser.add_argument("--manifest", default="data/MANIFEST.json", help="Caminho do MANIFEST.json (default: data/MANIFEST.json)")
    parser.add_argument("--inicio", default="2025-01-01", help="Início da janela temporal (default: 2025-01-01)")
    parser.add_argument("--fim", default="2025-12-31", help="Fim da janela temporal (default: 2025-12-31)")

    args = parser.parse_args()
    consolidar_dataset(
        pasta_dados=args.dados,
        caminho_saida=args.saida,
        caminho_manifest=args.manifest,
        inicio_janela=args.inicio,
        fim_janela=args.fim,
    )


if __name__ == "__main__":
    main()
