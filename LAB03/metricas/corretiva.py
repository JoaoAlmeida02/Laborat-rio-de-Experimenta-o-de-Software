"""Heurísticas automáticas de release corretiva (CFR b e rework rate).

Cada heurística recebe a tag da release anterior, a tag da release avaliada e as
mensagens dos commits entre as duas, e responde se a release é corretiva.
As versões ficam no dicionário HEURISTICAS para serem avaliadas juntas contra
a amostra-ouro (rotulagem/avaliar_heuristica.py).
"""
import re

from metricas.semver import somente_patch

_CORRETIVO = re.compile(r"\b(?:bug)?fix(?:es|ed)?\b|\bhotfix\b|\brevert", re.IGNORECASE)
_FEATURE = re.compile(r"^\s*feat(?:ure)?\b", re.IGNORECASE)


def commits_corretivos(mensagens):
    """Quantas mensagens citam fix, bugfix, hotfix ou revert."""
    return sum(1 for m in mensagens if _CORRETIVO.search(m or ""))


def commits_feature(mensagens):
    """Quantas mensagens começam com feat ou feature."""
    return sum(1 for m in mensagens if _FEATURE.search(m or ""))


def heuristica_v0(tag_anterior, tag, mensagens):
    """Só o patch mudou (linha de base: ignora os commits)."""
    return somente_patch(tag_anterior, tag)


def heuristica_v1(tag_anterior, tag, mensagens):
    """Só o patch mudou OU há algum commit corretivo (sugestão do enunciado)."""
    return somente_patch(tag_anterior, tag) or commits_corretivos(mensagens) > 0


def heuristica_v2(tag_anterior, tag, mensagens):
    """Só o patch mudou E há algum commit corretivo."""
    return somente_patch(tag_anterior, tag) and commits_corretivos(mensagens) > 0


def heuristica_v3(tag_anterior, tag, mensagens):
    """Só o patch mudou E nenhum commit é de nova funcionalidade (feat)."""
    return somente_patch(tag_anterior, tag) and commits_feature(mensagens) == 0


def heuristica_v4(tag_anterior, tag, mensagens):
    """Só o patch mudou E não há mais commits de feature do que de correção."""
    return somente_patch(tag_anterior, tag) and commits_feature(mensagens) <= commits_corretivos(mensagens)


HEURISTICAS = {
    "v0": heuristica_v0,
    "v1": heuristica_v1,
    "v2": heuristica_v2,
    "v3": heuristica_v3,
    "v4": heuristica_v4,
}
# Escolhida pela avaliação contra a amostra-ouro (rotulagem/avaliacao/heuristicas_f1.csv)
HEURISTICA_PADRAO = "v4"


def eh_corretiva(tag_anterior, tag, mensagens, versao=HEURISTICA_PADRAO):
    return HEURISTICAS[versao](tag_anterior, tag, mensagens)


def mensagens_da_entrega(entrega):
    """Mensagens dos commits de uma entrega no formato salvo por pipeline.releases."""
    return [c.get("mensagem", "") for c in (entrega.get("commits") or [])]
