# Protocolo de Validação Manual da Amostra-Ouro

> **Seção da Metodologia do Artigo (Padrão SBC)**  
> **Subseção:** *Protocolo de Validação Manual e Concordância Interobservadores*  
> **Contexto:** Sprint 2 (Lab03S02) · Mineração de Métricas DORA

---

## 3.X. Protocolo de Validação Manual e Amostra-Ouro

Para avaliar a eficácia e calibrar as métricas de qualidade (Precisão, Revocação e $F_1\text{-Score}$) das heurísticas automatizadas de detecção de entregas corretivas (Change Failure Rate — CFR) e verificar os fatores arquiteturais dos projetos, foi construída uma base de referência padronizada (*ground truth* ou amostra-ouro), apoiada em rigoroso protocolo de rotulagem manual cega e análise estatística de concordância interobservadores.

### 3.X.1. Procedimento de Amostragem

A população elegível é constituída por repositórios de código aberto hospedados no GitHub que atenderam a todos os filtros de inclusão e integridade de pipeline (possuir histórico ativo no GitHub Actions, não ser fork ou espelho e contar com histórico rastreável).

A partir do universo de 300 repositórios consolidados no funil de seleção, adotou-se o seguinte processo amostral determinístico:

1. **Amostragem de Repositórios:** Sorteio pseudoaleatório de $n = 60$ repositórios utilizando semente determinística fixa (`random_state=42`), garantindo reprodutibilidade irrestrita da extração.
2. **Amostragem de Entregas (Releases):** Para cada repositório sorteado, extraiu-se a totalidade das releases publicadas cronologicamente. Nos projetos com mais de 5 entregas, foram sorteadas até 5 releases de forma pseudoaleatória (`random_state=42`), enquanto em projetos com 5 ou menos entregas, todas as releases publicadas foram incorporadas à amostra.
3. **Composição Final:** A amostra consolidou um total de 214 releases distribuídas entre os 45 repositórios que retornaram releases publicadas no GitHub, abrangendo diversas linguagens de programação, tamanhos de equipe e paradigmas arquiteturais. A amostra ficou abaixo do planejado (60 repositórios e 300 releases) e inclui releases anteriores à janela de observação; os motivos e impactos estão descritos na Seção 3.X.6.

### 3.X.2. Protocolo de Avaliação Cega (*Blind Review*)

A rotulagem foi realizada de modo estritamente independente por três pesquisadores (Avaliador A, Avaliador B e Avaliador C). Para mitigar potenciais vieses de confirmação, foi imposta avaliação cega:

- Cada integrante recebeu sua respectiva planilha de trabalho (`rotulos_A.csv`, `rotulos_B.csv`, `rotulos_C.csv`).
- As planilhas continham apenas os metadados brutos (nome do repositório, tag da release, data de publicação, tag anterior) e **links diretos** para a página oficial da release e para a interface de comparação de código do GitHub (`https://github.com/{owner}/{repo}/compare/{tag_ant}...{tag}`).
- Em nenhuma etapa do processo os avaliadores tiveram acesso aos resultados preditos pela heurística computacional antes da consolidação do consenso.

### 3.X.3. Dimensões Operacionais de Rotulagem

Para cada release da amostra-ouro, os três avaliadores classificaram independentemente três dimensões:

1. **Tipo de Projeto (`tipo_projeto`):** Categoria arquitetural do repositório:
   - `biblioteca_framework`: Módulos, pacotes reutilizáveis ou SDKs distribuídos via gerenciadores de dependências;
   - `aplicacao_servico`: Aplicações completas para usuário final, plataformas web ou serviços backend executáveis;
   - `ferramenta_cli`: Scripts e utilitários executados via linha de comando no terminal;
   - `outro`: Documentações, curadorias ou amostras sem artefato funcional.
2. **Entrega Real (`entrega_real`):** Avalia se a release representou um incremento de valor funcional ao software (`sim`), uma alteração meramente burocrática/vazia sem código (`nao`), ou evento com rastreabilidade indisponível (`incerto`).
3. **Release Corretiva (`corretiva`):** Avalia se o objetivo precípuo da release consistiu em sanar incidentes, falhas em produção, vulnerabilidades de segurança ou regressões (`sim`), ou se consistiu em evolução funcional planejada com novas *features* (`nao`).

---

### 3.X.4. Aferição da Concordância Interobservadores

A consistência da rotulagem manual entre os múltiplos avaliadores foi mensurada formalmente por meio de duas medidas estatísticas complementares:

#### Kappa de Fleiss Global ($\kappa_{\text{Fleiss}}$)
Calculado com base nas tabelas de contingência multiavaliador via rotinas da biblioteca `statsmodels.stats.inter_rater` (`aggregate_raters` e `fleiss_kappa`). A interpretação seguiu a escala canônica de Landis & Koch (1977):

$$\kappa = \frac{\bar{P} - \bar{P}_e}{1 - \bar{P}_e}$$

