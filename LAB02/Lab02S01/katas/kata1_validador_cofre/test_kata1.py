from solucao import validar_senha


def test_senha_valida():
    resultado = validar_senha("Abc12345")
    assert resultado["valida"] is True
    assert resultado["violacoes"] == []


def test_senha_curta():
    resultado = validar_senha("Ab1")
    assert resultado["valida"] is False
    assert "tamanho" in resultado["violacoes"]


def test_sem_digito():
    resultado = validar_senha("Abcdefgh")
    assert resultado["valida"] is False
    assert "digito" in resultado["violacoes"]


def test_sem_maiuscula():
    resultado = validar_senha("abcdefg1")
    assert resultado["valida"] is False
    assert "maiuscula" in resultado["violacoes"]


def test_repeticao():
    resultado = validar_senha("Abcaaa12")
    assert resultado["valida"] is False
    assert "repeticao" in resultado["violacoes"]


def test_com_espaco():
    resultado = validar_senha("Abc 1234")
    assert resultado["valida"] is False
    assert "espaco" in resultado["violacoes"]


def test_multiplas_violacoes_na_ordem():
    resultado = validar_senha("aa")
    assert resultado["valida"] is False
    assert resultado["violacoes"] == ["tamanho", "digito", "maiuscula"]
