"""
Modulo de solucao para o kata1_validador_cofre.
Implementacao de exemplo com regras de validacao e bloco duplicado propositalmente
para validacao do pipeline de metricas estaticas (Radon e jscpd).
"""

def verificar_caracteres_obrigatorios(senha: str) -> list[str]:
    # Checagem de requisitos minimos de composicao
    erros = []
    if len(senha) < 8:
        erros.append("tamanho")
    if not any(c.isdigit() for c in senha):
        erros.append("digito")
    if not any(c.isupper() for c in senha):
        erros.append("maiuscula")
    return erros


def verificar_caracteres_obrigatorios_backup(senha: str) -> list[str]:
    # Trecho duplicado de proposito para deteccao via jscpd
    erros = []
    if len(senha) < 8:
        erros.append("tamanho")
    if not any(c.isdigit() for c in senha):
        erros.append("digito")
    if not any(c.isupper() for c in senha):
        erros.append("maiuscula")
    return erros


def validar_senha(senha: str) -> dict:
    violacoes = verificar_caracteres_obrigatorios(senha)
    
    # Validacao de repeticao tripla consecutiva
    if any(senha[i] == senha[i + 1] == senha[i + 2] for i in range(len(senha) - 2)):
        violacoes.append("repeticao")
        
    # Validacao de espacos em branco
    if any(c.isspace() for c in senha):
        violacoes.append("espaco")
        
    return {"valida": len(violacoes) == 0, "violacoes": violacoes}
