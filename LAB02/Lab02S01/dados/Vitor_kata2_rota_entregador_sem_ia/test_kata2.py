from solucao import posicao_final

resultado = posicao_final(["N2", "L3", "S1"], 10)

assert resultado == {
    "x": 3,
    "y": 1,
    "saiu_da_grade": False
}

resultado = posicao_final(["N2", "L10"], 5)

assert resultado == {
    "x": 3,
    "y": 2,
    "saiu_da_grade": True
}

resultado = posicao_final([], 5)

assert resultado == {
    "x": 0,
    "y": 0,
    "saiu_da_grade": False
}

print("Todos os testes da Kata 2 passaram!")