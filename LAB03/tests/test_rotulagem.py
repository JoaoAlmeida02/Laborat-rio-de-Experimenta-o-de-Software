from pathlib import Path
import tempfile

import pandas as pd
import pytest

from rotulagem.concordancia import (
    avaliar_concordancia_completa,
    calcular_cohen_kappa_pares,
    calcular_fleiss_kappa_dimensao,
    carregar_planilhas,
    extrair_divergencias,
    gerar_relatorio_divergencias_md,
    interpretar_landis_koch,
)
from rotulagem.consenso import (
    consolidar_consenso,
    executar_consenso_completo,
    gerar_resumo_consenso,
    resolver_voto,
)
from rotulagem.gerar_planilhas import (
    amostrar_repositorios,
    construir_linhas_releases,
    salvar_planilha,
)


def test_amostrar_repositorios_reprodutibilidade(tmp_path):
    caminho_csv = tmp_path / "repos_teste.csv"
    dados = [f"owner/repo_{i}" for i in range(100)]
    pd.DataFrame({"full_name": dados}).to_csv(caminho_csv, index=False)

    amostra1 = amostrar_repositorios(caminho_csv, n=20, semente=42)
    amostra2 = amostrar_repositorios(caminho_csv, n=20, semente=42)
    amostra3 = amostrar_repositorios(caminho_csv, n=20, semente=99)

    assert len(amostra1) == 20
    assert amostra1 == amostra2
    assert amostra1 != amostra3


def test_construir_linhas_releases_poucas_releases():
    releases = [
        {"tag": "v1.0.0", "data": "2025-01-01T00:00:00Z", "prerelease": False},
        {"tag": "v1.0.1", "data": "2025-02-01T00:00:00Z", "prerelease": False},
        {"tag": "v1.1.0", "data": "2025-03-01T00:00:00Z", "prerelease": False},
    ]
    linhas = construir_linhas_releases("foo/bar", releases, n_amostra=5, semente=42)

    assert len(linhas) == 3
    # Primeira release não tem anterior nem compare
    assert linhas[0]["release_anterior"] == "-"
    assert linhas[0]["compare_url"] == "-"
    assert linhas[0]["release_url"] == "https://github.com/foo/bar/releases/tag/v1.0.0"

    # Segunda release tem anterior v1.0.0
    assert linhas[1]["release_anterior"] == "v1.0.0"
    assert "compare/v1.0.0...v1.0.1" in linhas[1]["compare_url"]


def test_construir_linhas_releases_muitas_releases():
    releases = [
        {"tag": f"v1.{i}.0", "data": f"2025-0{i+1}-01T00:00:00Z", "prerelease": False}
        for i in range(8)
    ]
    linhas = construir_linhas_releases("foo/bar", releases, n_amostra=5, semente=42)

    assert len(linhas) == 5
    # Verifica que todas têm tags válidas
    tags = [l["release_tag"] for l in linhas]
    assert len(set(tags)) == 5


def test_interpretar_landis_koch():
    assert interpretar_landis_koch(-0.1) == "Pobre (Poor)"
    assert interpretar_landis_koch(0.15) == "Leve (Slight)"
    assert interpretar_landis_koch(0.35) == "Razoável (Fair)"
    assert interpretar_landis_koch(0.55) == "Moderada (Moderate)"
    assert interpretar_landis_koch(0.75) == "Substancial (Substantial)"
    assert interpretar_landis_koch(0.95) == "Quase Perfeita (Almost Perfect)"


def test_fleiss_kappa_perfeito_e_moderado():
    # 100% concordância
    df_a = pd.DataFrame({"corretiva": ["sim", "sim", "nao", "nao"]})
    df_b = pd.DataFrame({"corretiva": ["sim", "sim", "nao", "nao"]})
    df_c = pd.DataFrame({"corretiva": ["sim", "sim", "nao", "nao"]})
    planilhas = {"A": df_a, "B": df_b, "C": df_c}

    kappa, interp = calcular_fleiss_kappa_dimensao(planilhas, "corretiva")
    assert kappa == 1.0
    assert interp == "Quase Perfeita (Almost Perfect)"

    # Divergências leves
    df_b2 = pd.DataFrame({"corretiva": ["sim", "nao", "nao", "nao"]})
    planilhas2 = {"A": df_a, "B": df_b2, "C": df_c}
    kappa2, interp2 = calcular_fleiss_kappa_dimensao(planilhas2, "corretiva")
    assert 0.0 < kappa2 < 1.0


