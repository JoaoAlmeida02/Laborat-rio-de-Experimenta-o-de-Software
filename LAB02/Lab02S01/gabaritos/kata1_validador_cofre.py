def validar_senha(senha: str) -> dict:
    violacoes = []
    if len(senha) < 8:
        violacoes.append("tamanho")
    if not any(c.isdigit() for c in senha):
        violacoes.append("digito")
    if not any(c.isupper() for c in senha):
        violacoes.append("maiuscula")
    if any(senha[i] == senha[i + 1] == senha[i + 2] for i in range(len(senha) - 2)):
        violacoes.append("repeticao")
    if any(c.isspace() for c in senha):
        violacoes.append("espaco")
    return {"valida": len(violacoes) == 0, "violacoes": violacoes}
