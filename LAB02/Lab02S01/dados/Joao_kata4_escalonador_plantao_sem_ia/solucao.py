def montar_escala(
    funci: list[str], dias: int, indisponiveis: dict[str, set[int]]
) -> list[str]:
    if dias <= 0 or not funci:
        return []

    escala = []
    idx = 0
    total = len(funci)

    for dia in range(1, dias + 1):

        encontrado = False
        
        for _ in range(total):
            func = funci[idx % total]
            idx += 1
        
            if dia not in indisponiveis.get(func, set()):
                escala.append(func)
                encontrado = True
                break
        
        if not encontrado:
            escala.append("SEM COBERTURA")

    return escala
