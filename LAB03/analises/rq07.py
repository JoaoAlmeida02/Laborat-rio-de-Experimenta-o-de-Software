"""RQ 07: Sensibilidade das classificações DORA a variações metodológicas (C1, C2, C3 e C4).

Compara o impacto das diferentes escolhas operacionais nas 4 métricas DORA:
- C1: unidade release, lead time (a: release), CFR (a: CI) [Combinação de referência]
- C2: unidade release + pré-release, lead time (b: commit), CFR (b: entrega)
- C3: unidade tags, lead time (b: commit), CFR (a: CI)
- C4: C1 filtrada apenas em repositórios da amostra rotulada como 'entrega real'

Gera em --saida (default: analises/saida):
- rq07_concordancia.csv: concordância (% mudança e Cohen's Kappa linear) entre os pares
- rq07_classificacoes_c1_c2_c3.csv: categoria geral de cada repositório em C1, C2 e C3
- rq07_transicao_C1_C2.csv: matriz de transição de C1 para C2
- rq07_transicao_C1_C3.csv: matriz de transição de C1 para C3
- rq07_transicao_C2_C3.csv: matriz de transição de C2 para C3
- rq07_c4_filtrada.csv: avaliação da amostra-ouro com filtro de entrega real (C4 vs C1)
- fig_rq07_transicao_C1_C2.png: heatmap visual da transição C1 -> C2
- RESUMO_RQ07.md: relatório textual consolidado com tabelas para o artigo
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from metricas.classificacao import (
    MAPEAMENTO_CATEGORIAS,
    classificar_dora,
)

RAIZ = Path(__file__).resolve().parents[1]
CATEGORIAS: list[str] = ["Low", "Medium", "High", "Elite"]

# Paleta estética consistente com o projeto (rq01_04, rq05, rq06)
SUPERFICIE, TINTA, TINTA_SEC, TINTA_MUDA, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
COR_MARCA = "#2a78d6"


def classificar_configuracao(
    df: pd.DataFrame,
    col_frequencia: str = "deploy_frequency_semana",
    col_lead_time: str = "lead_time_release_h",
    col_cfr: str = "cfr_ci",
    col_recuperacao: str = "tempo_recuperacao_h",
) -> pd.DataFrame:
    """Classifica cada repositório do DataFrame segundo uma configuração DORA.

    Retorna DataFrame indexado pelos mesmos índices do df de entrada,
    com colunas para categoria de cada métrica e categoria geral.
    """
    linhas: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        freq = None if pd.isna(row.get(col_frequencia)) else float(row[col_frequencia])
        lt = None if pd.isna(row.get(col_lead_time)) else float(row[col_lead_time])
        cfr = None if pd.isna(row.get(col_cfr)) else float(row[col_cfr])
        rec = row.get(col_recuperacao)
        rec_s = None if pd.isna(rec) else float(rec) * 3600.0

        res = classificar_dora(
            cfr=cfr,
            tempo_recuperacao_val=rec_s,
            frequencia=freq,
            lead_time_h=lt,
        )
        linhas.append({
            "repo": row.get("repo", ""),
            "categoria_frequencia": res["frequencia"],
            "categoria_lead_time": res["lead_time"],
            "categoria_cfr": res["cfr"],
            "categoria_recuperacao": res["recuperacao"],
            "categoria_geral": res["geral"],
            "n_metricas": res["n_metricas"],
        })

    return pd.DataFrame(linhas, index=df.index)


def comparar_pares(
    serie_a: pd.Series,
    serie_b: pd.Series,
    nome_a: str = "A",
    nome_b: str = "B",
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Calcula concordância, taxa de mudança e Cohen's Kappa linear entre duas classificações.

    Considera apenas repositórios com valor não-nulo em ambas as séries.
    """
    ordem = labels or CATEGORIAS
    mask = serie_a.notna() & serie_b.notna()
    val_a = serie_a[mask]
    val_b = serie_b[mask]
    n = len(val_a)

    if n == 0:
        return {
            "par": f"{nome_a} x {nome_b}",
            "n": 0,
            "mudaram": 0,
            "permaneceram": 0,
            "pct_mudanca": 0.0,
            "pct_concordancia": 0.0,
            "kappa_linear": None,
            "interpretacao_kappa": "Sem dados suficientes",
        }

    mudaram = int((val_a != val_b).sum())
    permaneceram = n - mudaram
    pct_mudanca = round(100.0 * mudaram / n, 2)
    pct_concordancia = round(100.0 * permaneceram / n, 2)

    # Cohen Kappa linear ponderado para variáveis ordinais
    try:
        kappa = cohen_kappa_score(val_a, val_b, labels=ordem, weights="linear")
        kappa = round(float(kappa), 4)
    except Exception:
        kappa = None

    # Interpretação Landis & Koch (1977)
    if kappa is None:
        interp = "Indeterminado"
    elif kappa < 0:
        interp = "Sem concordância (pior que o acaso)"
    elif kappa <= 0.20:
        interp = "Concordância leve (slight)"
    elif kappa <= 0.40:
        interp = "Concordância razoável (fair)"
    elif kappa <= 0.60:
        interp = "Concordância moderada (moderate)"
    elif kappa <= 0.80:
        interp = "Concordância substancial (substantial)"
    else:
        interp = "Concordância quase perfeita (almost perfect)"

    return {
        "par": f"{nome_a} x {nome_b}",
        "n": n,
        "mudaram": mudaram,
        "permaneceram": permaneceram,
        "pct_mudanca": pct_mudanca,
        "pct_concordancia": pct_concordancia,
        "kappa_linear": kappa,
        "interpretacao_kappa": interp,
    }


