# Protocolo de Rotulagem Manual e Desempate (Amostra-Ouro)

Este documento estabelece as diretrizes metodológicas, definições conceituais e regras operacionais para a rotulagem manual independente da amostra-ouro do **Laboratório 03 (Mineração de Métricas DORA)**, bem como os critérios formais para cálculo de concordância e resolução de divergências (consenso).

---

## 1. Contexto e Amostragem

A validação da acurácia e calibração das heurísticas automáticas requer uma base de verdade de referência (*ground truth* ou amostra-ouro).

- **População Base:** 300 repositórios de código aberto selecionados após os critérios de inclusão e funil (`data/repos.csv`).
- **Amostra de Repositórios:** 60 repositórios sorteados de forma pseudoaleatória com semente fixa (`random_state=42`). Desses, **45** tinham releases publicadas e entraram na rotulagem (ver seção 5).
- **Amostra de Releases:** Até 5 releases publicadas por repositório sorteado, também com amostragem determinística (`random_state=42`), totalizando **214 releases** (ver seção 5).
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

---

## 5. Desvios em relação ao planejado e critério prático de `corretiva`

Esta seção registra, de forma transparente, onde a amostra-ouro efetivamente rotulada difere do enunciado e como o critério de `corretiva` foi aplicado na prática. Esses pontos são retomados na seção de ameaças à validade do artigo.

### 5.1. Tamanho da amostra: 45 repositórios e 214 releases (planejado: 60 e 300)

| Item | Planejado | Rotulado | Motivo |
| :--- | :---: | :---: | :--- |
| Repositórios | 60 | 45 | 15 dos 60 sorteados não retornaram nenhuma release publicada. O `gerar_planilhas.py` trata do mesmo jeito "repositório sem releases" (usa só tags ou não versiona) e "falha na consulta à API", então os dois casos não são distinguíveis nesta execução. |
| Releases | 300 (5 × 60) | 214 | 41 repositórios contribuíram com 5 releases; 4 tinham menos de 5 releases no histórico (1, 2, 3 e 3), e todas foram incluídas. |
| Período das releases | Janela de observação (2025-01-01 a 2025-12-31) | 2013 a 2026 | As releases foram sorteadas do histórico completo do repositório, não só da janela. |

Esses desvios são consequência de a lista de 300 repositórios ter sido usada **antes** da aplicação do critério mínimo de inclusão (≥ 5 releases e ≥ 50 workflow runs na janela). Com o critério aplicado, todo repositório sorteado teria pelo menos 5 releases na janela, e a amostra chegaria a 60 × 5 = 300 releases.

**Impacto:**
- A amostra menor reduz a precisão das estimativas de kappa e de P/R/F1 (intervalos de confiança mais largos).
- Releases antigas (anteriores à janela) podem ter padrões de versionamento e de notas diferentes dos atuais; a validação da heurística vale para releases em geral, e não especificamente para as releases da janela em que o CFR (b) é calculado.
- Restam 15 releases sem release anterior (primeira da lista), que não podem ser avaliadas como corretivas e ficam fora do cálculo de P/R/F1.

### 5.2. Critério prático usado para `corretiva`

O critério da Dimensão 3 (seção 2) lista o **incremento exclusivamente no número de patch do SemVer** como uma das evidências de release corretiva. Na prática, os três avaliadores trataram esse sinal como a evidência principal, conferindo as notas de release e os commits para confirmar:

- Das 199 releases com release anterior, o consenso marcou **82 como corretivas, e todas as 82 são mudanças apenas de patch**.
- Das 83 mudanças apenas de patch, **82 foram rotuladas como corretivas e 1 não**.
- Nenhuma release minor ou major foi rotulada como corretiva, mesmo quando continha commits de correção.

**Por que isso importa:** as heurísticas automáticas (`metricas/corretiva.py`) também usam o número de patch. Como o rótulo humano e a heurística se apoiam no mesmo sinal, a concordância entre eles tende a ser alta por construção, e o F1 obtido pode **superestimar** a qualidade real da heurística. Pelo mesmo motivo, os kappas altos da dimensão `corretiva` refletem em parte o uso de um critério comum e objetivo, e não apenas julgamentos independentes convergentes.

**Como isso é tratado:**
- O resultado é reportado no artigo como ameaça à validade **de construto** (o rótulo humano não é totalmente independente do proxy medido).
- Os falsos positivos e falsos negativos de cada versão da heurística (`rotulagem/avaliacao/erros_<versao>.csv`) são analisados caso a caso, já que mostram justamente onde notas e commits contradizem o número de versão.
- Em uma replicação, recomenda-se rotular `corretiva` lendo apenas as notas de release e os commits, **ocultando as tags de versão**, para quebrar a dependência com a heurística.

### 5.3. Resultado da avaliação da heurística e escolha da versão padrão

Avaliação de `metricas/corretiva.py` contra o consenso (`python -m rotulagem.avaliar_heuristica`, 199 releases com release anterior; arquivos em `rotulagem/avaliacao/`):

| Versão | Regra | Precisão | Recall | F1 |
| :--- | :--- | :---: | :---: | :---: |
| v0 | Só o patch mudou (linha de base, ignora os commits) | 0,988 | 1,000 | 0,994 |
| v1 | Só o patch mudou **ou** há commit com fix/hotfix/revert | 0,503 | 1,000 | 0,669 |
| v2 | Só o patch mudou **e** há commit com fix/hotfix/revert | 1,000 | 0,671 | 0,803 |
| v3 | Só o patch mudou **e** nenhum commit `feat` | 0,986 | 0,878 | 0,929 |
| **v4 (padrão)** | Só o patch mudou **e** commits `feat` ≤ commits de correção | 0,987 | 0,951 | **0,969** |

- A **v1** (sugestão do enunciado) ficou abaixo do F1 mínimo de 0,70: quase toda release tem algum commit de "fix", então ela marca como corretivas também as releases minor e major.
- A **v0** tem o maior F1 porque reproduz exatamente o critério que os avaliadores usaram (seção 5.2). Ela é mantida apenas como linha de base que evidencia essa dependência.
- A **v4** foi adotada como padrão no pipeline (`HEURISTICA_PADRAO`) por combinar os dois sinais disponíveis (número de versão e mensagens dos commits) e não depender só do critério dos rótulos. Os 4 falsos negativos restantes são releases de patch com mais commits `feat` do que de correção (ver `erros_v4.csv`).
