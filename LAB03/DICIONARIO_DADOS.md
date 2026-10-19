# Dicionário de Dados - Dataset DORA (LAB03)

Este documento descreve detalhadamente cada uma das colunas presentes no arquivo consolidado [`data/dataset.csv`](file:///c:/Users/vitve/OneDrive/%C3%81rea%20de%20Trabalho/LAB-3/Laborat-rio-de-Experimenta-o-de-Software/LAB03/data/dataset.csv), gerado pelo módulo [`pipeline/consolidar.py`](file:///c:/Users/vitve/OneDrive/%C3%81rea%20de%20Trabalho/LAB-3/Laborat-rio-de-Experimenta-o-de-Software/LAB03/pipeline/consolidar.py).

O dataset consolida as quatro métricas clássicas do DORA (*DevOps Research and Assessment*), complementadas pelas métricas de retrabalho (*Rework Rate*, DORA 2024), metadados de projetos e categorizações de desempenho de engenharia.

---

## 1. Visão Geral da Tabela

| Coluna | Tipo | Unidade | Descrição Resumida |
| :--- | :--- | :--- | :--- |
| `repo` | String | Texto | Nome completo do repositório (`owner/repo`) |
| `owner` | String | Texto | Nome do proprietário ou organização no GitHub |
| `repo_nome` | String | Texto | Nome do repositório no GitHub |
| `stars` | Inteiro | Contagem | Número de estrelas (*stargazers*) |
| `forks` | Inteiro | Contagem | Número de bifurcações (*forks*) |
| `open_issues` | Inteiro | Contagem | Número de issues abertas |
| `language` | String | Categórica | Linguagem de programação principal |
| `contribuidores` | Inteiro | Contagem | Número total aproximado de contribuidores |
| `idade_anos` | Float | Anos | Idade do repositório em anos na data fim |
| `idade_dias` | Float | Dias | Idade do repositório em dias na data fim |
| `created_at` | String | ISO 8601 | Data e hora de criação do repositório no GitHub |
| `default_branch` | String | Texto | Branch padrão monitorada (ex.: `main`, `master`) |
| `deploy_frequency_semana` | Float | Deploys/Semana | Frequência de deploy normalizada por semana |
| `n_entregas` | Inteiro | Contagem | Total de releases publicadas válidas na janela |
| `n_commits` | Inteiro | Contagem | Total de commits analisados entre releases |
| `lead_time_commit_h` | Float | Horas | Lead Time variante (a): do commit à release |
| `lead_time_release_h` | Float | Horas | Lead Time variante (b): intervalo entre releases |
| `cfr_ci` | Float | Proporção [0, 1] | Change Failure Rate variante (a): taxa de falhas em CI |
| `cfr_entrega` | Float | Proporção [0, 1] | Change Failure Rate variante (b): releases seguidas de correção |
| `cfr_entrega_avaliadas` | Inteiro | Contagem | Total de releases elegíveis para avaliação de correção |
| `cfr_entrega_censuradas` | Inteiro | Contagem | Total de releases dos últimos 7 dias da janela |
| `rework_rate` | Float | Proporção [0, 1] | Taxa de retrabalho (proporção de releases corretivas) |
| `tempo_recuperacao_s` | Float | Segundos | Mediana do Tempo de Recuperação de Serviço em CI |
| `tempo_recuperacao_h` | Float | Horas | Mediana do Tempo de Recuperação convertida em horas |
| `recuperacao_proporcao_censurados` | Float | Proporção [0, 1] | Proporção de episódios de falha de CI sem recuperação |
| `total_runs` | Inteiro | Contagem | Total de execuções de workflow coletadas |
| `total_episodios_recuperacao` | Inteiro | Contagem | Total de episódios de falha observados em workflows |
| `ignoradas_sem_anterior` | Inteiro | Contagem | Releases ignoradas por ausência de release base anterior |
| `ignoradas_compare_404` | Inteiro | Contagem | Releases com erro 404 na API de comparação do GitHub |
| `ignoradas_sem_commits` | Inteiro | Contagem | Releases onde o diff indicou 0 commits |
| `categoria_dora_frequencia` | String | Categórica | Categoria DORA da deployment frequency (C1) |
| `categoria_dora_lead_time` | String | Categórica | Categoria DORA do lead time por release, variante (a) (C1) |
| `categoria_dora_cfr` | String | Categórica | Categoria DORA do CFR por CI, variante (a) (C1) |
| `categoria_dora_recuperacao` | String | Categórica | Categoria DORA do tempo de recuperação (C1) |
| `categoria_dora_geral` | String | Categórica | Categoria geral DORA da combinação de referência C1 |
| `categoria_dora_n_metricas` | Inteiro | Contagem | Quantas das 4 métricas puderam ser classificadas |

---

## 2. Detalhamento e Fórmulas por Coluna

### 2.1 Metadados do Repositório

#### `repo`
- **Tipo:** String (`VARCHAR`)
- **Exemplo:** `psf/requests`
- **Definição:** Identificador canônico do repositório no formato `{owner}/{repo}`. Atua como chave primária do dataset.

#### `owner`
- **Tipo:** String
- **Exemplo:** `psf`
- **Definição:** Login da conta de usuário ou organização proprietária no GitHub.

#### `repo_nome`
- **Tipo:** String
- **Exemplo:** `requests`
- **Definição:** Nome do repositório no GitHub.

#### `stars`
- **Tipo:** Inteiro
- **Exemplo:** `51200`
- **Definição:** Quantidade total de estrelas registradas no momento da coleta (`stargazers_count`). Usado na amostragem estratificada.

#### `forks`
- **Tipo:** Inteiro
- **Exemplo:** `9200`
- **Definição:** Quantidade de bifurcações públicas ativas (`forks_count`).

#### `open_issues`
- **Tipo:** Inteiro
- **Exemplo:** `240`
- **Definição:** Número de issues e pull requests abertos (`open_issues_count`).

#### `language`
- **Tipo:** String
- **Exemplo:** `Python`
- **Definição:** Linguagem de programação predominante informada pela API do GitHub. Repositórios sem linguagem identificada recebem `"Outra"`.

#### `contribuidores`
- **Tipo:** Inteiro
- **Exemplo:** `412`
- **Definição:** Número total de contribuidores com commits no repositório.
- **Fórmula/Extração:** Obtido via paginação otimizada (`GET /contributors?per_page=1&anon=true`) através da extração do parâmetro `page` no cabeçalho HTTP `Link` com relação `rel="last"`.

#### `idade_anos`
- **Tipo:** Float
- **Unidade:** Anos
- **Fórmula:**
  $$\text{idade\_anos} = \frac{\text{idade\_dias}}{365.25}$$

#### `idade_dias`
- **Tipo:** Float
- **Unidade:** Dias
- **Fórmula:**
  $$\text{idade\_dias} = \max\left(\frac{T_{\text{fim}} - T_{\text{criacao}}}{86400}, 0\right)$$
  onde $T_{\text{fim}}$ é a data final da janela (ex.: `2025-12-31T23:59:59Z`) e $T_{\text{criacao}}$ é o campo `created_at`.

#### `created_at`
- **Tipo:** String (ISO 8601 UTC)
- **Exemplo:** `2011-02-13T18:00:00Z`
- **Definição:** Carimbo de data/hora oficial de criação do repositório.

#### `default_branch`
- **Tipo:** String
- **Exemplo:** `main` ou `master`
- **Definição:** Nome da branch principal do repositório onde ocorrem as integrações e pushes analisados.

---

### 2.2 Frequência de Deploy (*Deployment Frequency*)

#### `deploy_frequency_semana`
- **Tipo:** Float
- **Unidade:** Deploys / Semana
- **Definição:** Taxa média de releases publicadas por semana durante a janela de observação.
- **Fórmula:**
  $$\text{deploy\_frequency\_semana} = \frac{\text{n\_entregas}}{\left(\frac{T_{\text{fim}} - T_{\text{inicio}}}{7 \times 86400}\right)}$$

#### `n_entregas`
- **Tipo:** Inteiro
- **Definição:** Número total de releases publicadas (`draft == false`, sem pré-releases na modalidade padrão) com data de publicação dentro da janela temporal.

#### `n_commits`
- **Tipo:** Inteiro
- **Definição:** Somatório de commits contidos nos intervalos entre todas as releases válidas da janela.

---

### 2.3 Tempo de Espera para Mudanças (*Lead Time for Changes*)

#### `lead_time_commit_h` (Variante A)
- **Tipo:** Float (ou `null` se ausente)
- **Unidade:** Horas
- **Definição:** Mediana do tempo decorrido entre o primeiro commit de uma entrega e a data de publicação da respectiva release.
- **Fórmula:**
  $$\text{lead\_time\_commit\_h} = \text{mediana}\left(\left\{ \frac{T_{\text{release}, i} - T_{\text{primeiro\_commit}, i}}{3600} \;\middle|\; i \in \text{entregas válidas} \right\}\right)$$

#### `lead_time_release_h` (Variante B)
- **Tipo:** Float (ou `null` se ausente)
- **Unidade:** Horas
- **Definição:** Mediana do intervalo de tempo entre releases consecutivas publicadas no repositório.
- **Fórmula:**
  $$\text{lead\_time\_release\_h} = \text{mediana}\left(\left\{ \frac{T_{\text{release}, i} - T_{\text{release}, i-1}}{3600} \;\middle|\; i \ge 2 \right\}\right)$$

---

### 2.4 Taxa de Falha em Mudanças (*Change Failure Rate - CFR*) e Retrabalho

#### `cfr_ci` (Variante A - Execuções de CI)
- **Tipo:** Float [0.0 a 1.0] (ou `null` se nenhum run válido)
- **Definição:** Proporção de execuções de workflow de CI que resultaram em quebra ou timeout na branch principal. Runs cancelados (`cancelled`), pulados (`skipped`) ou neutros são ignorados.
- **Fórmula:**
  $$\text{cfr\_ci} = \frac{N_{\text{falhas}}}{N_{\text{sucessos}} + N_{\text{falhas}}}$$
  onde $N_{\text{falhas}}$ inclui `conclusion` igual a `failure`, `timed_out` e `startup_failure`.

#### `cfr_entrega` (Variante B - Releases Corretivas / Hotfixes)
- **Tipo:** Float [0.0 a 1.0] (ou `null` se não houver entregas avaliadas)
- **Definição:** Proporção de releases que falharam na produção, onde a falha é caracterizada pela publicação de uma **release corretiva em até 7 dias corridos** subsequentes, detectada via Heurística v4.
- **Fórmula:**
  $$\text{cfr\_entrega} = \frac{N_{\text{releases com falha}}}{N_{\text{entregas avaliadas}}}$$
  onde entregas ocorridas nos últimos 7 dias da janela de observação são consideradas censuradas e excluídas do denominador.

#### `cfr_entrega_avaliadas`
- **Tipo:** Inteiro
- **Definição:** Quantidade de releases publicadas a mais de 7 dias do fim da janela (possibilitando a observação completa do período de correção).

#### `cfr_entrega_censuradas`
- **Tipo:** Inteiro
- **Definição:** Quantidade de releases publicadas nos últimos 7 dias da janela temporal (onde não é possível garantir se houve ou não correção nos 7 dias subsequentes).

#### `rework_rate` (Taxa de Retrabalho - DORA 2024 / RQ 08)
- **Tipo:** Float [0.0 a 1.0] (ou `null`)
- **Definição:** Proporção de releases corretivas sobre o total de transições entre releases observadas no repositório, classificada pela Heurística v4.
- **Fórmula:**
  $$\text{rework\_rate} = \frac{\sum_{i=2}^{N} \text{eh\_corretiva}(\text{tag}_{i-1}, \text{tag}_{i}, \text{commits}_i)}{N - 1}$$
  *Heurística v4:* Uma release é corretiva se apenas o número de *patch* do SemVer foi incrementado E o número de commits de novas funcionalidades (`feat`) é menor ou igual ao número de commits de correção (`fix`, `bugfix`, `hotfix`, `revert`).

---

### 2.5 Tempo de Recuperação de Serviço (*Time to Restore Service*)

#### `tempo_recuperacao_s`
- **Tipo:** Float (segundos) ou `null`
- **Definição:** Mediana da duração dos episódios de falha observados nos workflows de CI da branch principal.
- **Fórmula:**
  $$\text{duração\_episódio} = T_{\text{sucesso}} - T_{\text{primeira\_falha}}$$
  $$\text{tempo\_recuperacao\_s} = \text{mediana}\left(\left\{ \text{duração\_episódio}_j \;\middle|\; j \in \text{episódios não censurados} \right\}\right)$$

#### `tempo_recuperacao_h`
- **Tipo:** Float (horas) ou `null`
- **Fórmula:**
  $$\text{tempo\_recuperacao\_h} = \frac{\text{tempo\_recuperacao\_s}}{3600}$$

#### `recuperacao_proporcao_censurados`
- **Tipo:** Float [0.0 a 1.0]
- **Definição:** Proporção de episódios de falha de CI que permaneceram sem recuperação até o final do período coletado (falhas em aberto).
- **Fórmula:**
  $$\text{recuperacao\_proporcao\_censurados} = \frac{N_{\text{episódios censurados}}}{N_{\text{total de episódios}}}$$

#### `total_runs`
- **Tipo:** Inteiro
- **Definição:** Quantidade total de workflow runs de evento `push` analisados na branch padrão do repositório.

#### `total_episodios_recuperacao`
- **Tipo:** Inteiro
- **Definição:** Quantidade total de sequências de quebra de CI observadas (episódios abertos e fechados).

---

### 2.6 Releases Ignoradas e Casos de Borda

#### `ignoradas_sem_anterior`
- **Tipo:** Inteiro
- **Definição:** Primeira release da janela temporal que não possui release anterior mapeada no intervalo coletado para cálculo de lead time b e rework rate.

#### `ignoradas_compare_404`
- **Tipo:** Inteiro
- **Definição:** Releases onde a chamada `GET /repos/{owner}/{repo}/compare/{base}...{head}` retornou HTTP 404 (ex.: reescrita de tags ou histórico git desconexo).

#### `ignoradas_sem_commits`
- **Tipo:** Inteiro
- **Definição:** Releases em que o endpoint de comparação de tags retornou zero commits.

---

### 2.7 Categorização de Desempenho DORA

Baseadas na tabela de referência fixa do enunciado (seção 5, RQ 07). As colunas seguem a **combinação de referência C1**: unidade de deploy = release, lead time variante (a) e CFR variante (a).

#### `categoria_dora_frequencia`
- **Tipo:** String enum (`Elite`, `High`, `Medium`, `Low`, ou `null`)
- **Origem:** `deploy_frequency_semana`
- **Limiares:**
  - **Elite:** $\ge 7$ entregas por semana
  - **High:** $\ge 1$ e $< 7$ por semana
  - **Medium:** $\ge 1$ por mês ($\approx 0{,}23$ por semana) e $< 1$ por semana
  - **Low:** $< 1$ por mês

#### `categoria_dora_lead_time`
- **Tipo:** String enum (`Elite`, `High`, `Medium`, `Low`, ou `null`)
- **Origem:** `lead_time_release_h` (variante a)
- **Limiares:**
  - **Elite:** $< 1$ dia
  - **High:** $1$ dia a $< 1$ semana
  - **Medium:** $1$ semana a $< 30$ dias
  - **Low:** $\ge 30$ dias

#### `categoria_dora_cfr`
- **Origem:** `cfr_ci` (variante a)
- **Tipo:** String enum (`Elite`, `High`, `Medium`, `Low`, ou `null`)
- **Limiares:**
  - **Elite:** $\text{CFR} \le 15\%$
  - **High:** $15\% < \text{CFR} \le 30\%$
  - **Medium:** $30\% < \text{CFR} \le 45\%$
  - **Low:** $\text{CFR} > 45\%$

#### `categoria_dora_recuperacao`
- **Tipo:** String enum (`Elite`, `High`, `Medium`, `Low`, ou `null`)
- **Limiares:**
  - **Elite:** Tempo $< 1\text{ hora}$ ($< 3.600\text{s}$)
  - **High:** $1\text{ hora} \le \text{Tempo} < 1\text{ dia}$ ($< 86.400\text{s}$)
  - **Medium:** $1\text{ dia} \le \text{Tempo} < 1\text{ semana}$ ($< 604.800\text{s}$)
  - **Low:** $\text{Tempo} \ge 1\text{ semana}$ ($\ge 604.800\text{s}$)

#### `categoria_dora_geral`
- **Tipo:** String enum (`Elite`, `High`, `Medium`, `Low`, ou `null`)
- **Definição:** Mediana das notas das 4 métricas (`Elite=4`, `High=3`, `Medium=2`, `Low=1`), arredondada para baixo (`floor`). Exemplo do enunciado: notas (4, 3, 3, 1) → mediana 3 → `High`. Métricas sem valor ficam fora da mediana; `categoria_dora_n_metricas` informa quantas foram usadas.

#### `categoria_dora_n_metricas`
- **Tipo:** Inteiro (0 a 4)
- **Definição:** Número de métricas com valor disponível para compor `categoria_dora_geral`.
