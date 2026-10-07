"""Cliente HTTP único para o pipeline de dados da API do GitHub.

Implementa cache em disco, controle de taxa (rate limiting), backoff exponencial e paginação.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable
import warnings

from dotenv import load_dotenv
import requests

API_GITHUB = "https://api.github.com"
PADRAO_LINK_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')

# Escolha de cache: JSON individual em disco por URL+parâmetros, pois permite inspeção transparente dos payloads e escrita atômica sem concorrência de banco.


def extrair_proxima_pagina(link_header: str | None) -> str | None:
    """Extrai a URL rel='next' do cabeçalho Link da resposta HTTP."""
    if not link_header:
        return None
    match = PADRAO_LINK_NEXT.search(link_header)
    return match.group(1) if match else None


class ClienteHTTP:
    """Cliente HTTP com suporte a autenticação, cache local, rate limit e retry."""

    def __init__(
        self,
        token: str | None = None,
        sessao: requests.Session | None = None,
        tentativas: int = 5,
        dormir: Callable[[float], None] = time.sleep,
        relogio: Callable[[], float] = time.time,
        cache_dir: str | Path | None = ".cache_http",
        usar_cache: bool = True,
        margem_reset: float = 1.0,
    ) -> None:
        """Inicializa o cliente HTTP configurando autenticação e mecanismos de resiliência."""
        # Tenta carregar .env caso exista
        raiz = Path(__file__).resolve().parents[1]
        for p in [raiz / ".env", raiz.parent / ".env", Path(".env")]:
            if p.exists():
                load_dotenv(p)
                break

        self.token = token if token is not None else os.getenv("GITHUB_TOKEN")
        self.sessao = sessao or requests.Session()
        self.tentativas = tentativas
        self.dormir = dormir
        self.relogio = relogio
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.usar_cache = usar_cache and (self.cache_dir is not None)
        self.margem_reset = margem_reset
        self.cota_restante: int | None = None

        if not hasattr(self.sessao, "headers") or self.sessao.headers is None:
            self.sessao.headers = {}

        if self.token:
            self.sessao.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
        else:
            warnings.warn(
                "Aviso: GITHUB_TOKEN não configurado. As requisições serão anônimas "
                "com limite severo de taxa (60 req/h). Defina GITHUB_TOKEN no ambiente ou .env.",
                UserWarning,
                stacklevel=2,
            )
            self.sessao.headers.update({
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })

    def _normalizar_url(self, url: str) -> str:
        """Assegura URL absoluta da API do GitHub se um caminho relativo for informado."""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{API_GITHUB}/{url.lstrip('/')}"

    def _caminho_cache(self, url: str, params: dict[str, Any] | None) -> Path:
        """Calcula o caminho do arquivo JSON de cache usando hash SHA-256 da URL e parâmetros."""
        assert self.cache_dir is not None
        chave_dados = f"{url}?{json.dumps(params or {}, sort_keys=True)}"
        nome_arquivo = f"{hashlib.sha256(chave_dados.encode('utf-8')).hexdigest()}.json"
        return self.cache_dir / nome_arquivo

    def _salvar_cache(self, caminho: Path, dados: Any, headers: dict[str, str]) -> None:
        """Salva a resposta em disco de forma atômica utilizando arquivo temporário."""
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

    def _requisitar(
        self, url: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        """Executa a chamada HTTP com backoff exponencial e gerenciamento de rate limit."""
        for tentativa in range(self.tentativas):
            resp = self.sessao.get(url, params=params, timeout=30)
            headers = dict(resp.headers)

            # Atualiza e avalia rate limit
            remaining = headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                try:
                    self.cota_restante = int(remaining)
                except ValueError:
                    pass

            if remaining == "0":
                reset_ts = float(headers.get("X-RateLimit-Reset", self.relogio()))
                espera = max(0.0, reset_ts - self.relogio()) + self.margem_reset
                self.dormir(espera)
                if resp.status_code in (403, 429):
                    continue

            # Backoff exponencial em respostas 5xx (1, 2, 4, 8...)
            if resp.status_code >= 500:
                if tentativa == self.tentativas - 1:
                    raise RuntimeError(
                        f"Falha após {self.tentativas} tentativas (HTTP {resp.status_code}) em: {url}"
                    )
                tempo_espera = 2**tentativa
                self.dormir(tempo_espera)
                continue

            resp.raise_for_status()
            return resp.json(), headers

        raise RuntimeError(
            f"Falha após {self.tentativas} tentativas de requisição em: {url}"
        )

    def _requisitar_com_cache(
        self, url: str, params: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, str]]:
        """Obtém dados a partir do cache se disponível; caso contrário, executa requisição HTTP."""
        if self.usar_cache:
            caminho = self._caminho_cache(url, params)
            if caminho.exists():
                with open(caminho, "r", encoding="utf-8") as f:
                    conteudo = json.load(f)
                    return conteudo["data"], conteudo.get("headers", {})

        dados, headers = self._requisitar(url, params)

        if self.usar_cache:
            caminho = self._caminho_cache(url, params)
            self._salvar_cache(caminho, dados, headers)

        return dados, headers

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        """Executa requisição GET retornando o corpo JSON (dict ou list)."""
        url_norm = self._normalizar_url(url)
        dados, _ = self._requisitar_com_cache(url_norm, params)
        return dados

    def get_paginado(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        chave_lista: str | None = None,
    ) -> list[Any]:
        """Realiza requisições paginadas seguindo o cabeçalho Link: rel='next' (per_page=100)."""
        url_atual = self._normalizar_url(url)
        params_atuais: dict[str, Any] | None = dict(params or {})
        params_atuais.setdefault("per_page", 100)
        resultados: list[Any] = []

        while url_atual:
            dados, headers = self._requisitar_com_cache(url_atual, params_atuais)

            if isinstance(dados, list):
                resultados.extend(dados)
            elif isinstance(dados, dict):
                if chave_lista and chave_lista in dados and isinstance(dados[chave_lista], list):
                    resultados.extend(dados[chave_lista])
                elif "workflow_runs" in dados and isinstance(dados["workflow_runs"], list):
                    resultados.extend(dados["workflow_runs"])
                elif "items" in dados and isinstance(dados["items"], list):
                    resultados.extend(dados["items"])
                else:
                    listas = [v for v in dados.values() if isinstance(v, list)]
                    if listas:
                        resultados.extend(listas[0])
                    else:
                        resultados.append(dados)

            url_proxima = extrair_proxima_pagina(headers.get("Link") or headers.get("link"))
            url_atual = url_proxima if url_proxima else ""
            params_atuais = None  # Parâmetros já estão codificados na URL do rel="next"

        return resultados
