import hashlib
import json
import os
from pathlib import Path
import re
import time

from dotenv import load_dotenv
import requests

API = "https://api.github.com"
_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')

RAIZ = Path(__file__).resolve().parents[1]
for p in [RAIZ / ".env", RAIZ.parent / ".env", RAIZ.parent.parent / ".env"]:
    if p.exists():
        load_dotenv(p)


class NaoEncontrado(Exception):
    """Resposta 404 (ex.: tag apagada ou reescrita no compare)."""


def proxima_pagina(link_header):
    m = _LINK_NEXT.search(link_header or "")
    return m.group(1) if m else None


class RespostaCache:
    """Wrapper leve para respostas carregadas do cache em disco."""

    def __init__(self, dados, headers=None, status_code=200):
        self._dados = dados
        self.headers = headers or {}
        self.status_code = status_code

    def json(self):
        return self._dados

    def raise_for_status(self):
        pass


class GitHubAPI:
    def __init__(
        self,
        token=None,
        sessao=None,
        tentativas=5,
        dormir=time.sleep,
        cache_dir=".cache_http",
        usar_cache=True,
    ):
        token = token or os.getenv("GITHUB_TOKEN")
        if not token:
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    token, _ = winreg.QueryValueEx(key, "GITHUB_TOKEN")
            except Exception:
                pass

        if not token and sessao is None:
            raise RuntimeError("GITHUB_TOKEN não definido (crie o arquivo .env com GITHUB_TOKEN=seu_token)")

        self.token = token
        self.sessao = sessao or requests.Session()
        if hasattr(self.sessao, "headers") and self.sessao.headers is not None and token:
            self.sessao.headers.update({
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        self.tentativas = tentativas
        self.dormir = dormir
        self.cache_dir = Path(cache_dir) if cache_dir else None
        # Usa cache apenas quando não é uma sessão mock injetada por testes unitários
        self.usar_cache = bool(usar_cache and self.cache_dir and sessao is None)

    def _caminho_cache(self, url: str, params: dict | None) -> Path:
        chave_dados = f"{url}?{json.dumps(params or {}, sort_keys=True)}"
        nome_arquivo = f"{hashlib.sha256(chave_dados.encode('utf-8')).hexdigest()}.json"
        return self.cache_dir / nome_arquivo

    def _salvar_cache(self, caminho: Path, dados, headers):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        temp_caminho = caminho.with_suffix(f".tmp.{os.getpid()}")
        conteudo = {
            "data": dados,
            "headers": {
                k: v
                for k, v in headers.items()
                if k.lower() in ("link", "x-ratelimit-remaining", "x-ratelimit-reset")
            },
        }
        with open(temp_caminho, "w", encoding="utf-8") as f:
            json.dump(conteudo, f, ensure_ascii=False, indent=2)
        os.replace(temp_caminho, caminho)

    def _requisitar(self, url, params=None):
        if self.usar_cache and self.cache_dir:
            caminho_cache = self._caminho_cache(url, params)
            if caminho_cache.exists():
                try:
                    with open(caminho_cache, "r", encoding="utf-8") as f:
                        conteudo = json.load(f)
                        return RespostaCache(conteudo["data"], conteudo.get("headers", {}))
                except Exception:
                    pass

        for tentativa in range(self.tentativas):
            resp = self.sessao.get(url, params=params, timeout=30)
            if resp.status_code == 404:
                raise NaoEncontrado(url)
            if resp.status_code == 401:
                raise RuntimeError("Token inválido ou expirado: gere outro e atualize GITHUB_TOKEN no .env")
            if resp.status_code in (403, 429) and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time()))
                self.dormir(max(reset - time.time(), 0) + 1)
                continue
            if resp.status_code >= 500:
                self.dormir(2 ** tentativa)
                continue
            resp.raise_for_status()

            if self.usar_cache and self.cache_dir:
                try:
                    self._salvar_cache(self._caminho_cache(url, params), resp.json(), dict(resp.headers))
                except Exception:
                    pass

            return resp
        raise RuntimeError(f"Falha após {self.tentativas} tentativas: {url}")

    def get(self, caminho, params=None):
        return self._requisitar(API + caminho, params).json()

    def paginar(self, caminho, params=None):
        url, params = API + caminho, dict(params or {}, per_page=100)
        while url:
            resp = self._requisitar(url, params)
            yield from resp.json()
            # a URL do rel="next" já carrega os parâmetros da consulta
            url, params = proxima_pagina(resp.headers.get("Link")), None
