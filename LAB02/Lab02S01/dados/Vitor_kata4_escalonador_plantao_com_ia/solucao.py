def montar_escala(funcionarios: list, dias: int, indisponiveis: dict) -> list:
    """
    Distribui plantoes para `dias` dias usando rodizio (round-robin).

    Args:
        funcionarios: Lista de funcionarios em ordem de rodizio.
        dias: Numero de dias a escalar (1 a dias).
        indisponiveis: Mapa nome -> conjunto de dias em que o funcionario nao pode trabalhar.

    Returns:
        Lista com `dias` elementos: nome do funcionario escalado ou "SEM COBERTURA".
    """
    if not funcionarios or dias == 0:
        return []

    n = len(funcionarios)
    escala = []
    ponteiro = 0  # ponteiro global da rotacao, nunca reinicia

    for dia in range(1, dias + 1):
        escalado = "SEM COBERTURA"
        # Tenta cada funcionario a partir do ponteiro atual (no maximo n tentativas)
        for tentativa in range(n):
            candidato = funcionarios[ponteiro % n]
            ponteiro += 1  # avanca o ponteiro independente de pular ou nao
            dias_indisp = indisponiveis.get(candidato, set())
            if dia not in dias_indisp:
                escalado = candidato
                break

        escala.append(escalado)

    return escala
