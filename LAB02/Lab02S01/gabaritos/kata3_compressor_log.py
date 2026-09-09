def comprimir_eventos(eventos: list[str]) -> list[str]:
    resultado = []
    i = 0
    while i < len(eventos):
        evento = eventos[i]
        contagem = 1
        while i + contagem < len(eventos) and eventos[i + contagem] == evento:
            contagem += 1
        resultado.append(f"{evento} x{contagem}" if contagem > 1 else evento)
        i += contagem
    return resultado
