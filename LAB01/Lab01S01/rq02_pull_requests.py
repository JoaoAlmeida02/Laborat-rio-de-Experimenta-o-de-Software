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
TOTAL_REPOS = 100

# Mantido em 10 seguindo o padrão da RQ03,
# pois páginas maiores podem causar timeout.
PAGE_SIZE = 10

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dados")
OUTPUT_CSV = os.path.join(DATA_DIR, "rq02_pull_requests.csv")

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5


QUERY = """
query ($queryString: String!, $reposPerPage: Int!, $cursor: String) {
    search(
        query: $queryString
        type: REPOSITORY
        first: $reposPerPage
        after: $cursor
    ) {
        repositoryCount
        pageInfo {
            hasNextPage
            endCursor
        }
        nodes {
            ... on Repository {
                nameWithOwner
                stargazerCount
                pullRequests(states: MERGED) {
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
            "Erro: defina a variavel de ambiente GITHUB_TOKEN com um "
            "Personal Access Token do GitHub antes de rodar o script."
        )

    return token


def fetch_page(headers: dict, variables: dict) -> dict:
    """Executa uma pagina da busca, com retry para falhas transitorias.

    Retorna o campo 'search' do payload (nodes + pageInfo).
    """

    for attempt in range(1, MAX_RETRIES + 1):

        try:
            response = requests.post(
                GITHUB_GRAPHQL_URL,
                json={
                    "query": QUERY,
                    "variables": variables
                },
                headers=headers,
                timeout=30,
            )

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ) as exc:

            print(
                f"Falha de rede ({exc.__class__.__name__}) na tentativa "
                f"{attempt}/{MAX_RETRIES}, tentando novamente..."
            )

            time.sleep(
                RETRY_BACKOFF_SECONDS * attempt
            )

            continue

        if response.status_code == 401:
            sys.exit(
                "Erro: GITHUB_TOKEN invalido ou expirado "
                "(401 Unauthorized)."
            )

        if response.status_code == 403:

            remaining = response.headers.get(
                "X-RateLimit-Remaining"
            )

            reset = response.headers.get(
                "X-RateLimit-Reset"
            )

            retry_after = response.headers.get(
                "Retry-After"
            )

            if remaining == "0" and reset:

                reset_time = datetime.fromtimestamp(
                    int(reset),
                    tz=timezone.utc
                )

                sys.exit(
                    "Erro: limite de requisicoes da API do GitHub atingido. "
                    f"O limite reseta em {reset_time.isoformat()} (UTC)."
                )

            if retry_after:

                print(
                    f"Rate limit secundario atingido, "
                    f"aguardando {retry_after}s..."
                )

                time.sleep(
                    int(retry_after)
                )

                continue

            sys.exit(
                f"Erro 403 ao acessar a API: {response.text}"
            )

        if response.status_code >= 500:

            print(
                f"Erro {response.status_code} do servidor na tentativa "
                f"{attempt}/{MAX_RETRIES}, tentando novamente..."
            )

            time.sleep(
                RETRY_BACKOFF_SECONDS * attempt
            )

            continue

        try:
            response.raise_for_status()

        except requests.exceptions.HTTPError as exc:
            sys.exit(
                f"Erro HTTP ao acessar a API: {exc}"
            )

        try:
            payload = response.json()

        except ValueError:
            sys.exit(
                "Erro: resposta da API nao e um JSON valido."
            )

        if "errors" in payload:
            sys.exit(
                f"Erro na API GraphQL: {payload['errors']}"
            )

        return payload["data"]["search"]

    sys.exit(
        f"Erro: falha ao consultar a API apos "
        f"{MAX_RETRIES} tentativas."
    )


def fetch_top_repositories(
    token: str,
    total: int
) -> list[dict]:

    headers = {
        "Authorization": f"Bearer {token}"
    }

    repos: list[dict] = []

    cursor = None

    while len(repos) < total:

        page_size = min(
            PAGE_SIZE,
            total - len(repos)
        )

        variables = {
            "queryString": "stars:>1 sort:stars-desc",
            "reposPerPage": page_size,
            "cursor": cursor,
        }

        search = fetch_page(
            headers,
            variables
        )

        repos.extend(
            search["nodes"]
        )

        if not search["pageInfo"]["hasNextPage"]:
            break

        cursor = search["pageInfo"]["endCursor"]

    return repos


def extract_metric(repo: dict) -> dict:

    return {
        "repository": repo["nameWithOwner"],
        "stars": repo["stargazerCount"],
        "total_accepted_pull_requests": (
            repo["pullRequests"]["totalCount"]
        ),
    }


def save_csv(
    rows: list[dict],
    path: str
) -> None:

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    fieldnames = [
        "repository",
        "stars",
        "total_accepted_pull_requests",
    ]

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


def print_validation_sample(
    rows: list[dict],
    sample_size: int = 10
) -> None:

    print(
        f"\nAmostra de validacao "
        f"({sample_size} primeiros repositorios):"
    )

    print(
        f"{'Repositorio':<40}"
        f"{'Estrelas':>10}"
        f"{'PRs aceitos':>15}"
    )

    for row in rows[:sample_size]:

        print(
            f"{row['repository']:<40}"
            f"{row['stars']:>10}"
            f"{row['total_accepted_pull_requests']:>15}"
        )


def print_summary(
    rows: list[dict]
) -> None:

    pull_requests = [
        row["total_accepted_pull_requests"]
        for row in rows
    ]

    print(
        "\nResumo (RQ02 - pull requests aceitos):"
    )

    print(
        f"  Repositorios analisados: "
        f"{len(pull_requests)}"
    )

    print(
        f"  Mediana: "
        f"{statistics.median(pull_requests)}"
    )

    print(
        f"  Media: "
        f"{statistics.mean(pull_requests):.2f}"
    )

    print(
        f"  Minimo: "
        f"{min(pull_requests)}"
    )

    print(
        f"  Maximo: "
        f"{max(pull_requests)}"
    )


def main() -> None:

    token = get_token()

    repos = fetch_top_repositories(
        token,
        TOTAL_REPOS
    )

    rows = [
        extract_metric(repo)
        for repo in repos
    ]

    save_csv(
        rows,
        OUTPUT_CSV
    )

    print(
        f"CSV salvo em: {OUTPUT_CSV}"
    )

    print_validation_sample(
        rows
    )

    print_summary(
        rows
    )


if __name__ == "__main__":
    main()