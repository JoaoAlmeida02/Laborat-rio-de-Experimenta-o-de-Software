def validar_senha(senha: str) -> dict:
    violacoes = []

    if len(senha) < 8:
        violacoes.append("tamanho")

    if not any(caractere.isdigit() for caractere in senha):
        violacoes.append("digito")

    if not any(caractere.isupper() for caractere in senha):
        violacoes.append("maiscula")

    if any(senha[i] == senha[i+1] == senha[i+2] for i in range(len(senha) - 2)):
        violacoes.append("repeticao")

    if any(caractere.isspace() for caractere in senha):
        violacoes.append("espaco")

    return {
        "valida": len(violacoes) == 0,
        "violacoes": violacoes
    }