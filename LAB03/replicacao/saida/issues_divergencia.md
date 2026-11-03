## [Replicação] Divergência na classificação DORA para o repositório `Canner/WrenAI`

Durante a replicação cruzada independente do pipeline, constatou-se que o repositório `Canner/WrenAI` migrou de categoria DORA:
- **Categoria Original Esperada:** `High`
- **Categoria Replicada Obtida:** `Medium`

### Comparativo das Métricas Individuais:
| Métrica | Original (Esperado) | Replicado (Obtido) | Diferença Relativa |
|---|---|---|---|
| Deployment frequency | 0.4986 | 0.4759 | 4.5% |
| Lead time (a) release | 167.3600 | 169.6600 | 1.4% |
| Lead time (b) commit | 57.8100 | 57.4600 | 0.6% |
| CFR (a) CI | 0.2407 | 0.2301 | 4.4% |
| CFR (b) entrega | 0.2308 | 0.2183 | 5.4% |
| Tempo de recuperação | - | - | - |

### Evidências e Hipótese de Diagnóstico:
- **Novos Commits / Releases:** Verificar se foram publicadas novas releases no default branch entre a data da coleta original e a data da replicação.
- **Tratamento de Rate Limit:** Averiguar se alguma chamada de API retornou cota excedida resultando em paginação truncada de workflow runs ou releases.
- **Filtros de Data:** Checar se a janela de 12 meses está estritamente delimitada no script replicado.

Solicitamos a verificação das evidências acima para mitigar divergências no estudo de reprodutibilidade.

---

## [Replicação] Divergência na classificação DORA para o repositório `canonical/lxd`

Durante a replicação cruzada independente do pipeline, constatou-se que o repositório `canonical/lxd` migrou de categoria DORA:
- **Categoria Original Esperada:** `Low`
- **Categoria Replicada Obtida:** `Medium`

### Comparativo das Métricas Individuais:
| Métrica | Original (Esperado) | Replicado (Obtido) | Diferença Relativa |
|---|---|---|---|
| Deployment frequency | 0.1342 | 0.1377 | 2.6% |
| Lead time (a) release | 13451.3100 | 12643.9800 | 6.0% |
| Lead time (b) commit | 4958.8100 | 5089.1800 | 2.6% |
| CFR (a) CI | 0.1421 | 0.1589 | 11.8% |
| CFR (b) entrega | 0.0000 | 0.0599 | 6.0% |
| Tempo de recuperação | 24.9500 | 23.3900 | 6.2% |

### Evidências e Hipótese de Diagnóstico:
- **Novos Commits / Releases:** Verificar se foram publicadas novas releases no default branch entre a data da coleta original e a data da replicação.
- **Tratamento de Rate Limit:** Averiguar se alguma chamada de API retornou cota excedida resultando em paginação truncada de workflow runs ou releases.
- **Filtros de Data:** Checar se a janela de 12 meses está estritamente delimitada no script replicado.

Solicitamos a verificação das evidências acima para mitigar divergências no estudo de reprodutibilidade.

---

## [Replicação] Divergência na classificação DORA para o repositório `replicate/cog`

Durante a replicação cruzada independente do pipeline, constatou-se que o repositório `replicate/cog` migrou de categoria DORA:
- **Categoria Original Esperada:** `High`
- **Categoria Replicada Obtida:** `Medium`

### Comparativo das Métricas Individuais:
| Métrica | Original (Esperado) | Replicado (Obtido) | Diferença Relativa |
|---|---|---|---|
| Deployment frequency | 0.6712 | 0.6800 | 1.3% |
| Lead time (a) release | 106.9700 | 99.2600 | 7.2% |
| Lead time (b) commit | 75.8500 | 79.3000 | 4.5% |
| CFR (a) CI | 0.0568 | 0.0500 | 12.0% |
| CFR (b) entrega | 0.5143 | 0.5394 | 4.9% |
| Tempo de recuperação | 21.7700 | 24.7300 | 13.6% |

### Evidências e Hipótese de Diagnóstico:
- **Novos Commits / Releases:** Verificar se foram publicadas novas releases no default branch entre a data da coleta original e a data da replicação.
- **Tratamento de Rate Limit:** Averiguar se alguma chamada de API retornou cota excedida resultando em paginação truncada de workflow runs ou releases.
- **Filtros de Data:** Checar se a janela de 12 meses está estritamente delimitada no script replicado.

Solicitamos a verificação das evidências acima para mitigar divergências no estudo de reprodutibilidade.

---
