import csv
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from metricas.datas import dentro_janela, para_datetime
from pipeline.github_api import GitHubAPI, NaoEncontrado

RE_LINK_LAST = re.compile(r'[?&]page=(\d+)[^>]*>;\s*rel="last"')


def extrair_ultimo_link(link_header: Optional[str]) -> Optional[int]:
    """Extrai o numero da ultima pagina a partir do cabecalho Link (rel="last").
    
    Usado para contar o total de contribuidores sem baixar todas as paginas,
    fazendo GET /contributors?per_page=1&anon=true.
    """
    if not link_header:
        return None
    m = RE_LINK_LAST.search(link_header)
    return int(m.group(1)) if m else None


def calcular_idade(created_at: str, data_referencia: Optional[str] = None) -> Dict[str, float]:
    """Calcula a idade do repositorio em dias e anos a partir de created_at.
    
    data_referencia: data final para calculo (ex.: fim da janela '2025-12-31').
    """
    dt_criacao = para_datetime(created_at)
    if data_referencia:
        dt_ref = para_datetime(data_referencia)
    else:
        dt_ref = datetime.now(timezone.utc)

    delta = dt_ref - dt_criacao
    dias = max(delta.total_seconds() / 86400.0, 0.0)
    anos = dias / 365.25
    return {"dias": round(dias, 1), "anos": round(anos, 2)}


def descartar_candidato_estatico(item: dict) -> Tuple[bool, Optional[str]]:
    """Inovacao do grupo: descarta imediatamente forks, repositorios arquivados e espelhos."""
    if item.get("fork"):
        return True, "fork"
    if item.get("archived"):
        return True, "arquivado"
    if item.get("mirror_url"):
        return True, "espelho"
    return False, None


def verificar_actions(api: GitHubAPI, owner: str, repo: str) -> bool:
    """Verifica se o repositorio usa GitHub Actions (GET /actions/workflows).
    
    Descartar total_count == 0 antes de gastar outras chamadas.
    """
    try:
        dados = api.get(f"/repos/{owner}/{repo}/actions/workflows")
        total = dados.get("total_count", 0) if isinstance(dados, dict) else len(dados)
        return total > 0
    except (NaoEncontrado, RuntimeError):
        return False


def contar_releases_janela(
    api: GitHubAPI,
    owner: str,
    repo: str,
    inicio: str,
    fim: str,
    min_esperado: int = 5,
    incluir_prerelease: bool = False,
) -> int:
    """Conta releases publicadas dentro da janela temporal [inicio, fim].
    
    Otimizado para parar assim que atinge min_esperado ou ultrapassa o início da janela.
    """
    total = 0
    pagina = 1
    while pagina <= 10:
        try:
            dados = api.get(f"/repos/{owner}/{repo}/releases", params={"per_page": 100, "page": pagina})
        except Exception:
            break
        if not dados or not isinstance(dados, list):
            break

        passou_do_inicio = False
        for r in dados:
            if r.get("draft"):
                continue
            if r.get("prerelease") and not incluir_prerelease:
                continue
            pub = r.get("published_at")
            if not pub:
                continue
            if dentro_janela(pub, inicio, fim):
                total += 1
            elif para_datetime(pub) < para_datetime(inicio):
                passou_do_inicio = True

        if total >= min_esperado or passou_do_inicio or len(dados) < 100:
            break
        pagina += 1

    return total


def contar_workflow_runs_janela(
    api: GitHubAPI,
    owner: str,
    repo: str,
    inicio: str,
    fim: str,
    default_branch: str = "main",
    min_esperado: int = 50,
) -> int:
    """Conta workflow runs na janela temporal usando a API de actions/runs do GitHub."""
    param_created = f"{inicio}..{fim}"
    # Consulta inicial filtrando branch e push
    try:
        dados = api.get(
            f"/repos/{owner}/{repo}/actions/runs",
            params={"branch": default_branch, "event": "push", "created": param_created, "per_page": 1},
        )
        total = dados.get("total_count", 0) if isinstance(dados, dict) else 0
    except Exception:
        total = 0

    # Se na default_branch não atingiu o mínimo, tenta consulta geral na janela
    if total < min_esperado:
        try:
            dados_geral = api.get(
                f"/repos/{owner}/{repo}/actions/runs",
                params={"created": param_created, "per_page": 1},
            )
            total_geral = dados_geral.get("total_count", 0) if isinstance(dados_geral, dict) else 0
            total = max(total, total_geral)
        except Exception:
            pass

    return total


