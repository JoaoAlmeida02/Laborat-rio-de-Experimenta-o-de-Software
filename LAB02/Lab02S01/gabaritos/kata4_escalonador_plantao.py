def montar_escala(funcionarios: list[str], dias: int, indisponiveis: dict[str, set[int]]) -> list[str]:
    escala = []
    ponteiro = 0
    n = len(funcionarios)

    for dia in range(1, dias + 1):
        atribuido = None
        for tentativa in range(n):
            candidato = funcionarios[(ponteiro + tentativa) % n]
            if dia not in indisponiveis.get(candidato, set()):
                atribuido = candidato
                ponteiro = (ponteiro + tentativa + 1) % n
                break
        escala.append(atribuido if atribuido is not None else "SEM COBERTURA")

    return escala
