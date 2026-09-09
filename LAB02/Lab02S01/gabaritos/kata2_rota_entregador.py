DELTAS = {"N": (0, 1), "S": (0, -1), "L": (1, 0), "O": (-1, 0)}


def posicao_final(comandos: list[str], tamanho_grade: int) -> dict:
    x, y = 0, 0
    saiu_da_grade = False

    for comando in comandos:
        direcao, passos = comando[0], int(comando[1:])
        if direcao not in DELTAS:
            raise ValueError(f"Direcao invalida: {direcao}")
        dx, dy = DELTAS[direcao]
        for _ in range(passos):
            novo_x, novo_y = x + dx, y + dy
            if 0 <= novo_x < tamanho_grade and 0 <= novo_y < tamanho_grade:
                x, y = novo_x, novo_y
            else:
                saiu_da_grade = True

    return {"x": x, "y": y, "saiu_da_grade": saiu_da_grade}