def verificar_criterio_inclusao(
    api: GitHubAPI,
    owner: str,
    repo: str,
    inicio: str,
    fim: str,
    min_releases: int = 5,
    min_runs: int = 50,
    default_branch: str = "main",
    incluir_prerelease: bool = False,
) -> Tuple[bool, Optional[str], int, int]:
    """Aplica o critério de inclusão: ≥ min_releases e ≥ min_runs na janela.
    
    Retorna (atende, motivo_descarte, n_releases, n_runs).
    """
    n_releases = contar_releases_janela(
        api, owner, repo, inicio, fim, min_esperado=min_releases, incluir_prerelease=incluir_prerelease
    )
    if n_releases < min_releases:
        return False, "poucas_releases", n_releases, 0

    n_runs = contar_workflow_runs_janela(
        api, owner, repo, inicio, fim, default_branch=default_branch, min_esperado=min_runs
    )
    if n_runs < min_runs:
        return False, "poucos_runs", n_releases, n_runs

    return True, None, n_releases, n_runs


def obter_contribuidores_count(api: GitHubAPI, owner: str, repo: str) -> int:
    """Obtem o numero aproximado de contribuidores via per_page=1 e cabecalho Link."""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contributors"
        resp = api._requisitar(url, params={"per_page": 1, "anon": "true"})
        total_paginas = extrair_ultimo_link(resp.headers.get("Link"))
        if total_paginas:
            return total_paginas
        corpo = resp.json()
        return len(corpo) if isinstance(corpo, list) else 1
    except (NaoEncontrado, RuntimeError, Exception):
        return 1


def coletar_metadados_repo(api: GitHubAPI, item: dict, data_referencia: Optional[str] = None) -> dict:
    """Coleta e estrutura os metadados obrigatorios de um repositorio aceito."""
    owner = item["owner"]["login"]
    repo_nome = item["name"]
    created_at = item.get("created_at", "")
    idade = calcular_idade(created_at, data_referencia)
    contribuidores = obter_contribuidores_count(api, owner, repo_nome)

    return {
        "full_name": item.get("full_name", f"{owner}/{repo_nome}"),
        "owner": owner,
        "repo": repo_nome,
        "stars": item.get("stargazers_count", 0),
        "forks": item.get("forks_count", 0),
        "open_issues": item.get("open_issues_count", 0),
        "language": item.get("language") or "Outra",
        "default_branch": item.get("default_branch", "main"),
        "created_at": created_at,
        "idade_anos": idade["anos"],
        "idade_dias": idade["dias"],
        "contribuidores": contribuidores,
    }


