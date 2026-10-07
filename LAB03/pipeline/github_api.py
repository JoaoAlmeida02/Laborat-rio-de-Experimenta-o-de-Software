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


class GitHubAPI:
    def __init__(self, token=None, sessao=None, tentativas=5, dormir=time.sleep):
        token = token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN não definido (crie o arquivo .env com GITHUB_TOKEN=seu_token)")
        self.sessao = sessao or requests.Session()
        self.sessao.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        self.tentativas = tentativas
        self.dormir = dormir

    def _requisitar(self, url, params=None):
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
