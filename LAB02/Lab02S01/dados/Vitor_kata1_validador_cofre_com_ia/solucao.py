def validar_senha(senha: str) -> dict:
    violacoes = []

    if len(senha) < 8:
        violacoes.append("tamanho")

    if not any(c.isdigit() for c in senha):
        violacoes.append("digito")

    if not any(c.isupper() for c in senha):
        violacoes.append("maiuscula")

    tem_repeticao = False
    for i in range(len(senha) - 2):
        if senha[i] == senha[i + 1] == senha[i + 2]:
            tem_repeticao = True
            break
    if tem_repeticao:
        violacoes.append("repeticao")

    if any(c.isspace() for c in senha):
        violacoes.append("espaco")

    return {
        "valida": len(violacoes) == 0,
        "violacoes": violacoes,
    }