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

def main():
    df = load_data()
    print(f"Dados carregados com sucesso: {len(df)} repositórios.")

    print("Gerando Ponto 1: Dispersão Estrelas vs Forks...")
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

    print("\nTodos os 2 gráficos (Pontos 1 e 2) foram gerados com sucesso!")

if __name__ == "__main__":
    main()
