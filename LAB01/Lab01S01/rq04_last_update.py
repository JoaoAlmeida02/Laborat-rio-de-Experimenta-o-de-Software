#RQ04 - Sistemas populares sao atualizados com frequencia?
#Metrica: tempo ate a ultima atualizacao.

#Busca os 100 repositorios com mais estrelas no GitHub e coleta a data do ultimo push (pushedAt) de cada um,
#convertendo para dias desde a ultima atualizacao.

import csv
import os
import statistics
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
REPOS_PER_PAGE = 100
DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")
OUTPUT_CSV = os.path.join(DATA_DIR, "rq04_last_update.csv")
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
        pushedAt
      }
    }
  }
}
"""


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit(
            "Erro: defina a variavel de ambiente GITHUB_TOKEN com um "
            "Personal Access Token do GitHub antes de rodar o script."
        )
    return token


def fetch_top_repositories(token: str, count: int) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    variables = {
        "queryString": "stars:>1 sort:stars-desc",
        "reposPerPage": count,
        "cursor": None,
    }

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

        return payload["data"]["search"]["nodes"]

    sys.exit(f"Erro: falha ao consultar a API apos {MAX_RETRIES} tentativas.")


def extract_metric(repo: dict, now: datetime) -> dict:
    pushed_at = datetime.strptime(repo["pushedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    days_since_update = (now - pushed_at).days

    return {
        "repository": repo["nameWithOwner"],
        "stars": repo["stargazerCount"],
        "pushed_at": repo["pushedAt"],
        "days_since_last_update": days_since_update,
    }


def save_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["repository", "stars", "pushed_at", "days_since_last_update"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_validation_sample(rows: list[dict], sample_size: int = 10) -> None:
    print(f"\nAmostra de validacao ({sample_size} primeiros repositorios):")
    print(f"{'Repositorio':<40}{'Estrelas':>10}{'Ultimo push':>22}{'Dias':>8}")
    for row in rows[:sample_size]:
        print(
            f"{row['repository']:<40}{row['stars']:>10}"
            f"{row['pushed_at']:>22}{row['days_since_last_update']:>8}"
        )


def print_summary(rows: list[dict]) -> None:
    days = [row["days_since_last_update"] for row in rows]
    print("\nResumo (RQ04 - dias desde a ultima atualizacao):")
    print(f"  Repositorios analisados: {len(days)}")
    print(f"  Mediana: {statistics.median(days)}")
    print(f"  Media: {statistics.mean(days):.2f}")
    print(f"  Minimo: {min(days)}")
    print(f"  Maximo: {max(days)}")


def main() -> None:
    token = get_token()
    repos = fetch_top_repositories(token, REPOS_PER_PAGE)
    now = datetime.now(timezone.utc)
    rows = [extract_metric(repo, now) for repo in repos]

    save_csv(rows, OUTPUT_CSV)
    print(f"CSV salvo em: {OUTPUT_CSV}")

    print_validation_sample(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()
