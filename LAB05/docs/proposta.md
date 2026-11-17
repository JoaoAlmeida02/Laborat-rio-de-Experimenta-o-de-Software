# LAB05 — Proposta (Sprint 1)

**Título:** Corrigir o PHP2Shell custa desempenho? E quanto tempo a correção levou para chegar a quem usa?

**Grupo:** Lucas Ferreira (A — Planejamento e Método) · Vitor Veiga (B — Instrumentação e Operação) · João Almeida (C — Análise e Impacto)

**Versão:** 1ª versão (S01) — será revisada na S03.

---

## 1. Software estudado e contexto

O objeto de estudo é o **PHP**, o interpretador que executa a maior parte das aplicações web do mundo, em **operação** — não o seu repositório.

Em 21/10/2026, o projeto PHP publicou correções para duas vulnerabilidades críticas de execução remota de código sem autenticação, apelidadas de **PHP2Shell**:

- **CVE-2026-109618:** corrupção de memória durante o tratamento de falta de memória.
- **CVE-2026-109619:** estado de uma requisição sobrevive após ser liberado e pode ser reaproveitado por outra requisição no mesmo processo.

As duas têm nota CVSS v4.0 de 9.2 e entraram, em 26/10/2026, na lista da CISA de vulnerabilidades exploradas ativamente. Em 23/10/2026 foi divulgada uma terceira falha, a **CVE-2026-115560**, cuja mitigação recomendada até a próxima correção é `session.upload_progress.enabled=0`.

## 2. Evidências dos três critérios

Data de acesso de todas as fontes: **17/11/2026**. Os números do php.net, do endoflife.date e do Docker Hub são coletados por [`scripts/evidencias_php.py`](../scripts/evidencias_php.py) e ficam em [`dados/evidencias_php.csv`](../dados/evidencias_php.csv) e [`dados/evidencias_docker.csv`](../dados/evidencias_docker.csv). Os números do W3Techs foram registrados manualmente, porque os termos do site não permitem extração automatizada.

