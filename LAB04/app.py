import csv
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

COR_Z = "#1f77b4"
COR_BINOM = "#ff7f0e"
COR_REAL = "#2ca02c"
COR_REF = "#d62728"
ALFA = 0.05
P0 = 0.05


def carregar_dados_reais():
    if not CAMINHO_DADOS.exists():
        return pd.DataFrame(), 0, 0, 0.0
    df = pd.read_csv(CAMINHO_DADOS)
    n = len(df)
    x = int(df["falha"].sum())
    p_hat = x / n if n > 0 else 0.0
    return df, n, x, p_hat


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
    if num_blocos == 0:
        num_blocos = 10
        taxas_reais = [p_hat * 100] * num_blocos
    else:
        taxas_reais = []
        for i in range(num_blocos):
            fatia = df_real.iloc[i * tamanho_bloco:(i + 1) * tamanho_bloco]
            taxa = (fatia["falha"].sum() / len(fatia)) * 100
            taxas_reais.append(taxa)

    rng = np.random.default_rng(42)
    falhas_simuladas = rng.binomial(n=tamanho_bloco, p=p_hat, size=num_blocos)
    taxas_simuladas = [(k / tamanho_bloco) * 100 for k in falhas_simuladas]

    blocos_rotulos = [f"Bloco {i + 1}" for i in range(num_blocos)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=blocos_rotulos,
        y=taxas_reais,
        name="Dados Reais (pytest-dev/pytest)",
        marker_color=COR_REAL,
        opacity=0.85
    ))
    fig.add_trace(go.Bar(
        x=blocos_rotulos,
        y=taxas_simuladas,
        name=f"Dados Simulados (p = {p_hat:.4f})",
        marker_color="#9467bd",
        opacity=0.85
    ))
    fig.add_trace(go.Scatter(
        x=blocos_rotulos,
        y=[P0 * 100] * num_blocos,
        mode="lines",
        name=f"Meta H0 ({P0 * 100:.0f}%)",
        line=dict(color=COR_REF, width=2, dash="dash")
    ))

    fig.update_layout(
        title="G1: Comparação de Taxa de Falhas por Bloco de 30 Execuções (Real vs Simulado)",
        xaxis_title="Blocos sequenciais de execuções (unidade: bloco de 30 runs)",
        yaxis_title="Taxa de falhas observada (%)",
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

    cores_barras = []
    textos_hover = []
    for k in valores_k:
        if k >= k_critico:
            cores_barras.append("rgba(214, 39, 40, 0.8)")
        else:
            cores_barras.append(COR_BINOM)
        sf_k = binom.sf(k - 1, n_amostra, P0)
        textos_hover.append(f"k = {k}<br>P(X = k) = {binom.pmf(k, n_amostra, P0):.4f}<br>P(X >= k) = {sf_k:.4f}")

    fig_bin = go.Figure()

    fig_bin.add_trace(go.Bar(
        x=valores_k,
        y=probs_bin,
        marker_color=cores_barras,
        hovertext=textos_hover,
        hoverinfo="text",
        name="Distribuição Bin(n=300, p0=0.05)"
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        height=450
    )

    return fig_z, fig_bin, z_ex, p_valor_z, p_valor_bin, z_critico, k_critico


df_real, n_real, x_real, p_hat_real = carregar_dados_reais()

st.title("LAB04 — Testes de Hipótese por Dentro")
st.markdown(
    """
    **Par de testes:** P4 — Teste Z para proporção $\\times$ Teste binomial exato  
    **Links do projeto:** [Repositório GitHub](https://github.com/JoaoAlmeida02/Laborat-rio-de-Experimenta-o-de-Software) | [GitHub Projects](https://github.com/users/JoaoAlmeida02/projects/)
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
st.plotly_chart(fig_g1, use_container_width=True)

st.markdown(
    """
    O gráfico G1 apresenta a taxa de falhas observada a cada bloco consecutivo de 30 execuções nos dados reais coletados do GitHub Actions versus uma realização simulada calibrada com a taxa média empírica ($p = 3{,}33\\%$, semente 42). Nota-se que tanto nas execuções reais quanto nas simuladas a ampla maioria dos blocos oscila abaixo do limite de 5% estabelecido por $H_0$, com flutuações pontuais compatíveis com um processo estocástico estacionário. Conclui-se que o modelo de amostragem binomial com $n = 300$ e probabilidade calibrada mimetiza adequadamente a variabilidade amostral do pipeline de integração contínua avaliado.
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
    st.plotly_chart(fig_g2_z, use_container_width=True)

with tab_bin:
    st.plotly_chart(fig_g2_bin, use_container_width=True)

st.markdown(
    f"""
    O gráfico G2 ilustra a distribuição da estatística sob $H_0$ para os dois testes com $n = 300$ e meta $p_0 = 0,05$, destacando a região crítica de rejeição à direita para $\\alpha = 0,05$. No teste Z (azul `{COR_Z}`), a região crítica inicia em $z \\ge {z_crit:.3f}$ sobre a normal padrão, enquanto no teste binomial exato (laranja `{COR_BINOM}`) ela abrange $x \\ge {k_crit}$ falhas na distribuição discreta. Para o exemplo destacado ($x = {x_destaque}$), o p-valor obtido foi de {p_z:.4f} no teste Z e {p_bin:.4f} no binomial exato, indicando a probabilidade de observar desvios iguais ou superiores caso $H_0$ seja verdadeira, sem representar a probabilidade de a hipótese nula estar correta.
    """
)
st.divider()

st.header("4. Erro tipo I (G3)")
st.markdown(
    """
    O erro tipo I ocorre quando o teste rejeita indevidamente a hipótese nula verdadeira (falso alarme), afirmando que a taxa de falha violou a meta quando na realidade $p = 0{,}05$.
    """
)
st.info(
    "Módulo de simulação de Monte Carlo da Sprint 2 (Issue #76). As 10.000 repetições com n = 300 e n pequeno (10, 20, 30, 50) quantificarão o conservadorismo do teste binomial exato e a degradação liberal do teste Z sob violação do pressuposto n·p0 >= 10."
)
st.divider()

st.header("5. Poder estatístico (G4)")
st.markdown(
    """
    O poder estatístico ($1 - \\beta$) quantifica a capacidade do teste de rejeitar $H_0$ quando existe uma degradação real no pipeline ($p > 0{,}05$).
    """
)
st.info(
    "Módulo de curva de poder da Sprint 2 (Issue #77). O gráfico G4 mapeará as probabilidades de rejeição para p variando entre 0,05 e 0,15, comparando a sensibilidade de ambos os testes em amostras grandes e restritas."
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
    A aplicação dos dois testes estatísticos aos dados empíricos do repositório `pytest-dev/pytest` resultou na concordância unânime pela não rejeição da hipótese nula. A taxa observada de 3,33% (10 falhas em 300 execuções) situou-se confortavelmente abaixo do limiar de 5%, traduzindo-se em um tamanho de efeito negativo ($h = -0{,}084$) e p-valores expressivos ($0{,}9073$ e $0{,}9350$). Conclui-se que o pipeline de integração contínua opera dentro dos parâmetros de confiabilidade estipulados pela equipe, dispensando intervenções emergenciais.
    """
)
st.divider()

st.header("7. Conclusão")
st.markdown(
    """
    - **Esperado antes de simular vs Encontrado:** Na amostra com $n = 300$, ambos os métodos mantêm alta consistência e chegam a decisões idênticas, uma vez que o pressuposto de aproximação normal ($n \\cdot p_0 = 15 \\ge 10$) é atendido.
    - **Recomendação técnica:** Para volumes amostrais elevados ($n \\ge 200$), ambos os testes são aplicáveis; contudo, recomenda-se a adoção prioritária do **teste binomial exato**, pois ele preserva rigorosamente o controle do erro tipo I mesmo em cenários de amostras reduzidas, sem sofrer das oscilações liberais causadas pela assimetria da cauda na aproximação contínua.
    - **Limitação do estudo:** A amostragem considerou execuções sequenciais de uma única branch (`main`), pressupondo independência condicional entre os disparos consecutivos de CI, o que pode mascarar dependências temporais ou quebras em cadeia transitórias.
    """
)
