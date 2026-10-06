import re

_VERSAO = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?(?:[-+]?([0-9A-Za-z][0-9A-Za-z.-]*))?$")


def parse_versao(tag):
    m = _VERSAO.search(tag or "")
    if not m:
        return None
    major, minor, patch, pre = m.groups()
    return int(major), int(minor), int(patch or 0), pre


def tipo_mudanca(tag_anterior, tag_nova):
    a, b = parse_versao(tag_anterior), parse_versao(tag_nova)
    if a is None or b is None:
        return None
    if b[0] != a[0]:
        return "major"
    if b[1] != a[1]:
        return "minor"
    if b[2] != a[2]:
        return "patch"
    if b[3] != a[3]:
        return "pre"
    return "igual"


def somente_patch(tag_anterior, tag_nova):
    return tipo_mudanca(tag_anterior, tag_nova) == "patch"
