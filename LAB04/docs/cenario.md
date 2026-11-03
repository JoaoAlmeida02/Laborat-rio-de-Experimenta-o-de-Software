# Cenário e Expectativa Prévia

## Cenário

- **Pergunta:** A taxa de falha do CI do repositório `pytest-dev/pytest` na branch `main` (evento `push`) está acima da meta de 5%?
- **Hipótese nula ($H_0$):** $p = 0,05$ (a taxa de falha está dentro da meta de 5%).
- **Hipótese alternativa ($H_1$):** $p > 0,05$ (a taxa de falha está acima da meta de 5%).
- **Nível de significância ($\alpha$):** $0,05$.
- **Justificativa do teste unicaudal à direita:** O interesse prático de monitoramento do CI é detectar apenas quando a taxa de falha ultrapassa o limite aceitável de 5% ($p > 0,05$). Uma taxa de falha abaixo de 5% indica bom funcionamento do pipeline e não exige intervenção, portanto desvios à esquerda não configuram problema a ser detectado pelo teste.

## Expectativa prévia

Antes de executar as simulações de Monte Carlo, registramos as hipóteses do grupo sobre o comportamento do **teste Z para proporção** e do **teste binomial exato**, a serem verificadas empiricamente nas sprints seguintes:

1. **Controle do erro tipo I e conservadorismo:** Esperamos que o **teste binomial exato** se saia melhor na garantia do nível de significância nominal em qualquer tamanho amostral, mantendo a taxa de erro tipo I sempre menor ou igual a $\alpha = 0,05$. Por trabalhar com uma distribuição discreta ($X \sim \text{Bin}(n, p_0)$), ele tende a ser **conservador** (erro tipo I efetivo abaixo de 5%).
2. **Violação de pressuposto com $n$ pequeno:** O teste Z depende da aproximação normal da binomial, cujo pressuposto exige $n \cdot p_0 \ge 10$ e $n \cdot (1 - p_0) \ge 10$ (para $p_0 = 0,05$, isso requer $n \ge 200$). Quando $n$ é pequeno (por exemplo, $n \in \{10, 20, 30, 50\}$, onde $n \cdot p_0 < 10$), a distribuição binomial é fortemente assimétrica à direita e a aproximação normal falha. Nessa situação, esperamos que o **teste Z se desvie de 5%**, oscilando conforme $n$ e podendo ficar **liberal** (erro tipo I acima de $\alpha$), o que torna o teste binomial exato mais confiável.
3. **Poder estatístico com $n = 300$:** Como para $n = 300$ o pressuposto $n \cdot p_0 = 15 \ge 10$ é atendido, esperamos que os dois testes apresentem **poder estatístico parecido** na amostra grande (com o teste Z possivelmente exibindo poder ligeiramente maior apenas por ser menos conservador na cauda discreta), enquanto em amostras pequenas as diferenças entre as curvas de poder e de erro tipo I devem se acentuar.

> Todas as afirmações acima são **hipóteses prévias** formuladas a partir da teoria estatística e serão testadas e confrontadas com os resultados das simulações nas etapas seguintes do laboratório.

## Exemplo simulado e interpretação

Utilizando a semente fixa `np.random.default_rng(42)` em `scripts/simulacao.py`, geramos um conjunto simulado calibrado pelos parâmetros observados nos dados reais ($n = 300$ e $p = \hat{p}_{\text{real}} = 10/300 \approx 0,0333$) e um segundo exemplo simulado com efeito verdadeiro acima da meta ($n = 300$ e $p = 0,09$), além da conferência nos dados reais:

### 1. Conferência nos dados reais ($n = 300$, $x = 10$, $\hat{p} = 0,0333$)

| Teste | Estatística | p-valor (unicaudal) | Tamanho do efeito ($h$ de Cohen) | Decisão ($\alpha = 0,05$) |
|---|---|---|---|---|
| Teste Z para proporção | $z = -1,325$ | $0,9073$ ($0,907$) | $h = -0,084$ | Não rejeita $H_0$ |
| Teste binomial exato | $x = 10$ | $0,9350$ ($0,935$) | $h = -0,084$ | Não rejeita $H_0$ |

### 2. Exemplo simulado 1 — Calibrado com os dados reais ($n = 300$, $p = 0,0333 \rightarrow x = 12$, $\hat{p} = 0,0400$)

| Teste | Estatística | p-valor (unicaudal) | Tamanho do efeito ($h$ de Cohen) | Decisão ($\alpha = 0,05$) |
|---|---|---|---|---|
| Teste Z para proporção | $z = -0,795$ | $0,7866$ ($0,787$) | $h = -0,048$ | Não rejeita $H_0$ |
| Teste binomial exato | $x = 12$ | $0,8220$ ($0,822$) | $h = -0,048$ | Não rejeita $H_0$ |

### 3. Exemplo simulado 2 — Cenário com efeito ($n = 300$, $p = 0,0900 \rightarrow x = 26$, $\hat{p} = 0,0867$)

| Teste | Estatística | p-valor (unicaudal) | Tamanho do efeito ($h$ de Cohen) | Decisão ($\alpha = 0,05$) |
|---|---|---|---|---|
| Teste Z para proporção | $z = 2,914$ | $0,0018$ ($0,002$) | $h = 0,147$ | Rejeita $H_0$ |
| Teste binomial exato | $x = 26$ | $0,0050$ ($0,005$) | $h = 0,147$ | Rejeita $H_0$ |

### Interpretação dos resultados

- **Significado do p-valor:** No Exemplo Simulado 1 ($x = 12$ falhas em $n = 300$), o p-valor representa a probabilidade de observar 12 ou mais falhas ($X \ge 12$) caso a verdadeira taxa de falha do CI fosse exatamente 5% ($H_0: p = 0,05$). Essa probabilidade é alta tanto pela aproximação normal ($78,66\%$) quanto pela distribuição binomial exata ($82,20\%$). Já no Exemplo Simulado 2 ($x = 26$ falhas), a probabilidade de observar 26 ou mais falhas sob $H_0$ é muito baixa ($0,18\%$ no teste Z e $0,50\%$ no binomial exato). Ressalta-se que o p-valor **não** é a probabilidade de $H_0$ ser verdadeira, mas sim o quão compatível a amostra observada é com $H_0$.
- **Justificativa da decisão:** No Exemplo Simulado 1, como a proporção amostral ($\hat{p} = 4,00\%$) ficou abaixo da meta de $5\%$, a estatística $z = -0,795$ caiu à esquerda da média sob $H_0$ e os p-valores ($0,7866$ e $0,8220$) superaram em muito o nível de significância $\alpha = 0,05$; logo, nenhum dos testes rejeita $H_0$ (decisão correta, pois os dados foram gerados com $p = 3,33\% < 5\%$). No Exemplo Simulado 2, gerado com $p = 9\%$, ambos os p-valores ficaram abaixo de $\alpha = 0,05$, levando ambos os testes a rejeitar $H_0$ corretamente.
- **Limitação de uma única amostra simulada:** Embora em ambos os exemplos o p-valor do binomial exato tenha sido ligeiramente maior que o do teste Z ($0,8220 > 0,7866$ e $0,0050 > 0,0018$), **uma única realização não permite concluir qual teste é melhor**. Para avaliar rigorosamente a taxa de falsos positivos (erro tipo I) e a capacidade de detecção (poder estatístico), bem como o efeito da violação do pressuposto $n \cdot p_0 \ge 10$ em amostras pequenas, é indispensável repetir o experimento milhares de vezes ($10.000$ repetições nas Issues #4 e #5) e medir a proporção empírica de rejeições em cada cenário.

