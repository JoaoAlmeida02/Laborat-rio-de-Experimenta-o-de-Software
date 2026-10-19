"""RQ 01 a 04 e classificação DORA de referência (C1).

Uso (de dentro de LAB03):
    python -m analises.rq01_04
    python -m analises.rq01_04 --dataset data/dataset.csv --saida analises/saida

Lê apenas o dataset consolidado e gera em --saida:
    rq01_04_descritiva.csv     mediana, quartis e IQR de cada métrica e variante (RQ 01 a 04)
    classificacao_C1.csv       categoria DORA por métrica e geral, por repositório (entrada da RQ 07)
    categorias_C1.csv          distribuição das categorias por métrica
    censura_e_ignoradas.csv    casos censurados (RQ 03 b e RQ 04) e releases fora do lead time
    frequencia_efetiva.csv     inovação: frequência sem releases repetidas (monorepos)
    RESUMO_RQ01_04.md          tabelas prontas para o artigo
    fig_rq01_04_boxplots.png, fig_categorias_C1.png, fig_heatmap_C1.png

C1 (enunciado, RQ 07): unidade de deploy = release, lead time (a), CFR (a) e tempo de recuperação.
"""
import argparse
from pathlib import Path

import pandas as pd

from metricas.classificacao import (
    MAPEAMENTO_CATEGORIAS,
    classificar_cfr,
    classificar_dora,
    classificar_frequencia,
    classificar_lead_time,
    classificar_recuperacao,
)
from metricas.datas import janela
from metricas.frequencia import semanas

RAIZ = Path(__file__).resolve().parents[1]
CATEGORIAS = ["Low", "Medium", "High", "Elite"]

# Cores: rampa ordinal azul (Low -> Elite), validada com o validador da skill de visualização
COR_CATEGORIA = {"Low": "#86b6ef", "Medium": "#3987e5", "High": "#1c5cab", "Elite": "#0d366b"}
COR_SEM_VALOR = "#f0efec"
COR_MARCA = "#2a78d6"
SUPERFICIE, TINTA, TINTA_SEC, TINTA_MUDA, GRADE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"


def _recuperacao_categoria(horas):
    return classificar_recuperacao(None if horas is None or pd.isna(horas) else horas * 3600)


METRICAS = [
    {"rq": "RQ 01", "coluna": "deploy_frequency_semana", "nome": "Deployment frequency",
     "variante": "-", "unidade": "releases/semana", "classificar": classificar_frequencia},
    {"rq": "RQ 02", "coluna": "lead_time_release_h", "nome": "Lead time",
     "variante": "(a) por release", "unidade": "horas", "classificar": classificar_lead_time},
    {"rq": "RQ 02", "coluna": "lead_time_commit_h", "nome": "Lead time",
     "variante": "(b) por commit", "unidade": "horas", "classificar": classificar_lead_time},
    {"rq": "RQ 03", "coluna": "cfr_ci", "nome": "Change failure rate",
     "variante": "(a) proxy de CI", "unidade": "proporção", "classificar": classificar_cfr},
    {"rq": "RQ 03", "coluna": "cfr_entrega", "nome": "Change failure rate",
     "variante": "(b) proxy de entrega", "unidade": "proporção", "classificar": classificar_cfr},
    {"rq": "RQ 04", "coluna": "tempo_recuperacao_h", "nome": "Tempo de recuperação",
     "variante": "-", "unidade": "horas", "classificar": _recuperacao_categoria},
]

# Métricas da C1 e coluna do dataset de onde cada uma vem
C1 = {
    "frequencia": "deploy_frequency_semana",
    "lead_time": "lead_time_release_h",
    "cfr": "cfr_ci",
    "recuperacao": "tempo_recuperacao_h",
}


def _valor(v):
    return None if pd.isna(v) else float(v)


def resumo(serie):
    """n, mediana, quartis e IQR de uma série (valores ausentes ignorados)."""
    s = pd.to_numeric(serie, errors="coerce").dropna()
    if s.empty:
        return {"n": 0, "mediana": None, "q1": None, "q3": None, "iqr": None, "min": None, "max": None}
    q1, mediana, q3 = s.quantile([0.25, 0.5, 0.75])
    return {"n": int(len(s)), "mediana": mediana, "q1": q1, "q3": q3, "iqr": q3 - q1,
            "min": s.min(), "max": s.max()}


