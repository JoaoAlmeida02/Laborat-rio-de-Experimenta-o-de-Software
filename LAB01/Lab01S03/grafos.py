import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["axes.edgecolor"] = "#cccccc"
plt.rcParams["axes.linewidth"] = 1.0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "dados", "repositorios_1000.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "graficos")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_data():
    if not os.path.exists(CSV_PATH):
        sys.exit(f"Erro: Arquivo CSV não encontrado em {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    
    df["issues_closed_ratio_clean"] = pd.to_numeric(df["issues_closed_ratio"], errors="coerce")
    df["stars_to_forks_ratio_clean"] = pd.to_numeric(df["stars_to_forks_ratio"], errors="coerce")
    
    df["primary_language_label"] = df["primary_language"].fillna("N/A")
    df.loc[df["primary_language_label"] == "N/A", "primary_language_label"] = "Docs / Listas (N/A)"
    
    return df

def generate_rq_graphs(df):
    print("\n--- Gerando gráficos individuais por Questão de Pesquisa (RQs) ---")

    # RQ01: Idade dos repositórios
    print("Gerando RQ01: Idade dos repositórios...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    med_idade = df["age_years"].median()
    sns.histplot(df["age_years"], bins=30, kde=True, color="#2980b9", ax=ax)
    ax.axvline(med_idade, color="#c0392b", linestyle="--", linewidth=1.8, label=f"Mediana: {med_idade:.2f} anos (~2.819 dias)")
    ax.set_title("RQ 01. Sistemas populares são maduros/antigos?\nDistribuição da Idade dos Repositórios", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Idade (Anos)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ01_idade_repositorios.png"))
    plt.close()

    # RQ02: Contribuição externa (PRs aceitos)
    print("Gerando RQ02: Pull Requests aceitos...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    med_prs = df["total_accepted_pull_requests"].median()
    # Usando escala logarítmica para acomodar a cauda longa
    log_prs = np.log10(df["total_accepted_pull_requests"] + 1)
    sns.histplot(log_prs, bins=30, kde=True, color="#27ae60", ax=ax)
    ax.axvline(np.log10(med_prs + 1), color="#c0392b", linestyle="--", linewidth=1.8, label=f"Mediana: {med_prs:.0f} PRs")
    ax.set_title("RQ 02. Sistemas populares recebem muita contribuição externa?\nDistribuição de PRs Aceitos (Escala Log10)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("log10(Total de PRs Aceitos + 1)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ02_pull_requests_aceitos.png"))
    plt.close()

    # RQ03: Frequência de releases
    print("Gerando RQ03: Total de releases...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    med_rel = df["total_releases"].median()
    log_rel = np.log10(df["total_releases"] + 1)
    sns.histplot(log_rel, bins=25, kde=True, color="#8e44ad", ax=ax)
    ax.axvline(np.log10(med_rel + 1), color="#c0392b", linestyle="--", linewidth=1.8, label=f"Mediana: {med_rel:.0f} releases")
    ax.set_title("RQ 03. Sistemas populares lançam releases com frequência?\nDistribuição de Total de Releases (Escala Log10)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("log10(Total de Releases + 1)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ03_total_releases.png"))
    plt.close()

    # RQ04: Tempo até última atualização
    print("Gerando RQ04: Dias até a última atualização...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    med_upd = df["days_since_last_update"].median()
    # Foco nos repositórios atualizados no último ano para melhor visualização
    sns.histplot(df["days_since_last_update"].clip(upper=365), bins=35, color="#e67e22", ax=ax)
    ax.axvline(med_upd, color="#c0392b", linestyle="--", linewidth=1.8, label=f"Mediana: {med_upd:.0f} dia (Recente)")
    ax.set_title("RQ 04. Sistemas populares são atualizados com frequência?\nDistribuição de Dias desde a Última Atualização", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Dias desde o Último Push (truncado em 365 dias)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ04_dias_ultima_atualizacao.png"))
    plt.close()

    # RQ05: Linguagens mais populares
    print("Gerando RQ05: Linguagens primárias...")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    top_langs = df["primary_language_label"].value_counts().head(10)
    sns.barplot(x=top_langs.values, y=top_langs.index, palette="viridis", ax=ax)
    for i, v in enumerate(top_langs.values):
        pct = (v / len(df)) * 100
        ax.text(v + 3, i, f"{v} ({pct:.1f}%)", va="center", fontsize=9, fontweight="bold")
    ax.set_xlim(0, max(top_langs.values) * 1.15)
    ax.set_title("RQ 05. Sistemas populares são escritos nas linguagens mais populares?\nTop 10 Linguagens Primárias (com base no GitHub Octoverse 2025)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Quantidade de Repositórios", fontsize=10, fontweight="bold")
    ax.set_ylabel("Linguagem Primária", fontsize=10, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ05_linguagens_populares.png"))
    plt.close()

    # RQ06: Razão de issues fechadas
    print("Gerando RQ06: Razão de issues fechadas...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    issues_clean = df["issues_closed_ratio_clean"].dropna()
    med_issues = issues_clean.median()
    sns.histplot(issues_clean, bins=25, kde=True, color="#16a085", ax=ax)
    ax.axvline(med_issues, color="#c0392b", linestyle="--", linewidth=1.8, label=f"Mediana: {med_issues:.2f} (88% fechadas)")
    ax.set_title("RQ 06. Sistemas populares possuem um alto percentual de issues fechadas?\nDistribuição da Taxa de Resolução de Issues", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Razão (Issues Fechadas / Total de Issues)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper left", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ06_razao_issues_fechadas.png"))
    plt.close()

    # RQ07: RQs 02, 03 e 04 divididas por linguagem
    # RQ07: RQs 02, 03 e 04 divididas por linguagem
    print("Gerando RQ07: Métricas divididas pelas linguagens principais...")
    top5_langs = ["Python", "TypeScript", "JavaScript", "Go", "Rust"]
    df_top5 = df[df["primary_language"].isin(top5_langs)].copy()

    fig, axes = plt.subplots(1, 3, figsize=(16, 6), dpi=300)
    
    # Subplot 1: PRs por stack
    sns.boxplot(data=df_top5, x="primary_language", y="total_accepted_pull_requests", order=top5_langs, palette="Set2", ax=axes[0])
    axes[0].set_yscale("log")
    axes[0].set_title("RQ 02: PRs Aceitos por Linguagem", fontsize=11, fontweight="bold", pad=10)
    axes[0].set_xlabel("Linguagem Primária", fontweight="bold", fontsize=10)
    axes[0].set_ylabel("PRs Mesclados (Escala Log)", fontweight="bold", fontsize=10)

    # Subplot 2: Releases por stack
    sns.boxplot(data=df_top5, x="primary_language", y="total_releases", order=top5_langs, palette="Set2", ax=axes[1])
    axes[1].set_yscale("log")
    axes[1].set_title("RQ 03: Total de Releases por Linguagem", fontsize=11, fontweight="bold", pad=10)
    axes[1].set_xlabel("Linguagem Primária", fontweight="bold", fontsize=10)
    axes[1].set_ylabel("Releases (Escala Log)", fontweight="bold", fontsize=10)

    # Subplot 3: Dias até atualização por stack
    sns.boxplot(data=df_top5, x="primary_language", y="days_since_last_update", order=top5_langs, palette="Set2", ax=axes[2])
    axes[2].set_ylim(-1, 30) # Foco no primeiro mês
    axes[2].set_title("RQ 04: Dias até Último Push por Linguagem", fontsize=11, fontweight="bold", pad=10)
    axes[2].set_xlabel("Linguagem Primária", fontweight="bold", fontsize=10)
    axes[2].set_ylabel("Dias até Última Atualização", fontweight="bold", fontsize=10)

    # Título principal com quebra de linha para não vazar a tela
    fig.suptitle(
        "RQ 07. Sistemas escritos em linguagens mais populares recebem mais contribuição externa,\n"
        "lançam mais releases e são atualizados com mais frequência?",
        fontsize=13,
        fontweight="bold",
        y=0.97
    )
    
    # Garante que os subplots não colidam com o suptitle
    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ07_metricas_por_linguagem.png"))
    plt.close()

    # RQ08: Bônus - Estrelas vs Engajamento / Forks
    print("Gerando RQ08 (Bônus): Estrelas vs Forks (Hype vs Reuso)...")
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    med_ratio = df["stars_to_forks_ratio_clean"].median()
    sns.histplot(df["stars_to_forks_ratio_clean"].clip(upper=50), bins=30, kde=True, color="#d35400", ax=ax)
    ax.axvline(med_ratio, color="#2c3e50", linestyle="--", linewidth=1.8, label=f"Mediana Global: {med_ratio:.2f}")
    ax.set_title("RQ 08 (Bônus). Estrelas correlacionam com engajamento real ou só fama?\nDistribuição da Razão Estrelas/Forks (Endosso Passivo vs Reuso)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Razão Estrelas / Forks (truncado em 50 para visualização)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Frequência (Repositórios)", fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "RQ08_estrelas_vs_forks.png"))
    plt.close()

def main():
    df = load_data()
    print(f"Dados carregados com sucesso: {len(df)} repositórios.")

    print("\nGerando Ponto 1: Dispersão Estrelas vs Forks...")
    fig, ax = plt.subplots(figsize=(11, 7), dpi=300)
    
    top_langs = df["primary_language_label"].value_counts().head(7).index.tolist()
    df["lang_group"] = df["primary_language_label"].apply(lambda x: x if x in top_langs else "Outras")
    
    min_prs, max_prs = df["total_accepted_pull_requests"].min(), df["total_accepted_pull_requests"].max()
    sizes = 30 + (df["total_accepted_pull_requests"] / max_prs) * 800

    scatter = sns.scatterplot(
        data=df,
        x="stars",
        y="forks",
        hue="lang_group",
        size=sizes,
        sizes=(30, 800),
        alpha=0.75,
        palette="tab10",
        ax=ax
    )
    
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Ponto 1: Hype vs. Reuso Real — Estrelas × Forks × PRs Aceitos", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Total de Estrelas (Escala Logarítmica)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Total de Forks (Escala Logarítmica)", fontsize=11, fontweight="bold")
    
    outliers_prod = df.nlargest(2, "total_accepted_pull_requests")
    for _, row in outliers_prod.iterrows():
        ax.annotate(
            f"{row['repository']}\n({row['total_accepted_pull_requests']:,} PRs)",
            (row["stars"], row["forks"]),
            xytext=(15, -15),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.2),
            fontsize=8,
            fontweight="bold",
            color="#2c3e50"
        )
        
    outliers_hype = df.nlargest(2, "stars_to_forks_ratio_clean")
    for _, row in outliers_hype.iterrows():
        ax.annotate(
            f"{row['repository']}\n(Razão Estrelas/Forks: {row['stars_to_forks_ratio_clean']:.1f})",
            (row["stars"], row["forks"]),
            xytext=(-40, 20),
            textcoords="offset points",
            arrowprops=dict(arrowstyle="->", color="#8e44ad", lw=1.2),
            fontsize=8,
            fontweight="bold",
            color="#2c3e50"
        )

    plt.legend(bbox_to_anchor=(1.03, 1), loc="upper left", title="Linguagem Principal", frameon=True)
    plt.tight_layout()
    p1_path = os.path.join(OUTPUT_DIR, "01_hype_vs_reuso_estrelas_forks.png")
    plt.savefig(p1_path)
    plt.close()
    print(f"  Salvo: {p1_path}")

    print("Gerando Ponto 2: Boxplot da Razão Estrelas/Forks...")
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    
    top_langs_box = df["primary_language_label"].value_counts().head(8).index.tolist()
    df_box = df[df["primary_language_label"].isin(top_langs_box)].copy()
    
    order = df_box.groupby("primary_language_label")["stars_to_forks_ratio_clean"].median().sort_values(ascending=False).index

    sns.boxplot(
        data=df_box,
        y="primary_language_label",
        x="stars_to_forks_ratio_clean",
        hue="primary_language_label",
        order=order,
        palette="Spectral",
        legend=False,
        showfliers=True,
        flierprops=dict(marker="o", markersize=4, alpha=0.5),
        ax=ax
    )
    
    ax.set_xscale("log")
    ax.set_title("Ponto 2: Proporção Estrelas / Forks (Hype vs Reuso em Código)", fontsize=13, fontweight="bold", pad=15)
    ax.set_xlabel("Razão Estrelas / Forks (Escala Logarítmica)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Linguagem Principal", fontsize=10, fontweight="bold")
    
    global_median = df["stars_to_forks_ratio_clean"].median()
    ax.axvline(global_median, color="#c0392b", linestyle="--", linewidth=1.5, label=f"Mediana Global ({global_median:.2f})")
    
    ax.legend(loc="lower right", frameon=True)
    plt.tight_layout()
    p2_path = os.path.join(OUTPUT_DIR, "02_estrelas_forks_ratio_boxplot.png")
    plt.savefig(p2_path)
    plt.close()
    print(f"  Salvo: {p2_path}")

    # Executa a geração de todos os gráficos específicos das RQs
    generate_rq_graphs(df)

    print("\nTodos os gráficos foram gerados e salvos com sucesso na pasta 'graficos/'!")

if __name__ == "__main__":
    main()