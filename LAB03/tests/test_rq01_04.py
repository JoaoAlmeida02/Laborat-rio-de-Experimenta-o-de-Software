"""Análise das RQ 01 a 04 e classificação C1 com um dataset pequeno montado à mão."""
import pandas as pd
import pytest

from analises.rq01_04 import (
    censura_e_ignoradas,
    classificacao_c1,
    contagem_categorias,
    executar,
    frequencia_efetiva,
    resumo,
    sobreposicao_amostra_ouro,
    tabela_descritiva,
)


@pytest.fixture
def dataset():
    """Três repositórios com perfis Elite, Medium e um sem episódios de recuperação."""
    return pd.DataFrame([
        {"repo": "o/rapido", "deploy_frequency_semana": 10.0, "n_entregas": 520, "ignoradas_sem_commits": 480,
         "lead_time_release_h": 12.0, "lead_time_commit_h": 6.0, "cfr_ci": 0.05, "cfr_entrega": 0.10,
         "tempo_recuperacao_h": 0.5, "recuperacao_proporcao_censurados": 0.0, "total_episodios_recuperacao": 10,
         "cfr_entrega_censuradas": 2, "cfr_entrega_avaliadas": 500, "ignoradas_sem_anterior": 0,
         "ignoradas_compare_404": 1},
        {"repo": "o/medio", "deploy_frequency_semana": 0.5, "n_entregas": 26, "ignoradas_sem_commits": 0,
         "lead_time_release_h": 200.0, "lead_time_commit_h": 100.0, "cfr_ci": 0.35, "cfr_entrega": 0.40,
         "tempo_recuperacao_h": 48.0, "recuperacao_proporcao_censurados": 0.25, "total_episodios_recuperacao": 4,
         "cfr_entrega_censuradas": 1, "cfr_entrega_avaliadas": 25, "ignoradas_sem_anterior": 1,
         "ignoradas_compare_404": 0},
        {"repo": "o/sem_falhas", "deploy_frequency_semana": 0.1, "n_entregas": 6, "ignoradas_sem_commits": 0,
         "lead_time_release_h": 1000.0, "lead_time_commit_h": -5.0, "cfr_ci": 0.0, "cfr_entrega": None,
         "tempo_recuperacao_h": None, "recuperacao_proporcao_censurados": 0.0, "total_episodios_recuperacao": 0,
         "cfr_entrega_censuradas": 0, "cfr_entrega_avaliadas": 0, "ignoradas_sem_anterior": 0,
         "ignoradas_compare_404": 0},
    ])


def test_resumo_mediana_quartis_e_iqr():
    r = resumo(pd.Series([1, 2, 3, 4, 5, None]))
    assert (r["n"], r["mediana"], r["q1"], r["q3"], r["iqr"]) == (5, 3, 2, 4, 2)
    assert resumo(pd.Series([None, None]))["mediana"] is None


def test_tabela_descritiva_tem_todas_as_variantes(dataset):
    t = tabela_descritiva(dataset).set_index("coluna")
    assert set(t["rq"]) == {"RQ 01", "RQ 02", "RQ 03", "RQ 04"}
    assert t.loc["cfr_entrega", "n"] == 2                    # valor ausente fica fora
    assert t.loc["deploy_frequency_semana", "categoria_da_mediana"] == "Medium"   # mediana 0,5/semana
    assert t.loc["tempo_recuperacao_h", "categoria_da_mediana"] == "Medium"       # mediana 24,25 h


def test_classificacao_c1_usa_cfr_a_e_quatro_metricas(dataset):
    c1 = classificacao_c1(dataset).set_index("repo")
    assert c1.loc["o/rapido", "categoria_geral"] == "Elite"
    assert c1.loc["o/rapido", "categoria_cfr"] == "Elite"    # CFR (a) = 5%
    assert c1.loc["o/medio", "categoria_cfr"] == "Medium"    # CFR (a) = 35%, não o CFR (b)
    # notas (Medium, High, Medium, Medium) = (2, 3, 2, 2) -> mediana 2 -> Medium
    assert c1.loc["o/medio", "categoria_geral"] == "Medium"
    sem = c1.loc["o/sem_falhas"]
    assert pd.isna(sem["categoria_recuperacao"]) and sem["n_metricas"] == 3


def test_contagem_categorias(dataset):
    contagem = contagem_categorias(classificacao_c1(dataset)).set_index("metrica")
    assert contagem.loc["recuperacao", "sem_valor"] == 1
    assert contagem.loc["geral", ["Low", "Medium", "High", "Elite"]].sum() == 3


def test_censura_e_ignoradas(dataset):
    c = censura_e_ignoradas(dataset).set_index("descricao")["valor"]
    assert c["repos sem nenhum episódio de recuperação na janela"] == 1
    assert c["repos com algum episódio censurado"] == 1
    assert c["releases censuradas (últimos 7 dias da janela)"] == 3
    assert c["releases sem commits novos"] == 480
    assert c["repos com mediana do lead time (b) <= 0 (datas de autor posteriores à release)"] == 1


def test_frequencia_efetiva_desconta_releases_sem_commits(dataset):
    f = frequencia_efetiva(dataset, "2025-01-01", "2025-12-31").set_index("repo")
    assert f.loc["o/rapido", "entregas_com_commits_novos"] == 40
    assert f.loc["o/rapido", "categoria_original"] == "Elite"
    assert f.loc["o/rapido", "categoria_efetiva"] == "Medium"   # 40 / 52,1 ≈ 0,77 por semana
    assert bool(f.loc["o/rapido", "mudou_categoria"])
    assert not bool(f.loc["o/medio", "mudou_categoria"])


def test_sobreposicao_amostra_ouro(dataset, tmp_path):
    consenso = tmp_path / "consenso.csv"
    pd.DataFrame({"repo": ["o/medio", "x/y", "x/y"]}).to_csv(consenso, index=False)
    assert sobreposicao_amostra_ouro(dataset, consenso) == (1, 2)
    assert sobreposicao_amostra_ouro(dataset, tmp_path / "nao_existe.csv") is None


def test_executar_gera_tabelas_resumo_e_figuras(dataset, tmp_path):
    caminho = tmp_path / "dataset.csv"
    dataset.to_csv(caminho, index=False)
    executar(caminho, tmp_path / "saida", "2025-01-01", "2025-12-31", caminho_consenso=None)
    gerados = {p.name for p in (tmp_path / "saida").iterdir()}
    assert {"rq01_04_descritiva.csv", "classificacao_C1.csv", "categorias_C1.csv", "censura_e_ignoradas.csv",
            "frequencia_efetiva.csv", "RESUMO_RQ01_04.md", "fig_rq01_04_boxplots.png",
            "fig_categorias_C1.png", "fig_heatmap_C1.png"} <= gerados
    resumo_md = (tmp_path / "saida" / "RESUMO_RQ01_04.md").read_text(encoding="utf-8")
    assert "Geral (C1)" in resumo_md and "frequência efetiva" in resumo_md
