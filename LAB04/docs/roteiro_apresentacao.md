# Roteiro da Apresentação Oral — LAB04 (15 Perguntas)

- **Duração máxima:** 7 minutos (~25–30 segundos por resposta).
- **Regra da disciplina:** todos os integrantes devem responder a pelo menos 4 perguntas (divisão sugerida abaixo: 5 para cada), e o professor pode direcionar qualquer pergunta a qualquer integrante usando o dashboard ao vivo.

## Divisão sugerida

| Integrante | Perguntas | Seções de apoio principais |
|---|---|---|
| **Vitor Veiga (Pessoa B)** | 1, 2, 5, 10, 11 | 1. Cenário · 3. Como os testes funcionam · 5. Poder (G4) |
| **Lucas (Pessoa A)** | 3, 4, 8, 9, 12 | 2. Os dados (G1) · 4. Erro tipo I (G3) · 5. Poder (G4) |
| **João (Pessoa C)** | 6, 7, 13, 14, 15 | 3. Como os testes funcionam (G2) · 6. Dados reais · 7. Conclusão |

---

## Respostas objetivas (apoiadas no dashboard)

### 1. Qual é o cenário de vocês e o que $H_0$ e $H_1$ afirmam, em palavras simples? — *Vitor (Seção 1: Cenário)*
- **Apoio visual:** Seção `1. Cenário` no topo do dashboard.
- **Resposta:** Avaliamos se a taxa de falhas do CI (`workflow test`) na branch `main` do repositório `pytest-dev/pytest` está acima da meta aceitável de 5%. A hipótese nula ($H_0: p = 0{,}05$) afirma que a taxa real de falhas está dentro da meta de 5%. A hipótese alternativa ($H_1: p > 0{,}05$) afirma que a taxa de falhas ultrapassou o limite de 5%.

### 2. O teste de vocês é unicaudal ou bicaudal? Por quê? — *Vitor (Seção 1: Cenário)*
- **Apoio visual:** Seção `1. Cenário`.
- **Resposta:** É **unicaudal à direita**. No monitoramento de CI, o interesse prático é detectar apenas degradações, ou seja, quando a taxa de falhas sobe acima de 5%. Uma taxa abaixo de 5% significa que o pipeline está ainda mais estável e não exige alerta nem intervenção.

### 3. Como os dados reais foram coletados, e o que eles mostraram sobre a forma da distribuição? — *Lucas (Seção 2: Os dados — G1)*
- **Apoio visual:** Seção `1. Cenário` + gráfico `G1`.
- **Resposta:** Coletamos via API REST do GitHub Actions as 300 execuções concluídas mais recentes do `pytest-dev/pytest` na branch `main` (evento `push`), descartando execuções canceladas ou puladas, entre fevereiro e outubro de 2026 — obtendo 10 falhas ($3{,}33\%$). Agrupando em 10 blocos de 30 execuções no G1, a distribuição é assimétrica à direita e sem outliers extremos: metade dos blocos teve 0 falhas e o máximo foi 3 falhas.

### 4. Como os dados reais ajudaram a escolher os parâmetros da simulação? — *Lucas (Seção 2: Os dados — G1)*
- **Apoio visual:** Gráfico `G1`.
- **Resposta:** Os dados reais calibraram o tamanho amostral base ($n = 300$, garantindo $n \cdot p_0 = 15 \ge 10$ para o teste Z) e a taxa empírica ($p = 3{,}33\%$) usada para gerar os 10.000 blocos simulados no G1 e o exemplo simulado 1 calibrado no G2. Além disso, a coleta nos mostrou que a simulação binomial captura bem a assimetria, embora na prática possam existir leves rajadas de falhas em sequência.

### 5. O que cada um dos dois testes compara de fato? — *Vitor (Seção 3: Como os testes funcionam — G2)*
- **Apoio visual:** Seção `3. Como os testes funcionam` (`G2`, abas Teste Z e Binomial Exato).
- **Resposta:** O **teste Z para proporção** compara a proporção observada $\hat{p}$ com a meta $p_0 = 0{,}05$ usando uma estatística padronizada $z$ sob a aproximação contínua da curva normal padrão. Já o **teste binomial exato** compara diretamente a contagem discreta de falhas $x$ com a distribuição exata $\text{Bin}(n, p_0)$, somando as probabilidades pontuais de obter $x$ ou mais falhas.

