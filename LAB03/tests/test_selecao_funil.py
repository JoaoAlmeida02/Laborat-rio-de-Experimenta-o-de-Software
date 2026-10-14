from pathlib import Path
import tempfile
import pytest

from pipeline.config_parser import _parse_yaml_simples, carregar_config
from pipeline.selecao import (
    FunilSelecao,
    buscar_candidatos_por_faixas,
    calcular_idade,
    coletar_metadados_repo,
    contar_releases_janela,
    contar_workflow_runs_janela,
    descartar_candidato_estatico,
    extrair_ultimo_link,
    selecionar_repositorios,
    verificar_actions,
    verificar_criterio_inclusao,
)


class MockAPI:
    def __init__(
        self,
        workflows_count=1,
        link_header=None,
        contributors_list=None,
        search_items=None,
        releases_list=None,
        runs_count=60,
    ):
        self.workflows_count = workflows_count
        self.link_header = link_header
        self.contributors_list = contributors_list or [{"id": 1}]
        self.search_items = search_items or []
        self.releases_list = (
            releases_list
            if releases_list is not None
            else [
                {"published_at": f"2025-0{i}-15T00:00:00Z", "draft": False, "prerelease": False}
                for i in range(1, 7)
            ]
        )
        self.runs_count = runs_count

    def get(self, caminho, params=None):
        if "search/repositories" in caminho:
            return {"total_count": len(self.search_items), "items": self.search_items}
        if "actions/workflows" in caminho:
            return {"total_count": self.workflows_count, "workflows": []}
        if "actions/runs" in caminho:
            return {"total_count": self.runs_count, "workflow_runs": []}
        if "/releases" in caminho:
            return self.releases_list
        return {}

    def paginar(self, caminho, params=None):
        if "search/repositories" in caminho:
            yield from self.search_items
        else:
            yield from []

    def _requisitar(self, url, params=None):
        class MockResp:
            def __init__(self, headers, json_data):
                self.headers = headers
                self._json = json_data
            def json(self):
                return self._json
        return MockResp({"Link": self.link_header}, self.contributors_list)


# --- Testes de Parser do cabecalho Link ---

def test_extrair_ultimo_link_com_sucesso():
    header = (
        '<https://api.github.com/repositories/123/contributors?per_page=1&anon=true&page=2>; rel="next", '
        '<https://api.github.com/repositories/123/contributors?per_page=1&anon=true&page=145>; rel="last"'
    )
    assert extrair_ultimo_link(header) == 145


def test_extrair_ultimo_link_sem_rel_last():
    header = '<https://api.github.com/repositories/123/contributors?per_page=1&anon=true&page=2>; rel="next"'
    assert extrair_ultimo_link(header) is None


def test_extrair_ultimo_link_nulo_ou_vazio():
    assert extrair_ultimo_link(None) is None
    assert extrair_ultimo_link("") is None


# --- Testes de Calculo de Idade ---

def test_calcular_idade_anos_e_dias():
    idade = calcular_idade("2020-01-01T00:00:00Z", data_referencia="2025-01-01T00:00:00Z")
    assert idade["anos"] == 5.0
    assert idade["dias"] == 1827.0


def test_calcular_idade_data_recente():
    idade = calcular_idade("2025-01-01T00:00:00Z", data_referencia="2025-01-02T00:00:00Z")
    assert idade["dias"] == 1.0
    assert idade["anos"] == 0.0


# --- Testes de Filtro Estatico (Inovacao) ---

def test_descartar_candidato_fork():
    item = {"fork": True, "archived": False, "mirror_url": None}
    descartar, motivo = descartar_candidato_estatico(item)
    assert descartar is True
    assert motivo == "fork"


def test_descartar_candidato_arquivado():
    item = {"fork": False, "archived": True, "mirror_url": None}
    descartar, motivo = descartar_candidato_estatico(item)
    assert descartar is True
    assert motivo == "arquivado"


def test_descartar_candidato_espelho():
    item = {"fork": False, "archived": False, "mirror_url": "https://git.example.com/mirror"}
    descartar, motivo = descartar_candidato_estatico(item)
    assert descartar is True
    assert motivo == "espelho"


def test_manter_candidato_valido():
    item = {"fork": False, "archived": False, "mirror_url": None}
    descartar, motivo = descartar_candidato_estatico(item)
    assert descartar is False
    assert motivo is None


# --- Testes de Verificacao de Actions ---

def test_verificar_actions_com_workflows():
    api = MockAPI(workflows_count=3)
    assert verificar_actions(api, "owner", "repo") is True


def test_verificar_actions_sem_workflows():
    api = MockAPI(workflows_count=0)
    assert verificar_actions(api, "owner", "repo") is False


# --- Testes de Metadados ---

def test_coletar_metadados_repo():
    link_header = '<https://api.github.com/repositories/123/contributors?per_page=1&anon=true&page=88>; rel="last"'
    api = MockAPI(workflows_count=2, link_header=link_header)
    item = {
        "full_name": "astral-sh/ruff",
        "name": "ruff",
        "owner": {"login": "astral-sh"},
        "stargazers_count": 35000,
        "forks_count": 1200,
        "open_issues_count": 300,
        "language": "Rust",
        "default_branch": "main",
        "created_at": "2022-08-01T00:00:00Z",
    }
    meta = coletar_metadados_repo(api, item, data_referencia="2025-01-01T00:00:00Z")
    assert meta["full_name"] == "astral-sh/ruff"
    assert meta["stars"] == 35000
    assert meta["language"] == "Rust"
    assert meta["contribuidores"] == 88
    assert meta["idade_anos"] > 2.0


# --- Testes do Funil de Selecao ---