def tabela_descritiva(df):
    linhas = []
    for m in METRICAS:
        r = resumo(df[m["coluna"]])
        linhas.append({
            "rq": m["rq"], "metrica": m["nome"], "variante": m["variante"], "coluna": m["coluna"],
            "unidade": m["unidade"], **r,
            "categoria_da_mediana": m["classificar"](r["mediana"]) if r["mediana"] is not None else None,
        })
    return pd.DataFrame(linhas)


def classificacao_c1(df):
    """Classifica cada repositório na C1 a partir das colunas brutas do dataset."""
    linhas = []
    for r in df.itertuples(index=False):
        rec_h = _valor(getattr(r, C1["recuperacao"]))
        c = classificar_dora(
            frequencia=_valor(getattr(r, C1["frequencia"])),
            lead_time_h=_valor(getattr(r, C1["lead_time"])),
            cfr=_valor(getattr(r, C1["cfr"])),
            tempo_recuperacao_val=None if rec_h is None else rec_h * 3600,
        )
        linhas.append({
            "repo": r.repo,
            **{f"valor_{k}": _valor(getattr(r, col)) for k, col in C1.items()},
            **{f"categoria_{k}": c[k] for k in C1},
            **{f"nota_{k}": MAPEAMENTO_CATEGORIAS.get(c[k]) for k in C1},
            "categoria_geral": c["geral"],
            "n_metricas": c["n_metricas"],
        })
    return pd.DataFrame(linhas)


def contagem_categorias(c1):
    """Quantos repositórios caem em cada categoria, por métrica e na geral."""
    colunas = {**{k: f"categoria_{k}" for k in C1}, "geral": "categoria_geral"}
    linhas = []
    for nome, col in colunas.items():
        contagem = c1[col].value_counts()
        total = int(c1[col].notna().sum())
        linha = {"metrica": nome, "n_classificados": total, "sem_valor": int(c1[col].isna().sum())}
        for cat in CATEGORIAS:
            n = int(contagem.get(cat, 0))
            linha[cat] = n
            linha[f"{cat}_pct"] = round(100 * n / total, 1) if total else None
        linhas.append(linha)
    return pd.DataFrame(linhas)


def censura_e_ignoradas(df):
    """Casos censurados e releases que ficaram fora do cálculo, como exige o enunciado."""
    entregas = int(df["n_entregas"].sum())
    sem_episodios = df["tempo_recuperacao_h"].isna()
    prop = df["recuperacao_proporcao_censurados"]
    itens = [
        ("RQ 04", "repos sem nenhum episódio de recuperação na janela", int(sem_episodios.sum()), len(df)),
        ("RQ 04", "repos com algum episódio censurado", int((prop > 0).sum()), len(df)),
        ("RQ 04", "mediana da proporção de episódios censurados por repo", round(float(prop.median()), 4), None),
        ("RQ 04", "média da proporção de episódios censurados por repo", round(float(prop.mean()), 4), None),
        ("RQ 04", "episódios de recuperação (total)", int(df["total_episodios_recuperacao"].sum()), None),
        ("RQ 03 (b)", "releases censuradas (últimos 7 dias da janela)", int(df["cfr_entrega_censuradas"].sum()),
         int(df["cfr_entrega_censuradas"].sum() + df["cfr_entrega_avaliadas"].sum())),
        ("RQ 02", "releases sem release anterior", int(df["ignoradas_sem_anterior"].sum()), entregas),
        ("RQ 02", "releases com compare indisponível (404/422)", int(df["ignoradas_compare_404"].sum()), entregas),
        ("RQ 02", "releases sem commits novos", int(df["ignoradas_sem_commits"].sum()), entregas),
        ("RQ 02", "repos com mediana do lead time (b) <= 0 (datas de autor posteriores à release)",
         int((df["lead_time_commit_h"] <= 0).sum()), len(df)),
    ]
    linhas = []
    for rq, descricao, valor, total in itens:
        pct = round(100 * valor / total, 1) if total else None
        linhas.append({"rq": rq, "descricao": descricao, "valor": valor, "total": total, "pct": pct})
    return pd.DataFrame(linhas)


