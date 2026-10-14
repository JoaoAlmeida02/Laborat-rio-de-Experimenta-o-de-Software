"""Avalia as heurísticas de release corretiva contra o consenso da amostra-ouro.

Uso (de dentro de LAB03):
    python -m rotulagem.avaliar_heuristica
    python -m rotulagem.avaliar_heuristica --consenso rotulagem/consenso.csv --saida rotulagem/avaliacao

Para cada versão de metricas.corretiva.HEURISTICAS calcula precisão, recall e F1
(classe positiva: corretiva = sim) e gera em --saida:
    heuristicas_f1.csv     P, R, F1 e matriz de confusão (VP, FP, FN, VN) por versão
    erros_<versao>.csv     falsos positivos e falsos negativos, com links, para justificar refinamentos
"""
import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from metricas.corretiva import HEURISTICA_PADRAO, HEURISTICAS

RAIZ = Path(__file__).resolve().parents[1]
F1_MINIMO = 0.70
SEM_ANTERIOR = {"", "-", "nan"}


def preparar_consenso(df):
    """Mantém só os itens avaliáveis: com release anterior e com consenso sim/nao."""
    df = df.copy()
    df["release_anterior"] = df["release_anterior"].fillna("").astype(str).str.strip()
    df["corretiva_consenso"] = df["corretiva_consenso"].fillna("").astype(str).str.strip().str.lower()
    avaliaveis = df[~df["release_anterior"].isin(SEM_ANTERIOR) & df["corretiva_consenso"].isin({"sim", "nao"})]
    return avaliaveis.reset_index(drop=True), len(df) - len(avaliaveis)


def mensagens_via_api(api):
    """Retorna uma função (repo, base, head) -> mensagens, usando o compare do pipeline."""
    from pipeline.github_api import NaoEncontrado
    from pipeline.releases import coletar_commits_entre

    def obter(repo, base, head):
        owner, nome = repo.split("/", 1)
        try:
            return [c["mensagem"] for c in coletar_commits_entre(api, owner, nome, base, head)]
        except NaoEncontrado:
            return []

    return obter


def avaliar(df, obter_mensagens, heuristicas=HEURISTICAS):
    """Aplica cada heurística aos itens do consenso.

    Retorno:
        (tabela de métricas por versão, {versao: DataFrame de erros})
    """
    mensagens = [obter_mensagens(r.repo, r.release_anterior, r.release_tag) for r in df.itertuples()]
    y_true = (df["corretiva_consenso"] == "sim").astype(int).tolist()

    linhas, erros = [], {}
    for versao, heuristica in heuristicas.items():
        y_pred = [int(heuristica(r.release_anterior, r.release_tag, m)) for r, m in zip(df.itertuples(), mensagens)]
        p, r, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="binary", pos_label=1, zero_division=0
        )
        vn, fp, fn, vp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        linhas.append({
            "versao": versao,
            "descricao": (heuristica.__doc__ or "").strip(),
            "n": len(y_true),
            "precisao": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "vp": int(vp), "fp": int(fp), "fn": int(fn), "vn": int(vn),
        })

        resultado = df.assign(heuristica=["sim" if v else "nao" for v in y_pred])
        errados = resultado[resultado["heuristica"] != resultado["corretiva_consenso"]].copy()
        errados["tipo_erro"] = errados["heuristica"].map({"sim": "falso_positivo", "nao": "falso_negativo"})
        colunas = [c for c in ("repo", "release_anterior", "release_tag", "corretiva_consenso",
                               "heuristica", "tipo_erro", "release_url", "compare_url") if c in errados.columns]
        erros[versao] = errados[colunas]

    return pd.DataFrame(linhas), erros


def salvar(tabela, erros, saida):
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(saida / "heuristicas_f1.csv", index=False, encoding="utf-8")
    for versao, df_erros in erros.items():
        df_erros.to_csv(saida / f"erros_{versao}.csv", index=False, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--consenso", default=str(RAIZ / "rotulagem" / "consenso.csv"))
    parser.add_argument("--saida", default=str(RAIZ / "rotulagem" / "avaliacao"))
    args = parser.parse_args(argv)

    from dotenv import load_dotenv
    from pipeline.github_api import GitHubAPI

    load_dotenv(RAIZ / ".env")
    df, descartados = preparar_consenso(pd.read_csv(args.consenso, dtype=str))
    print(f"{len(df)} releases avaliáveis ({descartados} sem release anterior ou com empate no consenso)")

    tabela, erros = avaliar(df, mensagens_via_api(GitHubAPI()))
    salvar(tabela, erros, args.saida)

    print(tabela[["versao", "n", "precisao", "recall", "f1", "vp", "fp", "fn", "vn"]].to_string(index=False))
    melhor = tabela.loc[tabela["f1"].idxmax()]
    padrao = tabela.set_index("versao").loc[HEURISTICA_PADRAO]
    print(f"\nMaior F1: {melhor['versao']} ({melhor['f1']:.2f})")
    print(f"Padrão adotado no pipeline: {HEURISTICA_PADRAO} (F1 = {padrao['f1']:.2f})")
    if padrao["f1"] < F1_MINIMO:
        print(f"F1 do padrão < {F1_MINIMO}: refine a heurística.")
    print(f"Resultados em {args.saida}")


if __name__ == "__main__":
    main()
