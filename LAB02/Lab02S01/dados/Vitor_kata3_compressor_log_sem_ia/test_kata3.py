from solucao import comprimir_eventos

resultado = comprimir_eventos(
    ["login", "login", "login", "erro", "erro", "logout"]
)

assert resultado == [
    "login x3",
    "erro x2",
    "logout"
]

resultado = comprimir_eventos(
    ["login", "erro", "login"]
)

assert resultado == [
    "login",
    "erro",
    "login"
]

resultado = comprimir_eventos(
    ["erro", "erro", "erro", "erro"]
)

assert resultado == [
    "erro x4"
]

resultado = comprimir_eventos([])

assert resultado == []

print("Todos os testes da Kata 3 passaram!")