def frequencia_efetiva(df, inicio, fim):
    """Inovação: frequência contando só releases com commits novos.

    Monorepos publicam várias releases (uma por pacote) sobre o mesmo commit, o que infla a
    deployment frequency sem que haja mudança nova entregue.
    """
    ini, fi = janela(inicio, fim)
    n_semanas = semanas(ini, fi)
    efetivas = (df["n_entregas"] - df["ignoradas_sem_commits"]).clip(lower=0)
    out = pd.DataFrame({
        "repo": df["repo"],
        "n_entregas": df["n_entregas"],
        "entregas_com_commits_novos": efetivas,
        "frequencia_semana": df["deploy_frequency_semana"],
        "frequencia_efetiva_semana": (efetivas / n_semanas).round(4),
    })
    out["categoria_original"] = out["frequencia_semana"].map(classificar_frequencia)
    out["categoria_efetiva"] = out["frequencia_efetiva_semana"].map(classificar_frequencia)
    out["mudou_categoria"] = out["categoria_original"] != out["categoria_efetiva"]
    return out


def sobreposicao_amostra_ouro(df, caminho_consenso):
    if not Path(caminho_consenso).exists():
        return None
    ouro = pd.read_csv(caminho_consenso, dtype=str)
    return len(set(df["repo"]) & set(ouro["repo"])), ouro["repo"].nunique()


# ----------------------------------------------------------------------------- gráficos

def _estilo(ax):
    ax.set_facecolor(SUPERFICIE)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color("#c3c2b7")
    ax.tick_params(colors=TINTA_MUDA, labelcolor=TINTA_SEC, labelsize=9)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def _boxplot(ax, series, rotulos, titulo, unidade, log):
    dados = [s.dropna() for s in series]
    if log:
        dados = [s[s > 0] for s in dados]
    caixas = ax.boxplot(dados, widths=0.45, patch_artist=True, showfliers=True,
                        medianprops={"color": TINTA, "linewidth": 2},
                        whiskerprops={"color": TINTA_MUDA}, capprops={"color": TINTA_MUDA},
                        flierprops={"marker": "o", "markersize": 3, "markerfacecolor": COR_MARCA,
                                    "markeredgecolor": "none", "alpha": 0.35})
    for caixa in caixas["boxes"]:
        caixa.set(facecolor="#cde2fb", edgecolor=COR_MARCA, linewidth=1.5)
    # mediana no rótulo do eixo X: não colide com caixas, outliers nem com o eixo Y
    ax.set_xticks(range(1, len(rotulos) + 1),
                  [f"{r}\nmediana {_num(d.median(), 2)}" if len(d) else r for r, d in zip(rotulos, dados)])
    if log:
        ax.set_yscale("log")
    ax.set_title(titulo, loc="left", fontsize=11, color=TINTA, fontweight="bold")
    ax.set_ylabel(unidade, color=TINTA_SEC, fontsize=9)
    _estilo(ax)


def grafico_boxplots(df, caminho):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, eixos = plt.subplots(1, 4, figsize=(16, 4.8), facecolor=SUPERFICIE)
    _boxplot(eixos[0], [df["deploy_frequency_semana"]], ["releases"], "RQ 01 · Frequência de deploy",
             "releases por semana (log)", log=True)
    _boxplot(eixos[1], [df["lead_time_release_h"] / 24, df["lead_time_commit_h"] / 24],
             ["(a) por release", "(b) por commit"], "RQ 02 · Lead time", "dias (log)", log=True)
    _boxplot(eixos[2], [df["cfr_ci"] * 100, df["cfr_entrega"] * 100],
             ["(a) CI", "(b) entrega"], "RQ 03 · Change failure rate", "% de falhas", log=False)
    _boxplot(eixos[3], [df["tempo_recuperacao_h"]], ["episódios"], "RQ 04 · Tempo de recuperação",
             "horas (log)", log=True)
    fig.text(0.01, 0.01, f"n = {len(df)} repositórios. Escala log exclui valores <= 0 "
             f"(lead time b: {int((df['lead_time_commit_h'] <= 0).sum())} repos).",
             fontsize=8, color=TINTA_MUDA)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(caminho, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)


