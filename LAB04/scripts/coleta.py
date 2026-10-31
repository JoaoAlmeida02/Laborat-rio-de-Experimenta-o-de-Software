import argparse
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
CONCLUSOES_VALIDAS = {"success", "failure", "timed_out"}
CONCLUSOES_FALHA = {"failure", "timed_out"}


def cabecalhos():
    load_dotenv(BASE / ".env")
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN não encontrado: crie LAB04/.env com GITHUB_TOKEN=seu_token")
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }


def buscar_runs(repo, branch, evento, n):
    sessao = requests.Session()
    sessao.headers.update(cabecalhos())
    runs, pagina = [], 1
    while len(runs) < n:
        resp = sessao.get(
            f"{API}/repos/{repo}/actions/runs",
            params={"branch": branch, "event": evento, "status": "completed", "per_page": 100, "page": pagina},
            timeout=30,
        )
        if resp.status_code == 401:
            raise RuntimeError("Token inválido ou expirado: gere outro e atualize GITHUB_TOKEN no .env")
        if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
            raise RuntimeError("Limite da API atingido: aguarde a renovação do limite e tente novamente")
        resp.raise_for_status()
        lote = resp.json()["workflow_runs"]
        if not lote:
            break
        runs += [r for r in lote if r["conclusion"] in CONCLUSOES_VALIDAS]
        pagina += 1
    return runs[:n]


def salvar_csv(runs, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "data", "workflow", "conclusao", "falha"])
        for r in sorted(runs, key=lambda r: r["created_at"]):
            w.writerow([r["id"], r["created_at"], r["name"], r["conclusion"], int(r["conclusion"] in CONCLUSOES_FALHA)])


def salvar_resumo(runs, args, destino):
    n = len(runs)
    falhas = sum(r["conclusion"] in CONCLUSOES_FALHA for r in runs)
    datas = sorted(r["created_at"][:10] for r in runs)
    workflows = sorted({r["name"] for r in runs})
    texto = f"""# Resumo da coleta

| Campo | Valor |
|---|---|
| Repositório | [{args.repo}](https://github.com/{args.repo}/actions) |
| Branch | `{args.branch}` |
| Evento | `{args.evento}` |
| Workflows | {", ".join(workflows)} |
| Período | {datas[0]} a {datas[-1]} |
| Data da coleta | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC |
| Execuções (n) | {n} |
| Falhas | {falhas} |
| Taxa de falha observada | {falhas / n:.2%} |
"""
    destino.write_text(texto, encoding="utf-8")
    return n, falhas


def main():
    p = argparse.ArgumentParser(description="Coleta execuções de CI do GitHub Actions")
    p.add_argument("--repo", default="pytest-dev/pytest")
    p.add_argument("--branch", default="main")
    p.add_argument("--evento", default="push")
    p.add_argument("--n", type=int, default=300)
    args = p.parse_args()

    runs = buscar_runs(args.repo, args.branch, args.evento, args.n)
    if not runs:
        raise SystemExit("Nenhuma execução encontrada com esses filtros")

    salvar_csv(runs, BASE / "dados" / "ci_runs.csv")
    n, falhas = salvar_resumo(runs, args, BASE / "dados" / "resumo_coleta.md")
    print(f"{args.repo}: {n} execuções, {falhas} falhas, taxa = {falhas / n:.2%}")
    print(f"Salvo em {BASE / 'dados'}")


if __name__ == "__main__":
    main()
