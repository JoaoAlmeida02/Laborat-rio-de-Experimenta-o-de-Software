/**
 * Script de carga k6 do experimento LAB05 (PUC Minas).
 *
 * Exercita 3 endpoints do WordPress local:
 *   1) home          -> GET  /
 *   2) rest_posts    -> GET  /wp-json/wp/v2/posts?per_page=10
 *   3) sessao_upload -> POST /?lab05_upload=1 (sessão + upload multipart benigno de 10 KB)
 *
 * Ética: nenhum exploit é enviado. O upload contém apenas 10 KB de bytes aleatórios
 * descartados imediatamente pelo mu-plugin local.
 *
 * Fases:
 *   - aquecimento (padrão 30s): descartado das métricas exportadas
 *   - medicao     (padrão 60s): métricas consolidadas em geral e por endpoint
 *
 * Variáveis de ambiente suportadas:
 *   BASE_URL     (padrão: http://localhost:8080)
 *   VUS          (padrão: 10)
 *   WARMUP_SEC   (padrão: 30)
 *   MEDICAO_SEC  (padrão: 60)
 *   SLEEP_MS     (padrão: 50)
 *   SUMMARY_PATH (opcional: caminho do arquivo JSON de saída)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import crypto from 'k6/crypto';
import exec from 'k6/execution';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8080').replace(/\/+$/, '');
const VUS = Math.max(1, parseInt(__ENV.VUS || '10', 10));
const WARMUP_SEC = Math.max(0, parseInt(__ENV.WARMUP_SEC || '30', 10));
const MEDICAO_SEC = Math.max(1, parseInt(__ENV.MEDICAO_SEC || '60', 10));
const SLEEP_MS = Math.max(0, parseInt(__ENV.SLEEP_MS || '50', 10));
const SUMMARY_PATH = __ENV.SUMMARY_PATH || '';

// Payload benigno de 10 KB (10240 bytes aleatórios) pré-alocado no init
const TAMANHO_UPLOAD_BYTES = 10240;
const PAYLOAD_10KB = crypto.randomBytes(TAMANHO_UPLOAD_BYTES);

// Métricas exclusivas da fase de medição (geral e por endpoint)
const METRICAS = {
  geral: {
    duracao: new Trend('medicao_duracao_geral', true),
    reqs: new Counter('medicao_reqs_geral'),
    erro: new Rate('medicao_erro_geral'),
  },
  home: {
    duracao: new Trend('medicao_duracao_home', true),
    reqs: new Counter('medicao_reqs_home'),
    erro: new Rate('medicao_erro_home'),
  },
  rest_posts: {
    duracao: new Trend('medicao_duracao_rest_posts', true),
    reqs: new Counter('medicao_reqs_rest_posts'),
    erro: new Rate('medicao_erro_rest_posts'),
  },
  sessao_upload: {
    duracao: new Trend('medicao_duracao_sessao_upload', true),
    reqs: new Counter('medicao_reqs_sessao_upload'),
    erro: new Rate('medicao_erro_sessao_upload'),
  },
};

const ENDPOINTS = ['home', 'rest_posts', 'sessao_upload'];

// Monta cenários separando aquecimento (descartado) e medição (analisada)
function montarCenarios() {
  const cenarios = {};
  if (WARMUP_SEC > 0) {
    cenarios.aquecimento = {
      executor: 'constant-vus',
      vus: VUS,
      duration: `${WARMUP_SEC}s`,
      startTime: '0s',
      gracefulStop: '5s',
      tags: { fase: 'aquecimento' },
    };
  }
  cenarios.medicao = {
    executor: 'constant-vus',
    vus: VUS,
    duration: `${MEDICAO_SEC}s`,
    startTime: `${WARMUP_SEC}s`,
    gracefulStop: '5s',
    tags: { fase: 'medicao' },
  };
  return cenarios;
}

export const options = {
  scenarios: montarCenarios(),
  summaryTrendStats: ['avg', 'min', 'med', 'p(50)', 'p(90)', 'p(95)', 'p(99)', 'max'],
  noConnectionReuse: false,
  userAgent: 'LAB05-k6-Benchmark/1.0',
};

function registrarMedicao(endpoint, duracaoMs, sucesso) {
  if (exec.scenario.name !== 'medicao') {
    return;
  }
  const falha = sucesso ? 0 : 1;

  METRICAS.geral.duracao.add(duracaoMs);
  METRICAS.geral.reqs.add(1);
  METRICAS.geral.erro.add(falha);

  METRICAS[endpoint].duracao.add(duracaoMs);
  METRICAS[endpoint].reqs.add(1);
  METRICAS[endpoint].erro.add(falha);
}

export default function () {
  const fase = exec.scenario.name;

  // 1) Página inicial "/"
  {
    const res = http.get(`${BASE_URL}/`, {
      tags: { endpoint: 'home', fase },
      timeout: '15s',
    });
    const ok = check(res, {
      'home: status 200': (r) => r.status === 200,
      'home: corpo HTML não vazio': (r) => typeof r.body === 'string' && r.body.length > 200,
    });
    registrarMedicao('home', res.timings.duration, ok);
  }

  // 2) API REST do WordPress "/wp-json/wp/v2/posts"
  {
    const res = http.get(`${BASE_URL}/wp-json/wp/v2/posts?per_page=10`, {
      tags: { endpoint: 'rest_posts', fase },
      headers: { Accept: 'application/json' },
      timeout: '15s',
    });
    const ok = check(res, {
      'rest_posts: status 200': (r) => r.status === 200,
      'rest_posts: lista JSON válida': (r) => {
        if (r.status !== 200) return false;
        try {
          const dados = r.json();
          return Array.isArray(dados) && dados.length > 0;
        } catch (_) {
          return false;
        }
      },
    });
    registrarMedicao('rest_posts', res.timings.duration, ok);
  }

  // 3) Endpoint com sessão e upload multipart benigno (10 KB descartados)
  {
    const formulario = {
      // Campo padrão e inofensivo do PHP para exercitar session.upload_progress
      PHP_SESSION_UPLOAD_PROGRESS: `lab05_vu_${exec.vu.idInTest}`,
      arquivo: http.file(PAYLOAD_10KB, 'amostra_benigna_10kb.bin', 'application/octet-stream'),
    };
    const res = http.post(`${BASE_URL}/?lab05_upload=1`, formulario, {
      tags: { endpoint: 'sessao_upload', fase },
      timeout: '15s',
    });
    const ok = check(res, {
      'sessao_upload: status 200': (r) => r.status === 200,
      'sessao_upload: resposta ok e 10 KB': (r) => {
        if (r.status !== 200) return false;
        try {
          const dados = r.json();
          return dados && dados.ok === true && dados.bytes_recebidos === TAMANHO_UPLOAD_BYTES;
        } catch (_) {
          return false;
        }
      },
    });
    registrarMedicao('sessao_upload', res.timings.duration, ok);
  }

  if (SLEEP_MS > 0) {
    sleep(SLEEP_MS / 1000);
  }
}

function extrairBlocoMetrica(data, chave) {
  const mDur = data.metrics[`medicao_duracao_${chave}`];
  const mReqs = data.metrics[`medicao_reqs_${chave}`];
  const mErro = data.metrics[`medicao_erro_${chave}`];

  const valoresDur = (mDur && mDur.values) || {};
  const totalReqs = (mReqs && mReqs.values && mReqs.values.count) || 0;
  const taxaErro = (mErro && mErro.values && mErro.values.rate) || 0;

  const p50 = valoresDur['p(50)'] !== undefined ? valoresDur['p(50)'] : (valoresDur.med || 0);
  const p95 = valoresDur['p(95)'] || 0;
  const p99 = valoresDur['p(99)'] || 0;
  const media = valoresDur.avg || 0;

  return {
    requisicoes: totalReqs,
    rps: Number((totalReqs / MEDICAO_SEC).toFixed(4)),
    p50_ms: Number(p50.toFixed(3)),
    p95_ms: Number(p95.toFixed(3)),
    p99_ms: Number(p99.toFixed(3)),
    media_ms: Number(media.toFixed(3)),
    taxa_erro: Number(taxaErro.toFixed(6)),
    taxa_erro_pct: Number((taxaErro * 100).toFixed(4)),
  };
}

export function handleSummary(data) {
  const resumoMedicao = {
    geral: extrairBlocoMetrica(data, 'geral'),
    endpoints: {},
  };

  for (const ep of ENDPOINTS) {
    resumoMedicao.endpoints[ep] = extrairBlocoMetrica(data, ep);
  }

  const saidaJson = {
    config: {
      base_url: BASE_URL,
      vus: VUS,
      warmup_sec: WARMUP_SEC,
      medicao_sec: MEDICAO_SEC,
      sleep_ms: SLEEP_MS,
      tamanho_upload_bytes: TAMANHO_UPLOAD_BYTES,
    },
    medicao: resumoMedicao,
    metricas_brutas_k6: data.metrics,
  };

  const linhas = [
    '=== Resumo LAB05 (somente fase de medição) ===',
    `Config: VUs=${VUS} | aquecimento=${WARMUP_SEC}s | medição=${MEDICAO_SEC}s | alvo=${BASE_URL}`,
    `  geral         -> rps=${resumoMedicao.geral.rps} | p50=${resumoMedicao.geral.p50_ms}ms | p95=${resumoMedicao.geral.p95_ms}ms | p99=${resumoMedicao.geral.p99_ms}ms | erro=${resumoMedicao.geral.taxa_erro_pct}%`,
  ];
  for (const ep of ENDPOINTS) {
    const b = resumoMedicao.endpoints[ep];
    linhas.push(
      `  ${ep.padEnd(13)} -> rps=${b.rps} | p50=${b.p50_ms}ms | p95=${b.p95_ms}ms | p99=${b.p99_ms}ms | erro=${b.taxa_erro_pct}%`
    );
  }

  const retorno = {
    stdout: `${linhas.join('\n')}\n`,
  };
  if (SUMMARY_PATH) {
    retorno[SUMMARY_PATH] = JSON.stringify(saidaJson, null, 2);
  }
  return retorno;
}
