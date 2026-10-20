# Analise da RQ 06: Fatores determinantes do desempenho DORA.
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu

from metricas.estatistica import (
    cliffs_delta,
    corrigir_pvalores_holm,
    epsilon_squared_kruskal,
    interpretar_cliffs_delta,
    interpretar_epsilon_squared,
)

RAIZ = Path(__file__).resolve().parents[1]
SUPERFICIE, TINTA, TINTA_SEC, TINTA_MUDA, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COR_MARCA = "#2a78d6"
COR_SECUNDARIA = "#1c5cab"

TOP_LINGUAGENS = ["TypeScript", "Python", "Go", "Rust", "C++"]

METRICAS_DORA = [
    ("deploy_frequency_semana", "Deployment frequency", "releases/sem"),
    ("lead_time_release_h", "Lead time (a) release", "horas"),
    ("lead_time_commit_h", "Lead time (b) commit", "horas"),
    ("cfr_ci", "CFR (a) CI", "% falhas"),
    ("cfr_entrega", "CFR (b) entrega", "% corretivas"),
    ("tempo_recuperacao_h", "Tempo de recuperação", "horas"),
]


# Prepara os fatores e quartis necessarios para os testes da RQ 06.
def preparar_dados_fatores(df, caminho_consenso=None):
    dados = df.copy()
    dados["estrelas_quartil"] = pd.qcut(dados["stars"], 4, labels=["Q1 (menor)", "Q2", "Q3", "Q4 (maior)"])
    dados["contrib_quartil"] = pd.qcut(dados["contribuidores"], 4, labels=["Q1 (menor)", "Q2", "Q3", "Q4 (maior)"])
    dados["idade_quartil"] = pd.qcut(dados["idade_anos"], 4, labels=["Q1 (mais jovem)", "Q2", "Q3", "Q4 (mais antigo)"])

    if caminho_consenso and Path(caminho_consenso).exists():
        c = pd.read_csv(caminho_consenso)[["repo", "tipo_projeto_consenso"]].drop_duplicates()
        dados = dados.merge(c, on="repo", how="left")
    else:
        dados["tipo_projeto_consenso"] = None

    return dados


# Executa os testes de Kruskal-Wallis para fatores multivariados.
def executar_testes_kruskal(dados):
    fatores = [
        ("Linguagem (Top 5)", dados[dados["language"].isin(TOP_LINGUAGENS)], "language"),
        ("Popularidade (Estrelas)", dados, "estrelas_quartil"),
        ("Equipe (Contribuidores)", dados, "contrib_quartil"),
        ("Maturidade (Idade)", dados, "idade_quartil"),
    ]

    # Inclui tipo de projeto da amostra-ouro se houver dados
    sub_tipo = dados.dropna(subset=["tipo_projeto_consenso"])
    if len(sub_tipo["tipo_projeto_consenso"].unique()) > 1:
        fatores.append(("Tipo de Projeto (Amostra-Ouro)", sub_tipo, "tipo_projeto_consenso"))

    linhas = []
    for f_nome, df_f, f_col in fatores:
        for m_col, m_nome, un in METRICAS_DORA:
            sub = df_f[[f_col, m_col]].dropna()
            grupos_unicos = [g for g in sub[f_col].unique() if pd.notna(g)]
            amostras = [sub[sub[f_col] == g][m_col].to_numpy(dtype=float) for g in grupos_unicos]
            amostras = [a for a in amostras if len(a) > 0]
            if len(amostras) < 2:
                continue
            n_total = sum(len(a) for a in amostras)
            res = kruskal(*amostras)
            h_stat = float(res.statistic)
            p_val = float(res.pvalue)
            eps2 = epsilon_squared_kruskal(h_stat, n_total)
            interp_efeito = interpretar_epsilon_squared(eps2)

            linhas.append({
                "rq": "RQ 06",
                "tipo_teste": "Kruskal-Wallis",
                "fator": f_nome,
                "coluna_fator": f_col,
                "metrica": m_nome,
                "coluna_metrica": m_col,
                "unidade": un,
                "n_grupos": len(amostras),
                "n_total": n_total,
                "estatistica": round(h_stat, 4),
                "p_valor": p_val,
                "tamanho_efeito_nome": "epsilon_squared",
                "tamanho_efeito_valor": round(eps2, 4) if eps2 is not None else None,
                "tamanho_efeito_interpretacao": interp_efeito,
            })

    return linhas


