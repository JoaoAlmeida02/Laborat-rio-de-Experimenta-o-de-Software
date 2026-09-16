import re


def validar_senha(senha: str) -> dict:
    violacoes = []

    if len(senha) < 8:
        violacoes.append("tamanho")

    if not re.search(r"\d", senha):
        violacoes.append("digito")

    if not re.search(r"[A-Z]", senha):
        violacoes.append("maiuscula")

    if re.search(r"(.)\1\1", senha):
        violacoes.append("repeticao")

    if re.search(r"\s", senha):
        violacoes.append("espaco")

    return {"valida": len(violacoes) == 0, "violacoes": violacoes}