class FunilSelecao:
    """Registra as etapas do funil de selecao e exporta para CSV e Markdown."""

    def __init__(self, min_releases: int = 5, min_workflow_runs: int = 50):
        self.min_releases = min_releases
        self.min_workflow_runs = min_workflow_runs
        self.contadores = {
            "1_busca_candidatos": 0,
            "descarte_fork": 0,
            "descarte_arquivado": 0,
            "descarte_espelho": 0,
            "descarte_sem_actions": 0,
            "descarte_criterio_inclusao": 0,
            "descarte_poucas_releases": 0,
            "descarte_poucos_runs": 0,
            "amostra_final": 0,
        }
        self.motivos_descarte = {}

    def registrar_busca(self, quantidade: int):
        self.contadores["1_busca_candidatos"] += quantidade

    def descartar(self, motivo: str):
        chave = f"descarte_{motivo}"
        self.contadores[chave] = self.contadores.get(chave, 0) + 1
        self.motivos_descarte[motivo] = self.motivos_descarte.get(motivo, 0) + 1
        if motivo in ("poucas_releases", "poucos_runs"):
            self.contadores["descarte_criterio_inclusao"] = (
                self.contadores.get("descarte_criterio_inclusao", 0) + 1
            )

    def registrar_etapa(self, etapa: str, quantidade: int):
        self.contadores[etapa] = quantidade

    def gerar_linhas_csv(self) -> List[dict]:
        c1 = self.contadores.get("1_busca_candidatos", 0)
        d_fork = self.contadores.get("descarte_fork", 0)
        c2 = max(c1 - d_fork, 0)
        d_arq = self.contadores.get("descarte_arquivado", 0)
        c3 = max(c2 - d_arq, 0)
        d_esp = self.contadores.get("descarte_espelho", 0)
        c4 = max(c3 - d_esp, 0)
        d_actions = self.contadores.get("descarte_sem_actions", 0)
        c5 = max(c4 - d_actions, 0)
        d_criterio = self.contadores.get("descarte_criterio_inclusao", 0)
        c6 = max(c5 - d_criterio, 0)
        c7 = self.contadores.get("amostra_final", self.contadores.get("4_amostra_final", c6))

        return [
            {"etapa": "1. Candidatos da busca inicial (search/repositories)", "restantes": c1, "descartados": 0, "motivo": "-"},
            {"etapa": "2. Filtro estatico (descarte de forks)", "restantes": c2, "descartados": d_fork, "motivo": "fork = true"},
            {"etapa": "3. Filtro estatico (descarte de arquivados)", "restantes": c3, "descartados": d_arq, "motivo": "archived = true"},
            {"etapa": "4. Filtro estatico (descarte de espelhos)", "restantes": c4, "descartados": d_esp, "motivo": "mirror_url presente"},
            {"etapa": "5. Verificacao de CI/CD (GitHub Actions)", "restantes": c5, "descartados": d_actions, "motivo": "total_count == 0 em /actions/workflows"},
            {"etapa": f"6. ≥ {self.min_releases} releases e ≥ {self.min_workflow_runs} runs na janela", "restantes": c6, "descartados": d_criterio, "motivo": f"< {self.min_releases} releases ou < {self.min_workflow_runs} workflow runs na janela"},
            {"etapa": "7. Amostra final selecionada", "restantes": c7, "descartados": max(c6 - c7, 0), "motivo": "limite_amostra alcancado"},
        ]

    def salvar_csv(self, caminho_csv: Path):
        caminho_csv.parent.mkdir(parents=True, exist_ok=True)
        linhas = self.gerar_linhas_csv()
        with open(caminho_csv, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=["etapa", "restantes", "descartados", "motivo"])
            escritor.writeheader()
            escritor.writerows(linhas)

    def salvar_markdown(self, caminho_md: Path):
        """Inovacao: gera tabela Markdown pronta para colar no artigo SBC."""
        caminho_md.parent.mkdir(parents=True, exist_ok=True)
        linhas = self.gerar_linhas_csv()
        
        md = [
            "# Funil de Selecao de Repositorios (LAB03)",
            "",
            "Tabela de filtragem gerada automaticamente pelo pipeline de selecao com criterios de inclusao.",
            "",
            "| Etapa | Repositorios Restantes | Descartados | Motivo do Descarte |",
            "|:---|:---:|:---:|:---|",
        ]
        for r in linhas:
            md.append(f"| {r['etapa']} | {r['restantes']} | {r['descartados']} | {r['motivo']} |")
        
        caminho_md.write_text("\n".join(md) + "\n", encoding="utf-8")


import time


