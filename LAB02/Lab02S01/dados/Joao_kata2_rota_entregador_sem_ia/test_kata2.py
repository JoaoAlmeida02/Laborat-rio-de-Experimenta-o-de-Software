import pytest

from solucao import posicao_final


def test_caminho_normal_dentro_da_grade():
    resultado = posicao_final(["N2", "L3"], tamanho_grade=5)
    assert resultado == {"x": 3, "y": 2, "saiu_da_grade": False}


def test_lista_vazia():
    resultado = posicao_final([], tamanho_grade=5)
    assert resultado == {"x": 0, "y": 0, "saiu_da_grade": False}


def test_sai_pelo_norte_e_fica_no_limite():
    resultado = posicao_final(["N10"], tamanho_grade=5)
    assert resultado == {"x": 0, "y": 4, "saiu_da_grade": True}


def test_sai_pelo_oeste_no_inicio():
    resultado = posicao_final(["O1"], tamanho_grade=5)
    assert resultado == {"x": 0, "y": 0, "saiu_da_grade": True}


def test_recupera_apos_tentar_sair():
    resultado = posicao_final(["S5", "N2"], tamanho_grade=3)
    assert resultado == {"x": 0, "y": 2, "saiu_da_grade": True}


def test_direcao_invalida_levanta_erro():
    with pytest.raises(ValueError):
        posicao_final(["X1"], tamanho_grade=5)
