# RQ 07. Sistemas escritos em linguagens mais populares recebem mais
# contribuicao externa, lancam mais releases e sao atualizados com mais
# frequencia? (divide os resultados das RQs 02, 03 e 04 por linguagem)

# Fonte usada para linguagens mais populares foi o GitHub Octoverse 

import csv
import os
import statistics
import sys

DATA_DIR = os.path.join(os.path.dirname(__file__), "dados")
OUTPUT_CSV = os.path.join(DATA_DIR, "rq07_language_breakdown.csv")

RQ02_CSV = os.path.join(DATA_DIR, "rq02_pull_requests.csv")
RQ03_CSV = os.path.join(DATA_DIR, "rq03_releases.csv")
RQ04_CSV = os.path.join(DATA_DIR, "rq04_last_update.csv")
RQ05_CSV = os.path.join(DATA_DIR, "rq05_language.csv")


POPULAR_LANGUAGES = {
    "JavaScript",
    "Python",
    "Java",
    "TypeScript",
    "C#",
    "C++",
    "PHP",
    "Shell",
    "C",
    "Go",
}


def load_csv(path: str) -> dict[str, dict]:
    if not os.path.exists(path):
        sys.exit(
            f"Erro: {path} nao encontrado. Rode o script correspondente "
            "(rq02/rq03/rq04/rq05) antes de rodar a RQ07."
        )

    with open(path, newline="", encoding="utf-8") as f:
        return {row["repository"]: row for row in csv.DictReader(f)}


def merge_datasets() -> list[dict]:
    pull_requests = load_csv(RQ02_CSV)
    releases = load_csv(RQ03_CSV)
    last_update = load_csv(RQ04_CSV)
    languages = load_csv(RQ05_CSV)

    repos = languages.keys() & pull_requests.keys() & releases.keys() & last_update.keys()
    missing = languages.keys() ^ repos
    if missing:
        print(
            f"Aviso: {len(missing)} repositorio(s) presentes em apenas parte "
            "dos CSVs foram ignorados no cruzamento (provavelmente os "
            "scripts rodaram em momentos diferentes)."
        )

    merged = []
    for repo in repos:
        language = languages[repo]["primary_language"]
        merged.append(
            {
                "repository": repo,
                "language": language,
                "total_accepted_pull_requests": int(
                    pull_requests[repo]["total_accepted_pull_requests"]
                ),
                "total_releases": int(releases[repo]["total_releases"]),
                "days_since_last_update": int(
                    last_update[repo]["days_since_last_update"]
                ),
            }
        )
    return merged


def group_by_language(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["language"], []).append(row)
    return groups


def summarize_group(language: str, rows: list[dict]) -> dict:
    prs = [row["total_accepted_pull_requests"] for row in rows]
    releases = [row["total_releases"] for row in rows]
    days = [row["days_since_last_update"] for row in rows]

    return {
        "language": language,
        "is_popular": language in POPULAR_LANGUAGES,
        "repo_count": len(rows),
        "median_pull_requests": statistics.median(prs),
        "median_releases": statistics.median(releases),
        "median_days_since_update": statistics.median(days),
    }


def save_csv(rows: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "language",
        "is_popular",
        "repo_count",
        "median_pull_requests",
        "median_releases",
        "median_days_since_update",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_language_table(summaries: list[dict]) -> None:
    print("\nMetricas por linguagem (ordenado por numero de repositorios):")
    print(
        f"{'Linguagem':<15}{'Repos':>7}{'Popular':>10}"
        f"{'Mediana PRs':>14}{'Mediana Rel.':>14}{'Mediana Dias':>14}"
    )
    for s in sorted(summaries, key=lambda s: s["repo_count"], reverse=True):
        print(
            f"{s['language']:<15}{s['repo_count']:>7}"
            f"{'sim' if s['is_popular'] else 'nao':>10}"
            f"{s['median_pull_requests']:>14}"
            f"{s['median_releases']:>14}"
            f"{s['median_days_since_update']:>14}"
        )


def print_popular_vs_others(rows: list[dict]) -> None:
    popular = [row for row in rows if row["language"] in POPULAR_LANGUAGES]
    others = [
        row
        for row in rows
        if row["language"] not in POPULAR_LANGUAGES and row["language"] != "N/A"
    ]

    print("\nResumo (RQ07 - linguagens populares vs demais):")
    print(f"  Fonte de 'linguagens populares': GitHub Octoverse (top 10)")
    for label, group in (("Populares", popular), ("Outras", others)):
        if not group:
            print(f"  {label}: nenhum repositorio")
            continue
        prs = [row["total_accepted_pull_requests"] for row in group]
        releases = [row["total_releases"] for row in group]
        days = [row["days_since_last_update"] for row in group]
        print(
            f"  {label} (n={len(group)}): "
            f"mediana PRs={statistics.median(prs)}, "
            f"mediana releases={statistics.median(releases)}, "
            f"mediana dias desde update={statistics.median(days)}"
        )


def main() -> None:
    rows = merge_datasets()
    groups = group_by_language(rows)
    summaries = [summarize_group(lang, group_rows) for lang, group_rows in groups.items()]

    save_csv(summaries, OUTPUT_CSV)
    print(f"CSV salvo em: {OUTPUT_CSV}")

    print_language_table(summaries)
    print_popular_vs_others(rows)


if __name__ == "__main__":
    main()
