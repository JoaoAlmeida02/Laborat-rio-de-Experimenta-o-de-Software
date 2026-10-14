import argparse
from collections import Counter
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from rotulagem.concordancia import carregar_planilhas, DIMENSOES

RAIZ = Path(__file__).resolve().parents[1]


def carregar_decisoes_reuniao(
    caminho_csv: Path | str,
) -> Dict[Tuple[str, str, str], str]:
    caminho = Path(caminho_csv)
    if not caminho.exists():
        return {}

    decisoes = {}
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        for linha in leitor:
            chave = (
                linha.get("repo", "").strip(),
                linha.get("release_tag", "").strip(),
                linha.get("dimensao", "").strip(),
            )
            decisoes[chave] = linha.get("rotulo_final", "").strip()
    return decisoes


def resolver_voto(
    votos: List[str],
    repo: str = "",
    tag: str = "",
    dimensao: str = "",
    decisoes: Optional[Dict[Tuple[str, str, str], str]] = None,
) -> Tuple[str, bool]:
    votos_limpos = [v.strip() for v in votos]
    contagem = Counter(votos_limpos)
    mais_comum, frequencia = contagem.most_common(1)[0]

    if frequencia == 3:
        return mais_comum, True
    elif frequencia == 2:
        return mais_comum, False
    else:
        chave = (repo.strip(), tag.strip(), dimensao.strip())
        if decisoes and chave in decisoes:
            return decisoes[chave], False
        print(
            f"[AVISO] Empate 1-1-1 não deliberado em reunião: {repo} {tag} ({dimensao}). "
            f"Requer deliberação em rotulagem/decisoes_reuniao.csv"
        )
        return "empate", False


def consolidar_consenso(
    planilhas: Dict[str, pd.DataFrame],
    decisoes: Optional[Dict[Tuple[str, str, str], str]] = None,
) -> pd.DataFrame:
    avaliadores = sorted(planilhas.keys())
    df_base = planilhas[avaliadores[0]]
    n_itens = len(df_base)

    linhas_consenso = []
    for i in range(n_itens):
        repo = df_base.iloc[i].get("repo", "")
        tag = df_base.iloc[i].get("release_tag", "")

        item = {
            "repo": repo,
            "release_tag": tag,
            "release_data": df_base.iloc[i].get("release_data", ""),
            "release_anterior": df_base.iloc[i].get("release_anterior", ""),
            "release_url": df_base.iloc[i].get("release_url", ""),
            "compare_url": df_base.iloc[i].get("compare_url", ""),
        }

        for dim in DIMENSOES:
            votos = [planilhas[av].iloc[i][dim] for av in avaliadores]
            rotulo_vencedor, unanime = resolver_voto(
                votos,
                repo=repo,
                tag=tag,
                dimensao=dim,
                decisoes=decisoes,
            )
            item[f"{dim}_consenso"] = rotulo_vencedor
            item[f"{dim}_unanimidade"] = "sim" if unanime else "nao"

        linhas_consenso.append(item)

    return pd.DataFrame(linhas_consenso)


def salvar_consenso_csv(
    df_consenso: pd.DataFrame, caminho_saida: Path | str
) -> None:
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df_consenso.to_csv(caminho, index=False, encoding="utf-8")


def gerar_resumo_consenso(df_consenso: pd.DataFrame) -> Dict[str, Any]:
    total = len(df_consenso)
    resumo = {"total_itens": total, "estatisticas": {}}

    for dim in DIMENSOES:
        col_unanime = f"{dim}_unanimidade"
        col_consenso = f"{dim}_consenso"

        n_unanime = (df_consenso[col_unanime] == "sim").sum()
        n_empate = (df_consenso[col_consenso] == "empate").sum()
        n_maioria = total - n_unanime - n_empate

        resumo["estatisticas"][dim] = {
            "unanimidade_pct": round((n_unanime / total) * 100, 2) if total else 0.0,
            "maioria_pct": round((n_maioria / total) * 100, 2) if total else 0.0,
            "empates_qtd": int(n_empate),
        }

    return resumo


def executar_consenso_completo(
    pasta_rotulagem: Path | str,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    pasta = Path(pasta_rotulagem)
    planilhas = carregar_planilhas(pasta)
    decisoes = carregar_decisoes_reuniao(pasta / "decisoes_reuniao.csv")
    df_consenso = consolidar_consenso(planilhas, decisoes=decisoes)
    caminho_csv = pasta / "consenso.csv"
    salvar_consenso_csv(df_consenso, caminho_csv)
    resumo = gerar_resumo_consenso(df_consenso)
    return df_consenso, resumo


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pasta",
        default=str(RAIZ / "rotulagem"),
        help="Diretório contendo rotulos_A.csv, rotulos_B.csv, rotulos_C.csv",
    )
    args = parser.parse_args(argv)

    pasta = Path(args.pasta)
    print("=" * 65)
    print(" CONSOLIDAÇÃO DO CONSENSO DA AMOSTRA-OURO (LAB03S02) ")
    print("=" * 65)

    df_consenso, resumo = executar_consenso_completo(pasta)

    print(f"Total de releases avaliadas: {resumo['total_itens']}")
    print("\nTaxas de concordância e resolução:")
    for dim, dados in resumo["estatisticas"].items():
        print(f" • {dim:<16}: {dados['unanimidade_pct']}% unânime | {dados['maioria_pct']}% maioria/reunião | {dados['empates_qtd']} empate(s)")

    print(f"\nArquivo de consenso salvo em: {pasta / 'consenso.csv'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
