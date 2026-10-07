"""Testes unitários para o cliente HTTP resiliente (pipeline/http.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

from pipeline.http import ClienteHTTP, extrair_proxima_pagina


def criar_sessao_mock() -> MagicMock:
    """Cria um mock de sessão HTTP com dicionário de cabeçalhos inicializado."""
    sessao = MagicMock()
    sessao.headers = {}
    return sessao


def test_token_ausente_emite_aviso_e_executa_sem_auth(tmp_path: Path):
    """Verifica que a ausência do token GITHUB_TOKEN gera warning e requisições sem Authorization."""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.warns(UserWarning, match="GITHUB_TOKEN não configurado"):
            cliente = ClienteHTTP(token=None, cache_dir=tmp_path)
            assert "Authorization" not in cliente.sessao.headers


def test_token_presente_configura_bearer(tmp_path: Path):
    """Verifica que o token informado é configurado como Bearer no cabeçalho."""
    cliente = ClienteHTTP(token="ghp_teste123", cache_dir=tmp_path)
    assert cliente.sessao.headers["Authorization"] == "Bearer ghp_teste123"


def test_cache_em_disco_evita_requisicao_duplicada(tmp_path: Path):
    """Garante que a segunda chamada à mesma URL não faz request à rede e usa o cache em disco."""
    sessao_mock = criar_sessao_mock()
    resp_mock = MagicMock()
    resp_mock.status_code = 200
    resp_mock.headers = {"X-RateLimit-Remaining": "4999"}
    resp_mock.json.return_value = {"msg": "ok", "id": 42}
    sessao_mock.get.return_value = resp_mock

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        cache_dir=tmp_path,
        usar_cache=True,
    )

    url = "https://api.github.com/repos/org/repo"
    params = {"page": 1}

    # 1ª chamada: deve consultar a rede e gravar em disco
    dado1 = cliente.get(url, params=params)
    assert dado1 == {"msg": "ok", "id": 42}
    assert sessao_mock.get.call_count == 1

    # Verifica que arquivo JSON de cache foi gravado no diretório
    arquivos_cache = list(tmp_path.glob("*.json"))
    assert len(arquivos_cache) == 1
    with open(arquivos_cache[0], "r", encoding="utf-8") as f:
        cache_salvo = json.load(f)
    assert cache_salvo["data"] == {"msg": "ok", "id": 42}

    # 2ª chamada: deve vir do cache sem chamar sessao.get novamente
    dado2 = cliente.get(url, params=params)
    assert dado2 == {"msg": "ok", "id": 42}
    assert sessao_mock.get.call_count == 1


def test_retry_5xx_com_backoff_exponencial(tmp_path: Path):
    """Testa backoff em sequência de erros 5xx (500, 502, 503, 200) com dormidas 1, 2, 4s."""
    sessao_mock = criar_sessao_mock()

    resp_500 = MagicMock(status_code=500, headers={})
    resp_502 = MagicMock(status_code=502, headers={})
    resp_503 = MagicMock(status_code=503, headers={})
    resp_200 = MagicMock(status_code=200, headers={})
    resp_200.json.return_value = {"sucesso": True}

    sessao_mock.get.side_effect = [resp_500, resp_502, resp_503, resp_200]
    dormir_mock = MagicMock()

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        tentativas=5,
        dormir=dormir_mock,
        cache_dir=tmp_path,
        usar_cache=False,
    )

    resultado = cliente.get("https://api.github.com/endpoint-teste")
    assert resultado == {"sucesso": True}
    assert sessao_mock.get.call_count == 4

    # Verifica a sequência exata de backoff: 2^0=1, 2^1=2, 2^2=4
    assert dormir_mock.call_args_list == [call(1), call(2), call(4)]


def test_retry_5xx_esgotado_levanta_excecao(tmp_path: Path):
    """Verifica se RuntimeError é levantado após esgotar o limite configurado de tentativas."""
    sessao_mock = criar_sessao_mock()
    resp_500 = MagicMock(status_code=500, headers={})
    sessao_mock.get.return_value = resp_500
    dormir_mock = MagicMock()

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        tentativas=3,
        dormir=dormir_mock,
        cache_dir=tmp_path,
        usar_cache=False,
    )

    with pytest.raises(RuntimeError, match="Falha após 3 tentativas"):
        cliente.get("https://api.github.com/falha-constante")

    assert dormir_mock.call_args_list == [call(1), call(2)]


def test_rate_limit_dorme_ate_reset(tmp_path: Path):
    """Verifica que quando Remaining=0, sleep é chamado com o tempo até Reset mais a margem."""
    sessao_mock = criar_sessao_mock()

    resp_rate = MagicMock(
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1500"},
    )
    resp_sucesso = MagicMock(
        status_code=200,
        headers={"X-RateLimit-Remaining": "4999", "X-RateLimit-Reset": "2000"},
    )
    resp_sucesso.json.return_value = {"status": "recuperado"}

    sessao_mock.get.side_effect = [resp_rate, resp_sucesso]
    dormir_mock = MagicMock()
    relogio_mock = MagicMock(return_value=1400.0)

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        dormir=dormir_mock,
        relogio=relogio_mock,
        margem_reset=1.0,
        cache_dir=tmp_path,
        usar_cache=False,
    )

    dados = cliente.get("https://api.github.com/rate-limited")
    assert dados == {"status": "recuperado"}
    # Reset em 1500, relógio em 1400, margem 1.0 => 101.0s de espera
    dormir_mock.assert_called_once_with(101.0)
    assert cliente.cota_restante == 4999


def test_paginacao_automatica_por_link_header(tmp_path: Path):
    """Verifica a paginação seguindo o header Link: rel='next' até a última página."""
    sessao_mock = criar_sessao_mock()

    resp1 = MagicMock(
        status_code=200,
        headers={
            "Link": '<https://api.github.com/itens?page=2&per_page=100>; rel="next"',
            "X-RateLimit-Remaining": "4990",
        },
    )
    resp1.json.return_value = [{"id": 1}, {"id": 2}]

    resp2 = MagicMock(
        status_code=200,
        headers={
            "Link": '<https://api.github.com/itens?page=3&per_page=100>; rel="next"',
            "X-RateLimit-Remaining": "4989",
        },
    )
    resp2.json.return_value = [{"id": 3}]

    resp3 = MagicMock(
        status_code=200,
        headers={"X-RateLimit-Remaining": "4988"},
    )
    resp3.json.return_value = [{"id": 4}]

    sessao_mock.get.side_effect = [resp1, resp2, resp3]

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        cache_dir=tmp_path,
        usar_cache=False,
    )

    itens = cliente.get_paginado("https://api.github.com/itens")
    assert itens == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    assert sessao_mock.get.call_count == 3


def test_paginacao_com_dicionario_workflow_runs(tmp_path: Path):
    """Verifica se get_paginado descompacta corretamente a chave workflow_runs."""
    sessao_mock = criar_sessao_mock()

    resp1 = MagicMock(
        status_code=200,
        headers={"Link": '<https://api.github.com/runs?page=2>; rel="next"'},
    )
    resp1.json.return_value = {
        "total_count": 2,
        "workflow_runs": [{"id": 101, "name": "CI"}],
    }

    resp2 = MagicMock(status_code=200, headers={})
    resp2.json.return_value = {
        "total_count": 2,
        "workflow_runs": [{"id": 102, "name": "CI"}],
    }

    sessao_mock.get.side_effect = [resp1, resp2]

    cliente = ClienteHTTP(
        token="token_mock",
        sessao=sessao_mock,
        cache_dir=tmp_path,
        usar_cache=False,
    )

    runs = cliente.get_paginado("/repos/test/repo/actions/runs")
    assert len(runs) == 2
    assert runs[0]["id"] == 101
    assert runs[1]["id"] == 102


def test_extrair_proxima_pagina():
    """Testa parser da URL rel='next' em múltiplos cenários de Link header."""
    assert extrair_proxima_pagina(None) is None
    assert extrair_proxima_pagina("") is None
    assert extrair_proxima_pagina('<http://ex.com/p1>; rel="prev"') is None
    assert (
        extrair_proxima_pagina('<http://ex.com/p2>; rel="next", <http://ex.com/p3>; rel="last"')
        == "http://ex.com/p2"
    )