def grafico_categorias(contagem, caminho):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    nomes = NOMES_C1
    tabela = contagem.set_index("metrica").loc[list(nomes)]
    fig, ax = plt.subplots(figsize=(10, 3.8), facecolor=SUPERFICIE)
    y = range(len(tabela))[::-1]
    esquerda = [0.0] * len(tabela)
    for cat in CATEGORIAS:
        larguras = tabela[f"{cat}_pct"].fillna(0).tolist()
        ax.barh(list(y), larguras, left=esquerda, color=COR_CATEGORIA[cat], edgecolor=SUPERFICIE,
                linewidth=2, height=0.62, label=cat)
        for yi, esq, larg in zip(y, esquerda, larguras):
            if larg >= 8:
                ax.text(esq + larg / 2, yi, f"{larg:.0f}%", ha="center", va="center", fontsize=8,
                        color="#0b0b0b" if cat == "Low" else "#ffffff")
        esquerda = [e + l for e, l in zip(esquerda, larguras)]
    ax.set_yticks(list(y), [f"{nomes[m]}  (n={tabela.loc[m, 'n_classificados']})" for m in tabela.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% dos repositórios classificados", color=TINTA_SEC, fontsize=9)
    ax.set_title("Classificação DORA de referência (C1) por métrica", loc="left", fontsize=11,
                 color=TINTA, fontweight="bold")
    _estilo(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)


def grafico_heatmap(c1, caminho):
    """Inovação: repositórios x métricas da C1, coloridos pela categoria."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch

    ordem = c1.assign(_g=c1["categoria_geral"].map(MAPEAMENTO_CATEGORIAS).fillna(0),
                      _s=c1[[f"nota_{k}" for k in C1]].sum(axis=1))
    ordem = ordem.sort_values(["_g", "_s"], ascending=False)
    matriz = ordem[[f"nota_{k}" for k in C1] + ["categoria_geral"]].copy()
    matriz["categoria_geral"] = matriz["categoria_geral"].map(MAPEAMENTO_CATEGORIAS)
    valores = matriz.fillna(0).to_numpy(dtype=float)

    cmap = ListedColormap([COR_SEM_VALOR] + [COR_CATEGORIA[c] for c in CATEGORIAS])
    fig, ax = plt.subplots(figsize=(7, 11), facecolor=SUPERFICIE)
    ax.imshow(valores, aspect="auto", cmap=cmap, vmin=-0.5, vmax=4.5, interpolation="nearest")
    ax.set_xticks(range(5), ["Frequência", "Lead time (a)", "CFR (a)", "Recuperação", "Geral"],
                  fontsize=9, color=TINTA_SEC)
    ax.axvline(3.5, color=SUPERFICIE, linewidth=4)
    ax.set_yticks([])
    ax.set_ylabel(f"{len(c1)} repositórios (ordenados pela categoria geral)", color=TINTA_SEC, fontsize=9)
    ax.set_title("Perfil DORA dos repositórios (C1)", loc="left", fontsize=11, color=TINTA, fontweight="bold")
    for lado in ax.spines.values():
        lado.set_visible(False)
    legenda = [Patch(facecolor=COR_CATEGORIA[c], label=c) for c in reversed(CATEGORIAS)]
    legenda.append(Patch(facecolor=COR_SEM_VALOR, edgecolor="#c3c2b7", label="sem valor"))
    ax.legend(handles=legenda, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, facecolor=SUPERFICIE)
    plt.close(fig)


# ----------------------------------------------------------------------------- resumo

def _num(v, casas=2):
    if v is None or pd.isna(v):
        return "–"
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar(v, unidade):
    if v is None or pd.isna(v):
        return "–"
    if unidade == "proporção":
        return f"{_num(100 * v, 1)}%"
    if unidade == "horas":
        return f"{_num(v, 1)} h ({_num(v / 24, 1)} d)"
    return _num(v, 3)


def _valor_md(v):
    if v is None or pd.isna(v):
        return "–"
    return str(int(v)) if float(v).is_integer() else _num(v, 4)


NOMES_C1 = {"frequencia": "Frequência de deploy", "lead_time": "Lead time (a)", "cfr": "CFR (a)",
            "recuperacao": "Tempo de recuperação", "geral": "Geral (C1)"}


def _tabela_md(colunas, linhas):
    md = ["| " + " | ".join(colunas) + " |", "|" + "|".join([" --- "] * len(colunas)) + "|"]
    md += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(md)


def gerar_resumo(df, descritiva, contagem, censura, freq_ef, ouro):
    partes = [
        "# RQ 01 a 04 e classificação DORA de referência (C1)",
        "",
        f"Gerado por `python -m analises.rq01_04` a partir de `data/dataset.csv` ({len(df)} repositórios). "
        "Valores reportados como mediana e IQR (1º a 3º quartil), como pede o enunciado.",
        "",
        "## Estatística descritiva (RQ 01 a 04)",
        "",
        _tabela_md(
            ["RQ", "Métrica", "Variante", "n", "Mediana", "1º quartil", "3º quartil", "Categoria da mediana"],
            [[r.rq, r.metrica, r.variante, r.n, _formatar(r.mediana, r.unidade), _formatar(r.q1, r.unidade),
              _formatar(r.q3, r.unidade), r.categoria_da_mediana or "–"] for r in descritiva.itertuples()],
        ),
        "",
        "## Classificação C1 (release, lead time (a), CFR (a) e recuperação)",
        "",
        _tabela_md(
            ["Métrica", "n"] + CATEGORIAS + ["Sem valor"],
            [[NOMES_C1.get(r.metrica, r.metrica), r.n_classificados] + [f"{getattr(r, c)} ({_num(getattr(r, c + '_pct'), 1)}%)"
                                               for c in CATEGORIAS] + [r.sem_valor]
             for r in contagem.itertuples()],
        ),
        "",
        f"A categoria geral é a mediana das notas (Elite=4 … Low=1), arredondada para baixo. "
        f"{int((df['tempo_recuperacao_h'].isna()).sum())} repositórios não tiveram nenhum episódio de recuperação "
        "na janela; para eles a categoria geral usa as 3 métricas disponíveis (coluna `n_metricas`).",
        "",
        "## Casos censurados e releases fora do cálculo",
        "",
        _tabela_md(
            ["RQ", "Descrição", "Valor", "Total", "%"],
            [[r.rq, r.descricao, _valor_md(r.valor), "–" if pd.isna(r.total) else int(r.total),
              "–" if pd.isna(r.pct) else f"{_num(r.pct, 1)}%"] for r in censura.itertuples()],
        ),
        "",
        "## Inovação: frequência efetiva (sem releases repetidas de monorepos)",
        "",
        f"Contando só releases com commits novos, a mediana da frequência passa de "
        f"{_num(freq_ef['frequencia_semana'].median(), 3)} para {_num(freq_ef['frequencia_efetiva_semana'].median(), 3)} "
        f"releases/semana, e **{int(freq_ef['mudou_categoria'].sum())} repositórios "
        f"({_num(100 * freq_ef['mudou_categoria'].mean(), 1)}%) mudam de categoria** de frequência. "
        f"Dos {int((freq_ef['categoria_original'] == 'Elite').sum())} repositórios Elite em frequência, "
        f"{int(((freq_ef['categoria_original'] == 'Elite') & (freq_ef['categoria_efetiva'] != 'Elite')).sum())} "
        "deixam de ser Elite: a frequência alta vem de várias releases publicadas sobre o mesmo commit.",
        "",
        _tabela_md(
            ["Categoria original \\ efetiva"] + CATEGORIAS,
            [[orig] + [int(((freq_ef['categoria_original'] == orig) & (freq_ef['categoria_efetiva'] == ef)).sum())
                       for ef in CATEGORIAS] for orig in CATEGORIAS],
        ),
        "",
        "Maiores diferenças:",
        "",
        _tabela_md(
            ["Repositório", "Releases", "Com commits novos", "Freq. original", "Freq. efetiva"],
            [[r.repo, r.n_entregas, r.entregas_com_commits_novos, _num(r.frequencia_semana, 3),
              _num(r.frequencia_efetiva_semana, 3)]
             for r in freq_ef.assign(_d=freq_ef["n_entregas"] - freq_ef["entregas_com_commits_novos"])
                           .sort_values("_d", ascending=False).head(5).itertuples()],
        ),
    ]
    if ouro:
        partes += [
            "",
            "## Limitação: sobreposição com a amostra-ouro",
            "",
            f"Apenas {ouro[0]} dos {ouro[1]} repositórios da amostra-ouro estão no dataset final, porque a "
            "amostra-ouro foi sorteada antes da aplicação do critério de inclusão. Por isso a comparação das "
            "categorias com o rótulo manual \"entrega real\" não tem tamanho de amostra suficiente e não é reportada.",
        ]
    partes += ["", "## Figuras", "",
               "- `fig_rq01_04_boxplots.png`: distribuição das métricas (RQ 01 a 04)",
               "- `fig_categorias_C1.png`: distribuição das categorias DORA por métrica (C1)",
               "- `fig_heatmap_C1.png`: perfil DORA de cada repositório (C1)", ""]
    return "\n".join(partes)


def executar(caminho_dataset, saida, inicio, fim, caminho_consenso=None, graficos=True):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(caminho_dataset)

    descritiva = tabela_descritiva(df)
    c1 = classificacao_c1(df)
    contagem = contagem_categorias(c1)
    censura = censura_e_ignoradas(df)
    freq_ef = frequencia_efetiva(df, inicio, fim)
    ouro = sobreposicao_amostra_ouro(df, caminho_consenso) if caminho_consenso else None

    descritiva.to_csv(saida / "rq01_04_descritiva.csv", index=False, encoding="utf-8")
    c1.to_csv(saida / "classificacao_C1.csv", index=False, encoding="utf-8")
    contagem.to_csv(saida / "categorias_C1.csv", index=False, encoding="utf-8")
    censura.to_csv(saida / "censura_e_ignoradas.csv", index=False, encoding="utf-8")
    freq_ef.to_csv(saida / "frequencia_efetiva.csv", index=False, encoding="utf-8")
    (saida / "RESUMO_RQ01_04.md").write_text(
        gerar_resumo(df, descritiva, contagem, censura, freq_ef, ouro), encoding="utf-8")

    if graficos:
        grafico_boxplots(df, saida / "fig_rq01_04_boxplots.png")
        grafico_categorias(contagem, saida / "fig_categorias_C1.png")
        grafico_heatmap(c1, saida / "fig_heatmap_C1.png")

    return {"descritiva": descritiva, "c1": c1, "contagem": contagem, "censura": censura, "frequencia_efetiva": freq_ef}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", default=str(RAIZ / "data" / "dataset.csv"))
    parser.add_argument("--saida", default=str(RAIZ / "analises" / "saida"))
    parser.add_argument("--consenso", default=str(RAIZ / "rotulagem" / "consenso.csv"))
    parser.add_argument("--inicio", default="2025-01-01", help="início da janela (AAAA-MM-DD)")
    parser.add_argument("--fim", default="2025-12-31", help="fim da janela, inclusivo (AAAA-MM-DD)")
    parser.add_argument("--sem-graficos", action="store_true")
    args = parser.parse_args(argv)

    r = executar(args.dataset, args.saida, args.inicio, args.fim, args.consenso, graficos=not args.sem_graficos)
    print(r["descritiva"][["rq", "metrica", "variante", "n", "mediana", "q1", "q3", "categoria_da_mediana"]]
          .to_string(index=False))
    print()
    print(r["contagem"][["metrica", "n_classificados"] + CATEGORIAS].to_string(index=False))
    print(f"\nResultados em {args.saida}")


if __name__ == "__main__":
    main()
