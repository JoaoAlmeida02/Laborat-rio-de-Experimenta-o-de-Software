def montar_escala(funcionarios: list, dias: int, indisponiveis: dict) -> list:
    n = len(funcionarios)
    escala = []
    ponteiro = 0

    for dia in range(1, dias + 1):
        escalado = None
        for tentativa in range(n):
            idx = (ponteiro + tentativa) % n
            candidato = funcionarios[idx]
            dias_indisponiveis = indisponiveis.get(candidato, set())
            if dia not in dias_indisponiveis:
                escalado = candidato
                ponteiro = (idx + 1) % n
                break

        if escalado is None:
            escala.append("SEM COBERTURA")
        else:
            escala.append(escalado)

    return escala