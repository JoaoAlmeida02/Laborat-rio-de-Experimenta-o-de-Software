from pathlib import Path
import tempfile
import pytest

from pipeline.config_parser import _parse_yaml_simples, carregar_config
from pipeline.selecao import (
    FunilSelecao,
    buscar_candidatos_por_faixas,
    calcular_idade,
    coletar_metadados_repo,
    descartar_candidato_estatico,
    extrair_ultimo_link,
    selecionar_repositorios,
    verificar_actions,
)


class MockAPI:
    def __init__(self, workflows_count=1, link_header=None, contributors_list=None, search_items=None):
        self.workflows_count = workflows_count
        self.link_header = link_header
        self.contributors_list = contributors_list or [{"id": 1}]
        self.search_items = search_items or []

    def get(self, caminho, params=None):
        if "search/repositories" in caminho:
            return {"total_count": len(self.search_items), "items": self.search_items}
        if "actions/workflows" in caminho:
            return {"total_count": self.workflows_count, "workflows": []}
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
    funil = FunilSelecao()
    funil.registrar_busca(500)
    funil.descartar("fork")
    funil.descartar("fork")
    funil.descartar("arquivado")
    funil.descartar("sem_actions")
    funil.registrar_etapa("4_amostra_final", 100)

    linhas = funil.gerar_linhas_csv()
    assert len(linhas) == 5
    assert linhas[0]["restantes"] == 500

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
    assert cfg["limite_repos"] == 100
    assert len(cfg["faixas_estrelas"]) >= 3
