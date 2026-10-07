from pathlib import Path
import re
import textwrap


def _parse_yaml_simples(conteudo: str) -> dict:
    """Parser leve para arquivos YAML sem dependencias externas."""
    resultado = {}
    chave_atual = None
    sub_chave = None

    conteudo_limpo = textwrap.dedent(conteudo)

    for linha_bruta in conteudo_limpo.splitlines():
        linha = linha_bruta.split("#")[0].rstrip()
        if not linha:
            continue

        # Nivel 1: chave:
        m_raiz = re.match(r"^([a-zA-Z0-9_]+):\s*(.*)$", linha)
        if m_raiz:
            chave, val = m_raiz.group(1), m_raiz.group(2).strip()
            chave_atual = chave
            sub_chave = None
            if val:
                resultado[chave] = _converter_tipo(val)
            else:
                resultado[chave] = {}
            continue

        # Nivel 2: subchave: valor ou lista
        m_item_lista = re.match(r"^\s+-\s+(.*)$", linha)
        if m_item_lista and chave_atual:
            val = m_item_lista.group(1).strip()
            if not isinstance(resultado[chave_atual], list):
                if isinstance(resultado[chave_atual], dict) and sub_chave:
                    if not isinstance(resultado[chave_atual][sub_chave], list):
                        resultado[chave_atual][sub_chave] = []
                    resultado[chave_atual][sub_chave].append(_converter_tipo(val))
                    continue
                resultado[chave_atual] = []
            resultado[chave_atual].append(_converter_tipo(val))
            continue

        m_sub = re.match(r"^\s+([a-zA-Z0-9_]+):\s*(.*)$", linha)
        if m_sub and chave_atual:
            sub_k, val = m_sub.group(1), m_sub.group(2).strip()
            sub_chave = sub_k
            if not isinstance(resultado[chave_atual], dict):
                resultado[chave_atual] = {}
            if val:
                resultado[chave_atual][sub_k] = _converter_tipo(val)
            else:
                resultado[chave_atual][sub_k] = []
            continue

    return resultado


def _converter_tipo(val: str):
    val = val.strip().strip('"').strip("'")
    if val.lower() in ("null", "none", "~", ""):
        return None
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if re.match(r"^-?\d+$", val):
        return int(val)
    if re.match(r"^-?\d+\.\d+$", val):
        return float(val)
    return val


def carregar_config(caminho="config.yaml") -> dict:
    caminho_p = Path(caminho)
    if not caminho_p.exists():
        raise FileNotFoundError(f"Arquivo de configuracao '{caminho}' nao encontrado.")

    texto = caminho_p.read_text(encoding="utf-8")
    try:
        import yaml
        cfg = yaml.safe_load(texto) or {}
    except ImportError:
        cfg = _parse_yaml_simples(texto)

    janela = cfg.get("janela", {})
    amostra = cfg.get("amostra", {})
    busca = cfg.get("busca", {})
    caminhos = cfg.get("caminhos", {})

    return {
        "inicio": janela.get("inicio", "2025-01-01"),
        "fim": janela.get("fim", "2025-12-31"),
        "limite_repos": int(amostra.get("limite_repos", 100)),
        "min_releases": int(amostra.get("min_releases", 5)),
        "min_workflow_runs": int(amostra.get("min_workflow_runs", 50)),
        "faixas_estrelas": busca.get("faixas_estrelas", ["stars:1000..2000", "stars:2000..5000", "stars:>5000"]),
        "linguagem": busca.get("linguagem"),
        "dados_dir": caminhos.get("dados", "data"),
        "repos_csv": caminhos.get("repos_csv", "data/repos.csv"),
        "funil_csv": caminhos.get("funil_csv", "data/funil.csv"),
        "funil_md": caminhos.get("funil_md", "data/funil.md"),
    }