def test_cohen_kappa_pares():
    df_a = pd.DataFrame({"entrega_real": ["sim", "sim", "nao", "sim"]})
    df_b = pd.DataFrame({"entrega_real": ["sim", "sim", "nao", "sim"]})
    df_c = pd.DataFrame({"entrega_real": ["sim", "nao", "nao", "sim"]})
    planilhas = {"A": df_a, "B": df_b, "C": df_c}

    pares = calcular_cohen_kappa_pares(planilhas, "entrega_real")
    assert pares["AxB"] == 1.0
    assert pares["AxC"] < 1.0
    assert pares["BxC"] < 1.0


def test_resolver_voto_regras():
    # Unanimidade 3x0
    vencedor, unanime = resolver_voto(["sim", "sim", "sim"])
    assert vencedor == "sim"
    assert unanime is True

    # Maioria 2x1
    vencedor, unanime = resolver_voto(["sim", "nao", "sim"])
    assert vencedor == "sim"
    assert unanime is False

    # Empate 1-1-1
    vencedor, unanime = resolver_voto(["sim", "nao", "incerto"])
    assert vencedor == "empate"
    assert unanime is False


def test_extrair_divergencias_e_gerar_md(tmp_path):
    df_a = pd.DataFrame({
        "repo": ["org/repo1"],
        "release_tag": ["v1.0"],
        "release_url": ["http://rel"],
        "compare_url": ["http://cmp"],
        "tipo_projeto": ["ferramenta_cli"],
        "entrega_real": ["sim"],
        "corretiva": ["nao"],
    })
    df_b = pd.DataFrame({
        "repo": ["org/repo1"],
        "release_tag": ["v1.0"],
        "release_url": ["http://rel"],
        "compare_url": ["http://cmp"],
        "tipo_projeto": ["biblioteca_framework"],
        "entrega_real": ["sim"],
        "corretiva": ["nao"],
    })
    df_c = pd.DataFrame({
        "repo": ["org/repo1"],
        "release_tag": ["v1.0"],
        "release_url": ["http://rel"],
        "compare_url": ["http://cmp"],
        "tipo_projeto": ["ferramenta_cli"],
        "entrega_real": ["sim"],
        "corretiva": ["sim"],
    })
    planilhas = {"A": df_a, "B": df_b, "C": df_c}

    divergencias = extrair_divergencias(planilhas)
    assert len(divergencias) == 2  # tipo_projeto e corretiva
    assert divergencias[0]["tipo_divergencia"] == "2-1 (maioria)"

    caminho_md = tmp_path / "divergencias_teste.md"
    gerar_relatorio_divergencias_md(divergencias, caminho_md)
    assert caminho_md.exists()
    conteudo = caminho_md.read_text(encoding="utf-8")
    assert "org/repo1" in conteudo
    assert "tipo_projeto" in conteudo


