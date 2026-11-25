"""Dados sintéticos em memória para verificar as decisões estatísticas."""
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

from scripts.analise_rq1_rq2 import (
    LEGADO, METRICAS, PILOTO, TRATAMENTOS, analisar, avisos_amostra, efeitos, preparar, resumo,
)
from scripts.analise_rq3 import EXPLORATORIA, PRINCIPAL, analisar_rq3, km_grupo
from scripts import graficos


def amostra(n=40, efeito=0, assimetrica=False):
    rng = np.random.default_rng(502)
    linhas = []
    normal = rng.permutation(norm.ppf((np.arange(n) + .5) / n))
    # Mesmas magnitudes em cada célula para isolar o efeito plantado.
    ruido = normal if not assimetrica else np.r_[np.linspace(-.5, .5, n-1), 50]
    for tratamento, (php, mitigacao) in TRATAMENTOS.items():
        for i, deslocamento in enumerate(ruido):
            valor = 100 + deslocamento + (efeito if php == "8.4.27" else 0)
            linha = dict(execucao_id=f"{tratamento}-{i}", tratamento=tratamento, php_version=php,
                         mitigacao=mitigacao, repeticao=i+1, endpoint="home", status="ok")
            linha.update({m: valor * .0001 if m == "taxa_erro" else valor for m in METRICAS})
            linhas.append(linha)
    return pd.DataFrame(linhas)


def test_anova_detecta_efeito_grande():
    linhas = efeitos(amostra(efeito=25), "mem_php_media_mb", .05)
    versao = next(r for r in linhas if r["efeito"] == "versao")
    assert versao["teste"] == "ANOVA tipo II"
    assert versao["p"] < .001
    assert versao["eta2_parcial"] > .9
    assert versao["magnitude"] == "grande"


def test_tost_estabelece_equivalencia():
    _, _, tabela = analisar(amostra())
    linha = tabela.query("metrica == 'rps' and contraste == 'T1 vs T3'").iloc[0]
    assert linha.conclusao == "equivalente"
    assert linha.p_holm < .05
    assert -linha.margem < linha.ic90_inferior < 0 < linha.ic90_superior < linha.margem


def test_dados_assimetricos_acionam_art():
    linhas = efeitos(amostra(assimetrica=True), "mem_php_media_mb", .05)
    assert all(r["teste"] == "ART-ANOVA tipo II" for r in linhas)
    assert all(r["p_shapiro"] < .05 for r in linhas)


def test_km_mediana_com_censura():
    df = pd.DataFrame({"tempo_dias": [1, 2, 3, 4], "evento": [0, 1, 1, 0]})
    resumo_km, curva = km_grupo(df)
    assert resumo_km["mediana_dias"] == 3
    assert resumo_km["censurados"] == 2
    assert curva.loc[curva.tempo_dias.eq(3), "sem_correcao"].item() == pytest.approx(1/3)
    censurado, _ = km_grupo(df.assign(evento=0))
    assert np.isnan(censurado["mediana_dias"])


def test_rq3_separa_principal_de_exploratoria():
    df = pd.DataFrame(dict(tempo_dias=[0, 2, 1, 9, 3], evento=[1, 1, 1, 0, 1],
                           tipo=["Distribuição Linux", "Distribuição Linux", "Nuvem", "Nuvem", "Hospedagem"],
                           grupo=["comunitario", "comercial", "nuvem", "nuvem", "hospedagem"]))
    km, lr = analisar_rq3(df)
    assert set(km.analise) == {PRINCIPAL, EXPLORATORIA}
    assert lr.groupby("analise").size().to_dict() == {PRINCIPAL: 4, EXPLORATORIA: 1}
    assert lr.baixo_poder.all()
    assert (lr.p_holm >= lr.p).all()


def test_entrada_invalida_tem_mensagem_clara():
    with pytest.raises(ValueError, match="Colunas faltando.*rps"):
        preparar(amostra().drop(columns="rps"))
    with pytest.raises(ValueError, match="Sem execuções válidas"):
        preparar(amostra().assign(status="falha"))


def test_resumo_piloto_e_formato_legado():
    origem = amostra(n=3).drop(columns="status")
    origem.loc[0, "rps"] = np.nan
    dados, info = preparar(origem)
    texto = resumo(*analisar(dados), info, avisos_amostra(dados, "brutos/dados.csv", sintetico=True), .05)
    assert PILOTO in texto
    assert LEGADO in texto
    assert "SINTÉTICO" in texto
    assert info["linhas_incompletas"] == info["execucoes_descartadas"] == 1


def test_graficos_sinteticos_renderizam_png_em_memoria(monkeypatch):
    imagens = {}
    salvar = graficos.salvar

    def em_memoria(fig, caminho, avisos):
        assert "SINTÉTICO" in avisos
        assert PILOTO in avisos
        arquivo = BytesIO()
        salvar(fig, arquivo, avisos)
        imagens[caminho.name] = arquivo.getvalue()

    monkeypatch.setattr(graficos, "salvar", em_memoria)
    dados = amostra(n=3)
    avisos = avisos_amostra(dados, "piloto/piloto.csv", sintetico=True)
    grafico_km = pd.DataFrame(dict(tempo_dias=[0, 2, 3], evento=[1, 0, 1],
                                   tipo=["Distribuição Linux", "Nuvem", "Hospedagem"],
                                   grupo=["comunitario", "nuvem", "hospedagem"]))
    km, _ = analisar_rq3(grafico_km)
    graficos.desempenho(dados, analisar(dados)[2], Path("."), avisos)
    graficos.sobrevivencia(km, Path("."), avisos)
    assert len(imagens) == len(METRICAS) + 2
    assert all(imagem.startswith(b"\x89PNG\r\n\x1a\n") for imagem in imagens.values())

