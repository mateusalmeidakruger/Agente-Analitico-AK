"""Status da base do dia: laudo do validador e veredito do auditor-base."""
import json
from datetime import date

import numpy as np


def _ultimo_json(pasta):
    arquivos = sorted(pasta.glob("*.json")) if pasta.exists() else []
    if not arquivos:
        return None, None
    p = arquivos[-1]
    try:
        return p, json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return p, None


def status(cfg, hoje=None):
    hoje = (hoje or date.today()).isoformat()
    p_laudo, laudo = _ultimo_json(cfg.caminho_fluxo(cfg.bruto["laudos"]))
    p_aud, aud = _ultimo_json(cfg.caminho_fluxo(cfg.bruto["auditorias"]))

    laudo_data = (laudo or {}).get("data_referencia")
    laudo_status = (laudo or {}).get("status")
    aud_data = ((aud or {}).get("registrado_em") or "")[:10]
    aud_veredito = (aud or {}).get("veredito")

    # o auditor só conta se for do mesmo dia do laudo
    segurou = aud_data == laudo_data and aud_veredito == "SEGURAR"
    liberada = laudo_data == hoje and laudo_status == "APROVADO" and not segurou

    if liberada:
        aviso = None
    elif laudo_data != hoje:
        aviso = f"A base de hoje ainda não foi validada; os números são da base de {laudo_data}."
    elif segurou:
        aviso = "O auditor-base mandou SEGURAR a base de hoje; trate os números com cuidado."
    else:
        aviso = f"O laudo de hoje está {laudo_status}; trate os números com cuidado."

    return {
        "liberada": liberada,
        "aviso": aviso,
        "laudo": {"arquivo": p_laudo.name if p_laudo else None, "data": laudo_data, "status": laudo_status},
        "auditoria": {"arquivo": p_aud.name if p_aud else None, "data": aud_data or None, "veredito": aud_veredito},
    }


def dias_uteis_entre(cfg, inicio, fim):
    """Dias úteis depois de `inicio` até `fim` (inclusive), sem fins de semana e feriados do config."""
    um_dia = np.timedelta64(1, "D")
    return int(np.busday_count(
        np.datetime64(inicio, "D") + um_dia, np.datetime64(fim, "D") + um_dia,
        holidays=cfg.feriados,
    ))
