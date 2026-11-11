import csv
import sys
from math import asin, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import binom, binomtest, norm
import streamlit as st

st.set_page_config(
    page_title="LAB04 — Testes de Hipótese por Dentro",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
CAMINHO_DADOS = BASE_DIR / "dados" / "ci_runs.csv"
sys.path.insert(0, str(BASE_DIR / "scripts"))

from erro_tipo1 import calcular_erro_tipo1
from poder import calcular_curva_poder, gerar_grafico_g4

COR_Z = "#1f77b4"
COR_BINOM = "#ff7f0e"
COR_REAL = "#2ca02c"
COR_REF = "#d62728"
ALFA = 0.05
P0 = 0.05


@st.cache_data
def carregar_dados_reais():
    if not CAMINHO_DADOS.exists():
        return pd.DataFrame(), 0, 0, 0.0
    df = pd.read_csv(CAMINHO_DADOS)
    n = len(df)
    x = int(df["falha"].sum())
    p_hat = x / n if n > 0 else 0.0
    return df, n, x, p_hat


@st.cache_data
def obter_erro_tipo1(n_total):
    return calcular_erro_tipo1(n_total)


@st.cache_data
def obter_curva_poder(n_total, alfa=ALFA):
    return calcular_curva_poder(n_total, alfa=alfa)


def teste_z(x, n, p0=P0):
    z = (x / n - p0) / sqrt(p0 * (1 - p0) / n)
    return z, float(norm.sf(z))


def teste_binomial(x, n, p0=P0):
    res = binomtest(int(x), int(n), p0, alternative="greater")
    return int(x), float(res.pvalue)


def h_cohen(p_hat, p0=P0):
    return 2 * asin(sqrt(p_hat)) - 2 * asin(sqrt(p0))


def gerar_grafico_g1(df_real, p_hat, n_total):
    tamanho_bloco = 30
    num_blocos = n_total // tamanho_bloco
    falhas_reais = [
        int(df_real["falha"].iloc[i * tamanho_bloco:(i + 1) * tamanho_bloco].sum())
        for i in range(num_blocos)
    ]

    rng = np.random.default_rng(42)
    falhas_simuladas = rng.binomial(n=tamanho_bloco, p=p_hat, size=10_000)

    maximo = max(max(falhas_reais), int(falhas_simuladas.max()))
    valores = np.arange(maximo + 1)
    proporcao_reais = np.bincount(falhas_reais, minlength=maximo + 1) / num_blocos * 100
    proporcao_simuladas = np.bincount(falhas_simuladas, minlength=maximo + 1) / len(falhas_simuladas) * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valores,
        y=proporcao_reais,
        name=f"Dados Reais (pytest-dev/pytest, {num_blocos} blocos)",
        marker_color=COR_REAL,
        opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=valores,
        y=proporcao_simuladas,
        name=f"Dados Simulados (p = {p_hat:.4f}, 10.000 blocos)",
        marker_color="#9467bd",
        opacity=0.85
    ))

    fig.update_layout(
        title="G1: Histograma de Falhas por Bloco de 30 Execuções (Real vs Simulado)",
        xaxis=dict(title="Número de falhas no bloco (contagem por bloco de 30 execuções)", dtick=1),
        yaxis_title="Proporção de blocos (%)",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=450
    )
    return fig


