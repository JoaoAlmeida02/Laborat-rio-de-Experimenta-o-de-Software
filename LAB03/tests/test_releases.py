import pytest

from metricas.datas import janela
from pipeline.github_api import GitHubAPI, NaoEncontrado, proxima_pagina
from pipeline.releases import coletar_commits_entre, coletar_repositorio, coletar_tags, resumir


def _commit(sha, data, msg="feat: x"):
    return {"sha": sha, "commit": {"author": {"date": data}, "message": msg}}


class APIFalsa:
    def __init__(self, releases=(), compares=None, tags=(), commits=None):
        self.releases, self.tags = list(releases), list(tags)
        self.compares = compares or {}
        self.commits = commits or {}
        self.chamadas = []

    def paginar(self, caminho, params=None):
        return iter(self.tags if caminho.endswith("/tags") else self.releases)

    def get(self, caminho, params=None):
        self.chamadas.append((caminho, params))
        if "/commits/" in caminho:
            return self.commits[caminho.rsplit("/", 1)[1]]
        chave = caminho.rsplit("/compare/", 1)[1]
        if chave not in self.compares:
            raise NaoEncontrado(caminho)
        todos = self.compares[chave]
        pagina, por_pagina = params["page"], params["per_page"]
        return {"total_commits": len(todos), "commits": todos[(pagina - 1) * por_pagina: pagina * por_pagina]}


def _release(tag, data, draft=False, prerelease=False):
    return {"tag_name": tag, "published_at": data, "draft": draft, "prerelease": prerelease}


@pytest.fixture
def ano_2025():
    return janela("2025-01-01", "2025-12-31")


def test_compare_pagina_alem_de_250_commits():
    commits = [_commit(str(i), "2025-03-01T00:00:00Z") for i in range(260)]
    api = APIFalsa(compares={"v1...v2": commits})
    resultado = coletar_commits_entre(api, "o", "r", "v1", "v2")
    assert len(resultado) == 260
    assert len(api.chamadas) == 3


def test_mensagem_guarda_so_a_primeira_linha():
    api = APIFalsa(compares={"a...b": [_commit("1", "2025-01-01T00:00:00Z", "fix: bug\n\ncorpo")]})
    assert coletar_commits_entre(api, "o", "r", "a", "b")[0]["mensagem"] == "fix: bug"


def test_coleta_repositorio_regras_principais(ano_2025):
    api = APIFalsa(
        releases=[
            _release("v1.0", "2024-11-01T00:00:00Z"),          # fora da janela, serve de base
            _release("v1.1", "2025-03-15T00:00:00Z"),
            _release("v1.2-rc", "2025-04-01T00:00:00Z", prerelease=True),
            _release("v1.2", "2025-05-01T00:00:00Z"),
            _release("v2.0", "2025-06-01T00:00:00Z", draft=True),
        ],
        compares={"v1.0...v1.1": [_commit("a", "2025-03-02T00:00:00Z")]},
    )
    dados = coletar_repositorio(api, "o", "r", *ano_2025)
    tags = [e["tag"] for e in dados["entregas"]]
    assert tags == ["v1.1", "v1.2"]                    # sem draft, sem pré-release, só janela
    assert dados["entregas"][0]["commits"][0]["sha"] == "a"
    assert dados["entregas"][1]["motivo"] == "compare_404"


def test_primeira_release_da_historia_sem_anterior(ano_2025):
    api = APIFalsa(releases=[_release("v1.0", "2025-02-01T00:00:00Z")])
    entrega = coletar_repositorio(api, "o", "r", *ano_2025)["entregas"][0]
    assert entrega["commits"] is None and entrega["motivo"] == "sem_anterior"


def test_variante_release_mais_prerelease(ano_2025):
    api = APIFalsa(
        releases=[_release("v1.0", "2025-01-10T00:00:00Z"),
                  _release("v1.1-rc", "2025-02-01T00:00:00Z", prerelease=True)],
        compares={"v1.0...v1.1-rc": [_commit("a", "2025-01-20T00:00:00Z")]},
    )
    dados = coletar_repositorio(api, "o", "r", *ano_2025, unidade="release+pre")
    assert [e["tag"] for e in dados["entregas"]] == ["v1.0", "v1.1-rc"]


def test_tags_datadas_pelo_commit():
    api = APIFalsa(
        tags=[{"name": "v2", "commit": {"sha": "s2"}}, {"name": "v1", "commit": {"sha": "s1"}}],
        commits={"s1": _commit("s1", "2025-01-01T00:00:00Z"), "s2": _commit("s2", "2025-02-01T00:00:00Z")},
    )
    assert [t["tag"] for t in coletar_tags(api, "o", "r")] == ["v1", "v2"]


def test_resumo_por_repositorio(ano_2025):
    dados = {"repo": "o/r", "unidade": "release", "entregas": [
        {"tag": "v1.1", "data": "2025-03-15T00:00:00Z", "commits": [{"data": "2025-03-14T00:00:00Z"}]},
        {"tag": "v1.2", "data": "2025-04-15T00:00:00Z", "commits": None, "motivo": "compare_404"},
    ]}
    linha = resumir(dados, *ano_2025)
    assert linha["lead_time_release_h"] == 24.0
    assert linha["n_commits"] == 1
    assert linha["ignoradas_compare_404"] == 1


def test_proxima_pagina():
    link = '<https://api.github.com/x?page=2>; rel="next", <https://api.github.com/x?page=5>; rel="last"'
    assert proxima_pagina(link) == "https://api.github.com/x?page=2"
    assert proxima_pagina(None) is None


class _Resp:
    def __init__(self, status, corpo=None, headers=None):
        self.status_code, self._corpo, self.headers = status, corpo, headers or {}

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class _Sessao:
    def __init__(self, respostas):
        self.respostas, self.headers = list(respostas), {}

    def get(self, url, params=None, timeout=None):
        return self.respostas.pop(0)


def test_cliente_repete_5xx_e_espera_rate_limit():
    esperas = []
    sessao = _Sessao([
        _Resp(502),
        _Resp(403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "0"}),
        _Resp(200, [1, 2], {"Link": '<https://api.github.com/p2>; rel="next"'}),
        _Resp(200, [3]),
    ])
    api = GitHubAPI(token="t", sessao=sessao, dormir=esperas.append)
    assert list(api.paginar("/x")) == [1, 2, 3]
    assert len(esperas) == 2


def test_cliente_404_vira_excecao():
    api = GitHubAPI(token="t", sessao=_Sessao([_Resp(404)]))
    with pytest.raises(NaoEncontrado):
        api.get("/x")
