from itertools import groupby


def comprimir_eventos(eventos: list[str]) -> list[str]:
    if not eventos:
        return []

    resultado = []
    for evento, grupo in groupby(eventos):
        count = sum(1 for _ in grupo)
        if count > 1:
            resultado.append(f"{evento} x{count}")
        else:
            resultado.append(evento)
    return resultado
