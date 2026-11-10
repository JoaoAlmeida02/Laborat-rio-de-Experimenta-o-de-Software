import pandas as pd

from erro_tipo1 import N_PEQUENOS
from simulacao import ALFA, P0, criar_rng, ler_dados_reais, taxa_rejeicao

TAXAS_FALHA = (0.05, 0.07, 0.09, 0.11, 0.13, 0.15)
COR_Z = "#1f77b4"
COR_BINOM = "#ff7f0e"
COR_REF = "#d62728"
ESTILOS_LINHA = {
    10: "dot",
    20: "dashdot",
    30: "dash",
    50: "longdash",
    100: "longdashdot",
    300: "solid",
}


def calcular_curva_poder(n_real=None, taxas=TAXAS_FALHA, n_pequenos=N_PEQUENOS, reps=10_000, alfa=ALFA, semente=42):
    if n_real is None:
        n_real, _, _ = ler_dados_reais()
    linhas = []
    for n in (*n_pequenos, n_real):
        for p in taxas:
            poder_z, poder_binomial = taxa_rejeicao(p, n, reps=reps, alfa=alfa, p0=P0, rng=criar_rng(semente))
            linhas.append({"p": p, "n": n, "teste": "Teste Z", "poder": poder_z})
            linhas.append({"p": p, "n": n, "teste": "Binomial exato", "poder": poder_binomial})
    return pd.DataFrame(linhas, columns=["p", "n", "teste", "poder"])


def gerar_grafico_g4(df_poder, alfa=ALFA, cor_z=COR_Z, cor_binom=COR_BINOM, cor_ref=COR_REF):
    import plotly.graph_objects as go

    fig = go.Figure()
    cores = {"Teste Z": cor_z, "Binomial exato": cor_binom}
    simbolos = {"Teste Z": "circle", "Binomial exato": "diamond"}
    tamanhos_marcador = {"Teste Z": 9, "Binomial exato": 6}
    valores_n = sorted(df_poder["n"].unique())
    estilos_padrao = ["dot", "dashdot", "dash", "longdash", "longdashdot", "solid"]

    for idx, n in enumerate(valores_n):
        estilo = ESTILOS_LINHA.get(n, estilos_padrao[idx % len(estilos_padrao)])
        largura_base = 3.0 if n == max(valores_n) else 2.0
        for teste in ("Teste Z", "Binomial exato"):
            largura = largura_base + (1.0 if teste == "Teste Z" else 0.0)
            sub = df_poder[(df_poder["n"] == n) & (df_poder["teste"] == teste)].sort_values("p")
            fig.add_trace(go.Scatter(
                x=sub["p"] * 100,
                y=sub["poder"] * 100,
                mode="lines+markers",
                name=f"{teste} (n = {n})",
                line=dict(color=cores[teste], dash=estilo, width=largura),
                marker=dict(symbol=simbolos[teste], size=tamanhos_marcador[teste]),
                hovertemplate=f"<b>{teste} (n = {n})</b><br>Taxa real p: %{{x:.1f}}%<br>Poder: %{{y:.2f}}%<extra></extra>",
            ))

    fig.add_hline(
        y=alfa * 100,
        line_width=2,
        line_dash="dash",
        line_color=cor_ref,
        showlegend=True,
        name=f"Nível nominal (alfa = {alfa * 100:.0f}%)",
    )

    fig.update_layout(
        title="G4: Curvas de Poder por Teste e Tamanho da Amostra (10.000 Repetições)",
        xaxis=dict(title="Taxa real de falha p (%)", dtick=2),
        yaxis=dict(title="Poder estatístico — proporção de rejeições (%)", range=[0, 105]),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        template="plotly_white",
        height=550,
    )
    return fig


def main():
    df = calcular_curva_poder()
    tabela = df.pivot(index=["n", "p"], columns="teste", values="poder")[["Teste Z", "Binomial exato"]]
    print(f"{'n':>5} {'p':>7} {'Teste Z':>12} {'Binomial exato':>16}")
    for (n, p), linha in tabela.iterrows():
        print(f"{n:>5} {p:>7.2%} {linha['Teste Z']:>12.2%} {linha['Binomial exato']:>16.2%}")


if __name__ == "__main__":
    main()