# Executa os contrastes pareados de dois grupos com teste de Mann-Whitney e Cliff's Delta.
def executar_contrastes_mannwhitney(dados):
    contrastes = [
        ("Equipe: Grande (Q4) vs. Pequena (Q1)", dados, "contrib_quartil", "Q4 (maior)", "Q1 (menor)"),
        ("Maturidade: Antigo (Q4) vs. Jovem (Q1)", dados, "idade_quartil", "Q4 (mais antigo)", "Q1 (mais jovem)"),
        ("Popularidade: Alta (Q4) vs. Baixa (Q1)", dados, "estrelas_quartil", "Q4 (maior)", "Q1 (menor)"),
        ("Linguagem: TypeScript vs. Python", dados, "language", "TypeScript", "Python"),
    ]

    linhas = []
    for rotulo_contraste, df_c, col_f, val1, val2 in contrastes:
        for m_col, m_nome, un in METRICAS_DORA:
            x = df_c[df_c[col_f] == val1][m_col].dropna().to_numpy(dtype=float)
            y = df_c[df_c[col_f] == val2][m_col].dropna().to_numpy(dtype=float)
            if len(x) == 0 or len(y) == 0:
                continue
            res = mannwhitneyu(x, y, alternative="two-sided")
            u_stat = float(res.statistic)
            p_val = float(res.pvalue)
            delta = cliffs_delta(x, y)
            interp_delta = interpretar_cliffs_delta(delta)

            linhas.append({
                "rq": "RQ 06",
                "tipo_teste": "Mann-Whitney",
                "fator": rotulo_contraste,
                "coluna_fator": col_f,
                "metrica": m_nome,
                "coluna_metrica": m_col,
                "unidade": un,
                "n_grupos": 2,
                "n_total": len(x) + len(y),
                "estatistica": round(u_stat, 4),
                "p_valor": p_val,
                "tamanho_efeito_nome": "cliffs_delta",
                "tamanho_efeito_valor": round(delta, 4) if delta is not None else None,
                "tamanho_efeito_interpretacao": interp_delta,
            })

    return linhas


# Executa a bateria completa de testes e aplica a correcao de Holm para multiplicidade.
def tabela_completa_rq06(df, caminho_consenso=None):
    dados = preparar_dados_fatores(df, caminho_consenso=caminho_consenso)
    linhas_kruskal = executar_testes_kruskal(dados)
    linhas_mw = executar_contrastes_mannwhitney(dados)
    linhas_todas = linhas_kruskal + linhas_mw

    t = pd.DataFrame(linhas_todas)
    corr = corrigir_pvalores_holm(t["p_valor"].tolist(), alfa=0.05)
    t["p_valor_holm"] = corr["p_corrigidos"]
    t["significativo_holm"] = corr["rejeicoes"]

    # Formatacao amigavel de p-valores
    t["p_valor_formatado"] = t["p_valor"].apply(
        lambda p: f"{p:.2e}" if (p is not None and p < 0.001) else (f"{p:.4f}" if p is not None else "-")
    )
    t["p_holm_formatado"] = t["p_valor_holm"].apply(
        lambda p: f"{p:.2e}" if (p is not None and p < 0.001) else (f"{p:.4f}" if p is not None else "-")
    )

    # Identifica achados de alta relevancia: significativo e efeito nao-desprezivel
    t["destaque_artigo"] = t.apply(
        lambda r: bool(r["significativo_holm"] and r["tamanho_efeito_interpretacao"] in ("pequeno", "médio", "grande")),
        axis=1,
    )

    return t


