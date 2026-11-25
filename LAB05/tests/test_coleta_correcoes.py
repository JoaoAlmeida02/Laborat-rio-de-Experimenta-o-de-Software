"""Testes offline (sem rede) de scripts/coleta_correcoes.py, com respostas reduzidas das APIs reais."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from coleta_correcoes import (  # noqa: E402
    CVE, CVE_2, ID_ALMA, ID_FEDORA, ID_REDHAT, ID_ROCKY, ID_SUSE, ID_UBUNTU,
    Aviso, aviso_osv, aviso_rocky, avisos_bodhi, avisos_redhat, avisos_ubuntu, consolidar,
    distribuidor_do_aviso_osv, id_rocky, ids_relacionados_osv, linha_sobrevivencia, para_data,
    pendentes_redhat, pendentes_ubuntu, unificar,
)

CORTE = date(2026, 11, 24)


def test_para_data_aceita_os_formatos_das_apis():
    assert para_data("2026-10-21T13:56:19.543268") == date(2026, 10, 21)
    assert para_data("2026-10-21T00:00:00Z") == date(2026, 10, 21)
    assert para_data("2026-10-22T00:08:23.571327+00:00") == date(2026, 10, 22)
    assert para_data("2026-10-22 16:40:54") == date(2026, 10, 22)


def test_ubuntu_avisos_e_pendentes():
    dados = {
        "notices": [{"id": "USN-8948-1", "published": "2026-10-21T13:56:19", "title": "PHP vulnerabilities"}],
        "packages": [{"name": "php8.3", "statuses": [
            {"release_codename": "noble", "status": "released"},
            {"release_codename": "upstream", "status": "needed"},   # não conta: não é release do Ubuntu
            {"release_codename": "jammy", "status": "needed"},
            {"release_codename": "focal", "status": "DNE"},
        ]}],
    }
    avisos = avisos_ubuntu(dados, CVE, "url")
    assert avisos == [Aviso(ID_UBUNTU, "USN-8948-1", date(2026, 10, 21), "PHP vulnerabilities", frozenset({CVE}), "url")]
    assert pendentes_ubuntu(dados) == 1


def test_redhat_avisos_e_pendentes():
    dados = {
        "affected_release": [
            {"product_name": "RHEL 10", "release_date": "2026-10-21T00:00:00Z", "advisory": "RHSA-2026:87070"},
            {"product_name": "RHEL 9", "release_date": "2026-11-10T00:00:00Z", "advisory": "RHSA-2026:97880"},
            {"product_name": "sem data", "advisory": "RHSA-2026:1"},
        ],
        "package_state": [{"fix_state": "Not affected"}, {"fix_state": "Affected"}, {"fix_state": "Will not fix"}],
    }
    avisos = avisos_redhat(dados, CVE, "url")
    assert [(a.aviso, a.data) for a in avisos] == [
        ("RHSA-2026:87070", date(2026, 10, 21)), ("RHSA-2026:97880", date(2026, 11, 10))]
    assert all(a.distribuidor_id == ID_REDHAT for a in avisos)
    assert pendentes_redhat(dados) == 2


def test_osv_filtra_prefixos_e_identifica_distribuidor():
    dados = {"related": ["ALSA-2026:87070", "SUSE-SU-2026:4843-1", "openSUSE-SU-2026:12219-1", "MGASA-2026-1"]}
    assert ids_relacionados_osv(dados) == ["ALSA-2026:87070", "SUSE-SU-2026:4843-1", "openSUSE-SU-2026:12219-1"]
    assert distribuidor_do_aviso_osv("ALSA-2026:A011") == ID_ALMA
    assert distribuidor_do_aviso_osv("SUSE-SU-2026:4843-1") == ID_SUSE
    assert distribuidor_do_aviso_osv("openSUSE-SU-2026:12219-1") == ID_SUSE
    assert distribuidor_do_aviso_osv("DSA-6574-1") is None


def test_aviso_osv_le_data_e_cves():
    dados = {
        "id": "ALSA-2026:87070", "published": "2026-10-21T00:00:00Z",
        "upstream": [CVE, CVE_2, "CVE-2026-91765"],
        "affected": [{"package": {"ecosystem": "AlmaLinux:10", "name": "php"}},
                     {"package": {"ecosystem": "AlmaLinux:10", "name": "php-cli"}}],
    }
    a = aviso_osv(dados, "url")
    assert (a.distribuidor_id, a.data, a.produto, a.cves) == (ID_ALMA, date(2026, 10, 21), "AlmaLinux:10", frozenset({CVE, CVE_2}))


def test_aviso_osv_que_nao_corrige_as_cves_e_ignorado():
    dados = {"id": "ALSA-2026:1", "published": "2026-10-21T00:00:00Z", "upstream": ["CVE-2026-1"]}
    assert aviso_osv(dados, "url") is None


def test_rocky_usa_o_numero_do_rhsa():
    assert id_rocky("RHSA-2026:87070") == "RLSA-2026:87070"
    dados = {"advisory": {
        "name": "RLSA-2026:87070", "published_at": "2026-10-22T00:08:23+00:00",
        "cves": [{"cve": CVE}, {"cve": "CVE-2026-1"}],
        "affected_products": [{"name": "Rocky Linux 10 x86_64"}, {"name": "Rocky Linux 10 aarch64"}],
    }}
    a = aviso_rocky(dados, "url")
    assert (a.distribuidor_id, a.data, a.produto, a.cves) == (ID_ROCKY, date(2026, 10, 22), "Rocky Linux 10", frozenset({CVE}))


def test_rocky_sem_as_cves_e_ignorado():
    dados = {"advisory": {"name": "RLSA-2026:102297", "published_at": "2026-11-25T00:05:01+00:00",
                          "cves": [{"cve": "CVE-2026-126714"}]}}
    assert aviso_rocky(dados, "url") is None


def test_bodhi_so_conta_php_estavel_que_cita_a_cve():
    dados = {"updates": [
        {"alias": "FEDORA-1", "title": "php-8.5.12-1.fc44", "date_stable": "2026-10-21 16:43:43",
         "release": {"name": "F44"}, "notes": f"fix {CVE}"},
        {"alias": "FEDORA-2", "title": "php-8.5.12-1.fc46", "date_stable": "2026-10-21 15:31:09",
         "release": {"name": "F46"}, "notes": "sem citar"},                    # não cita a CVE
        {"alias": "FEDORA-3", "title": "php-8.4.27-2.fc43", "date_stable": None,
         "release": {"name": "F43"}, "notes": CVE},                           # ainda em testing
        {"alias": "FEDORA-4", "title": "elfutils-0.197 php-8.5.12", "date_stable": "2026-10-21",
         "release": {"name": "ELN"}, "notes": CVE},                           # não é o pacote php
    ]}
    avisos = avisos_bodhi(dados, "url")
    assert [(a.aviso, a.distribuidor_id, a.data) for a in avisos] == [("FEDORA-1", ID_FEDORA, date(2026, 10, 21))]


def test_unificar_junta_a_mesma_usn_das_duas_cves():
    a1 = Aviso(ID_UBUNTU, "USN-1", date(2026, 10, 21), "PHP", frozenset({CVE}), "u1")
    a2 = Aviso(ID_UBUNTU, "USN-1", date(2026, 10, 21), "PHP", frozenset({CVE_2}), "u2")
    assert unificar([a1, a2]) == [Aviso(ID_UBUNTU, "USN-1", date(2026, 10, 21), "PHP", frozenset({CVE, CVE_2}), "u1")]


def test_linha_sobrevivencia():
    assert linha_sobrevivencia("corrigido", date(2026, 10, 22), CORTE) == (1, 1, "sim")
    assert linha_sobrevivencia("sem_correcao_publicada", None, CORTE) == (34, 0, "sim")  # censurado
    assert linha_sobrevivencia("a_verificar", None, CORTE) == ("", "", "não")
    assert linha_sobrevivencia("corrigido_sem_data", None, CORTE) == ("", "", "não")


FONTES = [
    {"id": "2", "distribuidor": "Ubuntu", "grupo": "comercial", "forma_coleta": "api", "url_api": "api-ubuntu"},
    {"id": "3", "distribuidor": "Red Hat", "grupo": "comercial", "forma_coleta": "api", "url_api": "api-rh"},
    {"id": "7", "distribuidor": "Arch", "grupo": "comunitario", "forma_coleta": "manual", "url_api": ""},
    {"id": "15", "distribuidor": "Plesk", "grupo": "hospedagem", "forma_coleta": "manual", "url_api": ""},
    {"id": "18", "distribuidor": "NVD", "grupo": "referencia", "forma_coleta": "api", "url_api": ""},
]
MANUAL = {7: {
    "situacao": "corrigido", "data_primeira_correcao": "2026-10-21", "data_ultima_correcao": "2026-10-21",
    "precisao_data": "exata", "avisos": "ASA-202610-1;ASA-202610-2", "pendentes": "",
    "url_evidencia": "https://security.archlinux.org/CVE-2026-109618", "observacao": "",
}}


def test_consolidar_api_manual_censura_e_referencia():
    avisos = [
        Aviso(ID_UBUNTU, "USN-1", date(2026, 10, 21), "PHP", frozenset({CVE, CVE_2}), "u"),
        Aviso(ID_REDHAT, "RHSA-1", date(2026, 10, 21), "RHEL 10", frozenset({CVE}), "r"),
        Aviso(ID_REDHAT, "RHSA-2", date(2026, 11, 11), "RHEL 9", frozenset({CVE}), "r"),
        Aviso(ID_REDHAT, "RHSA-3", date(2026, 10, 23), "RHEL 8", frozenset({CVE_2}), "r"),
    ]
    linhas, alertas = consolidar(FONTES, avisos, {ID_UBUNTU: 0}, MANUAL, CORTE)
    por_nome = {l["distribuidor"]: l for l in linhas}

    assert "NVD" not in por_nome  # referência não entra
    ubuntu = por_nome["Ubuntu"]
    assert (ubuntu["situacao"], ubuntu["tempo_dias"], ubuntu["evento"], ubuntu["pendentes"]) == ("corrigido", 0, 1, 0)
    assert ubuntu["data_primeira_correcao_109619"] == date(2026, 10, 21)

    rh = por_nome["Red Hat"]
    assert (rh["data_primeira_correcao"], rh["data_ultima_correcao"]) == (date(2026, 10, 21), date(2026, 11, 11))
    assert (rh["dias_ate_ultima_correcao"], rh["n_avisos"], rh["avisos"]) == (21, 2, "RHSA-1;RHSA-2")
    assert rh["data_primeira_correcao_109619"] == date(2026, 10, 23)

    arch = por_nome["Arch"]
    assert (arch["forma_coleta"], arch["tempo_dias"], arch["evento"], arch["n_avisos"]) == ("manual", 0, 1, 2)

    plesk = por_nome["Plesk"]
    assert (plesk["situacao"], plesk["incluir_analise"]) == ("a_verificar", "não")
    assert any("Plesk" in a for a in alertas)


def test_consolidar_api_sem_aviso_vira_censurado():
    linhas, _ = consolidar(FONTES[:1], [], {}, {}, CORTE)
    assert (linhas[0]["situacao"], linhas[0]["tempo_dias"], linhas[0]["evento"]) == ("sem_correcao_publicada", 34, 0)


def test_consolidar_alerta_data_fora_do_intervalo():
    avisos = [Aviso(ID_UBUNTU, "USN-0", date(2026, 10, 20), "PHP", frozenset({CVE}), "u")]
    _, alertas = consolidar(FONTES[:1], avisos, {}, {}, CORTE)
    assert any("anterior ao T0" in a for a in alertas)
