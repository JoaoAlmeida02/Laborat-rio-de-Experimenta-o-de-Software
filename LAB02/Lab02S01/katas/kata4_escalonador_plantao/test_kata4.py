from solucao import montar_escala


def test_rodizio_simples_sem_restricoes():
    escala = montar_escala(["Ana", "Bia", "Caio"], dias=4, indisponiveis={})
    assert escala == ["Ana", "Bia", "Caio", "Ana"]


def test_pula_indisponivel_sem_reiniciar_rotacao():
    escala = montar_escala(["Ana", "Bia"], dias=3, indisponiveis={"Bia": {2}})
    assert escala == ["Ana", "Ana", "Bia"]


def test_dia_sem_cobertura():
    escala = montar_escala(
        ["Ana", "Bia"], dias=2, indisponiveis={"Ana": {1}, "Bia": {1}}
    )
    assert escala == ["SEM COBERTURA", "Ana"]


def test_um_unico_funcionario_sem_restricao():
    escala = montar_escala(["Ana"], dias=3, indisponiveis={})
    assert escala == ["Ana", "Ana", "Ana"]


def test_zero_dias_retorna_lista_vazia():
    assert montar_escala(["Ana", "Bia"], dias=0, indisponiveis={}) == []
