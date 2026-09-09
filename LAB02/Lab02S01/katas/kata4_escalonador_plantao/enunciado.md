# Kata 4 — Escalonador de plantão

Implemente `montar_escala(funcionarios: list[str], dias: int, indisponiveis: dict[str, set[int]]) -> list[str]`
em `solucao.py`.

A função distribui plantões para `dias` dias (numerados de `1` a `dias`),
usando rodízio (round-robin) sobre a lista `funcionarios`, na ordem em que
aparecem.

- `indisponiveis` mapeia o nome de um funcionário para o conjunto de dias em
  que ele **não pode** trabalhar.
- Para cada dia, o próximo funcionário da rotação é escolhido; se ele estiver
  indisponível naquele dia, pula-se para o próximo da rotação (sem voltar
  atrás), e assim por diante.
- Se **nenhum** funcionário estiver disponível em um dia, a escala daquele dia
  deve ser `"SEM COBERTURA"`.
- O ponteiro da rotação **não reinicia** a cada dia: ele continua de onde
  parou, mesmo quando um funcionário é pulado por indisponibilidade.

Retorna uma lista com `dias` elementos, um por dia, com o nome do funcionário
escalado (ou `"SEM COBERTURA"`).

Exemplo:
```python
montar_escala(["Ana", "Bia", "Caio"], dias=4, indisponiveis={})
# -> ["Ana", "Bia", "Caio", "Ana"]

montar_escala(["Ana", "Bia"], dias=3, indisponiveis={"Bia": {2}})
# dia 1: Ana | dia 2: Bia indisponivel -> pula para Ana | dia 3: Bia
# -> ["Ana", "Ana", "Bia"]
```