### 6. No G2: o que é a distribuição da estatística sob $H_0$, e por que a região de rejeição fica onde fica? — *João (Seção 3: Como os testes funcionam — G2)*
- **Apoio visual:** Gráfico `G2` (mostrar as duas abas).
- **Resposta:** A distribuição sob $H_0$ mostra todos os valores possíveis da estatística (e suas probabilidades) assumindo que a taxa real do CI é exatamente 5% ($\mathcal{N}(0,1)$ no Z; barras da $\text{Bin}(300; 0{,}05)$ no exato). Como $H_1$ é $p > 0{,}05$, apenas valores muito altos de falhas contradizem $H_0$, colocando a região de rejeição ($\alpha = 5\%$) na cauda direita: $z \ge 1{,}645$ no teste Z e $x \ge 22$ falhas no binomial exato.

### 7. O que significa o p-valor do exemplo mostrado no G2? E o que ele não significa? — *João (Seção 3: Como os testes funcionam — G2)*
- **Apoio visual:** Gráfico `G2` (selecionar `Exemplo simulado 1` ou `Exemplo simulado 2`).
- **Resposta:** No Exemplo 1 ($x = 12$ falhas), o p-valor ($0{,}7866$ no Z e $0{,}8220$ no binomial) é a probabilidade de observar 12 ou mais falhas *assumindo que $H_0$ é verdadeira* ($p = 0{,}05$). O p-valor **não** é a probabilidade de $H_0$ ser verdadeira, nem a probabilidade de termos errado ao tomar uma decisão.

### 8. No cenário de vocês, o que seria um erro tipo I e um erro tipo II? Qual é mais grave? — *Lucas (Seção 4: Erro tipo I — G3)*
- **Apoio visual:** Seção `4. Erro tipo I` (`G3`).
- **Resposta:** O **erro tipo I** é um alarme falso: concluir que o CI ultrapassou 5% de falhas quando na verdade está dentro da meta (desperdiça tempo de engenharia investigando um problema inexistente). O **erro tipo II** é deixar passar uma degradação real ($p > 0{,}05$) sem detectar. Em sistemas críticos ou pipelines grandes, o erro tipo II costuma ser mais grave porque código quebrado ou testes instáveis passam despercebidos; porém, alarmes falsos constantes também geram fadiga de alerta no time.

### 9. No G3, algum teste se afastou de 5%? Ele ficou liberal ou conservador, e por quê? — *Lucas (Seção 4: Erro tipo I — G3)*
- **Apoio visual:** Gráfico `G3` e tabela da Seção 4.
- **Resposta:** Sim. Em $n = 300$, ambos ficaram em $4{,}87\%$, bem perto de 5%. Já para amostras pequenas ($n \cdot p_0 < 10$), o **teste binomial exato** ficou **conservador** ($1{,}24\%$ a $3{,}76\%$) porque a distribuição é discreta e os cortes inteiros nunca deixam passar de 5%. O **teste Z** ficou **liberal** na maioria dos casos pequenos ($8{,}53\%$ em $n=10$, $7{,}48\%$ em $n=20$, $6{,}05\%$ em $n=30$, $6{,}21\%$ em $n=100$) porque a binomial é assimétrica à direita e a curva normal subestima a cauda, mas curiosamente empatou como conservador em $n=50$ ($3{,}76\%$) devido à discretização.

### 10. No G4, qual teste tem mais poder? A diferença muda conforme o tamanho do efeito? — *Vitor (Seção 5: Poder estatístico — G4)*
- **Apoio visual:** Gráfico `G4`.
- **Resposta:** Em $n = 300$ e em $n = 50$, ambos os testes têm **exatamente o mesmo poder** em todos os tamanhos de efeito (chegando a $86{,}86\%$ em $p=9\%$ e $100\%$ em $p=15\%$ para $n=300$), porque compartilham o mesmo corte discreto ($x \ge 22$ e $x \ge 6$). Nos outros cenários ($n \in \{10, 20, 30, 100\}$), o teste Z rejeita mais que o binomial em toda a curva, mas essa vantagem não é legítima: ela vem do fato de o Z ter erro tipo I inflado acima de 5% no efeito zero.