| Critério | Evidência | Fonte |
|---|---|---|
| **Real** | Linguagem e interpretador oficiais, com site, documentação e downloads mantidos pelo projeto PHP | [php.net](https://www.php.net/) |
| **Em operação** | Quatro ramos mantidos (8.2, 8.3, 8.4 e 8.5); último release em 21/10/2026 (8.5.12, 8.4.27, 8.3.36 e 8.2.35) | [API de releases do php.net](https://www.php.net/releases/active.php) |
| **Em operação** | 8.4 e 8.5 em suporte ativo; 8.2 e 8.3 só com correções de segurança (8.2 até 31/12/2026) | [endoflife.date](https://endoflife.date/php) |
| **Em operação** | AWS e Google Cloud publicaram boletins próprios sobre o PHP2Shell para seus runtimes PHP | [AWS](https://aws.amazon.com/security/security-bulletins/2026-143-aws/) · [Google Cloud](https://cloud.google.com/blog/products/identity-security/responding-to-core-php-vulnerabilities-cve-2026-109618-cve-2026-109619) |
| **Alto impacto** | O PHP é usado por **68,1%** dos sites cuja linguagem de servidor é conhecida | [W3Techs — PHP](https://w3techs.com/technologies/details/pl-php) |
| **Alto impacto** | O WordPress (escrito em PHP) roda em **38,5% de todos os sites** | [W3Techs — WordPress](https://w3techs.com/technologies/details/cm-wordpress) |
| **Alto impacto** | Imagens oficiais no Docker Hub: `php` com **1,40 bilhão** de downloads e `wordpress` com **1,51 bilhão** | [Docker Hub](https://hub.docker.com/_/php) |
| **Alto impacto** | Mais de **22,6 milhões** de instâncias expostas potencialmente vulneráveis ao PHP2Shell | [Palo Alto Unit 42](https://unit42.paloaltonetworks.com/cve-2026-109618-cve-2026-109619/) |

**Dado que reforça a relevância da RQ3:** segundo o W3Techs, **32,2%** dos sites com PHP ainda usam a versão 7 ou anterior, e mais **12,4%** usam 8.0 ou 8.1. São cerca de **44,6%** dos sites PHP em ramos que **não receberam correção oficial** da CVE-2026-109618. O W3Techs só enxerga sites que expõem a versão, então esse número é uma estimativa (ver ameaças, seção 11).

## 3. Perguntas de pesquisa

| Pergunta | Caminho | Tipo de estudo |
|---|---|---|
| **RQ1:** A correção do PHP2Shell (8.4.26 → 8.4.27) altera o desempenho de uma aplicação PHP real (WordPress)? | Rodar o software no ambiente do grupo | Experimento controlado |
| **RQ2:** A mitigação temporária `session.upload_progress.enabled=0` altera o desempenho? | Rodar o software no ambiente do grupo | Experimento controlado (2º fator) |
| **RQ3:** Quanto tempo distribuições Linux, provedores de nuvem e painéis de hospedagem levaram para publicar a correção? | Analisar dados de operação | Observacional (análise de sobrevivência) |

**Por que combinar caminhos:** o experimento (RQ1/RQ2) responde se corrigir tem custo; os dados de operação (RQ3) respondem quanto tempo a correção levou para ficar disponível a quem usa. Juntos, contam a história completa da correção, do lançamento pelo php.net até o servidor do usuário.

## 4. GQM

### Objetivo G1 (experimento)

> **Analisar** o interpretador PHP 8.4 (versão vulnerável 8.4.26 e corrigida 8.4.27)
> **com o propósito de** avaliar
> **com respeito ao** desempenho (vazão, latência e memória)
> **do ponto de vista de** quem opera aplicações PHP em produção (empresas de hospedagem e equipes de infraestrutura)
> **no contexto de** uma aplicação WordPress executada em contêineres Docker, com carga gerada localmente.

### Objetivo G2 (dados de operação)

> **Analisar** a publicação da correção do PHP2Shell por distribuidores do PHP
> **com o propósito de** caracterizar
> **com respeito ao** tempo até a correção ficar disponível
> **do ponto de vista de** quem usa PHP por meio de distribuições Linux, nuvens e painéis de hospedagem
> **no contexto dos** boletins e bases públicas de segurança, a partir de 21/10/2026.

### Perguntas e métricas

| Pergunta | Métrica | Entidade · atributo | Medida | Escala |
|---|---|---|---|---|
| Q1 (G1): A versão corrigida atende menos requisições? | Requisições por segundo | Produto · externo | Direta | Razão |
| Q2 (G1): A versão corrigida responde mais devagar, inclusive no pior caso? | Latência p50, p95 e p99 (ms) | Produto · externo | Direta | Razão |
| Q3 (G1): A versão corrigida consome mais memória? | Pico de memória do PHP-FPM (MB) | Recurso · externo | Direta | Razão |
| Q4 (G1): A mitigação altera as métricas acima? | Q1–Q3 com e sem mitigação | Produto · externo | Direta | Razão |
| Q5 (G1): A correção quebra a aplicação? | Taxa de erro HTTP (%) | Produto · externo | Derivada | Razão (proporção) |
| Q6 (G2): Quanto tempo cada distribuidor levou para publicar a correção? | Dias entre 21/10/2026 e a publicação | Processo · externo | Derivada | Razão |
| Q7 (G2): Distribuidores comerciais corrigem mais rápido que os comunitários? | Tempo até a correção por grupo | Processo · externo | Derivada | Razão (tempo) × nominal (grupo) |
| Q8 (G2): Que fração dos distribuidores ainda não corrigiu? | Proporção de censurados | Processo · externo | Derivada | Razão (proporção) |

## 5. Hipóteses

**RQ1 — efeito da correção (teste de equivalência, TOST, margem de ±5%):**
- H0: a diferença de desempenho entre 8.4.26 e 8.4.27 é de **5% ou mais** (as versões não são equivalentes).
- H1: a diferença é **menor que 5%** (as versões são equivalentes na prática).

Também é feito o teste de diferença tradicional (ANOVA fatorial 2×2):
- H0: a versão do PHP não altera a média do log da latência.
- H1: a versão do PHP altera a média do log da latência.

**RQ2 — efeito da mitigação:** mesmas hipóteses da RQ1, trocando a versão pela mitigação. Também é testada a **interação** versão × mitigação (H0: o efeito da mitigação é o mesmo nas duas versões).

**RQ3 — tempo até a correção:**
- H0: as curvas de tempo até a correção são iguais entre os grupos (comunitário, comercial, nuvem, hospedagem).
- H1: ao menos um grupo tem curva diferente.

## 6. Variáveis e desenho do experimento (RQ1 e RQ2)

| Elemento | Definição |
|---|---|
| **Variáveis independentes (fatores)** | Versão do PHP (8.4.26 × 8.4.27); mitigação (`session.upload_progress.enabled` 1 × 0) |
| **Variáveis dependentes** | Requisições/s; latência p50, p95 e p99; pico de memória do PHP-FPM; taxa de erro |
| **Variáveis controladas** | Máquina, versões do Nginx, do MariaDB, do WordPress e do k6; configuração do PHP-FPM e do OPcache; conteúdo do banco; núcleos de CPU separados para carga e servidor |
| **Objetos** | Três endpoints do WordPress: página inicial, API REST e um endpoint com sessão e upload |
| **Design** | Fatorial 2×2 completo, k repetições por tratamento, ordem aleatória com semente fixa |
| **Operação** | Em cada repetição: reiniciar os contêineres, aquecer por 30 s, medir por 60 s |
| **Instrumentação** | Docker Compose; k6 para carga e latência; `docker stats` para memória |

O valor de **k** sai da análise de poder feita com os dados do piloto (S01, João), como no LAB04.

## 7. As 7 categorias da pesquisa (1ª versão)

| Categoria | Classificação | Justificativa |
|---|---|---|
| **Natureza** | Aplicada | Gera conhecimento para uma decisão prática: atualizar o PHP e aplicar a mitigação tem custo? |
| **Objetivos** | Explicativa (RQ1/RQ2) e descritiva (RQ3) | RQ1/RQ2 investigam se a correção e a mitigação *causam* mudança de desempenho; RQ3 descreve como a correção se espalhou |
| **Abordagem** | Quantitativa | Todas as métricas são numéricas e analisadas com estatística |
| **Procedimentos** | Experimental (RQ1/RQ2) e documental (RQ3) | RQ1/RQ2 manipulam versão e mitigação; RQ3 usa registros públicos já existentes (boletins e bases de segurança) |
| **Tempo** | Transversal (RQ1/RQ2) e longitudinal retrospectivo (RQ3) | O experimento mede em uma janela única; a RQ3 acompanha cada distribuidor desde 21/10/2026 até a data da coleta |
| **Controle** | Alto, em laboratório (RQ1/RQ2); nenhum (RQ3) | No experimento, o grupo controla ambiente, carga e ordem; na RQ3, apenas observa o que já aconteceu |
| **Nível de evidência** | Experimento controlado (RQ1/RQ2); estudo observacional (RQ3) | RQ1/RQ2 permitem inferência causal no ambiente testado; RQ3 permite só associação (ex.: grupo × tempo), sem causalidade |

## 8. Plano de coleta

**Experimento (responsável: Vitor):**
1. Subir o ambiente com Docker Compose e conferir os 4 tratamentos.
2. Registrar o ambiente da máquina (CPU, RAM, sistema, versão do Docker).
3. **Piloto:** 2 repetições por tratamento, para medir duração e variabilidade.
4. **Coleta completa (S02):** k repetições por tratamento, em ordem aleatória, com retomada em caso de interrupção.

**Dados de operação (responsável: Lucas):**
1. Distribuidores e fontes listados em [`dados/rq3_fontes.csv`](../dados/rq3_fontes.csv): 16 distribuidores em 5 grupos, mais 3 fontes de referência (php.net, NVD e OSV).
2. Na S01, o João testa quais APIs trazem a data da correção.
3. Na S02, o script `scripts/coleta_correcoes.py` coleta as datas das fontes com API, e as demais são preenchidas à mão, com link e data de acesso.
4. Distribuidor sem correção na data da coleta entra como **censurado**.

## 9. Plano de análise

| RQ | Análise |
|---|---|
| RQ1/RQ2 | Descritiva (mediana e IQR por tratamento); ANOVA fatorial 2×2 sobre o log da latência (ART-ANOVA se os pressupostos falharem); TOST com margem de ±5%; tamanho do efeito (η² parcial) |
| RQ3 | Curva de Kaplan-Meier; tempo mediano até a correção; teste log-rank entre grupos |

Como a RQ3 terá poucos distribuidores (cerca de 16), a análise de poder do LAB04 será usada para deixar claro quanto o teste log-rank consegue detectar com essa amostra.

## 10. Armadilhas de medição

- **Lei de Goodhart:** se o grupo olhasse só a latência média, uma correção poderia "passar" mesmo piorando o pior caso. Por isso medimos p95 e p99.
- **Falácia de McNamara:** medir só desempenho ignora o que não é medido — a segurança. Uma versão mais rápida e vulnerável não é "melhor"; o estudo mede o custo, não decide sozinho.
- **Escalas:** latência e vazão são de razão, então médias, razões e percentuais são válidos; o grupo de distribuidor é nominal, então só entra como fator de comparação.

## 11. Ameaças à validade (primeira lista)

A lista completa, com mitigações, será feita na S02 em `docs/ameacas_validade.md`.

| Tipo | Ameaça inicial |
|---|---|
| **Conclusão** | Variabilidade entre execuções; poucos distribuidores na RQ3 |
| **Interna** | Ruído da máquina (outros processos, temperatura da CPU); ordem dos tratamentos |
| **Construto** | Carga sintética do k6 pode não representar o tráfego real; a data de publicação no boletim pode não ser a data em que o pacote ficou disponível |
| **Externa** | Uma máquina, uma aplicação (WordPress) e um ramo (8.4); W3Techs só enxerga sites que expõem a versão do PHP |

## 12. Ética

- Nenhum exploit é executado, nem localmente: o estudo mede o **custo da correção**, não explora a falha.
- Teste de carga **somente** nos contêineres do grupo.
- Coletas externas com no máximo 1 requisição por segundo, User-Agent genérico, respeitando termos de uso e robots.txt. O W3Techs não é coletado por script.
- Nenhum dado pessoal é coletado.

## 13. Reaproveitamento dos laboratórios anteriores

| Laboratório | O que é reaproveitado |
|---|---|
| LAB01 | Coleta automatizada via API (evidências e RQ3) e Kanban no GitHub Projects |
| LAB03 | Lead time e recuperação (DORA) aplicados ao tempo até a correção; tratamento de dados censurados |
| LAB04 | Análise de poder por simulação para definir k; escolha do teste; dashboard em Streamlit |

## 14. Coleta piloto

*A preencher pelo Vitor depois do piloto:* data, máquina, duração de cada execução e principais observações.