def iterar_candidatos_por_faixas(
    api: GitHubAPI,
    faixas_estrelas: List[str],
    linguagem: Optional[str] = None,
):
    """Gera candidatos continuamente fatiando por faixas de estrelas e paginando até 10 páginas por faixa."""
    vistos = set()
    for faixa in faixas_estrelas:
        query = faixa
        if linguagem:
            query += f" language:{linguagem}"

        caminho = "/search/repositories"
        pagina = 1
        while pagina <= 10:
            params = {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": pagina}
            try:
                dados = api.get(caminho, params=params)
                itens = dados.get("items", []) if isinstance(dados, dict) else (dados if isinstance(dados, list) else [])
                if not itens:
                    break
                for item in itens:
                    full_name = item.get("full_name")
                    if full_name and full_name not in vistos:
                        vistos.add(full_name)
                        yield item
                if len(itens) < 100:
                    break
                pagina += 1
                if getattr(api, "usar_cache", False):
                    time.sleep(0.5)
            except Exception as err:
                print(f"Aviso na busca da faixa '{faixa}' (pag {pagina}): {err}")
                break


def buscar_candidatos_por_faixas(
    api: GitHubAPI,
    faixas_estrelas: List[str],
    linguagem: Optional[str] = None,
    max_candidatos: Optional[int] = None,
) -> List[dict]:
    """Busca repositorios fatiando por faixas de estrelas para contornar o limite de 1.000 da API."""
    candidatos = []
    for item in iterar_candidatos_por_faixas(api, faixas_estrelas, linguagem):
        candidatos.append(item)
        if max_candidatos and len(candidatos) >= max_candidatos:
            break
    return candidatos


def selecionar_repositorios(api: GitHubAPI, config: dict) -> Tuple[List[dict], FunilSelecao]:
    """Executa o pipeline completo de selecao, funil e coleta de metadados com retomada e criterios de inclusao."""
    limite = config.get("limite_repos", 300)
    faixas = config.get("faixas_estrelas", ["stars:1000..2000", "stars:2000..5000", "stars:>5000"])
    linguagem = config.get("linguagem")
    data_inicio = config.get("inicio", "2025-01-01")
    data_fim = config.get("fim", "2025-12-31")
    min_releases = config.get("min_releases", 5)
    min_workflow_runs = config.get("min_workflow_runs", 50)
    caminho_repos = Path(config.get("repos_csv", "data/repos.csv"))
    caminho_funil_csv = Path(config.get("funil_csv", "data/funil.csv"))
    caminho_funil_md = Path(config.get("funil_md", "data/funil.md"))

    funil = FunilSelecao(min_releases=min_releases, min_workflow_runs=min_workflow_runs)

    selecionados: List[dict] = []
    nomes_vistos: set[str] = set()

    # Retomada: se já existem dados coletados em repos.csv
    if caminho_repos.exists() and not config.get("refazer", False):
        try:
            with open(caminho_repos, "r", encoding="utf-8") as f:
                leitor = csv.DictReader(f)
                for linha in leitor:
                    linha["stars"] = int(linha["stars"])
                    linha["forks"] = int(linha["forks"])
                    linha["open_issues"] = int(linha["open_issues"])
                    linha["idade_anos"] = float(linha["idade_anos"])
                    linha["idade_dias"] = float(linha["idade_dias"])
                    linha["contribuidores"] = int(linha["contribuidores"])
                    selecionados.append(linha)
                    nomes_vistos.add(linha["full_name"])
            print(f"Retomada ativa: {len(selecionados)} repositórios já carregados de {caminho_repos}")
        except Exception as err:
            print(f"Aviso ao ler {caminho_repos} para retomada ({err}). Iniciando coleta normal.")

    if len(selecionados) >= limite:
        print(f"Meta de {limite} repositórios já atingida.")
        funil.registrar_etapa("amostra_final", len(selecionados))
        funil.salvar_csv(caminho_funil_csv)
        funil.salvar_markdown(caminho_funil_md)
        return selecionados[:limite], funil

    print("Iniciando busca contínua de repositórios candidatos com critérios de inclusão...")

    def _salvar_progresso():
        if selecionados:
            caminho_repos.parent.mkdir(parents=True, exist_ok=True)
            with open(caminho_repos, "w", newline="", encoding="utf-8") as f:
                escritor = csv.DictWriter(f, fieldnames=list(selecionados[0].keys()))
                escritor.writeheader()
                escritor.writerows(selecionados)
        funil.registrar_etapa("amostra_final", len(selecionados))
        funil.salvar_csv(caminho_funil_csv)
        funil.salvar_markdown(caminho_funil_md)

    try:
        for item in iterar_candidatos_por_faixas(api, faixas, linguagem):
            if len(selecionados) >= limite:
                break

            funil.registrar_busca(1)
            full_name = item.get("full_name")
            if not full_name or full_name in nomes_vistos:
                continue

            owner = item["owner"]["login"]
            repo_nome = item["name"]

            # 1. Filtros estáticos (fork, archived, mirror)
            descartar_estatico, motivo_estatico = descartar_candidato_estatico(item)
            if descartar_estatico:
                funil.descartar(motivo_estatico)
                continue

            # 2. Filtro de GitHub Actions ativo
            if not verificar_actions(api, owner, repo_nome):
                funil.descartar("sem_actions")
                continue

            # 3. Critério de inclusão: ≥ min_releases e ≥ min_workflow_runs na janela
            default_branch = item.get("default_branch", "main")
            atende, motivo_criterio, n_rel, n_runs = verificar_criterio_inclusao(
                api,
                owner,
                repo_nome,
                inicio=data_inicio,
                fim=data_fim,
                min_releases=min_releases,
                min_runs=min_workflow_runs,
                default_branch=default_branch,
            )
            if not atende:
                funil.descartar(motivo_criterio or "criterio_inclusao")
                continue

            # 4. Coleta metadados
            meta = coletar_metadados_repo(api, item, data_referencia=data_fim)
            selecionados.append(meta)
            nomes_vistos.add(full_name)
            print(
                f"[{len(selecionados)}/{limite}] Aceito: {full_name} "
                f"({meta['stars']} stars, {meta['language']}, {meta['contribuidores']} contrib., "
                f"{n_rel} releases, {n_runs} runs)"
            )

            if len(selecionados) % 10 == 0:
                _salvar_progresso()

    finally:
        _salvar_progresso()

    print(f"Lista final de {len(selecionados)} repositorios salva em: {caminho_repos}")
    print(f"Funil salvo em: {caminho_funil_csv} e {caminho_funil_md}")

    return selecionados, funil