def gerar_grafico_g2(n_amostra, x_exemplo):
    p_hat_ex = x_exemplo / n_amostra
    z_ex, p_valor_z = teste_z(x_exemplo, n_amostra, P0)
    _, p_valor_bin = teste_binomial(x_exemplo, n_amostra, P0)

    z_critico = float(norm.ppf(1 - ALFA))

    x_vals_z = np.linspace(-4, 5, 500)
    y_vals_z = norm.pdf(x_vals_z)

    fig_z = go.Figure()

    fig_z.add_trace(go.Scatter(
        x=x_vals_z,
        y=y_vals_z,
        mode="lines",
        name="Densidade N(0, 1) sob H0",
        line=dict(color=COR_Z, width=3)
    ))

    x_rej_z = np.linspace(z_critico, 5, 200)
    fig_z.add_trace(go.Scatter(
        x=x_rej_z,
        y=norm.pdf(x_rej_z),
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(214, 39, 40, 0.35)",
        line=dict(color="rgba(214, 39, 40, 0)"),
        name=f"Região de rejeição (z >= {z_critico:.3f}, alfa = {ALFA})"
    ))

    limite_esq_ex = max(z_ex, -4)
    x_p_z = np.linspace(limite_esq_ex, 5, 200)
    fig_z.add_trace(go.Scatter(
        x=x_p_z,
        y=norm.pdf(x_p_z),
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(31, 119, 180, 0.25)",
        line=dict(color="rgba(31, 119, 180, 0)"),
        name=f"P-valor do exemplo (área z >= {z_ex:.3f}: {p_valor_z:.4f})"
    ))

    fig_z.add_vline(
        x=z_ex,
        line_width=2,
        line_dash="dot",
        line_color=COR_Z,
        annotation_text=f"z obs = {z_ex:.2f}",
        annotation_position="top left"
    )
    fig_z.add_vline(
        x=z_critico,
        line_width=2,
        line_dash="dash",
        line_color=COR_REF,
        annotation_text=f"z crit = {z_critico:.2f}",
        annotation_position="top right"
    )

    fig_z.update_layout(
        title=f"G2 (Parte 1): Teste Z — Distribuição da Estatística sob H0 (n = {n_amostra})",
        xaxis_title="Estatística Z padronizada (adimensional)",
        yaxis_title="Densidade de probabilidade",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=450
    )

    valores_k = np.arange(0, 36)
    probs_bin = binom.pmf(valores_k, n_amostra, P0)

    k_critico = int(binom.ppf(1 - ALFA, n_amostra, P0))
    while binom.sf(k_critico - 1, n_amostra, P0) > ALFA:
        k_critico += 1

    textos_hover = np.array([
        f"k = {k}<br>P(X = k) = {binom.pmf(k, n_amostra, P0):.4f}<br>P(X >= k) = {binom.sf(k - 1, n_amostra, P0):.4f}"
        for k in valores_k
    ])

    fig_bin = go.Figure()

    for mascara, cor, nome in (
        (valores_k < k_critico, COR_BINOM, f"Não rejeição (x < {k_critico})"),
        (valores_k >= k_critico, "rgba(214, 39, 40, 0.8)", f"Região de rejeição (x >= {k_critico}, alfa <= {ALFA})"),
    ):
        fig_bin.add_trace(go.Bar(
            x=valores_k[mascara],
            y=probs_bin[mascara],
            marker_color=cor,
            hovertext=textos_hover[mascara],
            hoverinfo="text",
            name=nome
        ))

    cauda_exemplo = valores_k >= x_exemplo
    fig_bin.add_trace(go.Bar(
        x=valores_k[cauda_exemplo],
        y=probs_bin[cauda_exemplo],
        marker=dict(
            color="rgba(0, 0, 0, 0)",
            line=dict(color="#17becf", width=2),
            pattern=dict(shape="/", fgcolor="#17becf")
        ),
        hovertext=textos_hover[cauda_exemplo],
        hoverinfo="text",
        name=f"P-valor do exemplo (área x >= {x_exemplo}: {p_valor_bin:.4f})"
    ))

    fig_bin.add_vline(
        x=k_critico - 0.5,
        line_width=2,
        line_dash="dash",
        line_color=COR_REF,
        annotation_text=f"Crítico x >= {k_critico} (alfa <= {ALFA})",
        annotation_position="top right"
    )

    fig_bin.add_vline(
        x=x_exemplo,
        line_width=2,
        line_dash="dot",
        line_color="#17becf",
        annotation_text=f"Exemplo x = {x_exemplo} (p = {p_valor_bin:.4f})",
        annotation_position="top left"
    )

    fig_bin.update_layout(
        title=f"G2 (Parte 2): Teste Binomial Exato — Distribuição sob H0 (n = {n_amostra})",
        xaxis_title="Número de falhas observadas x (contagem)",
        yaxis_title="Probabilidade pontual P(X = x)",
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=450
    )

    return fig_z, fig_bin, z_ex, p_valor_z, p_valor_bin, z_critico, k_critico


def gerar_grafico_g3(erros):
    rotulos = [f"n = {linha['n']} ({linha['pergunta']})" for linha in erros]

    fig = go.Figure()
    for chave, nome, cor in (
        ("erro_z", "Teste Z para proporção", COR_Z),
        ("erro_binomial", "Teste binomial exato", COR_BINOM),
    ):
        fig.add_trace(go.Bar(
            x=rotulos,
            y=[linha[chave] * 100 for linha in erros],
            name=nome,
            marker_color=cor,
            hovertemplate="%{x}<br>" + nome + ": %{y:.2f}%<extra></extra>"
        ))

    fig.add_hline(
        y=ALFA * 100,
        line_width=2,
        line_dash="dash",
        line_color=COR_REF,
        showlegend=True,
        name=f"Nível nominal (alfa = {ALFA * 100:.0f}%)"
    )

    fig.update_layout(
        title="G3: Erro Tipo I por Teste e Situação Simulada (10.000 Repetições, p = 5%)",
        xaxis_title="Tamanho da amostra n (execuções de CI) e pergunta do enunciado",
        yaxis_title="Erro tipo I (% de rejeições sob H0)",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=450
    )
    return fig


