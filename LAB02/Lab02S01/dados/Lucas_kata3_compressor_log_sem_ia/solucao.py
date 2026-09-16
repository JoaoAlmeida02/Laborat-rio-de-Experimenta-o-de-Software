def comprimir_eventos(eventos: list[str]) -> list[str]:
    if not eventos:
        return []

    resultado = []
    atual = eventos[0]
    contador = 1

    for evento in eventos[1:]:
        if evento == atual:
            contador += 1
        else: 
            if contador > 1:
                resultado.append(f"{atual} x{contador}")
            else:
                resultado.append(atual)

            atual = evento
            contador = 1

    if contador > 1:
        resultado.append(f"{atual} x {contador}")
    else:
        resultado.append(atual)

    return resultado