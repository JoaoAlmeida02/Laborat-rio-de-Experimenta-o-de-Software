# Kata 2 — Rota do entregador

Implemente `posicao_final(comandos: list[str], tamanho_grade: int) -> dict` em `solucao.py`.

O entregador começa na posição `(0, 0)` em uma grade quadrada cujas coordenadas
válidas vão de `0` até `tamanho_grade - 1` (nos eixos x e y).

Cada comando é uma string com uma letra de direção seguida de um número de passos:
- `"N"` (norte): y aumenta
- `"S"` (sul): y diminui
- `"L"` (leste): x aumenta
- `"O"` (oeste): x diminui

Exemplo: `"N3"` move 3 passos para norte, `"L2"` move 2 passos para leste.

Regras:
- Os comandos são processados em ordem, um passo de cada vez.
- Se um passo levaria a posição para fora dos limites da grade (`< 0` ou
  `>= tamanho_grade` em qualquer eixo), esse passo é **ignorado** (a posição
  não muda) e o resto da rota continua sendo processado a partir da posição
  atual.
- Uma letra de direção fora de `{N, S, L, O}` deve levantar `ValueError`.

A função deve retornar:
```python
{"x": <int>, "y": <int>, "saiu_da_grade": <bool>}
```
onde `"saiu_da_grade"` é `True` se **algum** passo da rota foi ignorado por
estar fora dos limites.