def test_consolidar_consenso_e_resumo():
    df_a = pd.DataFrame({
        "repo": ["org/r1", "org/r2"],
        "release_tag": ["v1", "v2"],
        "release_data": ["d1", "d2"],
        "release_anterior": ["-", "v1"],
        "release_url": ["u1", "u2"],
        "compare_url": ["-", "c2"],
        "tipo_projeto": ["cli", "lib"],
        "entrega_real": ["sim", "sim"],
        "corretiva": ["sim", "nao"],
    })
    df_b = pd.DataFrame({
        "repo": ["org/r1", "org/r2"],
        "release_tag": ["v1", "v2"],
        "release_data": ["d1", "d2"],
        "release_anterior": ["-", "v1"],
        "release_url": ["u1", "u2"],
        "compare_url": ["-", "c2"],
        "tipo_projeto": ["cli", "app"],
        "entrega_real": ["sim", "sim"],
        "corretiva": ["nao", "nao"],
    })
    df_c = pd.DataFrame({
        "repo": ["org/r1", "org/r2"],
        "release_tag": ["v1", "v2"],
        "release_data": ["d1", "d2"],
        "release_anterior": ["-", "v1"],
        "release_url": ["u1", "u2"],
        "compare_url": ["-", "c2"],
        "tipo_projeto": ["cli", "outro"],
        "entrega_real": ["sim", "sim"],
        "corretiva": ["sim", "nao"],
    })
    planilhas = {"A": df_a, "B": df_b, "C": df_c}

    df_consenso = consolidar_consenso(planilhas)
    assert len(df_consenso) == 2
    assert df_consenso.iloc[0]["tipo_projeto_consenso"] == "cli"
    assert df_consenso.iloc[0]["tipo_projeto_unanimidade"] == "sim"
    # r2 teve lib vs app vs outro -> empate
    assert df_consenso.iloc[1]["tipo_projeto_consenso"] == "empate"
    assert df_consenso.iloc[1]["tipo_projeto_unanimidade"] == "nao"

    resumo = gerar_resumo_consenso(df_consenso)
    assert resumo["total_itens"] == 2
    assert resumo["estatisticas"]["tipo_projeto"]["empates_qtd"] == 1


def test_fluxo_concordancia_e_consenso_completo(tmp_path):
    # Cria planilhas de teste no tmp_path
    from rotulagem.concordancia import main as main_concordancia
    from rotulagem.consenso import main as main_consenso

    df_base = pd.DataFrame({
        "repo": ["org/r1", "org/r2"],
        "release_tag": ["v1.0.0", "v1.0.1"],
        "release_data": ["2025-01-01", "2025-02-01"],
        "release_anterior": ["-", "v1.0.0"],
        "release_url": ["http://r1", "http://r2"],
        "compare_url": ["-", "http://c2"],
        "tipo_projeto": ["ferramenta_cli", "biblioteca_framework"],
        "entrega_real": ["sim", "sim"],
        "corretiva": ["nao", "sim"],
        "observacoes": ["", ""],
    })
    df_base.to_csv(tmp_path / "rotulos_A.csv", index=False)
    df_base.to_csv(tmp_path / "rotulos_B.csv", index=False)
    df_base.to_csv(tmp_path / "rotulos_C.csv", index=False)

    res_concordancia = avaliar_concordancia_completa(tmp_path)
    assert "fleiss" in res_concordancia
    assert res_concordancia["divergencias_total"] == 0

    df_consenso, resumo = executar_consenso_completo(tmp_path)
    assert len(df_consenso) == 2
    assert resumo["total_itens"] == 2

    # Testa execução CLI
    main_concordancia(["--pasta", str(tmp_path)])
    main_consenso(["--pasta", str(tmp_path)])


def test_gerar_planilhas_fluxo_com_mock(tmp_path):
    from unittest.mock import MagicMock
    from rotulagem.gerar_planilhas import gerar_planilhas_avaliacao, main as main_gerar

    caminho_csv = tmp_path / "repos.csv"
    pd.DataFrame({"full_name": ["org/test_repo"]}).to_csv(caminho_csv, index=False)

    api_mock = MagicMock()
    api_mock.paginar.return_value = [
        {"tag_name": "v1.0.0", "published_at": "2025-01-01T00:00:00Z", "draft": False, "prerelease": False},
        {"tag_name": "v1.0.1", "published_at": "2025-02-01T00:00:00Z", "draft": False, "prerelease": False},
    ]

    caminhos = gerar_planilhas_avaliacao(
        caminho_repos=caminho_csv,
        pasta_saida=tmp_path / "saida",
        n_repos=1,
        n_releases=5,
        semente=42,
        api=api_mock,
        sobrescrever_preenchidos=True,
    )

    assert caminhos["template"].exists()
    assert caminhos["A"].exists()
    df_gerado = pd.read_csv(caminhos["template"])
    assert len(df_gerado) == 2
    assert df_gerado.iloc[0]["release_tag"] == "v1.0.0"
    assert df_gerado.iloc[1]["release_anterior"] == "v1.0.0"