df_real, n_real, x_real, p_hat_real = carregar_dados_reais()

st.title("LAB04 — Testes de Hipótese por Dentro")
st.markdown(
    """
    **Par de testes:** P4 — Teste Z para proporção $\\times$ Teste binomial exato  
    **Links do projeto:** [Repositório GitHub](https://github.com/JoaoAlmeida02/Laborat-rio-de-Experimenta-o-de-Software) | [GitHub Projects](https://github.com/JoaoAlmeida02/Laborat-rio-de-Experimenta-o-de-Software/projects) | Execução local: `streamlit run app.py`
    """
)
st.divider()

st.header("1. Cenário")
col_cen1, col_cen2 = st.columns([2, 1])

with col_cen1:
    st.markdown(
        """
        - **Pergunta:** A taxa de falha do CI do repositório `pytest-dev/pytest` está acima da meta de 5%?
        - **Hipótese Nula ($H_0$):** $p = 0{,}05$ (a taxa de falha do pipeline está dentro da meta aceitável).
        - **Hipótese Alternativa ($H_1$):** $p > 0{,}05$ (a taxa de falha do pipeline está acima da meta).
        - **Direcionalidade:** Teste **unicaudal à direita**, pois o monitoramento de engenharia de software busca detectar unicamente degradações de confiabilidade ($p > 0{,}05$). Taxas de falha inferiores a 5% indicam alta qualidade e estabilidade da suíte, não constituindo motivo para intervenção.
        - **Nível de significância nominal:** $\\alpha = 0{,}05$.
        """
    )

with col_cen2:
    st.metric(label="Tamanho da Amostra Coletada (n)", value=f"{n_real} execuções")
    st.metric(label="Falhas Observadas (x)", value=f"{x_real} falhas")
    st.metric(label="Taxa Observada (p̂)", value=f"{p_hat_real * 100:.2f}%")

st.info(
    "Os dados reais foram coletados da API REST do GitHub Actions para a branch main e evento push no repositório pytest-dev/pytest, totalizando 300 execuções válidas concluídas entre fevereiro e outubro de 2026."
)
st.divider()

st.header("2. Os dados (G1)")
fig_g1 = gerar_grafico_g1(df_real, p_hat_real, n_real)
st.plotly_chart(fig_g1, width="stretch")

st.markdown(
    """
    O G1 mostra o histograma do número de falhas em cada bloco de 30 execuções: os 10 blocos reais ao lado de 10.000 blocos simulados com $p = 3{,}33\\%$, a taxa média observada nos dados reais (semente 42). Os dados reais são assimétricos à direita e sem outliers extremos: 5 dos 10 blocos não têm falha e o máximo é de 3 falhas. A simulação reproduz essa assimetria, mas prevê menos blocos com 3 falhas (cerca de 6%, contra 2 dos 10 blocos reais). Com apenas 10 blocos a diferença pode ser acaso, mas também é compatível com falhas em sequência, que o modelo binomial não representa.
    """
)
st.divider()

st.header("3. Como os testes funcionam (G2)")

col_sel1, col_sel2 = st.columns([1, 2])
with col_sel1:
    opcao_exemplo = st.radio(
        "Selecione o caso a destacar na distribuição sob H0:",
        options=[
            "Dados reais coletados (x = 10)",
            "Exemplo simulado 1 calibrado (x = 12)",
            "Exemplo simulado 2 com efeito (x = 26)"
        ],
        index=1
    )

if "x = 10" in opcao_exemplo:
    x_destaque = 10
elif "x = 12" in opcao_exemplo:
    x_destaque = 12
else:
    x_destaque = 26

fig_g2_z, fig_g2_bin, z_val, p_z, p_bin, z_crit, k_crit = gerar_grafico_g2(n_real, x_destaque)

tab_z, tab_bin = st.tabs(["Teste Z para proporção (Normal)", "Teste binomial exato (Discreto)"])

with tab_z:
    st.plotly_chart(fig_g2_z, width="stretch")

with tab_bin:
    st.plotly_chart(fig_g2_bin, width="stretch")

