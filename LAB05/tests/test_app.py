"""Carregamento, seleção de fonte e filtros sem navegador."""
from pathlib import Path

import pandas as pd

from app import detectar_entrada, filtrar, filtrar_inferencia, ler_csv


def test_detecta_bruto_antes_do_piloto(monkeypatch):
    piloto = Path("dados/piloto/piloto.csv")
    bruto = Path("dados/brutos/dados.csv")
    existentes = {piloto}
    monkeypatch.setattr(Path, "is_file", lambda caminho: caminho in existentes)
    assert detectar_entrada(Path("dados")) == piloto
    existentes.add(bruto)
    assert detectar_entrada(Path("dados")) == bruto


def test_le_csv_sem_criar_arquivo(monkeypatch):
    caminho = Path("dados/sintetico.csv")
    quadro = pd.DataFrame({"tratamento": ["T1", "T2"]})
    is_file = Path.is_file
    monkeypatch.setattr(Path, "is_file", lambda p: p == caminho or is_file(p))
    monkeypatch.setattr(pd, "read_csv", lambda p: quadro.copy())
    ler_csv.clear()
    try:
        pd.testing.assert_frame_equal(ler_csv(caminho), quadro)
        assert ler_csv(Path("arquivo-ausente.csv")) is None
    finally:
        ler_csv.clear()


def test_filtra_com_intersecao_e_preserva_indices():
    quadro = pd.DataFrame({"endpoint": ["home", "rest_posts", "home"],
                            "tratamento": ["T1", "T1", "T2"], "mitigacao": [0, 0, 1]})
    resposta = filtrar(quadro, {"endpoint": ["home"], "mitigacao": [1], "tratamento": ["T1", "T2"]})
    assert resposta.index.tolist() == [2]
    assert filtrar(quadro, {"tratamento": []}).empty
    assert filtrar(None, {}) is None


def test_inferencia_exige_celulas_do_contraste():
    a = pd.DataFrame({"efeito": ["versao", "mitigacao"]})
    e = pd.DataFrame({"contraste": ["T1 vs T3", "T1 vs T2", "versao", "mitigacao"]})
    filtrada, tost = filtrar_inferencia(a, e, ["T1", "T3"])
    assert filtrada.empty
    assert tost.contraste.tolist() == ["T1 vs T3"]