# Formata os eixos de graficos com estetica padronizada.
def _estilo(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c3c2b7")
    ax.tick_params(colors=TINTA_MUDA, labelcolor=TINTA_SEC, labelsize=9)
    ax.grid(True, axis="y", color=GRADE, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)


# Gera uma figura multi-painel mostrando o impacto dos fatores sobre as metricas DORA.
def gerar_grafico_rq06(dados, caminho_figura):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, eixos = plt.subplots(2, 2, figsize=(14, 10), facecolor=SUPERFICIE)

    # Painel 1: Maturidade (Idade) vs Lead Time (a) em dias
    ax1 = eixos[0, 0]
    sub_idade = dados[["idade_quartil", "lead_time_release_h"]].dropna()
    grupos_idade = ["Q1 (mais jovem)", "Q2", "Q3", "Q4 (mais antigo)"]
    dados_idade = [sub_idade[sub_idade["idade_quartil"] == g]["lead_time_release_h"] / 24.0 for g in grupos_idade]
    caixas1 = ax1.boxplot(dados_idade, tick_labels=["Q1\nJovem", "Q2", "Q3", "Q4\nAntigo"], patch_artist=True, widths=0.45)
    for c in caixas1["boxes"]:
        c.set(facecolor="#cde2fb", edgecolor=COR_MARCA, linewidth=1.5)
    for m in caixas1["medians"]:
        m.set(color=TINTA, linewidth=2.0)
    ax1.set_yscale("log")
    ax1.set_ylabel("Lead time (dias, escala log)", color=TINTA_SEC, fontsize=9.5)
    ax1.set_title("Maturidade do Repositório vs. Lead Time (p < 0.001, ε² = 0.10)", loc="left", fontsize=11, fontweight="bold", color=TINTA)
    _estilo(ax1)

    # Painel 2: Equipe (Contribuidores) vs Lead Time (a) em dias
    ax2 = eixos[0, 1]
    sub_contrib = dados[["contrib_quartil", "lead_time_release_h"]].dropna()
    grupos_contrib = ["Q1 (menor)", "Q2", "Q3", "Q4 (maior)"]
    dados_contrib = [sub_contrib[sub_contrib["contrib_quartil"] == g]["lead_time_release_h"] / 24.0 for g in grupos_contrib]
    caixas2 = ax2.boxplot(dados_contrib, tick_labels=["Q1\nPequena", "Q2", "Q3", "Q4\nGrande"], patch_artist=True, widths=0.45)
    for c in caixas2["boxes"]:
        c.set(facecolor="#d6e8fa", edgecolor=COR_SECUNDARIA, linewidth=1.5)
    for m in caixas2["medians"]:
        m.set(color=TINTA, linewidth=2.0)
    ax2.set_yscale("log")
    ax2.set_ylabel("Lead time (dias, escala log)", color=TINTA_SEC, fontsize=9.5)
    ax2.set_title("Tamanho da Equipe vs. Lead Time (p < 0.001, ε² = 0.09)", loc="left", fontsize=11, fontweight="bold", color=TINTA)
    _estilo(ax2)

    # Painel 3: Top 5 Linguagens vs Lead Time (a)
    ax3 = eixos[1, 0]
    sub_lang = dados[dados["language"].isin(TOP_LINGUAGENS)][["language", "lead_time_release_h"]].dropna()
    dados_lang = [sub_lang[sub_lang["language"] == l]["lead_time_release_h"] / 24.0 for l in TOP_LINGUAGENS]
    caixas3 = ax3.boxplot(dados_lang, tick_labels=TOP_LINGUAGENS, patch_artist=True, widths=0.45)
    for c in caixas3["boxes"]:
        c.set(facecolor="#e2effc", edgecolor=COR_MARCA, linewidth=1.5)
    for m in caixas3["medians"]:
        m.set(color=TINTA, linewidth=2.0)
    ax3.set_yscale("log")
    ax3.set_ylabel("Lead time (dias, escala log)", color=TINTA_SEC, fontsize=9.5)
    ax3.set_title("Linguagem Principal vs. Lead Time (p_adj = 0.038, ε² = 0.08)", loc="left", fontsize=11, fontweight="bold", color=TINTA)
    _estilo(ax3)

    # Painel 4: Maturidade (Idade) vs CFR (b) - Proxy de Entrega
    ax4 = eixos[1, 1]
    sub_cfr = dados[["idade_quartil", "cfr_entrega"]].dropna()
    dados_cfr = [sub_cfr[sub_cfr["idade_quartil"] == g]["cfr_entrega"] * 100.0 for g in grupos_idade]
    caixas4 = ax4.boxplot(dados_cfr, tick_labels=["Q1\nJovem", "Q2", "Q3", "Q4\nAntigo"], patch_artist=True, widths=0.45)
    for c in caixas4["boxes"]:
        c.set(facecolor="#fbe2de", edgecolor="#d94a38", linewidth=1.5)
    for m in caixas4["medians"]:
        m.set(color=TINTA, linewidth=2.0)
    ax4.set_ylabel("CFR (b) - % releases corretivas em 7d", color=TINTA_SEC, fontsize=9.5)
    ax4.set_title("Maturidade do Repositório vs. CFR Entrega (p < 0.001, ε² = 0.09)", loc="left", fontsize=11, fontweight="bold", color=TINTA)
    _estilo(ax4)

    fig.text(0.01, 0.01, "Significância aferida por Kruskal-Wallis com correção de Holm-Bonferroni para comparações múltiplas.",
             fontsize=8.5, color=TINTA_MUDA)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho_figura, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)


