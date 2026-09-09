# Kata 3 — Compressor de log

Implemente `comprimir_eventos(eventos: list[str]) -> list[str]` em `solucao.py`.

Recebe uma lista de eventos (strings) na ordem em que ocorreram e deve
comprimir **sequências consecutivas** do mesmo evento em uma única entrada:
- Se o evento se repete `N > 1` vezes seguidas, a entrada comprimida deve ser
  `"<evento> xN"`.
- Se o evento aparece sozinho (não repetido na sequência), a entrada deve ser
  apenas `"<evento>"`, sem sufixo.

Exemplo:
```python
comprimir_eventos(["login", "login", "login", "erro", "erro", "logout"])
# -> ["login x3", "erro x2", "logout"]
```

Casos extremos:
- Lista vazia deve retornar `[]`.
- Eventos não consecutivos (mesmo que iguais) **não** devem ser agrupados:
  `["login", "erro", "login"]` deve virar `["login", "erro", "login"]`.