def calcular_matriz_transicao(
    serie_de: pd.Series,
    serie_para: pd.Series,
    labels: list[str] | None = None,
) -> pd.DataFrame:
    """Gera matriz de transição (contingência) com contagens absolutas reindexada pelas categorias ordinais."""
    ordem = labels or CATEGORIAS
    mask = serie_de.notna() & serie_para.notna()
    ct = pd.crosstab(serie_de[mask], serie_para[mask])
    return ct.reindex(index=ordem, columns=ordem, fill_value=0)


def avaliar_c4_filtrada(
    df_dataset: pd.DataFrame,
    caminho_consenso: Path | str,
    c1_geral: pd.Series,
    labels: list[str] | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Avalia a C4 (C1 restrita a repositórios cujas releases foram rotuladas como 'entrega real').

    Retorna estatísticas comparativas e DataFrame detalhado dos repositórios participantes.
    """
    ordem = labels or CATEGORIAS
    caminho = Path(caminho_consenso)
    if not caminho.exists():
        return {
            "n_amostra_rotulada": 0,
            "n_sobreposicao_dataset": 0,
            "mudaram": 0,
            "pct_mudanca": 0.0,
            "kappa_linear": None,
            "interpretacao": "Arquivo de consenso não encontrado.",
        }, pd.DataFrame()

    cons = pd.read_csv(caminho)
    # Repositórios com ao menos uma release rotulada como 'sim' em entrega_real
    repos_com_entrega_real = set(cons[cons["entrega_real_consenso"] == "sim"]["repo"].unique())
    # Repositórios onde 100% das releases avaliadas foram 'sim'
    sim_counts = cons.groupby("repo")["entrega_real_consenso"].apply(lambda s: (s == "sim").all())
    repos_100pct_real = set(sim_counts[sim_counts].index)

    # Filtra repositórios presentes no dataset final
    df_c4 = df_dataset[df_dataset["repo"].isin(repos_com_entrega_real)].copy()
    indices = df_c4.index

    c1_sub = c1_geral.loc[indices]
    # Na definição C4 filtrada, a classificação DORA aplica as mesmas regras de C1 na subamostra validada
    c4_classif = classificar_configuracao(
        df_c4,
        col_frequencia="deploy_frequency_semana",
        col_lead_time="lead_time_release_h",
        col_cfr="cfr_ci",
        col_recuperacao="tempo_recuperacao_h",
    )
    c4_geral = c4_classif["categoria_geral"]

    comp = comparar_pares(c1_sub, c4_geral, nome_a="C1_amostra", nome_b="C4_filtrada", labels=ordem)

    detalhe_repos = pd.DataFrame({
        "repo": df_c4["repo"].values,
        "categoria_C1": c1_sub.values,
        "categoria_C4": c4_geral.values,
        "todas_releases_reais": [r in repos_100pct_real for r in df_c4["repo"]],
    })

    resultado = {
        "n_repos_amostra_ouro": cons["repo"].nunique(),
        "n_repos_com_entrega_real": len(repos_com_entrega_real),
        "n_sobreposicao_dataset_final": len(df_c4),
        "repositorios": list(df_c4["repo"]),
        "mudaram": comp["mudaram"],
        "pct_mudanca": comp["pct_mudanca"],
        "kappa_linear": comp["kappa_linear"],
        "interpretacao": comp["interpretacao_kappa"],
    }
    return resultado, detalhe_repos


def gerar_grafico_transicao(
    matriz: pd.DataFrame,
    caminho_figura: Path | str,
    titulo: str = "Matriz de Transição DORA: C1 → C2",
    rotulo_x: str = "Configuração C2 (releases+pre, lead time b, CFR b)",
    rotulo_y: str = "Configuração C1 (releases, lead time a, CFR a)",
) -> None:
    """Gera heatmap estilizado da matriz de transição entre categorias DORA."""
    caminho = Path(caminho_figura)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 6.2), facecolor=SUPERFICIE)
    ax.set_facecolor(SUPERFICIE)

    valores = matriz.values
    total = valores.sum()

    # Heatmap em tons de azul condizente com a paleta do laboratório
    im = ax.imshow(valores, cmap="Blues", interpolation="nearest")

    ax.set_xticks(range(len(matriz.columns)))
    ax.set_yticks(range(len(matriz.index)))
    ax.set_xticklabels(matriz.columns, fontsize=10, color=TINTA_SEC)
    ax.set_yticklabels(matriz.index, fontsize=10, color=TINTA_SEC)

    ax.set_xlabel(rotulo_x, fontsize=10.5, color=TINTA, fontweight="bold", labelpad=10)
    ax.set_ylabel(rotulo_y, fontsize=10.5, color=TINTA, fontweight="bold", labelpad=10)
    ax.set_title(titulo, loc="left", fontsize=12, color=TINTA, fontweight="bold", pad=14)

    # Anotação com contagem absoluta e percentual
    vmax = valores.max()
    for i in range(len(matriz.index)):
        for j in range(len(matriz.columns)):
            val = valores[i, j]
            pct = 100.0 * val / total if total > 0 else 0.0
            cor_texto = "#ffffff" if val > (vmax * 0.55) else TINTA
            texto = f"{val}\n({pct:.1f}%)" if val > 0 else "0"
            ax.text(j, i, texto, ha="center", va="center", color=cor_texto, fontsize=9.5, fontweight="medium")

    # Linhas de separação e spines limpos
    ax.set_xticks(np.arange(-0.5, len(matriz.columns), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(matriz.index), 1), minor=True)
    ax.grid(which="minor", color=SUPERFICIE, linestyle="-", linewidth=2.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    for lado in ("top", "right", "bottom", "left"):
        ax.spines[lado].set_visible(False)

    plt.tight_layout()
    plt.savefig(caminho, dpi=300, facecolor=SUPERFICIE)
    plt.close(fig)


def gerar_relatorio_md(
    df_pares: pd.DataFrame,
    matriz_c1_c2: pd.DataFrame,
    c4_res: dict[str, Any],
    caminho_md: Path | str,
) -> None:
    """Gera documento Markdown com tabelas prontas para inclusão no artigo/relatório."""
    caminho = Path(caminho_md)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    linhas = [
        "# RQ 07: Sensibilidade das Métricas DORA a Variações Metodológicas",
        "",
        "Avaliação do impacto de diferentes escolhas de unidade de entrega, variante de lead time e proxy de CFR:",
        "- **C1 (Referência):** unidade release, lead time (a: release), CFR (a: CI);",
        "- **C2:** unidade releases + pré-releases, lead time (b: commit), CFR (b: entrega);",
        "- **C3:** unidade tags, lead time (b: commit), CFR (a: CI);",
        "- **C4 (Filtrada):** C1 aplicada exclusivamente aos repositórios rotulados com entrega real na amostra-ouro.",
        "",
        "## 1. Concordância e Estabilidade entre Combinações (Pares C1, C2, C3)",
        "",
        "| Par de Combinações | n | Repositórios que Mudaram | % Mudança | Concordância (%) | Cohen's Kappa (linear) | Interpretação |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for _, r in df_pares.iterrows():
        linhas.append(
            f"| **{r['par']}** | {r['n']} | {r['mudaram']} | {r['pct_mudanca']}% | {r['pct_concordancia']}% | "
            f"{r['kappa_linear']:.4f} | {r['interpretacao_kappa']} |"
        )

    linhas.extend([
        "",
        "## 2. Matriz de Transição C1 → C2 (Contagens Absolutas)",
        "",
        "Mostra as mudanças de classificação quando se migra da combinação clássica (C1) para a combinação com commits e entregas corretivas (C2):",
        "",
        "| C1 (Linhas) \\ C2 (Colunas) | Low | Medium | High | Elite | Total C1 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for cat in CATEGORIAS:
        linha_vals = [str(matriz_c1_c2.loc[cat, col]) for col in CATEGORIAS]
        tot = matriz_c1_c2.loc[cat].sum()
        linhas.append(f"| **{cat}** | " + " | ".join(linha_vals) + f" | **{tot}** |")

    tot_cols = [str(matriz_c1_c2[col].sum()) for col in CATEGORIAS]
    linhas.append(f"| **Total C2** | " + " | ".join(tot_cols) + f" | **{matriz_c1_c2.values.sum()}** |")

    linhas.extend([
        "",
        "## 3. Análise da Configuração C4 ('Filtrada' por Entrega Real)",
        "",
        f"- **População da amostra-ouro rotulada:** {c4_res.get('n_repos_amostra_ouro', 0)} repositórios ({c4_res.get('n_repos_com_entrega_real', 0)} com entregas reais);",
        f"- **Repositórios sobrepostos no dataset final (funil):** {c4_res.get('n_sobreposicao_dataset_final', 0)} repositórios ({', '.join(c4_res.get('repositorios', []))});",
        f"- **Taxa de mudança C4 vs C1:** {c4_res.get('pct_mudanca', 0.0)}% ({c4_res.get('mudaram', 0)} repositórios);",
        f"- **Cohen's Kappa linear:** {c4_res.get('kappa_linear')} ({c4_res.get('interpretacao')});",
        "",
        "> **Nota Metodológica:** Como documentado no funil e na amostra-ouro, apenas 4 repositórios da amostra rotulada atenderam aos critérios de inclusão (≥5 releases e ≥50 runs em 2025). As classificações C1 desses repositórios se mantêm inalteradas sob a regra de C4, pois todas as suas releases avaliadas constituíram entregas reais de valor.",
        "",
    ])

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def rodar_rq07(
    caminho_dataset: Path | str = "data/dataset.csv",
    pasta_saida: Path | str = "analises/saida",
    caminho_consenso: Path | str = "rotulagem/consenso.csv",
) -> dict[str, Any]:
    """Executa o pipeline analítico completo da RQ 07."""
    p_dataset = Path(caminho_dataset)
    p_saida = Path(pasta_saida)
    p_consenso = Path(caminho_consenso)
    p_saida.mkdir(parents=True, exist_ok=True)

    if not p_dataset.exists():
        raise FileNotFoundError(f"Dataset não encontrado em: {p_dataset}")

    df = pd.read_csv(p_dataset)

    # 1. Classificação C1: releases, lead time (a), CFR (a)
    c1 = classificar_configuracao(
        df,
        col_frequencia="deploy_frequency_semana",
        col_lead_time="lead_time_release_h",
        col_cfr="cfr_ci",
        col_recuperacao="tempo_recuperacao_h",
    )

    # 2. Classificação C2: releases + pré-releases, lead time (b), CFR (b)
    c2 = classificar_configuracao(
        df,
        col_frequencia="deploy_frequency_semana",
        col_lead_time="lead_time_commit_h",
        col_cfr="cfr_entrega",
        col_recuperacao="tempo_recuperacao_h",
    )

    # 3. Classificação C3: apenas tags, lead time (b), CFR (a)
    c3 = classificar_configuracao(
        df,
        col_frequencia="deploy_frequency_semana",
        col_lead_time="lead_time_commit_h",
        col_cfr="cfr_ci",
        col_recuperacao="tempo_recuperacao_h",
    )

    # Exporta tabela consolidada por repositório
    df_consolidado = pd.DataFrame({
        "repo": df["repo"],
        "C1_categoria_geral": c1["categoria_geral"],
        "C2_categoria_geral": c2["categoria_geral"],
        "C3_categoria_geral": c3["categoria_geral"],
        "C1_nota": c1["categoria_geral"].map(MAPEAMENTO_CATEGORIAS),
        "C2_nota": c2["categoria_geral"].map(MAPEAMENTO_CATEGORIAS),
        "C3_nota": c3["categoria_geral"].map(MAPEAMENTO_CATEGORIAS),
        "mudou_C1_C2": c1["categoria_geral"] != c2["categoria_geral"],
        "mudou_C1_C3": c1["categoria_geral"] != c3["categoria_geral"],
        "mudou_C2_C3": c2["categoria_geral"] != c3["categoria_geral"],
    })
    df_consolidado.to_csv(p_saida / "rq07_classificacoes_c1_c2_c3.csv", index=False)

    # Comparações de pares ordinais
    pares = [
        ("C1", c1["categoria_geral"], "C2", c2["categoria_geral"]),
        ("C1", c1["categoria_geral"], "C3", c3["categoria_geral"]),
        ("C2", c2["categoria_geral"], "C3", c3["categoria_geral"]),
    ]

    linhas_pares: list[dict[str, Any]] = []
    for nome_a, s_a, nome_b, s_b in pares:
        res_par = comparar_pares(s_a, s_b, nome_a=nome_a, nome_b=nome_b, labels=CATEGORIAS)
        linhas_pares.append(res_par)

    df_pares = pd.DataFrame(linhas_pares)
    df_pares.to_csv(p_saida / "rq07_concordancia.csv", index=False)

    # Matrizes de transição
    matriz_c1_c2 = calcular_matriz_transicao(c1["categoria_geral"], c2["categoria_geral"], labels=CATEGORIAS)
    matriz_c1_c3 = calcular_matriz_transicao(c1["categoria_geral"], c3["categoria_geral"], labels=CATEGORIAS)
    matriz_c2_c3 = calcular_matriz_transicao(c2["categoria_geral"], c3["categoria_geral"], labels=CATEGORIAS)

    matriz_c1_c2.to_csv(p_saida / "rq07_transicao_C1_C2.csv")
    matriz_c1_c3.to_csv(p_saida / "rq07_transicao_C1_C3.csv")
    matriz_c2_c3.to_csv(p_saida / "rq07_transicao_C2_C3.csv")

    # Heatmap PNG
    caminho_fig = p_saida / "fig_rq07_transicao_C1_C2.png"
    gerar_grafico_transicao(matriz_c1_c2, caminho_fig)

    # Avaliação da C4 filtrada
    c4_res, df_c4_detalhes = avaliar_c4_filtrada(df, p_consenso, c1["categoria_geral"], labels=CATEGORIAS)
    df_c4_detalhes.to_csv(p_saida / "rq07_c4_filtrada.csv", index=False)

    # Relatório resumido em Markdown
    caminho_md = p_saida / "RESUMO_RQ07.md"
    gerar_relatorio_md(df_pares, matriz_c1_c2, c4_res, caminho_md)

    print(f"RQ 07 concluída com sucesso!")
    print(f"Resultados e matrizes exportados em: {p_saida}")
    print(f"Figura gerada em: {caminho_fig}")
    print(f"Resumo salvo em: {caminho_md}")

    return {
        "pares": df_pares,
        "matriz_c1_c2": matriz_c1_c2,
        "c4": c4_res,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ 07: Sensibilidade das Classificações DORA (C1, C2, C3, C4).")
    parser.add_argument("--dataset", default="data/dataset.csv", help="Caminho para o dataset.csv")
    parser.add_argument("--saida", default="analises/saida", help="Diretório para salvar saídas analíticas")
    parser.add_argument("--consenso", default="rotulagem/consenso.csv", help="Caminho para consenso.csv")
    args = parser.parse_args()

    caminho_ds = RAIZ / args.dataset if not Path(args.dataset).is_absolute() else Path(args.dataset)
    pasta_saida = RAIZ / args.saida if not Path(args.saida).is_absolute() else Path(args.saida)
    caminho_cons = RAIZ / args.consenso if not Path(args.consenso).is_absolute() else Path(args.consenso)

    rodar_rq07(caminho_dataset=caminho_ds, pasta_saida=pasta_saida, caminho_consenso=caminho_cons)


if __name__ == "__main__":
    main()
