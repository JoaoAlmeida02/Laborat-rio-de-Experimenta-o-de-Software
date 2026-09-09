# Desenho do Experimento - LAB02

## Objetivo (GQM)
Avaliar o impacto de usar assistente de IA generativa vs programar manualmente pra resolver katas de código. A ideia é comparar tempo de resolução, quantidade de testes passando e qualidade do código gerado.

## Perguntas de Pesquisa (RQs) e Métricas
- **RQ1 (Tempo)**: Usar IA deixa o desenvolvimento mais rápido?
  - Métrica: Tempo em segundos ate passar nos testes (time-to-green). Quem estourar o limite de 35 min fica registrado em 35 min (dado censurado).
- **RQ2 (Defeitos)**: A IA reduz falhas nos testes?
  - Métrica: Porcentagem de testes passando no final do tempo (taxa de sucesso).
- **RQ3 (Qualidade do Código)**: O código gerado pela IA fica mais complexo ou altera a manutenibilidade?
  - Métrica: Complexidade ciclomática (cc), índice de manutenibilidade (mi) e linhas de código (LOC) extraídos via Radon.

## Hipóteses
- RQ1:
  - H0: O tempo de resolução com IA e sem IA é igual.
  - H1: Usar IA reduz o tempo de resolução.
- RQ2:
  - H0: A taxa de testes passando é igual nos dois casos.
  - H1: Usar IA aumenta a taxa de testes passando.
- RQ3:
  - H0: A complexidade e manutenibilidade do código são iguais nos dois tratamentos.
  - H1: Usar IA altera a complexidade e a manutenibilidade do código.

## Variáveis
- Variável Independente: tratamento (`com_ia` vs `sem_ia`)
- Variáveis Dependentes: `tempo_segundos`, `censurado`, `taxa_sucesso`, `cc`, `mi`, `loc`.

## Desenho do Experimento (Crossover / Within-Subject)
Cada integrante resolve os 4 katas (2 com IA e 2 sem IA), intercalando para evitar viés:

| Integrante | Kata 1 (Cofre) | Kata 2 (Rota) | Kata 3 (Log) | Kata 4 (Plantão) |
|---|---|---|---|---|
| Joao | com_ia | sem_ia | com_ia | sem_ia |
| Lucas | sem_ia | com_ia | sem_ia | com_ia |
| Vitor | com_ia | com_ia | sem_ia | sem_ia |

## Ameaças à Validade
- IA decorando solução: usamos 4 katas autorais próprios, sem cópia do LeetCode.
- Efeito de aprendizado/fadiga: mitigado alternando a ordem de com_ia e sem_ia (contrabalanceamento).
- Pressão do tempo: time-box fixo de 35 min por trial, registrando censura no tempo limite se não finalizar.
- Diferença de habilidade individual: como é within-subject, comparamos a mesma pessoa com e sem IA.
