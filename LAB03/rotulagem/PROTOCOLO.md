# Protocolo de Rotulagem Manual e Desempate (Amostra-Ouro)

Este documento estabelece as diretrizes metodológicas, definições conceituais e regras operacionais para a rotulagem manual independente da amostra-ouro do **Laboratório 03 (Mineração de Métricas DORA)**, bem como os critérios formais para cálculo de concordância e resolução de divergências (consenso).

---

## 1. Contexto e Amostragem

A validação da acurácia e calibração das heurísticas automáticas requer uma base de verdade de referência (*ground truth* ou amostra-ouro).

- **População Base:** 300 repositórios de código aberto selecionados após os critérios de inclusão e funil (`data/repos.csv`).
- **Amostra de Repositórios:** 60 repositórios sorteados de forma pseudoaleatória com semente fixa (`random_state=42`).
- **Amostra de Releases:** Até 5 releases publicadas por repositório sorteado, também com amostragem determinística (`random_state=42`).
- **Princípio da Avaliação Cega (*Blind Review*):**
  - Cada um dos três pesquisadores (Avaliador A, Avaliador B e Avaliador C) recebe sua respectiva planilha (`rotulos_A.csv`, `rotulos_B.csv`, `rotulos_C.csv`).
  - As planilhas contêm exclusivamente identificadores, datas e links diretos para a release e comparação de código (`compare_url`), sem exibir a predição da heurística automática, garantindo independência e neutralidade.

---

## 2. Dimensões de Rotulagem

Para cada item da amostra, o avaliador inspeciona a página da release e a diferença de commits/arquivos alterados no GitHub, preenchendo as seguintes três dimensões:

### Dimensão 1: `tipo_projeto` (Classificação Arquitetural do Repositório)
Classifica a natureza do artefato de software produzido pelo repositório:

| Valor | Descrição | Exemplos |
| :--- | :--- | :--- |
| `biblioteca_framework` | Pacote, SDK, biblioteca, plugin ou framework reutilizável por desenvolvedores via gerenciadores de dependências (npm, PyPI, Maven, etc.). | `elastic/elasticsearch-ruby`, `TypeStrong/fork-ts-checker-webpack-plugin`, `gin-contrib/cors` |
| `aplicacao_servico` | Software funcional completo voltado para usuário final, webapp, serviço de backend ou microsserviço executável. | `coralproject/talk`, `DeaDBeeF-Player/deadbeef`, `veops/oneterm` |
| `ferramenta_cli` | Utilitário executável exclusivamente por linha de comando ou script de automação operacional. | `pterodactyl-installer/pterodactyl-installer`, `Meliox/PVE-mods` |
| `outro` | Repositórios de documentação pura, listas de curadoria (*awesome lists*), tutoriais, benchmarks sem software empacotado. | `szabgab/awesome-for-non-programmers`, `ad-si/awesome-3d-printing` |

---

### Dimensão 2: `entrega_real` (Validação de Entrega Funcional)
Determina se a release representou uma entrega efetiva de valor ao usuário/sistema, ou se foi um evento administrativo/ruído:

| Valor | Critério Operacional |
| :--- | :--- |
| `sim` | A release contém alterações reais de código, novos recursos, melhorias funcionais ou correções de defeitos incorporadas. |
| `nao` | A release não introduz modificações funcionais. Exemplos: atualização isolada de `README.md`, alteração de versão acidental vazia, tag de espelhamento ou commit puramente cosmético de documentação. |
| `incerto` | A release não possui commits associados acessíveis (ex.: erro 404 no compare por histórico reescrito/force push) e não há notas de versão que permitam inferir a entrega com segurança. |

---

### Dimensão 3: `corretiva` (Natureza da Mudança na Release)
Avalia se o propósito primário da entrega foi a remediação de falhas ou incidentes:

| Valor | Critério Operacional |
| :--- | :--- |
| `sim` | A release tem objetivo predominantemente corretivo (*bug fix*, *hotfix*, correção de vulnerabilidade de segurança, correção de regressão, *revert* de commit problemático). Evidenciado por notas de lançamento ("Bugfixes", "Patch release"), mensagens de commit e incremento exclusivamente no número de *patch* do SemVer (ex.: `v1.2.3` -> `v1.2.4`). |
| `nao` | A release introduz novas funcionalidades (*features*, *minor* ou *major* releases), refatorações planejadas, modernização de infraestrutura ou suporte a novas plataformas sem intuito emergencial de correção. |

---

## 3. Protocolo de Concordância Interobservadores

A concordância entre os três avaliadores independentes é aferida por meio de métricas estatísticas formais:

1. **Kappa de Fleiss ($\kappa_{\text{Fleiss}}$):**
   - Utilizado para avaliar a concordância geral entre múltiplos avaliadores nominais nas três dimensões.
   - Implementado via biblioteca `statsmodels.stats.inter_rater` (`aggregate_raters` e `fleiss_kappa`).
   - Escala de interpretação de **Landis & Koch (1977)**:
     - $< 0{,}00$: Concordância Pobre (*Poor*)
     - $0{,}00 - 0{,}20$: Concordância Leve (*Slight*)
     - $0{,}21 - 0{,}40$: Concordância Razoável (*Fair*)
     - $0{,}41 - 0{,}60$: Concordância Moderada (*Moderate*)
     - $0{,}61 - 0{,}80$: Concordância Substancial (*Substantial*)
     - $0{,}81 - 1{,}00$: Concordância Quase Perfeita (*Almost Perfect*)

2. **Kappa de Cohen Par a Par ($\kappa_{\text{Cohen}}$):**
   - Calculado para cada par de avaliadores ($A \times B$, $A \times C$, $B \times C$) usando `scikit-learn.metrics.cohen_kappa_score`.
   - Permite diagnosticar assimetrias e identificar se algum avaliador específico apresentou viés sistemático em relação aos pares.

---

## 4. Regras de Desempate e Consenso

Após a conclusão das rotulagens individuais e execução do cálculo de concordância, a amostra-ouro unificada (`rotulagem/consenso.csv`) é consolidada segundo as seguintes regras determinísticas:

1. **Unanimidade ($3 \times 0$):**
   - Quando os três avaliadores atribuem o mesmo rótulo ($A = B = C$), esse valor é adotado automaticamente como verdade absoluta da amostra-ouro.
2. **Maioria Simples ($2 \times 1$):**
   - Quando dois avaliadores concordam e um discorda (ex.: $A = B \neq C$), o voto da maioria é adotado no consenso.
   - O caso divergente é registrado no relatório de auditoria (`rotulagem/divergencias.md`).
3. **Empate Triplo ($1 \times 1 \times 1$):**
   - Possível exclusivamente em dimensões com três ou mais opções (como `tipo_projeto` e `entrega_real`).
   - O item é marcado explicitamente como `empate` na coluna de consenso preliminar.
   - Uma reunião síncrona de alinhamento entre os três integrantes é convocada, utilizando o arquivo `divergencias.md` como pauta oficial. O artefato e histórico de commits são reexaminados em conjunto até que um consenso fundamentado seja atingido e registrado formalmente.