st.markdown(
    f"""
    O teste Z compara a proporção amostral padronizada com a meta $p_0 = 0,05$ pela aproximação normal padrão, enquanto o teste binomial exato compara diretamente a contagem de falhas $X$ com a distribuição discreta $\\text{{Bin}}(300; 0,05)$ sob $H_0$. No teste Z (azul `{COR_Z}`), a região de rejeição unicaudal à direita para $\\alpha = 0,05$ inicia em $z \\ge {z_crit:.3f}$, enquanto no binomial exato (laranja `{COR_BINOM}`) ela abrange $x \\ge {k_crit}$ falhas. Para o exemplo destacado ($x = {x_destaque}$), o p-valor obtido foi de {p_z:.4f} no teste Z e {p_bin:.4f} no binomial exato, indicando a probabilidade de observar desvios iguais ou mais extremos caso $H_0$ seja verdadeira, e não a probabilidade de $H_0$ estar correta.
    """
)
st.divider()

st.header("4. Erro tipo I (G3)")

erros_tipo1 = obter_erro_tipo1(n_real)
erro_por_n = {linha["n"]: linha for linha in erros_tipo1}

st.plotly_chart(gerar_grafico_g3(erros_tipo1), width="stretch")

st.table(pd.DataFrame([
    {
        "Situação": f"{linha['pergunta']}: n = {linha['n']} (n·p0 = {linha['n'] * P0:g})",
        "Teste Z": f"{linha['erro_z'] * 100:.2f}%",
        "Binomial exato": f"{linha['erro_binomial'] * 100:.2f}%",
    }
    for linha in erros_tipo1
]))

st.markdown(
    f"""
    O G3 mostra com que frequência cada teste dá um falso alarme: a proporção de rejeições em 10.000 amostras simuladas com $H_0$ verdadeira ($p = 5\\%$), comparada à linha do nível nominal. Com $n = {n_real}$ (Q1), os dois testes rejeitam a partir da mesma contagem de falhas e têm o mesmo erro ({erro_por_n[n_real]['erro_z'] * 100:.2f}%), perto de 5%. Com amostras pequenas (Q3, $n \\cdot p_0 < 10$), o teste Z fica liberal em $n$ = 10, 20, 30 e 100, chegando a {erro_por_n[10]['erro_z'] * 100:.2f}% em $n = 10$, porque a binomial é assimétrica à direita e a aproximação normal subestima a cauda. O binomial exato nunca passa de 5%, mas é conservador por ser discreto (apenas {erro_por_n[10]['erro_binomial'] * 100:.2f}% em $n = 10$), e em $n = 50$ os dois empatam em {erro_por_n[50]['erro_z'] * 100:.2f}%, o que mostra que o Z não é liberal em todo $n$ pequeno.
    """
)
st.divider()

st.header("5. Poder estatístico (G4)")

df_poder = obter_curva_poder(n_real, alfa=ALFA)
st.plotly_chart(
    gerar_grafico_g4(df_poder, alfa=ALFA, cor_z=COR_Z, cor_binom=COR_BINOM, cor_ref=COR_REF),
    width="stretch"
)

st.markdown(
    """
    O G4 apresenta as curvas de poder dos dois testes (10.000 simulações por ponto) para $p$ entre 5% (efeito zero) e 15%: em $n = 300$ (Q2) e em $n = 50$ (Q3), o teste Z e o binomial exato compartilham exatamente a mesma região crítica discreta ($x \\ge 22$ e $x \\ge 6$) e empatam em todos os níveis de efeito, indo de 4,87% ($p = 5\\%$) a 86,86% ($p = 9\\%$) e 100,00% ($p = 15\\%$) para $n = 300$. Para $n \\in \\{10, 20, 30, 100\\}$ (Q3), o teste Z rejeita $H_0$ com maior frequência que o binomial exato em toda a curva — por exemplo, em $p = 9\\%$, alcança 22,10% contra 5,45% em $n = 10$ e 54,61% contra 41,00% em $n = 100$. Entretanto, a comparação de poder entre os dois testes não é equivalente nesses casos, pois o teste Z tem erro tipo I inflado acima do nível nominal de 5% no efeito zero (entre 6,05% e 8,53%, contra 1,24% a 2,90% do binomial conservador), ganhando poder aparente justamente por adotar um limiar liberal que erra mais sob $H_0$. Em nenhum cenário simulado a vantagem de poder muda de lado para o binomial exato: quando o teste Z não excede 5% sob $H_0$ ($n = 50$ e $n = 300$), as curvas coincidem integralmente, confirmando a expectativa de poder igual em $n = 300$, mas revelando que toda vantagem de detecção do Z em amostras menores vem às custas da violação do nível $\\alpha$.
    """
)
st.divider()

