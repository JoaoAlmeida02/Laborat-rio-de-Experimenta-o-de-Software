import re


def validar_senha(senha: str) -> dict:
    """
    Valida a senha de acordo com as regras do cofre.

    Regras:
        1. Comprimento minimo de 8 caracteres ("tamanho").
        2. Ao menos um digito ("digito").
        3. Ao menos uma letra maiuscula ("maiuscula").
        4. Nenhum caractere pode se repetir 3 ou mais vezes seguidas ("repeticao").
        5. Nao pode conter espacos em branco ("espaco").

    Retorna:
        dict com chaves "valida" (bool) e "violacoes" (list[str]).
    """
    violacoes = []

    if len(senha) < 8:
        violacoes.append("tamanho")

    if not any(c.isdigit() for c in senha):
        violacoes.append("digito")

    if not any(c.isupper() for c in senha):
        violacoes.append("maiuscula")

    if re.search(r'(.)\1{2,}', senha):
        violacoes.append("repeticao")

    if any(c.isspace() for c in senha):
        violacoes.append("espaco")

    return {
        "valida": len(violacoes) == 0,
        "violacoes": violacoes,
    }
