# Kata 1 — Validador de senha de cofre

Implemente `validar_senha(senha: str) -> dict` em `solucao.py`.

A função deve retornar um dicionário com:
- `"valida"`: `bool` — `True` se a senha atende a todas as regras abaixo.
- `"violacoes"`: `list[str]` — lista com o nome de cada regra violada (vazia se `valida` for `True`).

Regras (nomes das violações entre parênteses):
1. Comprimento mínimo de 8 caracteres (`"tamanho"`).
2. Ao menos um dígito (`"digito"`).
3. Ao menos uma letra maiúscula (`"maiuscula"`).
4. Nenhum caractere pode se repetir 3 ou mais vezes seguidas, ex.: `"aaa"` (`"repeticao"`).
5. Não pode conter espaços em branco (`"espaco"`).

A ordem da lista `"violacoes"` deve seguir a ordem das regras acima.
