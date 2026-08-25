# Lab01S03 - mesmo script unico da Lab01S02, com a RQ08 adicionada.
#
# Junta numa unica consulta GraphQL os campos que RQ01, RQ02, RQ03, RQ04,
# RQ05 e RQ06 buscavam separadamente na Lab01S01, e pagina ate 1000
# repositorios (limite maximo da Search API do GitHub, que coincide com o
# que o enunciado pede).
#
# RQ08 (nova, bonus): estrelas correlacionam com engajamento real, ou so
# com fama? Estrela e "endosso passivo" (favoritei, nao necessariamente
# uso), fork e "reuso ativo" (vou construir em cima). Comparamos
# stargazerCount com forkCount para ver se repositorios muito populares por
# hype tem uma proporcao estrela/fork bem diferente de bibliotecas
# realmente usadas em producao.


import csv
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
TOTAL_REPOS = 1000

# A query combina 4 connection counts caras (pullRequests, releases,
# issuesOpen, issuesClosed) no mesmo node - mais caro para o backend do
# GitHub resolver do que so releases.totalCount
PAGE_SIZE = 10

DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")
OUTPUT_CSV = os.path.join(DATA_DIR, "repositorios_1000.csv")
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5

QUERY = """
query ($queryString: String!, $reposPerPage: Int!, $cursor: String) {
  search(query: $queryString, type: REPOSITORY, first: $reposPerPage, after: $cursor) {
    repositoryCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        nameWithOwner
        stargazerCount
        forkCount
        createdAt
        pushedAt
        primaryLanguage {
          name
        }
        pullRequests(states: MERGED) {
          totalCount
        }
        releases {
          totalCount
        }
        issuesOpen: issues(states: OPEN) {
          totalCount
        }
        issuesClosed: issues(states: CLOSED) {
          totalCount
        }
      }
    }
  }
}
"""


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit(
            "Erro: defina a variavel de ambiente GITHUB_TOKEN (ou crie um "
            ".env em LAB01/Lab01S03/ com GITHUB_TOKEN=...) antes de rodar o "
            "script."
        )
    return token