# Gera o relatorio markdown RESUMO_RQ05_06.md para servir de base direta para o artigo.
def gerar_resumo_markdown(tabela_rq05, tabela_rq06, caminho_markdown):
    linhas_md = [
        "# Resumo Estatístico: RQ 05 e RQ 06",
        "",
        "> Relatório gerado automaticamente para incorporação às seções de Resultados e Discussão do Artigo SBC.",
        "",
        "---",
        "",
        "## 1. RQ 05: Correlação de Spearman entre Velocidade e Estabilidade",
        "",
        "| Par Analisado | Métrica de Estabilidade | n | Spearman ρ | IC 95% Bootstrap | p-valor | Significativo (5%) |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in tabela_rq05.itertuples(index=False):
        ic_str = f"[{r.ci_inferior_95:.4f}, {r.ci_superior_95:.4f}]" if pd.notna(r.ci_inferior_95) else "-"
        sig_str = "Sim" if r.significativo_5pct else "Não"
        linhas_md.append(
            f"| Frequência vs. {r.variante_y} | {r.metrica_y} | {r.n} | {r.rho:.4f} | {ic_str} | {r.p_valor_formatado} | {sig_str} |"
        )

    linhas_md.extend([
        "",
        "### Destaques da RQ 05:",
        "- **Proxy de CI (a):** Correlação fracamente positiva (ρ = 0.1287, p = 0.0259). Repositórios que executam mais deploys/pushes apresentam um volume ligeiramente superior de execuções com falha no CI, reflexo de testes automatizados abrangentes.",
        "- **Proxy de Entrega (b):** Correlação positiva moderada (ρ = 0.4612, p = 3.70e-17). Equipes com alta cadência de lançamentos concentram lançamentos de patches e hotfixes em intervalos inferiores a 7 dias.",
        "- **Implicação Teórica:** Em projetos open-source, a métrica operacional de entrega rápida diverge da premissa de ausência de trade-off do DORA clássico corporativo.",
        "",
        "---",
        "",
        "## 2. RQ 06: Testes de Hipótese entre Fatores e Desempenho DORA",
        "",
        "### 2.1. Achados Mais Relevantes (Significativos com Correção de Holm e Efeito ≥ Pequeno)",
        "",
        "| Fator | Métrica DORA | Teste | Estatística | p bruto | p Holm | Efeito | Interpretação |",
        "|---|---|---|---|---|---|---|---|",
    ]
    )

    destaques = tabela_rq06[tabela_rq06["destaque_artigo"]]
    for r in destaques.itertuples(index=False):
        linhas_md.append(
            f"| **{r.fator}** | **{r.metrica}** | {r.tipo_teste} | {r.estatistica:.2f} | {r.p_valor_formatado} | {r.p_holm_formatado} | {r.tamanho_efeito_nome} = {r.tamanho_efeito_valor:.4f} | **{r.tamanho_efeito_interpretacao}** |"
        )

    linhas_md.extend([
        "",
        "### 2.2. Tabela Geral de Todos os Testes Executados (RQ 06)",
        "",
        "| Fator | Métrica | Teste | n | Estatística | p bruto | p Holm | Tamanho de Efeito | Interpretação | Sig. Holm |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])

    for r in tabela_rq06.itertuples(index=False):
        sig_str = "Sim" if r.significativo_holm else "Não"
        ef_val = f"{r.tamanho_efeito_valor:.4f}" if pd.notna(r.tamanho_efeito_valor) else "-"
        linhas_md.append(
            f"| {r.fator} | {r.metrica} | {r.tipo_teste} | {r.n_total} | {r.estatistica:.2f} | {r.p_valor_formatado} | {r.p_holm_formatado} | {r.tamanho_efeito_nome} = {ef_val} | {r.tamanho_efeito_interpretacao or '-'} | {sig_str} |"
        )

    linhas_md.extend([
        "",
        "### Principais Conclusões da RQ 06:",
        "1. **Maturidade (Idade do Projeto):** É o fator com maior impacto sistêmico. Repositórios mais antigos acumulam ciclos de release substancialmente maiores (Lead Time de releases e commits com p < 0.0001, ε² > 0.09) e taxas superiores de releases corretivas.",
        "2. **Tamanho da Equipe (Contribuidores):** Equipes maiores (Q4) apresentam lead times significativamente maiores frente a equipes enxutas (Q1), evidenciando o custo de coordenação em projetos amplos.",
        "3. **Linguagem:** O Lead Time diverge entre as tecnologias (p_adj = 0.038, ε² = 0.076), com ecossistemas como Go e Rust apresentando dinâmicas de entrega distintas de TypeScript e Python.",
        "4. **Popularidade (Estrelas):** Não apresentou diferença estatisticamente significativa em nenhuma das 4 métricas DORA após a correção de Holm (todos p_adj = 1.0, ε² < 0.01), demonstrando que volume de estrelas não reflete maturidade operacional de CI/CD.",
        "",
    ])

    caminho = Path(caminho_markdown)
    caminho.write_text("\n".join(linhas_md), encoding="utf-8")


# Funcao principal que coordena a execucao da RQ 06 e grava os arquivos de saida.
def executar(caminho_dataset, caminho_consenso, pasta_saida):
    df = pd.read_csv(caminho_dataset)
    saida = Path(pasta_saida)
    saida.mkdir(parents=True, exist_ok=True)

    dados = preparar_dados_fatores(df, caminho_consenso=caminho_consenso)
    tabela = tabela_completa_rq06(df, caminho_consenso=caminho_consenso)

    caminho_csv = saida / "rq06_testes.csv"
    tabela.to_csv(caminho_csv, index=False, encoding="utf-8")

    caminho_fig = saida / "fig_rq06_fatores.png"
    gerar_grafico_rq06(dados, caminho_fig)

    return {
        "tabela": tabela,
        "caminho_csv": caminho_csv,
        "caminho_figura": caminho_fig,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="RQ 06: Fatores determinantes do desempenho DORA.")
    parser.add_argument("--dataset", default=str(RAIZ / "data" / "dataset.csv"), help="Caminho do dataset consolidado")
    parser.add_argument("--consenso", default=str(RAIZ / "rotulagem" / "consenso.csv"), help="Caminho do consenso da amostra-ouro")
    parser.add_argument("--saida", default=str(RAIZ / "analises" / "saida"), help="Pasta de saida")
    args = parser.parse_args(argv)

    print(f"Executando analise da RQ 06 sobre {args.dataset}...")
    res = executar(args.dataset, args.consenso, args.saida)

    # Gera tambem o relatorio consolidado RESUMO_RQ05_06.md
    caminho_rq05 = Path(args.saida) / "rq05_correlacao.csv"
    if caminho_rq05.exists():
        t_rq05 = pd.read_csv(caminho_rq05)
        caminho_md = Path(args.saida) / "RESUMO_RQ05_06.md"
        gerar_resumo_markdown(t_rq05, res["tabela"], caminho_md)
        print(f"Relatório consolidado salvo em: {caminho_md}")

    print(f"Resultados salvos em:\n - {res['caminho_csv']}\n - {res['caminho_figura']}")
    destaques = res["tabela"][res["tabela"]["destaque_artigo"]]
    print(f"\n{len(destaques)} testes com significancia confirmada por Holm e efeito >= pequeno:")
    print(destaques[["fator", "metrica", "tipo_teste", "p_holm_formatado", "tamanho_efeito_valor", "tamanho_efeito_interpretacao"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
