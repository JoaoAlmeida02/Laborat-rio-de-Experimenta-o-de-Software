def comprimir_eventos(eventos: list[str]) -> list[str]:
    resultado = []

    if len(eventos) == 0:
        return resultado

    evento_atual = eventos[0]
    quantidade = 1

    for i in range(1, len(eventos)):

        if eventos[i] == evento_atual:
            quantidade += 1

        else:
            if quantidade > 1:
                resultado.append(f"{evento_atual} x{quantidade}")
            else:
                resultado.append(evento_atual)

            evento_atual = eventos[i]
            quantidade = 1

    if quantidade > 1:
        resultado.append(f"{evento_atual} x{quantidade}")
    else:
        resultado.append(evento_atual)

    return resultado