def fetch_page(headers: dict, variables: dict) -> dict:
    """Executa uma pagina da busca, com retry para falhas transitorias.

    Retorna o campo "search" do payload (nodes + pageInfo).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                json={"query": QUERY, "variables": variables},
                headers=headers,
                timeout=30,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            print(
                f"Falha de rede ({exc.__class__.__name__}) na tentativa "
                f"{attempt}/{MAX_RETRIES}, tentando novamente..."
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue

        if response.status_code == 401:
            sys.exit("Erro: GITHUB_TOKEN invalido ou expirado (401 Unauthorized).")

        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            retry_after = response.headers.get("Retry-After")
            if remaining == "0" and reset:
                reset_time = datetime.fromtimestamp(int(reset), tz=timezone.utc)
                sys.exit(
                    "Erro: limite de requisicoes da API do GitHub atingido. "
                    f"O limite reseta em {reset_time.isoformat()} (UTC)."
                )
            if retry_after:
                print(f"Rate limit secundario atingido, aguardando {retry_after}s...")
                time.sleep(int(retry_after))
                continue
            sys.exit(f"Erro 403 ao acessar a API: {response.text}")

        if response.status_code >= 500:
            print(
                f"Erro {response.status_code} do servidor na tentativa "
                f"{attempt}/{MAX_RETRIES}, tentando novamente..."
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
            continue

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            sys.exit(f"Erro HTTP ao acessar a API: {exc}")

        try:
            payload = response.json()
        except ValueError:
            sys.exit("Erro: resposta da API nao e um JSON valido.")

        if "errors" in payload:
            sys.exit(f"Erro na API GraphQL: {payload['errors']}")

        return payload["data"]["search"]

    sys.exit(f"Erro: falha ao consultar a API apos {MAX_RETRIES} tentativas.")


def fetch_all_repositories(token: str, total: int) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    repos: list[dict] = []
    cursor = None

    while len(repos) < total:
        page_size = min(PAGE_SIZE, total - len(repos))
        variables = {
            "queryString": "stars:>1 sort:stars-desc",
            "reposPerPage": page_size,
            "cursor": cursor,
        }

        search = fetch_page(headers, variables)
        repos.extend(search["nodes"])
        print(f"  {len(repos)}/{total} repositorios coletados...", end="\r")

        if not search["pageInfo"]["hasNextPage"]:
            break
        cursor = search["pageInfo"]["endCursor"]

    print()
    return repos


def extract_metric(repo: dict, now: datetime) -> dict:
    created_at = datetime.strptime(repo["createdAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    pushed_at = datetime.strptime(repo["pushedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    age_days = (now - created_at).days
    language = repo["primaryLanguage"]

    issues_open = repo["issuesOpen"]["totalCount"]
    issues_closed = repo["issuesClosed"]["totalCount"]
    total_issues = issues_open + issues_closed
    issues_closed_ratio = (
        round(issues_closed / total_issues, 3) if total_issues > 0 else "N/A"
    )

    stars = repo["stargazerCount"]
    forks = repo["forkCount"]
    stars_to_forks_ratio = round(stars / forks, 2) if forks > 0 else "N/A"

    return {
        "repository": repo["nameWithOwner"],
        "stars": stars,
        "forks": forks,
        "stars_to_forks_ratio": stars_to_forks_ratio,
        "created_at": repo["createdAt"],
        "age_days": age_days,
        "age_years": round(age_days / 365.25, 2),
        "total_accepted_pull_requests": repo["pullRequests"]["totalCount"],
        "total_releases": repo["releases"]["totalCount"],
        "pushed_at": repo["pushedAt"],
        "days_since_last_update": (now - pushed_at).days,
        "primary_language": language["name"] if language else "N/A",
        "issues_open": issues_open,
        "issues_closed": issues_closed,
        "issues_closed_ratio": issues_closed_ratio,
    }


FIELDNAMES = [
    "repository",
    "stars",
    "forks",
    "stars_to_forks_ratio",
    "created_at",
    "age_days",
    "age_years",
    "total_accepted_pull_requests",
    "total_releases",
    "pushed_at",
    "days_since_last_update",
    "primary_language",
    "issues_open",
    "issues_closed",
    "issues_closed_ratio",
]


def save_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def print_validation_sample(rows: list[dict], sample_size: int = 10) -> None:
    print(f"\nAmostra de validacao ({sample_size} primeiros repositorios):")
    print(
        f"{'Repositorio':<38}{'Estrelas':>9}{'Forks':>9}{'Idade(d)':>9}{'PRs':>8}"
        f"{'Rel.':>6}{'Dias upd':>9}{'Linguagem':>13}{'Issues%':>9}"
    )
    for row in rows[:sample_size]:
        print(
            f"{row['repository']:<38}{row['stars']:>9}{row['forks']:>9}"
            f"{row['age_days']:>9}"
            f"{row['total_accepted_pull_requests']:>8}{row['total_releases']:>6}"
            f"{row['days_since_last_update']:>9}{row['primary_language']:>13}"
            f"{str(row['issues_closed_ratio']):>9}"
        )


def print_summary(rows: list[dict]) -> None:
    def stats(label: str, values: list[float]) -> None:
        print(
            f"  {label}: mediana={statistics.median(values):.2f} "
            f"media={statistics.mean(values):.2f} "
            f"min={min(values)} max={max(values)}"
        )

    print(f"\nResumo geral ({len(rows)} repositorios):")

    print("\n[RQ01] Idade (dias):")
    stats("age_days", [row["age_days"] for row in rows])

    print("\n[RQ02] Pull requests aceitos:")
    stats(
        "total_accepted_pull_requests",
        [row["total_accepted_pull_requests"] for row in rows],
    )

    print("\n[RQ03] Total de releases:")
    stats("total_releases", [row["total_releases"] for row in rows])

    print("\n[RQ04] Dias desde a ultima atualizacao:")
    stats("days_since_last_update", [row["days_since_last_update"] for row in rows])

    print("\n[RQ05] Linguagem primaria (top 10):")
    languages = Counter(row["primary_language"] for row in rows)
    na_lang = languages.get("N/A", 0)
    print(f"  Sem linguagem detectada (N/A): {na_lang}")
    for lang, count in languages.most_common(10):
        print(f"    {lang:<20}{count:>5} ({count / len(rows) * 100:.1f}%)")

    print("\n[RQ06] Razao issues fechadas/total:")
    ratios = [row["issues_closed_ratio"] for row in rows if row["issues_closed_ratio"] != "N/A"]
    na_ratio = len(rows) - len(ratios)
    print(f"  Sem nenhuma issue (N/A): {na_ratio}")
    if ratios:
        stats("issues_closed_ratio", ratios)

    print("\n[RQ08] Razao estrelas/forks (endosso passivo vs reuso ativo):")
    stats("forks", [row["forks"] for row in rows])
    fork_ratios = [row["stars_to_forks_ratio"] for row in rows if row["stars_to_forks_ratio"] != "N/A"]
    na_fork_ratio = len(rows) - len(fork_ratios)
    print(f"  Sem nenhum fork (N/A): {na_fork_ratio}")
    if fork_ratios:
        stats("stars_to_forks_ratio", fork_ratios)


def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else TOTAL_REPOS

    token = get_token()
    print(f"Buscando {total} repositorios...")
    repos = fetch_all_repositories(token, total)

    now = datetime.now(timezone.utc)
    rows = [extract_metric(repo, now) for repo in repos]

    save_csv(rows, OUTPUT_CSV)
    print(f"CSV salvo em: {OUTPUT_CSV}")

    print_validation_sample(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