Onde $\bar{P}$ representa a proporção média de concordância observada por item e $\bar{P}_e$ a concordância esperada unicamente pelo acaso.

#### Kappa de Cohen Par a Par ($\kappa_{\text{Cohen}}$)
Como inovação metodológica do grupo, foi computado o Kappa de Cohen pareado ($A \times B$, $A \times C$, $B \times C$) utilizando `scikit-learn`. Essa análise granular permite auditar desvios sistemáticos ou viés de severidade de algum avaliador frente aos pares.

**Tabela 1: Coeficientes de Concordância Interobservadores Obtidos na Amostra-Ouro**

| Dimensão Avaliada | $\kappa_{\text{Fleiss}}$ Global | Interpretação (Landis & Koch, 1977) | $A \times B$ ($\kappa_{\text{Cohen}}$) | $A \times C$ ($\kappa_{\text{Cohen}}$) | $B \times C$ ($\kappa_{\text{Cohen}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Tipo de Projeto** | **0,9621** | Quase Perfeita (*Almost Perfect*) | 0,9467 | 0,9925 | 0,9466 |
| **Entrega Real** | **0,7667** | Substancial (*Substantial*) | 0,8299 | 0,8183 | 0,6586 |
| **Release Corretiva** | **0,9476** | Quase Perfeita (*Almost Perfect*) | 0,9509 | 0,9704 | 0,9216 |

Os índices obtidos indicam concordância alta nas três dimensões, acima do limiar de 0,70 comumente adotado na literatura de Engenharia de Software Empírica. No caso da dimensão `corretiva`, porém, parte dessa concordância decorre do uso de um critério comum e objetivo (o incremento apenas no número de *patch*), como discutido na Seção 3.X.6.

---

### 3.X.5. Protocolo de Resolução de Divergências e Consenso

Após o término da rotulagem cega individual, foi executado o algoritmo de consolidação (`rotulagem/consenso.py`), aplicando as seguintes regras determinísticas:

1. **Unanimidade ($3 \times 0$):** Adotação direta do rótulo compartilhado pelos três avaliadores.
2. **Maioria Simples ($2 \times 1$):** Atribuição do valor sufragado por 2 dos 3 avaliadores, registrando o parecer minoritário no log de auditoria.
3. **Empate Triplo ($1 \times 1 \times 1$):** Classificação do item com o identificador transitório `empate`, acionando deliberação colegiada.
4. **Relatório Automatizado de Divergências (`rotulagem/divergencias.md`):** Como inovação operacional, foi sintetizada uma pauta em Markdown contendo todas as 20 divergências registradas, estruturada com hiperlinks diretos para a release e código diferencial no GitHub.

Na consolidação das 214 releases avaliadas, **96,7%** dos julgamentos de `tipo_projeto`, **97,7%** de `entrega_real` e **96,3%** de `corretiva` foram estabelecidos por unanimidade, com as divergências residuais pacificadas com sucesso na base final (`rotulagem/consenso.csv`), consolidando o *ground truth* utilizado para aferição do CFR.

---

### 3.X.6. Desvios da Amostra e Critério Prático de Release Corretiva

**Tamanho e período da amostra.** Dos 60 repositórios sorteados, 15 não retornaram nenhuma release publicada e foram excluídos, restando 45. Quatro desses repositórios tinham menos de 5 releases no histórico, o que resultou em 214 releases rotuladas em vez das 300 previstas. Além disso, as releases foram sorteadas do histórico completo de cada repositório (de 2013 a 2026), e não apenas da janela de observação (2025). Ambos os desvios decorrem de a amostra-ouro ter sido sorteada antes da aplicação do critério mínimo de inclusão (≥ 5 releases e ≥ 50 execuções de CI na janela). Como consequência, as estimativas de concordância e de precisão, revocação e F1 têm menor precisão estatística, e a validação da heurística se refere a releases em geral, e não especificamente às releases da janela em que o CFR (b) é medido.

**Critério prático de `corretiva`.** O protocolo de rotulagem lista o incremento exclusivo no número de *patch* do SemVer como uma das evidências de release corretiva, e os avaliadores o usaram como evidência principal, conferindo notas de release e commits. Das 199 releases com release anterior, as 82 rotuladas como corretivas no consenso são todas mudanças apenas de *patch*; das 83 mudanças apenas de *patch*, somente uma foi rotulada como não corretiva; e nenhuma release *minor* ou *major* foi considerada corretiva. Como as heurísticas automáticas também se baseiam no número de *patch*, o rótulo humano não é totalmente independente do *proxy* avaliado, e o F1 obtido tende a superestimar a qualidade da heurística. Esse ponto é tratado como ameaça à validade de construto, e os falsos positivos e falsos negativos de cada versão da heurística são analisados individualmente. Para uma replicação, recomenda-se rotular a dimensão `corretiva` com as tags de versão ocultas.