def test_funil_registro_e_exportacao():
    funil = FunilSelecao(min_releases=5, min_workflow_runs=50)
    funil.registrar_busca(500)
    funil.descartar("fork")
    funil.descartar("fork")
    funil.descartar("arquivado")
    funil.descartar("sem_actions")
    funil.descartar("poucas_releases")
    funil.descartar("poucos_runs")
    funil.registrar_etapa("amostra_final", 100)

    linhas = funil.gerar_linhas_csv()
    assert len(linhas) == 7
    assert linhas[0]["restantes"] == 500
    assert linhas[5]["etapa"] == "6. ≥ 5 releases e ≥ 50 runs na janela"
    assert linhas[5]["descartados"] == 2
    assert linhas[6]["etapa"] == "7. Amostra final selecionada"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        csv_path = tmp / "funil.csv"
        md_path = tmp / "funil.md"

        funil.salvar_csv(csv_path)
        funil.salvar_markdown(md_path)

        assert csv_path.exists()
        assert md_path.exists()
        assert "Funil de Selecao" in md_path.read_text(encoding="utf-8")


# --- Testes de Selecao Completa com Mock ---

def test_selecionar_repositorios_pipeline_completo():
    candidatos_mock = [
        {"full_name": "org/repo1", "name": "repo1", "owner": {"login": "org"}, "stargazers_count": 5000, "fork": False, "archived": False, "mirror_url": None, "created_at": "2021-01-01T00:00:00Z"},
        {"full_name": "org/repo-fork", "name": "repo-fork", "owner": {"login": "org"}, "stargazers_count": 4000, "fork": True, "archived": False, "mirror_url": None, "created_at": "2021-01-01T00:00:00Z"},
        {"full_name": "org/repo-no-actions", "name": "repo-no-actions", "owner": {"login": "org"}, "stargazers_count": 3000, "fork": False, "archived": False, "mirror_url": None, "created_at": "2021-01-01T00:00:00Z"},
    ]

    class MockSearchAPI(MockAPI):
        def get(self, caminho, params=None):
            if "search/repositories" in caminho:
                return {"total_count": len(self.search_items), "items": self.search_items}
            if "repo-no-actions/actions/workflows" in caminho:
                return {"total_count": 0}
            if "/releases" in caminho:
                return self.releases_list
            if "actions/runs" in caminho:
                return {"total_count": self.runs_count, "workflow_runs": []}
            return {"total_count": 2}

    api = MockSearchAPI(search_items=candidatos_mock)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = {
            "limite_repos": 10,
            "faixas_estrelas": ["stars:>1000"],
            "fim": "2025-12-31",
            "repos_csv": str(tmp / "repos.csv"),
            "funil_csv": str(tmp / "funil.csv"),
            "funil_md": str(tmp / "funil.md"),
        }
        selecionados, funil = selecionar_repositorios(api, cfg)

        assert len(selecionados) == 1
        assert selecionados[0]["full_name"] == "org/repo1"
        assert Path(cfg["repos_csv"]).exists()
        assert Path(cfg["funil_csv"]).exists()
        assert Path(cfg["funil_md"]).exists()


# --- Testes do Parser de Config YAML ---

def test_parse_yaml_simples():
    yaml_txt = """
    janela:
      inicio: "2025-01-01"
      fim: "2025-12-31"
    amostra:
      limite_repos: 100
      min_releases: 5
    busca:
      faixas_estrelas:
        - "stars:1000..2000"
        - "stars:>5000"
    """
    res = _parse_yaml_simples(yaml_txt)
    assert res["janela"]["inicio"] == "2025-01-01"
    assert res["amostra"]["limite_repos"] == 100
    assert len(res["busca"]["faixas_estrelas"]) == 2


def test_carregar_config_arquivo_real():
    cfg = carregar_config("config.yaml")
    assert cfg["inicio"] == "2025-01-01"
    assert cfg["fim"] == "2025-12-31"
    assert cfg["limite_repos"] == 300
    assert len(cfg["faixas_estrelas"]) >= 3


# --- Testes de Criterio de Inclusao (min_releases e min_workflow_runs) ---

def test_verificar_criterio_inclusao_aprovado():
    api = MockAPI(
        releases_list=[
            {"published_at": f"2025-0{i}-10T00:00:00Z", "draft": False, "prerelease": False}
            for i in range(1, 7)
        ],
        runs_count=120,
    )
    atende, motivo, n_rel, n_runs = verificar_criterio_inclusao(
        api, "org", "repo", "2025-01-01", "2025-12-31", min_releases=5, min_runs=50
    )
    assert atende is True
    assert motivo is None
    assert n_rel >= 5
    assert n_runs >= 50


def test_verificar_criterio_inclusao_poucas_releases():
    api = MockAPI(
        releases_list=[
            {"published_at": "2025-03-10T00:00:00Z", "draft": False, "prerelease": False},
            {"published_at": "2025-04-10T00:00:00Z", "draft": False, "prerelease": False},
        ],
        runs_count=120,
    )
    atende, motivo, n_rel, n_runs = verificar_criterio_inclusao(
        api, "org", "repo", "2025-01-01", "2025-12-31", min_releases=5, min_runs=50
    )
    assert atende is False
    assert motivo == "poucas_releases"
    assert n_rel == 2


def test_verificar_criterio_inclusao_poucos_runs():
    api = MockAPI(
        releases_list=[
            {"published_at": f"2025-0{i}-10T00:00:00Z", "draft": False, "prerelease": False}
            for i in range(1, 8)
        ],
        runs_count=25,
    )
    atende, motivo, n_rel, n_runs = verificar_criterio_inclusao(
        api, "org", "repo", "2025-01-01", "2025-12-31", min_releases=5, min_runs=50
    )
    assert atende is False
    assert motivo == "poucos_runs"
    assert n_runs == 25

