def montar_escala(funcionarios: list[str], dias: int, indisponiveis: dict[str, set[int]]) -> list[str]:
    """Ver enunciado.md para as regras do rodizio de plantao."""
    n = len(funcionarios)
    ponteiro = 0
    escala = []

    for dia in range(1, dias + 1):
        escalado = None
        for _ in range(n):
            candidato = funcionarios[ponteiro]
            ponteiro = (ponteiro + 1) % n
            if dia not in indisponiveis.get(candidato, set()):
                escalado = candidato
                break
        escala.append(escalado if escalado is not None else "SEM COBERTURA")

    return escala
