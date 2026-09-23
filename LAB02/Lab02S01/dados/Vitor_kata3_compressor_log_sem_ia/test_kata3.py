from solucao import comprimir_eventos


def test_lista_vazia():
    assert comprimir_eventos([]) == []


def test_evento_unico():
    assert comprimir_eventos(["login"]) == ["login"]


def test_sequencia_repetida():
    eventos = ["login", "login", "login", "erro", "erro", "logout"]
    assert comprimir_eventos(eventos) == ["login x3", "erro x2", "logout"]


def test_nao_agrupa_nao_consecutivos():
    eventos = ["login", "erro", "login"]
    assert comprimir_eventos(eventos) == ["login", "erro", "login"]


def test_todos_iguais():
    eventos = ["ping"] * 5
    assert comprimir_eventos(eventos) == ["ping x5"]


def test_mistura_de_grupos_e_unicos():
    eventos = ["a", "b", "b", "c", "c", "c", "a"]
    assert comprimir_eventos(eventos) == ["a", "b x2", "c x3", "a"]
