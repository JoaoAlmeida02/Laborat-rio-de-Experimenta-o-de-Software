"""Coleta de releases, tags e commits entre entregas, e resumo de lead time.

Uso:
    python -m pipeline.releases --inicio 2025-01-01 --fim 2025-12-31 --repos psf/requests
    python -m pipeline.releases --inicio ... --fim ... --arquivo data/repos.csv --unidade tag

Unidade de entrega ("deploy"):
    release      releases publicadas, sem pré-releases (definição principal)
    release+pre  releases publicadas, incluindo pré-releases (variante RQ 07)
    tag          tags, datadas pelo commit apontado (variante RQ 07)

Saídas (em data/):
    releases/<unidade>/<owner>__<repo>.json   dados brutos por repositório (retomada)
    lead_time_<unidade>.csv                   frequência e lead time por repositório
    releases_ignoradas_<unidade>.csv          entregas fora do lead time, por motivo
"""
import argparse
import csv
import json
from pathlib import Path
from urllib.parse import quote

from metricas.datas import dentro_janela, janela, para_datetime
from metricas.frequencia import deploy_frequency
from metricas.lead_time import contar_ignoradas, lead_time_commit, lead_time_release
from pipeline.github_api import GitHubAPI, NaoEncontrado

RAIZ = Path(__file__).resolve().parents[1]
UNIDADES = ("release", "release+pre", "tag")


def coletar_releases(api, owner, repo, incluir_prerelease=False):
    """Releases publicadas (draft = false), em ordem cronológica."""
    entregas = []
    for r in api.paginar(f"/repos/{owner}/{repo}/releases"):
        if r.get("draft") or not r.get("published_at"):
            continue
        if r.get("prerelease") and not incluir_prerelease:
            continue
        entregas.append({
            "tag": r["tag_name"],
            "data": r["published_at"],
            "prerelease": bool(r.get("prerelease")),
        })
    return sorted(entregas, key=lambda e: para_datetime(e["data"]))


def coletar_tags(api, owner, repo, max_tags=200):
    entregas = []
    for i, t in enumerate(api.paginar(f"/repos/{owner}/{repo}/tags")):
        if i >= max_tags:
            break
        commit = api.get(f"/repos/{owner}/{repo}/commits/{t['commit']['sha']}")
        entregas.append({"tag": t["name"], "data": commit["commit"]["author"]["date"], "prerelease": False})
    return sorted(entregas, key=lambda e: para_datetime(e["data"]))


def coletar_commits_entre(api, owner, repo, base, head):
    caminho = f"/repos/{owner}/{repo}/compare/{quote(base, safe='')}...{quote(head, safe='')}"
    commits, pagina = [], 1
    while True:
        dados = api.get(caminho, {"per_page": 100, "page": pagina})
        lote = dados.get("commits", [])
        commits.extend({
            "sha": c["sha"],
            "data": c["commit"]["author"]["date"],
            # 1ª linha da mensagem: usada pela heurística de release corretiva (S02)
            "mensagem": next(iter((c["commit"].get("message") or "").splitlines()), ""),
        } for c in lote)
        if not lote or len(commits) >= dados.get("total_commits", 0):
            return commits
        pagina += 1


def coletar_entregas(api, owner, repo, unidade):
    if unidade == "tag":
        return coletar_tags(api, owner, repo)
    return coletar_releases(api, owner, repo, incluir_prerelease=(unidade == "release+pre"))


def coletar_repositorio(api, owner, repo, inicio, fim, unidade="release"):
    todas = coletar_entregas(api, owner, repo, unidade)
    entregas = []
    for i, e in enumerate(todas):
        if not dentro_janela(e["data"], inicio, fim):
            continue
        item = dict(e, commits=None, motivo=None)
        if i == 0:
            item["motivo"] = "sem_anterior"
        else:
            try:
                item["commits"] = coletar_commits_entre(api, owner, repo, todas[i - 1]["tag"], e["tag"])
            except NaoEncontrado:
                item["motivo"] = "compare_404"
        entregas.append(item)
    return {"repo": f"{owner}/{repo}", "unidade": unidade, "entregas": entregas}


def resumir(dados, inicio, fim):
    """Uma linha do CSV de lead time para um repositório."""
    entregas = dados["entregas"]
    ignoradas = contar_ignoradas(entregas)
    return {
        "repo": dados["repo"],
        "unidade": dados["unidade"],
        "n_entregas": len(entregas),
        "deploy_frequency_semana": round(deploy_frequency(entregas, inicio, fim), 4),
        "lead_time_release_h": _arredondar(lead_time_release(entregas)),
        "lead_time_commit_h": _arredondar(lead_time_commit(entregas)),
        "n_commits": sum(len(e["commits"] or []) for e in entregas),
        **{f"ignoradas_{k}": v for k, v in ignoradas.items()},
    }


def _arredondar(valor):
    return None if valor is None else round(valor, 2)


def ler_repos(args):
    repos = list(args.repos or [])
    if args.arquivo:
        with open(args.arquivo, newline="", encoding="utf-8") as f:
            for linha in csv.DictReader(f):
                repos.append(linha.get("full_name") or linha.get("repo") or next(iter(linha.values())))
    return repos


def salvar_csv(caminho, linhas):
    if not linhas:
        return
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0]))
        escritor.writeheader()
        escritor.writerows(linhas)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inicio", required=True, help="início da janela (AAAA-MM-DD)")
    parser.add_argument("--fim", required=True, help="fim da janela, inclusivo (AAAA-MM-DD)")
    parser.add_argument("--repos", nargs="*", help="owner/repo ...")
    parser.add_argument("--arquivo", help="CSV com coluna full_name (saída da seleção de repositórios)")
    parser.add_argument("--unidade", choices=UNIDADES, default="release")
    parser.add_argument("--saida", default=str(RAIZ / "data"))
    parser.add_argument("--refazer", action="store_true", help="ignora o que já foi coletado")
    args = parser.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(RAIZ / ".env")

    inicio, fim = janela(args.inicio, args.fim)
    saida = Path(args.saida)
    pasta = saida / "releases" / args.unidade.replace("+", "_")
    pasta.mkdir(parents=True, exist_ok=True)
    api = GitHubAPI()

    resumos = []
    repos = ler_repos(args)
    for n, nome in enumerate(repos, 1):
        owner, repo = nome.strip().split("/")
        arquivo = pasta / f"{owner}__{repo}.json"
        if arquivo.exists() and not args.refazer:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            print(f"[{n}/{len(repos)}] {nome}: já coletado (cache)")
        else:
            try:
                dados = coletar_repositorio(api, owner, repo, inicio, fim, args.unidade)
            except NaoEncontrado:
                print(f"[{n}/{len(repos)}] {nome}: repositório não encontrado, pulando")
                continue
            arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{n}/{len(repos)}] {nome}: {len(dados['entregas'])} entregas na janela")
        resumos.append(resumir(dados, inicio, fim))

    sufixo = args.unidade.replace("+", "_")
    salvar_csv(saida / f"lead_time_{sufixo}.csv", resumos)
    salvar_csv(saida / f"releases_ignoradas_{sufixo}.csv", [
        {"repo": r["repo"], **{k: v for k, v in r.items() if k.startswith("ignoradas_")}} for r in resumos
    ])
    print(f"Resumo salvo em {saida / f'lead_time_{sufixo}.csv'}")


if __name__ == "__main__":
    main()
