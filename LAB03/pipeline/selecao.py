import csv
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

from metricas.datas import para_datetime
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
        total = dados.get("total_count", 0)
        return total > 0
    except (NaoEncontrado, RuntimeError):
        return False


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

    def __init__(self):
        self.contadores = {
            "1_busca_candidatos": 0,
            "descarte_fork": 0,
            "descarte_arquivado": 0,
            "descarte_espelho": 0,
            "2_ativos_e_originais": 0,
            "descarte_sem_actions": 0,
            "3_com_actions": 0,
            "4_amostra_final": 0,
        }
        self.motivos_descarte = {}

    def registrar_busca(self, quantidade: int):
        self.contadores["1_busca_candidatos"] += quantidade

    def descartar(self, motivo: str):
        chave = f"descarte_{motivo}"
        self.contadores[chave] = self.contadores.get(chave, 0) + 1
        self.motivos_descarte[motivo] = self.motivos_descarte.get(motivo, 0) + 1

    def registrar_etapa(self, etapa: str, quantidade: int):
        self.contadores[etapa] = quantidade

    def gerar_linhas_csv(self) -> List[dict]:
        c1 = self.contadores.get("1_busca_candidatos", 0)
        d_fork = self.contadores.get("descarte_fork", 0)
        d_arq = self.contadores.get("descarte_arquivado", 0)
        d_esp = self.contadores.get("descarte_espelho", 0)
        c2 = max(c1 - d_fork - d_arq - d_esp, 0)
        d_actions = self.contadores.get("descarte_sem_actions", 0)
        c3 = max(c2 - d_actions, 0)
        c4 = self.contadores.get("4_amostra_final", c3)

        return [
            {"etapa": "1. Candidatos da busca inicial (search/repositories)", "restantes": c1, "descartados": 0, "motivo": "-"},
            {"etapa": "2. Filtro estatico (descarte de forks)", "restantes": c1 - d_fork, "descartados": d_fork, "motivo": "fork = true"},
            {"etapa": "3. Filtro estatico (descarte de arquivados e mirrors)", "restantes": c2, "descartados": d_arq + d_esp, "motivo": "archived = true ou mirror"},
            {"etapa": "4. Verificacao de CI/CD (GitHub Actions)", "restantes": c3, "descartados": d_actions, "motivo": "total_count == 0 em /actions/workflows"},
            {"etapa": "5. Amostra final selecionada", "restantes": c4, "descartados": max(c3 - c4, 0), "motivo": "limite_amostra alcancado"},
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
            "Tabela de filtragem gerada automaticamente pelo pipeline de selecao.",
            "",
            "| Etapa | Repositorios Restantes | Descartados | Motivo do Descarte |",
            "|:---|:---:|:---:|:---|",
        ]
        for r in linhas:
            md.append(f"| {r['etapa']} | {r['restantes']} | {r['descartados']} | {r['motivo']} |")
        
        caminho_md.write_text("\n".join(md) + "\n", encoding="utf-8")


def buscar_candidatos_por_faixas(api: GitHubAPI, faixas_estrelas: List[str], linguagem: Optional[str] = None) -> List[dict]:
    """Busca repositorios fatiando por faixas de estrelas para contornar o limite de 1.000 da API."""
    candidatos = []
    vistos = set()

    for faixa in faixas_estrelas:
        query = faixa
        if linguagem:
            query += f" language:{linguagem}"

        caminho = "/search/repositories"
        pagina = 1
        while pagina <= 10:  # O Search API do GitHub limita a 1000 resultados (10 pags de 100)
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
                        candidatos.append(item)
                if len(itens) < 100:
                    break
                pagina += 1
            except Exception as err:
                print(f"Aviso na busca da faixa '{faixa}' (pag {pagina}): {err}")
                break

    return candidatos


def selecionar_repositorios(api: GitHubAPI, config: dict) -> Tuple[List[dict], FunilSelecao]:
    """Executa o pipeline completo de selecao, funil e coleta de metadados."""
    limite = config.get("limite_repos", 100)
    faixas = config.get("faixas_estrelas", ["stars:>1000"])
    linguagem = config.get("linguagem")
    data_fim = config.get("fim", "2025-12-31")

    funil = FunilSelecao()
    print("Iniciando busca de repositorios candidatos por faixas de estrelas...")
    candidatos = buscar_candidatos_por_faixas(api, faixas, linguagem)
    funil.registrar_busca(len(candidatos))
    print(f"Total de candidatos obtidos na busca: {len(candidatos)}")

    selecionados = []
    for item in candidatos:
        if len(selecionados) >= limite:
            break

        full_name = item.get("full_name")
        owner = item["owner"]["login"]
        repo_nome = item["name"]

        # Filtros estaticos (Inovacao: fork, archived, mirror)
        descartar_estatico, motivo_estatico = descartar_candidato_estatico(item)
        if descartar_estatico:
            funil.descartar(motivo_estatico)
            continue

        # Filtro de GitHub Actions
        if not verificar_actions(api, owner, repo_nome):
            funil.descartar("sem_actions")
            continue

        # Coleta metadados
        meta = coletar_metadados_repo(api, item, data_referencia=data_fim)
        selecionados.append(meta)
        print(f"[{len(selecionados)}/{limite}] Aceito: {full_name} ({meta['stars']} stars, {meta['language']}, {meta['contribuidores']} contrib.)")

    funil.registrar_etapa("4_amostra_final", len(selecionados))

    caminho_repos = Path(config.get("repos_csv", "data/repos.csv"))
    caminho_repos.parent.mkdir(parents=True, exist_ok=True)
    if selecionados:
        with open(caminho_repos, "w", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=list(selecionados[0].keys()))
            escritor.writeheader()
            escritor.writerows(selecionados)
        print(f"Lista de {len(selecionados)} repositorios salva em: {caminho_repos}")

    caminho_funil_csv = Path(config.get("funil_csv", "data/funil.csv"))
    caminho_funil_md = Path(config.get("funil_md", "data/funil.md"))
    funil.salvar_csv(caminho_funil_csv)
    funil.salvar_markdown(caminho_funil_md)
    print(f"Funil salvo em: {caminho_funil_csv} e {caminho_funil_md}")

    return selecionados, funil
