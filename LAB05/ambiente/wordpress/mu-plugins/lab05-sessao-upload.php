<?php
/**
 * Plugin Name: LAB05 - Endpoint Benigno de Sessão e Upload
 * Description: Endpoint inofensivo para benchmark do caminho de sessão + upload multipart no PHP (RQ1/RQ2).
 *              Recebe um arquivo pequeno (ex.: 10 KB), contabiliza o tamanho e descarta imediatamente.
 *              NENHUM conteúdo enviado é salvo, interpretado ou executado.
 */

if (!defined('ABSPATH')) {
    exit;
}

add_action('init', function () {
    $caminho = parse_url($_SERVER['REQUEST_URI'] ?? '', PHP_URL_PATH);
    $eh_rota_upload = (isset($_GET['lab05_upload']) && $_GET['lab05_upload'] === '1')
        || $caminho === '/lab05-sessao-upload';

    if (!$eh_rota_upload) {
        return;
    }

    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate');

    $upload_progress = ini_get('session.upload_progress.enabled');
    $metodo = $_SERVER['REQUEST_METHOD'] ?? 'GET';

    // GET leve para verificação de prontidão e conferência dos parâmetros efetivos
    if ($metodo === 'GET') {
        http_response_code(200);
        echo wp_json_encode([
            'ok' => true,
            'endpoint' => 'lab05_sessao_upload',
            'php_version' => PHP_VERSION,
            'session_upload_progress_enabled' => (string) $upload_progress,
        ]);
        exit;
    }

    if ($metodo !== 'POST') {
        http_response_code(405);
        echo wp_json_encode(['ok' => false, 'erro' => 'metodo_nao_permitido']);
        exit;
    }

    // Inicia sessão PHP padrão para exercitar o fluxo de sessão + upload
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }
    $_SESSION['lab05_contador'] = (int) ($_SESSION['lab05_contador'] ?? 0) + 1;
    $contador = $_SESSION['lab05_contador'];

    // Valida e descarta o upload benigno (limite rígido de 100 KB)
    $bytes_recebidos = 0;
    if (isset($_FILES['arquivo']) && is_array($_FILES['arquivo'])) {
        $erro_upload = (int) ($_FILES['arquivo']['error'] ?? UPLOAD_ERR_NO_FILE);
        $tamanho = (int) ($_FILES['arquivo']['size'] ?? 0);
        $arquivo_tmp = (string) ($_FILES['arquivo']['tmp_name'] ?? '');

        if ($arquivo_tmp !== '' && is_uploaded_file($arquivo_tmp)) {
            @unlink($arquivo_tmp);
        }

        if ($erro_upload !== UPLOAD_ERR_OK) {
            session_write_close();
            http_response_code(400);
            echo wp_json_encode([
                'ok' => false,
                'erro' => 'falha_no_upload',
                'codigo_upload' => $erro_upload,
            ]);
            exit;
        }

        if ($tamanho > 102400) {
            session_write_close();
            http_response_code(413);
            echo wp_json_encode(['ok' => false, 'erro' => 'arquivo_maior_que_100kb']);
            exit;
        }

        $bytes_recebidos = $tamanho;
    } else {
        session_write_close();
        http_response_code(400);
        echo wp_json_encode(['ok' => false, 'erro' => 'campo_arquivo_ausente']);
        exit;
    }

    session_write_close();

    http_response_code(200);
    echo wp_json_encode([
        'ok' => true,
        'bytes_recebidos' => $bytes_recebidos,
        'contador_sessao' => $contador,
        'php_version' => PHP_VERSION,
        'session_upload_progress_enabled' => (string) $upload_progress,
    ]);
    exit;
}, 1);