### 11. Que violação de pressuposto foi simulada, e por que ela afeta mais um teste do que o outro? — *Vitor (Seções 4 e 5 — G3 e G4)*
- **Apoio visual:** Gráficos `G3` e `G4` (comparar $n = 300$ vs $n \in \{10, 20, 30, 50, 100\}$).
- **Resposta:** Simulamos **amostras pequenas** ($n \in \{10, 20, 30, 50, 100\}$), que violam o pressuposto de aproximação normal do teste Z: $n \cdot p_0 \ge 10$ (com $p_0 = 0{,}05$, exige $n \ge 200$). Isso afeta o teste Z porque ele depende da normalidade para aproximar uma binomial que é muito assimétrica à direita quando $n \cdot p_0$ é baixo, enquanto o binomial exato usa a distribuição verdadeira e não depende dessa aproximação.

### 12. Se vocês usassem $\alpha = 0{,}01$ em vez de $0{,}05$, o que mudaria no G3 e no G4? — *Lucas (Seções 4 e 5 — G3 e G4)*
- **Apoio visual:** Gráficos `G3` e `G4`.
- **Resposta:** No **G3**, a linha de referência cairia de 5% para 1% e os pontos de corte ficariam bem mais rígidos (em $n = 300$, passariam para $z \ge 2{,}326$ e $x \ge 25$). O binomial exato continuaria abaixo de 1% (ainda mais conservador), enquanto a aproximação normal do teste Z falharia proporcionalmente ainda mais na cauda extrema em amostras pequenas. No **G4**, todas as curvas de poder desceriam para a direita: seria preciso um efeito bem maior (ou um $n$ maior) para atingir 80% de poder.

### 13. A simulação confirmou o que o grupo esperava antes de simular? Se não, o que explica a diferença? — *João (Seção 7: Conclusão)*
- **Apoio visual:** Seção `7. Conclusão` (confrontando com `G3` e `G4`).
- **Resposta:** Confirmou quase tudo: empate em $n = 300$, binomial exato sempre conservador ($\le 5\%$) e Z liberal na maioria das amostras pequenas. A surpresa veio em $n = 50$ ($n \cdot p_0 = 2{,}5 < 10$), onde o teste Z não ficou liberal e empatou com o binomial em $3{,}76\%$. Isso acontece porque o número de falhas $x$ é inteiro: dependendo de onde o ponto crítico contínuo do Z cai entre dois inteiros, ele pode coincidir exatamente com o corte conservador do binomial em certos valores de $n$.

### 14. Nos dados reais, os dois testes chegaram à mesma conclusão? O tamanho do efeito tem importância prática? — *João (Seção 6: Dados reais)*
- **Apoio visual:** Seção `6. Dados reais` (tabela e texto).
- **Resposta:** Sim, ambos concordaram em **não rejeitar $H_0$** ($z = -1{,}325$, $p = 0{,}9073$ no Z; $x = 10$, $p = 0{,}9350$ no binomial exato). O tamanho do efeito foi $h = -0{,}084$ — um efeito **desprezível** na escala de Cohen ($|h| < 0{,}20$), refletindo uma taxa real de $3{,}33\%$ apenas $1{,}67$ ponto percentual abaixo da meta. Vale notar que isso mostra ausência de evidência de problema, mas não prova estatisticamente que a taxa é menor que 5% ($P(X \le 10) = 0{,}112$).

### 15. Qual teste vocês recomendam para o cenário, em que situação mudariam a recomendação, e qual é a principal limitação do estudo? — *João (Seção 7: Conclusão)*
- **Apoio visual:** Seção `7. Conclusão` + `G1`.
- **Resposta:** Recomendamos o **teste binomial exato**, pois ele garante o controle rigoroso do erro tipo I ($\le 5\%$) para qualquer $n$ sem custo extra de computação hoje em dia. A escolha se torna indiferente quando $n \ge 200$ ($n \cdot p_0 \ge 10$), onde os testes convergem; e só mudaríamos em amostras pequenas caso falsos negativos fossem críticos e se buscasse um teste menos conservador (como p-valor *mid-p*). A principal limitação é que a simulação assume execuções independentes, enquanto em um CI real (como indicam os 2 blocos com 3 falhas no G1) falhas podem acontecer em sequência até o build ser consertado.
