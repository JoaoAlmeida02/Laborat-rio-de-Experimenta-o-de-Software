import argparse
import csv
from pathlib import Path
import random
from typing import Any, Dict, List, Optional

import pandas as pd

from metricas.datas import para_datetime
from pipeline.github_api import GitHubAPI

RAIZ = Path(__file__).resolve().parents[1]
CAMPOS_PLANILHA = [
    "repo",
    "release_tag",
    "release_data",
    "release_anterior",
    "release_url",
    "compare_url",
    "tipo_projeto",
    "entrega_real",
    "corretiva",
    "observacoes",
]


def amostrar_repositorios(
    caminho_repos: Path | str, n: int = 60, semente: int = 42
) -> List[str]:
    df = pd.read_csv(caminho_repos)
    coluna = "full_name" if "full_name" in df.columns else "repo"
    amostra = df.sample(n=min(n, len(df)), random_state=semente)
    return amostra[coluna].tolist()


def coletar_releases_ordenadas(
    api: GitHubAPI, owner: str, repo: str
) -> List[Dict[str, Any]]:
    entregas = []
    try:
        for r in api.paginar(f"/repos/{owner}/{repo}/releases"):
            if r.get("draft") or not r.get("published_at"):
                continue
            entregas.append(
                {
                    "tag": r.get("tag_name") or "",
                    "data": r.get("published_at") or "",
                    "prerelease": bool(r.get("prerelease")),
                }
            )
    except Exception:
        return []

    return sorted(entregas, key=lambda e: para_datetime(e["data"]))


def construir_linhas_releases(
    repo_full_name: str,
    releases_ordenadas: List[Dict[str, Any]],
    n_amostra: int = 5,
    semente: int = 42,
) -> List[Dict[str, str]]:
    if not releases_ordenadas:
        return []

    owner, repo_name = repo_full_name.split("/", 1)
    n_total = len(releases_ordenadas)

    itens_completos = []
    for idx, rel in enumerate(releases_ordenadas):
        tag = rel["tag"]
        data = rel["data"]
        tag_ant = releases_ordenadas[idx - 1]["tag"] if idx > 0 else "-"
        url_release = f"https://github.com/{owner}/{repo_name}/releases/tag/{tag}"
        url_compare = (
            f"https://github.com/{owner}/{repo_name}/compare/{tag_ant}...{tag}"
            if tag_ant != "-"
            else "-"
        )

        itens_completos.append(
            {
                "repo": repo_full_name,
                "release_tag": tag,
                "release_data": data,
                "release_anterior": tag_ant,
                "release_url": url_release,
                "compare_url": url_compare,
                "tipo_projeto": "",
                "entrega_real": "",
                "corretiva": "",
                "observacoes": "",
            }
        )

    if n_total <= n_amostra:
        return itens_completos

    rng = random.Random(semente + sum(ord(c) for c in repo_full_name))
    indices_sorteados = sorted(rng.sample(range(n_total), n_amostra))
    return [itens_completos[i] for i in indices_sorteados]


def gerar_amostra_completa(
    caminho_repos: Path | str,
    n_repos: int = 60,
    n_releases: int = 5,
    semente: int = 42,
    api: Optional[GitHubAPI] = None,
) -> List[Dict[str, str]]:
    api = api or GitHubAPI()
    repos_sorteados = amostrar_repositorios(caminho_repos, n=n_repos, semente=semente)
    todas_linhas: List[Dict[str, str]] = []

    for n, nome_repo in enumerate(repos_sorteados, 1):
        owner, repo_name = nome_repo.split("/", 1)
        releases = coletar_releases_ordenadas(api, owner, repo_name)
        linhas_repo = construir_linhas_releases(
            nome_repo, releases, n_amostra=n_releases, semente=semente
        )
        todas_linhas.extend(linhas_repo)

    return todas_linhas


def salvar_planilha(caminho: Path | str, linhas: List[Dict[str, str]]) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=CAMPOS_PLANILHA)
        escritor.writeheader()
        escritor.writerows(linhas)


def gerar_planilhas_avaliacao(
    caminho_repos: Path | str,
    pasta_saida: Path | str,
    n_repos: int = 60,
    n_releases: int = 5,
    semente: int = 42,
    api: Optional[GitHubAPI] = None,
    sobrescrever_preenchidos: bool = False,
) -> Dict[str, Path]:
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)

    linhas = gerar_amostra_completa(
        caminho_repos, n_repos=n_repos, n_releases=n_releases, semente=semente, api=api
    )

    caminhos = {
        "template": pasta / "rotulos_template.csv",
        "A": pasta / "rotulos_A.csv",
        "B": pasta / "rotulos_B.csv",
        "C": pasta / "rotulos_C.csv",
    }

    salvar_planilha(caminhos["template"], linhas)

    for letra, pth in [("A", caminhos["A"]), ("B", caminhos["B"]), ("C", caminhos["C"])]:
        if not pth.exists() or sobrescrever_preenchidos:
            salvar_planilha(pth, [dict(l) for l in linhas])

    return caminhos


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", default=str(RAIZ / "data" / "repos.csv"), help="Caminho do CSV de repos")
    parser.add_argument("--saida", default=str(RAIZ / "rotulagem"), help="Diretório de saída")
    parser.add_argument("--n-repos", type=int, default=60, help="Quantidade de repositórios a sortear")
    parser.add_argument("--n-releases", type=int, default=5, help="Máximo de releases por repositório")
    parser.add_argument("--semente", type=int, default=42, help="Semente do sorteio pseudoaleatório")
    parser.add_argument("--sobrescrever", action="store_true", help="Sobrescreve planilhas existentes")
    args = parser.parse_args(argv)

    print(f"Sorteando {args.n_repos} repositórios com seed={args.semente}...")
    caminhos = gerar_planilhas_avaliacao(
        caminho_repos=args.repos,
        pasta_saida=args.saida,
        n_repos=args.n_repos,
        n_releases=args.n_releases,
        semente=args.semente,
        sobrescrever_preenchidos=args.sobrescrever,
    )
    print(f"Planilhas geradas com sucesso em: {args.saida}")
    for k, v in caminhos.items():
        print(f" - {k}: {v}")


if __name__ == "__main__":
    main()
