"""Gera figuras de desempenho e sobrevivência em PNG (200 dpi)."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__:
    from .analise_rq1_rq2 import METRICAS, TRATAMENTOS, analisar, avisos_amostra, carregar, detectar_entrada
    from .analise_rq3 import BAIXO_PODER, analisar_rq3, carregar_rq3
else:
    from analise_rq1_rq2 import METRICAS, TRATAMENTOS, analisar, avisos_amostra, carregar, detectar_entrada
    from analise_rq3 import BAIXO_PODER, analisar_rq3, carregar_rq3

CORES = {"T1": "#0072B2", "T2": "#E69F00", "T3": "#009E73", "T4": "#CC79A7",
         "Distribuição Linux": "#0072B2", "Nuvem": "#E69F00", "Hospedagem": "#009E73",
         "comunitario": "#0072B2", "comercial": "#E69F00"}


def salvar(fig, caminho, avisos):
    if avisos:
        fig.text(.02, .015, "\n".join(avisos), fontsize=8, wrap=True)
    fig.tight_layout(rect=(0, .14 if avisos else 0, 1, 1))
    fig.savefig(caminho, dpi=200)
    plt.close(fig)


def desempenho(df, tost, saida, avisos):
    rng = np.random.default_rng(502)
    for i, (endpoint, dados) in enumerate(df.groupby("endpoint"), 1):
        for metrica, unidade in METRICAS.items():
            fig, eixos = plt.subplots(1, 3, figsize=(15, 4.7))
            grupos = [dados.loc[dados.tratamento.eq(t), metrica] for t in TRATAMENTOS]
            eixos[0].boxplot(grupos, showfliers=False)
            for j, (nome, valores) in enumerate(zip(TRATAMENTOS, grupos), 1):
                eixos[0].scatter(j + rng.uniform(-.10, .10, len(valores)), valores,
                                s=13, alpha=.65, color=CORES[nome])
            eixos[0].set_xticks(range(1, 5), list(TRATAMENTOS))
            eixos[0].set(title="Distribuição por tratamento", ylabel=unidade)

            for indice, rotulo in enumerate(["Desligada", "Ligada"]):
                eixos[1].plot(["8.4.26", "8.4.27"], [grupos[indice].median(), grupos[indice+2].median()],
                              "o-", color=CORES[list(TRATAMENTOS)[indice]], label=rotulo)
            eixos[1].set(title="Interação versão × mitigação", xlabel="Versão do PHP",
                         ylabel=f"Mediana ({unidade})")
            eixos[1].legend(title="Mitigação")

            linhas = tost[tost.endpoint.eq(endpoint) & tost.metrica.eq(metrica)]
            for j, r in enumerate(linhas.itertuples()):
                if np.isfinite(r.margem):
                    eixos[2].fill_betweenx([j-.28, j+.28], -r.margem, r.margem, color="#009E73", alpha=.2)
                if np.isfinite(r.ic90_inferior):
                    eixos[2].hlines(j, r.ic90_inferior, r.ic90_superior, color="#0072B2")
                    eixos[2].plot(r.diferenca, j, "o", color="#0072B2")
                else:
                    eixos[2].text(.02, j, "IC indisponível", transform=eixos[2].get_yaxis_transform())
            eixos[2].axvline(0, color="gray", linestyle=":")
            eixos[2].set_yticks(range(len(linhas)), linhas.contraste)
            eixos[2].set(title="TOST · IC 90% e faixa de equivalência",
                         xlabel=f"Diferença ({unidade})")
            fig.suptitle(f"{endpoint} — {metrica}")
            salvar(fig, saida / f"rq1_rq2_{i:02d}_{metrica}.png", avisos)


def sobrevivencia(km, saida, avisos):
    for i, (analise, dados) in enumerate(km.groupby("analise", sort=False), 1):
        fig, ax = plt.subplots(figsize=(9, 5))
        for grupo, curva in dados[dados.grupo.ne("Geral")].groupby("grupo"):
            cor = CORES[grupo]
            x, y = curva.tempo_dias, curva.sem_correcao
            if x.iloc[0] == 0:
                ax.vlines(0, y.iloc[0], 1, color=cor)
            ax.step(x, y, where="post", label=grupo, color=cor)
            ax.fill_between(x, curva.ic95_inferior, curva.ic95_superior,
                            step="post", alpha=.14, color=cor)
            censura = curva.censuras_no_dia.gt(0)
            ax.plot(x[censura], y[censura], marker="+", linestyle="none", color=cor)
        ax.set(title=f"RQ3 — {analise} · IC 95% · + censura", xlabel="Dias desde 21/10/2026",
               ylabel="Probabilidade de permanecer sem correção", ylim=(-.04, 1.04))
        ax.legend()
        notas = avisos + ([BAIXO_PODER] if dados.baixo_poder.any() else [])
        salvar(fig, saida / f"rq3_km_{i:02d}.png", notas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=detectar_entrada())
    parser.add_argument("--entrada-rq3", type=Path, default=Path("dados/rq3_correcoes.csv"))
    parser.add_argument("--saida", type=Path, default=Path("resultados"))
    parser.add_argument("--alfa", type=float, default=.05)
    parser.add_argument("--margem", type=float, default=.05)
    args = parser.parse_args()
    if not 0 < args.alfa < .5 or not 0 < args.margem < 1:
        parser.error("--alfa deve estar entre 0 e 0,5 e --margem entre 0 e 1.")
    args.saida.mkdir(parents=True, exist_ok=True)
    avisos, gerado = [], False
    if args.entrada.is_file():
        try:
            df, _ = carregar(args.entrada)
        except ValueError as erro:
            parser.error(str(erro))
        avisos = avisos_amostra(df, args.entrada)
        _, _, tost = analisar(df, args.alfa, args.margem)
        desempenho(df, tost, args.saida, avisos)
        gerado = True
    else:
        print(f"Sem gráficos de desempenho: {args.entrada} ausente.")
    if args.entrada_rq3.is_file():
        try:
            _, df = carregar_rq3(args.entrada_rq3)
        except ValueError as erro:
            parser.error(str(erro))
        km, _ = analisar_rq3(df)
        sobrevivencia(km, args.saida, avisos)
        gerado = True
    else:
        print(f"Sem curvas RQ3: {args.entrada_rq3} ausente.")
    if not gerado:
        parser.error("Nenhuma entrada disponível para gerar gráficos.")


if __name__ == "__main__":
    main()

