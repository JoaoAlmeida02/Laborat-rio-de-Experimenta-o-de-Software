# Katas do experimento (LAB02)

## Escolha e justificativa

Foram escolhidos **4 katas autorais** (não copiados de LeetCode/HackerRank/Codewars),
para reduzir o risco de memorização pelo assistente de IA (ameaça à validade
citada no enunciado do laboratório). Todos são problemas de manipulação de
strings/listas/dicionários em Python puro, sem dependências externas, com
dificuldade alvo comparável: implementáveis por um estudante de graduação em
até ~35 minutos, com 5 a 7 casos de teste cobrindo caso normal, casos de borda
e pelo menos uma condição de erro/exceção.

| Kata | Tema | Nº de testes |
|---|---|---|
| 1 — Validador de senha de cofre | validação de string com múltiplas regras | 7 |
| 2 — Rota do entregador | simulação de movimento em grade com limites | 6 |
| 3 — Compressor de log | agrupamento de sequências consecutivas | 6 |
| 4 — Escalonador de plantão | rodízio (round-robin) com exceções | 5 |

Número par de katas (4) para permitir divisão exata pela metade entre
tratamentos "com IA" e "sem IA" por integrante, conforme exigido no enunciado.

## Como usar durante a execução (Sprint 2)

Cada trial deve ser feito em uma cópia própria da pasta do kata (não editar o
template original em `katas/`), para permitir reuso do mesmo kata por várias
pessoas/tratamentos sem conflito:

```
LAB02/Lab02S02/trials/<pessoa>_<kata>_<tratamento>/
    solucao.py   (copiado do template, implementado durante o trial)
    test_kataN.py  (copiado sem alteração — é o critério de aceitação)
```

O script `../cronometro.py` automatiza a cópia, a cronometragem e a execução
dos testes ao final do trial.
