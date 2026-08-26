# *RQ 05.** Sistemas populares são escritos nas linguagens mais populares?
#  Métrica: linguagem primária de cada repositorio
#busca os 100 repositorios mais populares do GitHub e coleta a linguagem principal de cada um.

import csv
import os
import statistics
import sys
import time
from collections import Counter  
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
TOTAL_REPOS = 100

PAGE_SIZE = 10
DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")
OUTPUT_CSV = os.path.join(DATA_DIR, "rq05_language.csv")
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
        primaryLanguage {
          name
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
            "Erro: defina a variavel de ambiente GITHUB_TOKEN com um personal Access Token do GitHub antes de rodar o script "
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


def fetch_top_repositories(token: str, total: int) -> list[dict]:
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

        if not search["pageInfo"]["hasNextPage"]:
            break
        cursor = search["pageInfo"]["endCursor"]

    return repos

def extract_metric(repo: dict) -> dict:
    # primaryLanguage pode vir None (repos so de dados/config)
    language = repo["primaryLanguage"]
    return{
        "repository": repo["nameWithOwner"],
        "stars": repo["stargazerCount"],
        "primary_language": language["name"] if language else "N/A"
    }

def save_csv(rows: list[dict], path:str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok = True)
    with open(path, "w", newline = "", encoding= "utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["repository", "stars", "primary_language"])
        writer.writeheader()
        writer.writerows(rows)

def print_validation_sample(rows: list[dict], sample_size: int = 10) -> None:
    print(f"\nAmostra de validacao ({sample_size} primeiros repositorios):")
    print(f"{'Repositorio':<40}{'Estrelas':>10}{'Linguagem':>15}")
    for row in rows[:sample_size]:
        print(f"{row['repository']:<40}{row['stars']:>10}{row['primary_language']:>15}")

def print_summary(rows: list[dict]) -> None:
    languages = [row["primary_language"] for row in rows]
    counts = Counter(languages)
    total = len(languages)

    print("\nResumo (RQ05 - linguagem primaria):")
    print(f"Repositorios analisados: {total}")
    print(f"Sem linguagem detectdada (N/A): {counts.get('N/A', 0)}")
    print(f"Total de linguagens distintas: {len([l for l in counts if l != 'N/A'])}")
    print("\nTop 10 linguagens mais frequentes:")
    for lang, count in counts.most_common(10):
        pct = (count / total) * 100
        print(f"    {lang:<20}{count:>5}  ({pct:.1f}%)")

def main() -> None:
    token = get_token()
    repos = fetch_top_repositories(token, TOTAL_REPOS)
    rows = [extract_metric(repo) for repo in repos]

    save_csv(rows, OUTPUT_CSV)
    print(f"CSV salvo em: {OUTPUT_CSV}")

    print_validation_sample(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()