st.header("6. Dados reais")

z_real, p_z_real = teste_z(x_real, n_real, P0)
_, p_bin_real = teste_binomial(x_real, n_real, P0)
h_real = h_cohen(p_hat_real, P0)

tabela_dados_reais = pd.DataFrame([
    {
        "Teste": "Teste Z para proporção",
        "Estatística": f"z = {z_real:.3f}",
        "p-valor (unicaudal)": f"{p_z_real:.4f}",
        "Tamanho do efeito (h de Cohen)": f"h = {h_real:.3f}",
        "Decisão (α = 0,05)": "Não rejeita H0" if p_z_real >= ALFA else "Rejeita H0"
    },
    {
        "Teste": "Teste binomial exato",
        "Estatística": f"x = {x_real}",
        "p-valor (unicaudal)": f"{p_bin_real:.4f}",
        "Tamanho do efeito (h de Cohen)": f"h = {h_real:.3f}",
        "Decisão (α = 0,05)": "Não rejeita H0" if p_bin_real >= ALFA else "Rejeita H0"
    }
])

st.table(tabela_dados_reais)

st.markdown(
    """
    A aplicação dos dois testes estatísticos aos dados empíricos do repositório `pytest-dev/pytest` resultou na concordância unânime pela não rejeição da hipótese nula. A taxa observada de 3,33% (10 falhas em 300 execuções) situou-se abaixo do limiar de 5%, com tamanho de efeito desprezível segundo Cohen ($h = -0{,}084$, $|h| < 0{,}20$, cerca de 1,67 ponto percentual abaixo da meta) e p-valores elevados ($0{,}9073$ e $0{,}9350$). Os dados não indicam taxa acima de 5%, mas também não comprovam que ela esteja abaixo da meta, pois 10 falhas em 300 não são significativamente menos que 5% ($P(X \\le 10) = 0{,}112$). Conclui-se que não há evidência estatística de degradação no pipeline de CI avaliado.
    """
)
st.divider()

st.header("7. Conclusão")
st.markdown(
    """
    - **Esperado antes de simular × Encontrado:** Antes de simular, esperávamos que o teste binomial exato fosse conservador em todas as amostras, que o teste Z ficasse liberal quando $n \\cdot p_0 < 10$ e que ambos tivessem poder semelhante com $n = 300$. As simulações confirmaram que, em $n = 300$, ambos compartilham exatamente a região crítica ($x \\ge 22$) e empatam em erro tipo I ($4{,}87\\%$) e poder ($86{,}86\\%$ em $p = 9\\%$ e $100{,}00\\%$ em $p = 15\\%$); também confirmaram que o binomial exato nunca excede 5% ($1{,}24\\%$ a $4{,}87\\%$) e que o Z fica liberal em $n \\in \\{10, 20, 30, 100\\}$ (chegando a $8{,}53\\%$ em $n = 10$). A surpresa apareceu em $n = 50$: apesar de violar $n \\cdot p_0 = 2{,}5 < 10$, o teste Z empatou com o binomial em $x \\ge 6$ e ficou conservador ($3{,}76\\%$), mostrando que a discretização faz o erro do Z oscilar em vez de subir continuamente, enquanto seu aparente poder maior no G4 para $n \\in \\{10, 20, 30, 100\\}$ decorre apenas do erro tipo I inflado sob $H_0$.
    - **Recomendação e quando a escolha mudaria:** Para este cenário de monitoramento de CI, recomendamos o **teste binomial exato**, pois ele garante que a taxa de falsos alarmes nunca ultrapasse o limite nominal $\\alpha = 5\\%$ independentemente do tamanho da amostra. A escolha mudaria de forma indiferente quando $n \\ge 200$ ($n \\cdot p_0 \\ge 10$), faixa em que ambos os testes convergem para as mesmas decisões (idênticas em $n = 300$); já em amostras pequenas, só se consideraria abrir mão do binomial exato padrão caso o custo de um **erro tipo II** (não detectar regressões reais no CI) fosse muito superior ao de um alarme falso e o conservadorismo extremo ($1{,}24\\%$ a $1{,}72\\%$) tornasse o teste pouco sensível.
    - **Principal limitação do estudo:** As simulações modelam cada execução como independente e identicamente distribuída com probabilidade fixa $p$, enquanto na prática do repositório `pytest-dev/pytest` (como sugerem os dois blocos reais com 3 falhas no G1) falhas podem ocorrer em sequência até que um commit corretivo seja integrado na branch `main`.
    """
)
